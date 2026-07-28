from __future__ import annotations

import hashlib
import os
import re
import stat as stat_module
import threading
import time
import traceback
import xml.etree.ElementTree as ET
from copy import copy
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app import schemas
from app.chain.media import MediaChain
from app.chain.tmdb import TmdbChain
from app.core.config import settings
from app.core.metainfo import MetaInfoPath
from app.db.transferhistory_oper import TransferHistoryOper
from app.helper.nfo import NfoReader
from app.log import logger
from app.plugins import _PluginBase
from app.schemas import MediaType, NotificationType

try:
    import fcntl
except ImportError:
    fcntl = None

try:
    from app.chain.media import scraping_lock
except ImportError:
    # MoviePilot 2.14.x exposes this lock. The fallback keeps older releases usable.
    scraping_lock = threading.Lock()


@dataclass
class ScrapeTarget:
    path: Path
    mtype: MediaType
    target_type: str
    source_root: Path
    forced_type: Optional[MediaType] = None
    tmdbid: Optional[int] = None
    doubanid: Optional[str] = None
    file_count: int = 0
    total_size: int = 0
    max_mtime_ns: int = 0
    signature: int = 0
    media_files: List[Path] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.target_type}|{self.mtype.value}|{self.path}"

    @property
    def fingerprint(self) -> List[Any]:
        return [
            self.file_count,
            self.total_size,
            self.max_mtime_ns,
            f"{self.signature:016x}",
            self.tmdbid,
            self.doubanid,
        ]

    def include_file(
        self,
        file_path: Path,
        stat_result: os.stat_result,
        tmdbid: Optional[int],
        doubanid: Optional[str],
    ) -> None:
        mtime_ns = int(
            getattr(stat_result, "st_mtime_ns", stat_result.st_mtime * 1_000_000_000)
        )
        self.file_count += 1
        self.total_size += int(stat_result.st_size)
        self.max_mtime_ns = max(self.max_mtime_ns, mtime_ns)
        token = hashlib.blake2b(
            f"{file_path}\0{stat_result.st_size}\0{mtime_ns}".encode("utf-8"),
            digest_size=8,
        )
        self.signature ^= int.from_bytes(token.digest(), byteorder="big")
        self.media_files.append(file_path)
        if not self.tmdbid and tmdbid:
            self.tmdbid = tmdbid
        if not self.doubanid and doubanid:
            self.doubanid = doubanid


@dataclass
class ScrapeOutcome:
    status: str
    scraped_files: int = 0
    unrecognized_files: int = 0
    failed_files: int = 0
    detail: str = ""
    item_details: List[Dict[str, Any]] = field(default_factory=list)
    duration_seconds: float = 0


class _NonOverwritingOption:
    """Policy view that preserves skip choices but downgrades overwrite to missing-only."""

    def __init__(self, option: Any):
        self._option = option

    @property
    def is_skip(self) -> bool:
        return self._option.is_skip

    @property
    def is_overwrite(self) -> bool:
        return False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._option, name)


class _NonOverwritingPolicies:
    def __init__(self, policies: Any):
        self._policies = policies

    def option(self, *args: Any, **kwargs: Any) -> _NonOverwritingOption:
        return _NonOverwritingOption(self._policies.option(*args, **kwargs))


class LibraryScraperFix(_PluginBase):
    plugin_name = "媒体库刮削(魔改版)"
    plugin_desc = "安全增量刮削媒体库，支持 NFO 空白概要与通用标题修复。"
    plugin_icon = (
        "https://raw.githubusercontent.com/Wning-ady/"
        "MoviePilot-Plugins-repair-shop/main/icons/Ombi_A.png"
    )
    plugin_version = "1.1.5"
    plugin_author = "jxxghp,Wning-ady"
    author_url = "https://github.com/Wning-ady/MoviePilot-Plugins-repair-shop"
    plugin_config_prefix = "libraryscraperfix_"
    plugin_order = 7
    auth_level = 1
    user_level = 1

    _target_dir = "dir"
    _target_file = "file"
    _state_key = "scan_state_v1"
    _nfo_repair_state_key = "nfo_repair_state_v1"
    _last_run_key = "last_run"
    _history_key = "run_history"
    _detail_limit = 200
    _run_lock = threading.Lock()

    _scheduler: Optional[BackgroundScheduler] = None
    _enabled = False
    _onlyonce = False
    _cron = "0 3 * * *"
    _mode = ""
    _scraper_paths = ""
    _exclude_paths = ""
    _dry_run = True
    _incremental = True
    _force_full_scan = False
    _max_targets = 0
    _interval_seconds = 0.0
    _retry_count = 1
    _full_scan_days = 7
    _notify = True
    _repair_nfo_enabled = False
    _nfo_audit_days = 30

    def init_plugin(self, config: dict = None):
        self.stop_service()
        self._cancel_event = threading.Event()
        self._running_status: Dict[str, Any] = {}

        config = config or {}
        self._enabled = bool(config.get("enabled", False))
        self._onlyonce = bool(config.get("onlyonce", False))
        self._cron = str(config.get("cron") or "0 3 * * *").strip()
        self._mode = str(config.get("mode") or "").strip()
        if self._mode not in ("", "force_all"):
            logger.warning(f"媒体库刮削(魔改版)覆盖模式无效，已按不覆盖处理：{self._mode}")
            self._mode = ""
        self._scraper_paths = str(config.get("scraper_paths") or "")
        self._exclude_paths = str(config.get("exclude_paths") or "")
        self._dry_run = bool(config.get("dry_run", True))
        self._incremental = bool(config.get("incremental", True))
        self._force_full_scan = bool(config.get("force_full_scan", False))
        self._max_targets = self._bounded_int(config.get("max_targets"), 0, 0, 100000)
        self._interval_seconds = self._bounded_float(
            config.get("interval_seconds"), 0.0, 0.0, 30.0
        )
        self._retry_count = self._bounded_int(config.get("retry_count"), 1, 0, 3)
        self._full_scan_days = self._bounded_int(
            config.get("full_scan_days"), 7, 0, 365
        )
        self._notify = bool(config.get("notify", True))
        self._repair_nfo_enabled = bool(config.get("repair_nfo_fields", False))
        self._nfo_audit_days = self._bounded_int(
            config.get("nfo_audit_days"), 30, 0, 365
        )

        clear_cache = bool(config.get("clear_cache", False))
        if clear_cache:
            try:
                self.del_data(self._state_key)
                self.del_data(self._nfo_repair_state_key)
                logger.info("媒体库刮削(魔改版)增量缓存已清空")
            except Exception as err:
                logger.error(f"清空媒体库刮削增量缓存失败：{err}")

        if self._onlyonce or clear_cache:
            run_once = self._onlyonce
            self._onlyonce = False
            self.update_config(
                self._current_config(
                    force_full_scan=self._force_full_scan, clear_cache=False
                )
            )
            if run_once:
                self._scheduler = BackgroundScheduler(timezone=settings.TZ)
                self._scheduler.add_job(
                    func=self.run,
                    trigger="date",
                    run_date=datetime.now(tz=pytz.timezone(settings.TZ))
                    + timedelta(seconds=3),
                    name="媒体库刮削(魔改版)",
                    max_instances=1,
                    coalesce=True,
                )
                self._scheduler.start()

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        return []

    def get_api(self) -> List[Dict[str, Any]]:
        return []

    def get_service(self) -> List[Dict[str, Any]]:
        if not self._enabled:
            return []
        try:
            trigger = CronTrigger.from_crontab(self._cron)
        except (TypeError, ValueError) as err:
            message = f"媒体库刮削(魔改版) Cron 无效，不会注册定时任务：{self._cron} ({err})"
            logger.error(message)
            try:
                self.systemmessage.put(message)
            except Exception:
                pass
            return []
        return [
            {
                "id": "LibraryScraperFix",
                "name": "媒体库刮削(魔改版)",
                "trigger": trigger,
                "func": self.run,
                "kwargs": {},
            }
        ]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        sections = [
            self._form_section(
                "1. 运行与通知",
                "控制定时任务、单次执行和结果通知。",
                [
                    {
                        "component": "VRow",
                        "content": [
                            self._switch(
                                "enabled", "启用定时任务", "按执行周期自动运行。"
                            ),
                            self._switch(
                                "onlyonce", "保存后运行一次", "触发后自动复位。"
                            ),
                            self._switch(
                                "notify", "发送运行摘要", "完成后发送数量、耗时和问题统计。"
                            ),
                        ],
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VCronField",
                                        "props": {
                                            "model": "cron",
                                            "label": "执行周期",
                                            "placeholder": "0 3 * * *",
                                            "hint": "5 位 Cron，默认每天 03:00。",
                                            "persistentHint": True,
                                        },
                                    }
                                ],
                            }
                        ],
                    },
                ],
            ),
            self._form_section(
                "2. 扫描范围",
                "明确指定容器内媒体库路径和永久排除目录。",
                [
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "VTextarea",
                                        "props": {
                                            "model": "scraper_paths",
                                            "label": "刮削路径",
                                            "rows": 6,
                                            "placeholder": "/media/movies #电影\n/media/tv #电视剧",
                                            "hint": "每行一个绝对路径；类型明确时可追加 #电影 或 #电视剧。",
                                            "persistentHint": True,
                                        },
                                    }
                                ],
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {
                                        "component": "VTextarea",
                                        "props": {
                                            "model": "exclude_paths",
                                            "label": "排除路径",
                                            "rows": 3,
                                            "placeholder": "/media/private",
                                            "hint": "该路径及所有子目录不会进入扫描或回退刮削。",
                                            "persistentHint": True,
                                        },
                                    }
                                ],
                            },
                        ],
                    }
                ],
            ),
            self._form_section(
                "3. 刮削与增量策略",
                "决定本轮是否写入、处理多少目标以及何时重新复核。",
                [
                    {
                        "component": "VRow",
                        "content": [
                            self._switch(
                                "dry_run", "预演模式", "扫描和识别，不写 NFO 或图片。"
                            ),
                            self._switch(
                                "incremental", "启用目标缓存", "跳过近期成功且文件未变的目标。"
                            ),
                        ],
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 6},
                                "content": [
                                    {
                                        "component": "VSelect",
                                        "props": {
                                            "model": "mode",
                                            "label": "元数据写入策略",
                                            "items": [
                                                {
                                                    "title": "仅补齐缺失元数据（推荐）",
                                                    "value": "",
                                                },
                                                {
                                                    "title": "覆盖未被全局禁用的元数据",
                                                    "value": "force_all",
                                                },
                                            ],
                                            "hint": "全库长期使用建议仅补齐缺失项。",
                                            "persistentHint": True,
                                        },
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "component": "VRow",
                        "content": [
                            self._number_field(
                                "max_targets",
                                "单次最多处理目标",
                                0,
                                100000,
                                hint="0 表示不限量；延后目标下轮继续。",
                            ),
                            self._number_field(
                                "interval_seconds",
                                "目标间隔（秒）",
                                0,
                                30,
                                step=0.1,
                                hint="降低刮削端和网络压力。",
                            ),
                            self._number_field(
                                "retry_count",
                                "异常重试次数",
                                0,
                                3,
                                hint="单个目标异常后的额外尝试次数。",
                            ),
                            self._number_field(
                                "full_scan_days",
                                "目标完整复核（天）",
                                0,
                                365,
                                hint="0 表示成功目标永不按时间重新刮削。",
                            ),
                        ],
                    },
                ],
            ),
            self._form_section(
                "4. NFO 字段修复",
                "独立检查电视剧单集 NFO，与目标刮削缓存分开统计。",
                [
                    {
                        "component": "VAlert",
                        "props": {
                            "type": "info",
                            "variant": "tonal",
                            "text": "只补空白 plot/outline，只替换“第 N 集”等通用标题；不改正常标题、ID、年份、文件名或图片。",
                        },
                    },
                    {
                        "component": "VRow",
                        "content": [
                            self._switch(
                                "repair_nfo_fields",
                                "修复空白概要和通用标题",
                                "建议先对小目录预演。",
                            ),
                            self._number_field(
                                "nfo_audit_days",
                                "NFO 完整复核（天）",
                                0,
                                365,
                                hint="0 表示仅在 NFO 文件状态变化后重新检查。",
                            ),
                        ],
                    },
                ],
            ),
            self._form_section(
                "5. 一次性维护",
                "这些操作会增加下一轮处理量，日常运行保持关闭。",
                [
                    {
                        "component": "VRow",
                        "content": [
                            self._switch(
                                "force_full_scan",
                                "下次忽略目标缓存",
                                "仅下一轮强制处理，保存后自动复位。",
                            ),
                            self._switch(
                                "clear_cache",
                                "清空全部增量缓存",
                                "删除目标与 NFO 检查记录，下轮重建。",
                            ),
                        ],
                    },
                ],
            ),
        ]
        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VExpansionPanels",
                        "props": {
                            "variant": "accordion",
                            "multiple": True,
                            "modelValue": [0, 1],
                        },
                        "content": sections,
                    }
                ],
            }
        ], self._default_config()

    def get_page(self) -> List[dict]:
        running_status = getattr(self, "_running_status", {})
        if running_status:
            status = running_status
            current = int(status.get("current", 0) or 0)
            total = int(status.get("total", 0) or 0)
            progress = round(current / total * 100, 1) if total else 0
            return [
                {
                    "component": "VAlert",
                    "props": {
                        "type": "info",
                        "variant": "tonal",
                        "title": f"运行中：{status.get('stage', '处理中')}",
                        "text": f"当前进度 {current} / {total}",
                    },
                },
                {
                    "component": "VProgressLinear",
                    "props": {
                        "modelValue": progress,
                        "indeterminate": not total,
                        "height": 8,
                        "rounded": True,
                        "color": "primary",
                    },
                },
            ]

        try:
            last_run = self.get_data(self._last_run_key) or {}
        except Exception as err:
            logger.error(f"读取媒体库刮削运行摘要失败：{err}")
            last_run = {}
        if not last_run:
            return [
                {
                    "component": "VAlert",
                    "props": {
                        "type": "info",
                        "variant": "tonal",
                        "title": "暂无运行记录",
                        "text": "下一次运行后将显示结果、缓存命中、待处理原因和耗时。",
                    },
                }
            ]

        page = [self._status_alert(last_run)]
        issues = self._issue_items(last_run)
        if issues:
            page.append(self._issues_panel(issues))
        page.extend(self._overview_components(last_run))

        details = self._target_detail_items(last_run)
        if details:
            slow_panel = self._slow_targets_panel(details)
            if slow_panel:
                page.append(slow_panel)
            page.append(self._details_panel(details))
        return page

    def run(self, progress_callback=None):
        if not self._run_lock.acquire(blocking=False):
            logger.warning("媒体库刮削(魔改版)已有任务运行，本次触发已跳过")
            return False, "已有任务运行"

        lock_acquired, lock_fd = self._acquire_run_file_lock()
        if not lock_acquired:
            self._run_lock.release()
            logger.warning("媒体库刮削(魔改版)已有跨重载任务运行，本次触发已跳过")
            return False, "已有跨重载任务运行"

        cancel_event = self._cancel_event
        started = time.monotonic()
        scan_finished = started
        process_started = started
        started_at = self._now()
        summary = self._new_summary(started_at)
        scan_state = self._load_scan_state()
        self._nfo_repair_state = self._load_nfo_repair_state()
        self._tmdb_episode_cache: Dict[Tuple[int, int], List[Any]] = {}
        self._active_summary = summary
        try:
            if self._force_full_scan:
                self.update_config(
                    self._current_config(force_full_scan=False, clear_cache=False)
                )
            self._running_status = {"stage": "扫描媒体文件", "current": 0, "total": 0}
            self._progress(progress_callback, 0, "开始扫描媒体文件", summary)
            exclusions = self._parse_exclusions(summary)
            targets = self._discover_targets(exclusions, summary, cancel_event, progress_callback)
            scan_finished = time.monotonic()
            summary["scan_seconds"] = round(scan_finished - started, 2)
            if cancel_event.is_set():
                summary["cancelled"] = True
                return False, "任务已取消"

            self._prune_scan_state(scan_state, targets, summary)
            ordered_targets = sorted(
                targets.values(),
                key=lambda item: self._candidate_sort_key(item, scan_state),
            )
            candidates = []
            for target in ordered_targets:
                scraper_cached = self._should_skip_target(target, scan_state)
                nfo_due = self._nfo_repair_due(target) if scraper_cached else False
                if scraper_cached and not nfo_due:
                    summary["unchanged"] += 1
                else:
                    candidates.append(target)
                    reason = self._candidate_reason(
                        target, scan_state, scraper_cached, nfo_due
                    )
                    summary[f"eligible_{reason}"] += 1
            summary["eligible"] = len(candidates)

            if self._max_targets and len(candidates) > self._max_targets:
                summary["deferred"] = len(candidates) - self._max_targets
                for target in candidates[self._max_targets :]:
                    self._record_target_detail(
                        summary,
                        target,
                        ScrapeOutcome(status="deferred", detail="超过单次处理目标上限"),
                    )
                candidates = candidates[: self._max_targets]

            total = len(candidates)
            process_started = time.monotonic()
            self._running_status = {"stage": "处理刮削目标", "current": 0, "total": total}
            self._progress(progress_callback, 30, f"发现 {total} 个待处理目标", summary)

            for index, target in enumerate(candidates, start=1):
                if cancel_event.is_set():
                    summary["cancelled"] = True
                    break

                self._running_status.update(
                    {"stage": str(target.path), "current": index, "total": total}
                )
                target_started = time.monotonic()
                if self._dry_run:
                    outcome = ScrapeOutcome(status="dry_run")
                else:
                    outcome = self._run_target_with_retry(target, exclusions, cancel_event)
                outcome.duration_seconds = round(time.monotonic() - target_started, 2)

                if cancel_event.is_set() and outcome.status != "cancelled":
                    outcome.status = "cancelled"
                self._apply_outcome(summary, target, outcome)
                scan_state[target.key] = self._state_entry(target, outcome.status)
                if outcome.status == "cancelled":
                    summary["cancelled"] = True
                    break

                if index % 25 == 0:
                    self._save_scan_state(scan_state)
                progress = 100 if total == 0 else 30 + int(index / total * 70)
                self._progress(
                    progress_callback,
                    min(progress, 100),
                    f"处理 {index}/{total}：{target.path.name}",
                    summary,
                )

                if self._interval_seconds and index < total:
                    if cancel_event.wait(self._interval_seconds):
                        summary["cancelled"] = True
                        break

            self._save_scan_state(scan_state)
            self._save_nfo_repair_state(self._nfo_repair_state)
            complete = (
                not summary["failed"]
                and not summary["partial"]
                and not summary["cancelled"]
            )
            return complete, self._format_service_result(summary)
        except Exception as err:
            summary["failed"] += 1
            self._remember_failure(summary, "任务", str(err))
            logger.error(f"媒体库刮削(魔改版)任务异常：{err}")
            logger.debug(traceback.format_exc())
            return False, str(err)
        finally:
            summary["finished_at"] = self._now()
            summary["duration_seconds"] = round(time.monotonic() - started, 2)
            summary["scan_seconds"] = summary.get(
                "scan_seconds", round(scan_finished - started, 2)
            )
            summary["process_seconds"] = round(
                time.monotonic() - process_started, 2
            )
            self._save_run_summary(summary)
            self._send_summary(summary)
            self._progress(progress_callback, 100, "任务结束", summary)
            self._force_full_scan = False
            self._running_status = {}
            self._active_summary = None
            self._release_run_file_lock(lock_fd)
            self._run_lock.release()

    def stop_service(self):
        cancel_event = getattr(self, "_cancel_event", None)
        if cancel_event:
            cancel_event.set()
        scheduler = getattr(self, "_scheduler", None)
        if not scheduler:
            return
        try:
            scheduler.remove_all_jobs()
            if scheduler.running:
                scheduler.shutdown(wait=False)
        except Exception as err:
            logger.warning(f"停止媒体库刮削(魔改版)一次性任务失败：{err}")
        finally:
            self._scheduler = None

    def _discover_targets(
        self,
        exclusions: List[Path],
        summary: Dict[str, Any],
        cancel_event: threading.Event,
        progress_callback=None,
    ) -> Dict[str, ScrapeTarget]:
        targets: Dict[str, ScrapeTarget] = {}
        roots = self._parse_scraper_roots(summary)
        media_extensions = {str(ext).lower() for ext in settings.RMT_MEDIAEXT}

        for root, forced_type in roots:
            if cancel_event.is_set():
                break
            if self._is_excluded(root, exclusions):
                summary["excluded_roots"] += 1
                logger.info(f"刮削根目录在排除范围中，跳过：{root}")
                continue
            logger.info(f"开始检索目录：{root} {forced_type or ''}")
            for file_path, stat_result in self._iter_media_file_entries(
                root, exclusions, media_extensions, summary, cancel_event
            ):
                summary["media_files"] += 1
                try:
                    file_meta = MetaInfoPath(file_path)
                    mtype = forced_type or file_meta.type
                    if mtype == MediaType.UNKNOWN:
                        mtype = self._infer_type_from_path(file_path, root)
                    if mtype not in (MediaType.MOVIE, MediaType.TV):
                        summary["unknown_type"] += 1
                        logger.warning(f"无法确定媒体类型，跳过：{file_path}")
                        continue
                    if forced_type and not self._match_forced_type_path(
                        file_path, root, forced_type
                    ):
                        summary["forced_type_skipped"] += 1
                        continue
                    tmdbid = self._valid_tmdbid(getattr(file_meta, "tmdbid", None))
                    doubanid = self._valid_doubanid(
                        getattr(file_meta, "doubanid", None)
                    )
                    item = self._get_scrape_item(file_path, root, mtype)
                    if not item:
                        summary["scan_errors"] += 1
                        continue
                    target_path, target_type = item
                    key = f"{target_type}|{mtype.value}|{target_path}"
                    target = targets.get(key)
                    if not target:
                        target = ScrapeTarget(
                            path=target_path,
                            mtype=mtype,
                            target_type=target_type,
                            source_root=root,
                            forced_type=forced_type,
                            tmdbid=tmdbid,
                            doubanid=doubanid,
                        )
                        targets[key] = target
                        logger.debug(f"发现刮削目标：{target_path}")
                    target.include_file(file_path, stat_result, tmdbid, doubanid)
                except (FileNotFoundError, PermissionError, OSError) as err:
                    summary["scan_errors"] += 1
                    self._remember_failure(summary, str(file_path), f"扫描失败：{err}")
                except Exception as err:
                    summary["scan_errors"] += 1
                    self._remember_failure(summary, str(file_path), f"解析失败：{err}")
                    logger.error(f"解析媒体文件失败：{file_path} - {err}")

                if summary["media_files"] % 500 == 0:
                    self._progress(
                        progress_callback,
                        min(29, 1 + summary["media_files"] // 500),
                        f"已扫描 {summary['media_files']} 个媒体文件",
                        summary,
                    )

        summary["targets"] = len(targets)
        return targets

    def _iter_media_files(
        self,
        root: Path,
        exclusions: List[Path],
        media_extensions: Iterable[str],
        summary: Dict[str, Any],
        cancel_event: threading.Event,
    ) -> Iterable[Path]:
        for file_path, _stat_result in self._iter_media_file_entries(
            root, exclusions, media_extensions, summary, cancel_event
        ):
            yield file_path

    def _iter_media_file_entries(
        self,
        root: Path,
        exclusions: List[Path],
        media_extensions: Iterable[str],
        summary: Dict[str, Any],
        cancel_event: threading.Event,
    ) -> Iterable[Tuple[Path, os.stat_result]]:
        extensions = set(media_extensions)

        def on_error(err: OSError) -> None:
            summary["scan_errors"] += 1
            self._remember_failure(summary, str(getattr(err, "filename", root)), str(err))

        pending = [root]
        while pending:
            if cancel_event.is_set():
                return
            current_path = pending.pop()
            try:
                with os.scandir(current_path) as scanner:
                    entries = list(scanner)
            except OSError as err:
                on_error(err)
                continue

            child_dirs = []
            for entry in entries:
                entry_path = Path(entry.path)
                try:
                    if entry.is_symlink():
                        summary["symlinks_skipped"] += 1
                        logger.warning(f"跳过符号链接：{entry_path}")
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        if self._is_excluded(entry_path, exclusions):
                            summary["excluded_dirs"] += 1
                            continue
                        child_dirs.append(entry_path)
                        continue
                    if entry_path.suffix.lower() not in extensions:
                        continue
                    if self._is_excluded(entry_path, exclusions):
                        summary["excluded_files"] += 1
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    yield entry_path, entry.stat(follow_symlinks=False)
                except OSError as err:
                    on_error(err)
            pending.extend(reversed(child_dirs))

    def _run_target_with_retry(
        self,
        target: ScrapeTarget,
        exclusions: List[Path],
        cancel_event: threading.Event,
    ) -> ScrapeOutcome:
        for attempt in range(self._retry_count + 1):
            try:
                return self._scrape_target(target, exclusions, cancel_event)
            except Exception as err:
                if attempt >= self._retry_count or cancel_event.is_set():
                    logger.error(f"刮削目标失败：{target.path} - {err}")
                    logger.debug(traceback.format_exc())
                    return ScrapeOutcome(status="failed", failed_files=1, detail=str(err))
                delay = min(2 ** attempt, 10)
                logger.warning(
                    f"刮削目标异常，{delay} 秒后重试 {attempt + 1}/{self._retry_count}："
                    f"{target.path} - {err}"
                )
                if cancel_event.wait(delay):
                    return ScrapeOutcome(status="cancelled", detail="任务已取消")
        return ScrapeOutcome(status="failed", failed_files=1, detail="未知错误")

    def _scrape_target(
        self,
        target: ScrapeTarget,
        exclusions: List[Path],
        cancel_event: threading.Event,
    ) -> ScrapeOutcome:
        logger.info(f"开始刮削目标：{target.path}")
        if self._scrape_one(
            target.path,
            target.mtype,
            target.target_type,
            target.tmdbid,
            cancel_event,
            target.source_root,
            target.doubanid,
        ):
            return ScrapeOutcome(status="success", scraped_files=target.file_count)

        if target.target_type != self._target_dir:
            logger.warning(f"未识别到媒体信息：{target.path}")
            return ScrapeOutcome(status="unrecognized", unrecognized_files=1)

        child_files = list(
            self._iter_media_files(
                target.path,
                exclusions,
                {str(ext).lower() for ext in settings.RMT_MEDIAEXT},
                self._new_scan_counters(),
                cancel_event,
            )
        )
        if not child_files:
            return ScrapeOutcome(status="unrecognized", unrecognized_files=1)

        logger.info(f"目录无法识别，安全回退到 {len(child_files)} 个媒体文件：{target.path}")
        outcome = ScrapeOutcome(status="unrecognized")
        for child_file in child_files:
            if cancel_event.is_set():
                outcome.status = "cancelled"
                break
            child_meta = MetaInfoPath(child_file)
            child_mtype = target.forced_type or child_meta.type
            if child_mtype == MediaType.UNKNOWN:
                child_mtype = self._infer_type_from_path(child_file, target.source_root)
            if child_mtype not in (MediaType.MOVIE, MediaType.TV):
                outcome.unrecognized_files += 1
                outcome.item_details.append(
                    {
                        "status": "unrecognized",
                        "path": str(child_file),
                        "files": 1,
                        "detail": "未识别到媒体类型",
                    }
                )
                continue
            try:
                recognized = self._scrape_one(
                    child_file,
                    child_mtype,
                    self._target_file,
                    self._valid_tmdbid(getattr(child_meta, "tmdbid", None)),
                    cancel_event,
                    target.source_root,
                    self._valid_doubanid(getattr(child_meta, "doubanid", None)),
                )
                if recognized:
                    outcome.scraped_files += 1
                else:
                    outcome.unrecognized_files += 1
                    outcome.item_details.append(
                        {
                            "status": "unrecognized",
                            "path": str(child_file),
                            "files": 1,
                            "detail": "未识别到媒体信息",
                        }
                    )
            except Exception as err:
                outcome.failed_files += 1
                logger.error(f"回退刮削文件失败：{child_file} - {err}")
                outcome.item_details.append(
                    {
                        "status": "failed",
                        "path": str(child_file),
                        "files": 1,
                        "detail": str(err),
                    }
                )

        if outcome.status == "cancelled":
            return outcome
        if outcome.scraped_files and (outcome.failed_files or outcome.unrecognized_files):
            outcome.status = "partial"
        elif outcome.failed_files:
            outcome.status = "failed"
        elif outcome.scraped_files:
            outcome.status = "success"
        return outcome

    def _scrape_one(
        self,
        path: Path,
        mtype: MediaType,
        target_type: str,
        tmdbid: Optional[int],
        cancel_event: threading.Event,
        source_root: Optional[Path] = None,
        doubanid: Optional[str] = None,
    ) -> bool:
        if cancel_event.is_set():
            return False
        tmdbid = self._tmdbid_for_target(
            path, mtype, target_type, tmdbid, source_root
        )
        doubanid = self._doubanid_for_target(
            path, mtype, target_type, doubanid, source_root
        )
        recognize_source = str(
            getattr(settings, "RECOGNIZE_SOURCE", "") or ""
        ).lower()
        use_douban = bool(doubanid and (recognize_source == "douban" or not tmdbid))
        if use_douban:
            logger.info(f"使用豆瓣 ID 识别：{doubanid} - {path}")
            mediainfo = self.chain.recognize_media(
                mtype=mtype, doubanid=doubanid
            )
        elif tmdbid:
            logger.info(f"使用 TMDB ID 识别：{tmdbid} - {path}")
            mediainfo = self.chain.recognize_media(tmdbid=tmdbid, mtype=mtype)
        else:
            meta = MetaInfoPath(path)
            meta.type = mtype
            mediainfo = self.chain.recognize_media(meta=meta)
        if not mediainfo:
            return False
        if use_douban:
            # MoviePilot 2.15+ selects metadata modules per request with this field.
            # Older releases ignore the dynamic attribute and use SCRAP_SOURCE.
            mediainfo.scrape_source = "douban"

        self._repair_nfo_target(path, mtype, target_type, mediainfo)

        media_tmdbid = self._valid_tmdbid(getattr(mediainfo, "tmdb_id", None))
        if not settings.SCRAP_FOLLOW_TMDB and media_tmdbid:
            transfer_history = TransferHistoryOper().get_by_type_tmdbid(
                tmdbid=media_tmdbid, mtype=mediainfo.type.value
            )
            if transfer_history:
                mediainfo.title = transfer_history.title

        self.chain.obtain_images(mediainfo)
        path_stat = path.stat()
        item_path = str(path).replace("\\", "/")
        if target_type == self._target_dir:
            item_path = f"{item_path}/"

        with self._metadata_chain(cancel_event) as media_chain:
            media_chain.scrape_metadata(
                fileitem=schemas.FileItem(
                    storage="local",
                    type=target_type,
                    path=item_path,
                    name=path.name,
                    basename=path.stem,
                    extension=path.suffix[1:] if target_type == self._target_file else None,
                    modify_time=path_stat.st_mtime,
                ),
                mediainfo=mediainfo,
                overwrite=self._mode == "force_all",
            )
        logger.info(f"{path} 刮削完成")
        return True

    @contextmanager
    def _metadata_chain(self, cancel_event: threading.Event):
        acquired = False
        while not cancel_event.is_set():
            acquired = scraping_lock.acquire(timeout=0.5)
            if acquired:
                break
        if not acquired:
            raise RuntimeError("等待 MoviePilot 刮削锁时任务被取消")

        # A shallow copy shares MoviePilot's services but owns its policy attribute,
        # so missing-only enforcement never mutates the global MediaChain singleton.
        media_chain = copy(MediaChain())
        original_policies = getattr(media_chain, "scraping_policies", None)
        policy_view = None
        try:
            if self._mode != "force_all" and original_policies is not None:
                policy_view = _NonOverwritingPolicies(original_policies)
                media_chain.scraping_policies = policy_view
            yield media_chain
        finally:
            if policy_view is not None and media_chain.scraping_policies is policy_view:
                media_chain.scraping_policies = original_policies
            scraping_lock.release()

    def _repair_nfo_target(
        self, path: Path, mtype: MediaType, target_type: str, mediainfo: Any
    ) -> None:
        if not self._repair_nfo_enabled or mtype != MediaType.TV:
            return
        if target_type == self._target_file:
            self._repair_episode_nfo(path, mediainfo)
            return
        extensions = {str(ext).lower() for ext in settings.RMT_MEDIAEXT}
        for current, _dirs, filenames in os.walk(path, followlinks=False):
            for filename in filenames:
                episode_path = Path(current) / filename
                if (
                    episode_path.suffix.lower() in extensions
                    and not episode_path.is_symlink()
                ):
                    self._repair_episode_nfo(episode_path, mediainfo)

    def _repair_episode_nfo(self, path: Path, mediainfo: Any) -> None:
        nfo_path = path.with_suffix(".nfo")
        try:
            stat_result = nfo_path.lstat()
        except OSError:
            return
        if stat_module.S_ISLNK(stat_result.st_mode):
            return
        if not self._nfo_path_due(nfo_path, stat_result):
            summary = getattr(self, "_active_summary", None)
            if summary is not None:
                summary["nfo_cached"] += 1
            return

        summary = getattr(self, "_active_summary", None)
        if summary is not None:
            summary["nfo_checked"] += 1
        try:
            tree = ET.parse(nfo_path)
            root = tree.getroot()
        except (ET.ParseError, OSError) as err:
            logger.warning(f"NFO 字段修复跳过，无法解析：{nfo_path} - {err}")
            return
        if root.tag.lower() != "episodedetails":
            return

        meta = MetaInfoPath(path)
        season = getattr(meta, "begin_season", None)
        episode = getattr(meta, "begin_episode", None)
        tmdbid = self._valid_tmdbid(getattr(mediainfo, "tmdb_id", None))
        if not season or not episode or not tmdbid:
            return
        episode_data = self._tmdb_episode_data(
            tmdbid, int(season), int(episode), getattr(mediainfo, "episode_group", None)
        )
        if not episode_data:
            return

        updates = {}
        source_title = self._text_value(episode_data, "name")
        source_overview = self._text_value(episode_data, "overview")
        existing_title = self._xml_text(root, "title")
        if source_title and (
            not existing_title or self._is_generic_episode_title(existing_title)
        ) and not self._is_generic_episode_title(source_title):
            updates["title"] = source_title
        for field in ("plot", "outline"):
            if source_overview and not self._xml_text(root, field):
                updates[field] = source_overview
        if not updates:
            self._remember_nfo_repair_state(nfo_path, "checked")
            return

        preview = ", ".join(sorted(updates))
        if self._dry_run:
            logger.info(f"预演 NFO 字段修复：{nfo_path} - {preview}")
            if summary is not None:
                summary["nfo_preview"] += 1
            return

        for field, value in updates.items():
            element = root.find(field)
            if element is None:
                element = ET.SubElement(root, field)
            element.text = value
        temp_path = nfo_path.with_suffix(f"{nfo_path.suffix}.libraryscraperfix.tmp")
        try:
            tree.write(temp_path, encoding="utf-8", xml_declaration=True)
            os.replace(temp_path, nfo_path)
            self._remember_nfo_repair_state(nfo_path, "updated")
            logger.info(f"已修复 NFO 字段：{nfo_path} - {preview}")
            if summary is not None:
                summary["nfo_updated"] += 1
                if "title" in updates:
                    summary["nfo_titles_updated"] += 1
                if "plot" in updates or "outline" in updates:
                    summary["nfo_overviews_updated"] += 1
        except OSError as err:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            logger.warning(f"NFO 字段修复写入失败：{nfo_path} - {err}")

    @staticmethod
    def _xml_text(root: ET.Element, field: str) -> str:
        element = root.find(field)
        return (element.text or "").strip() if element is not None else ""

    @staticmethod
    def _text_value(value: Any, field: str) -> str:
        raw = value.get(field) if isinstance(value, dict) else getattr(value, field, None)
        return str(raw).strip() if raw is not None else ""

    @staticmethod
    def _is_generic_episode_title(value: str) -> bool:
        return bool(
            re.fullmatch(
                r"(?:第\s*\d+\s*集|Episode\s*\d+|S\d+\s*E\d+)",
                value.strip(),
                flags=re.IGNORECASE,
            )
        )

    def _tmdb_episode_data(
        self, tmdbid: int, season: int, episode: int, episode_group: Optional[str]
    ) -> Optional[Any]:
        cache = getattr(self, "_tmdb_episode_cache", {})
        cache_key = (tmdbid, season)
        try:
            if cache_key not in cache:
                # MoviePilot's public TmdbChain interface accepts a series ID and season.
                cache[cache_key] = TmdbChain().tmdb_episodes(tmdbid, season) or []
            episodes = cache[cache_key]
        except Exception as err:
            logger.warning(f"读取 TMDB 剧集信息失败：{tmdbid} S{season:02d}E{episode:02d} - {err}")
            return None
        for item in episodes or []:
            number = item.get("episode_number") if isinstance(item, dict) else getattr(item, "episode_number", None)
            if number == episode:
                return item
        return None

    def _nfo_repair_due(self, target: ScrapeTarget) -> bool:
        if not self._repair_nfo_enabled or target.mtype != MediaType.TV:
            return False
        nfo_paths = [target.path.with_suffix(".nfo")]
        if target.target_type == self._target_dir:
            media_files = target.media_files
            if not media_files:
                media_files = [
                    item
                    for item in target.path.rglob("*")
                    if item.is_file()
                    and not item.is_symlink()
                    and item.suffix.lower()
                    in {str(ext).lower() for ext in settings.RMT_MEDIAEXT}
                ]
            nfo_paths = [item.with_suffix(".nfo") for item in media_files]
        if not nfo_paths:
            return False
        cached = 0
        for nfo_path in nfo_paths:
            try:
                stat_result = nfo_path.lstat()
            except FileNotFoundError:
                continue
            except OSError:
                return True
            if stat_module.S_ISLNK(stat_result.st_mode):
                continue
            if self._nfo_path_due(nfo_path, stat_result):
                return True
            cached += 1
        summary = getattr(self, "_active_summary", None)
        if summary is not None:
            summary["nfo_cached"] += cached
        return False

    def _nfo_path_due(
        self, nfo_path: Path, stat_result: Optional[os.stat_result] = None
    ) -> bool:
        state = getattr(self, "_nfo_repair_state", {})
        try:
            entry = state.get(str(nfo_path))
            metadata = self._nfo_stat_fingerprint(
                stat_result if stat_result is not None else nfo_path.stat()
            )
        except OSError:
            return True
        fingerprint = entry.get("fingerprint") if isinstance(entry, dict) else None
        if not isinstance(fingerprint, list):
            return True
        metadata_length = 3 if len(fingerprint) >= 4 else 2
        if fingerprint[:metadata_length] != metadata[:metadata_length]:
            return True
        if self._nfo_audit_days:
            try:
                age = (datetime.now().astimezone() - datetime.fromisoformat(entry["updated_at"])).total_seconds()
                return age >= self._nfo_audit_days * 86400
            except (KeyError, TypeError, ValueError):
                return True
        return False

    @staticmethod
    def _nfo_stat_fingerprint(stat_result: os.stat_result) -> List[int]:
        mtime_ns = int(
            getattr(
                stat_result,
                "st_mtime_ns",
                stat_result.st_mtime * 1_000_000_000,
            )
        )
        ctime_ns = int(
            getattr(
                stat_result,
                "st_ctime_ns",
                stat_result.st_ctime * 1_000_000_000,
            )
        )
        return [int(stat_result.st_size), mtime_ns, ctime_ns]

    @classmethod
    def _nfo_fingerprint(cls, nfo_path: Path) -> List[Any]:
        stat_result = nfo_path.stat()
        digest = hashlib.blake2b(nfo_path.read_bytes(), digest_size=8).hexdigest()
        return [*cls._nfo_stat_fingerprint(stat_result), digest]

    def _remember_nfo_repair_state(self, nfo_path: Path, status: str) -> None:
        state = getattr(self, "_nfo_repair_state", None)
        if state is None or self._dry_run:
            return
        try:
            state[str(nfo_path)] = {
                "fingerprint": self._nfo_fingerprint(nfo_path),
                "status": status,
                "updated_at": self._now(),
            }
        except OSError as err:
            logger.warning(f"保存 NFO 字段缓存失败：{nfo_path} - {err}")

    def _load_nfo_repair_state(self) -> Dict[str, Any]:
        try:
            state = self.get_data(self._nfo_repair_state_key)
            return state if isinstance(state, dict) else {}
        except Exception as err:
            logger.error(f"读取 NFO 字段缓存失败，将执行检查：{err}")
            return {}

    def _save_nfo_repair_state(self, state: Dict[str, Any]) -> None:
        try:
            self.save_data(self._nfo_repair_state_key, state)
        except Exception as err:
            logger.error(f"保存 NFO 字段缓存失败：{err}")

    def _tmdbid_for_target(
        self,
        path: Path,
        mtype: MediaType,
        target_type: str,
        fallback_tmdbid: Optional[int],
        source_root: Optional[Path] = None,
    ) -> Optional[int]:
        tmdbid = self._valid_tmdbid(fallback_tmdbid)
        for nfo_path in self._nfo_candidates_for_target(
            path, mtype, target_type, source_root
        ):
            if not nfo_path.exists() or nfo_path.is_symlink():
                continue
            nfo_tmdbid = self._get_tmdbid_from_nfo(nfo_path)
            if nfo_tmdbid:
                return nfo_tmdbid
        return tmdbid

    def _doubanid_for_target(
        self,
        path: Path,
        mtype: MediaType,
        target_type: str,
        fallback_doubanid: Optional[str],
        source_root: Optional[Path] = None,
    ) -> Optional[str]:
        doubanid = self._valid_doubanid(fallback_doubanid)
        for nfo_path in self._nfo_candidates_for_target(
            path, mtype, target_type, source_root
        ):
            if not nfo_path.exists() or nfo_path.is_symlink():
                continue
            nfo_doubanid = self._get_doubanid_from_nfo(nfo_path)
            if nfo_doubanid:
                return nfo_doubanid
        return doubanid

    @classmethod
    def _nfo_candidates_for_target(
        cls,
        path: Path,
        mtype: MediaType,
        target_type: str,
        source_root: Optional[Path],
    ) -> List[Path]:
        if target_type == cls._target_file and mtype == MediaType.TV:
            # Episode NFO IDs identify episodes, not the parent TV series.
            return cls._tvshow_nfo_candidates(path, source_root)
        if target_type == cls._target_file:
            return [path.with_suffix(".nfo")]
        if mtype == MediaType.MOVIE:
            return [path / "movie.nfo", path / f"{path.stem}.nfo"]
        if mtype == MediaType.TV:
            return [path / "tvshow.nfo"]
        return []

    @classmethod
    def _tvshow_nfo_candidates(
        cls, media_path: Path, source_root: Optional[Path]
    ) -> List[Path]:
        candidates = []
        current = cls._normalize_path(media_path.parent)
        root = cls._normalize_path(source_root) if source_root else None
        while current != current.parent:
            candidates.append(current / "tvshow.nfo")
            if root and current == root:
                break
            if root and not cls._is_within(current.parent, root):
                break
            current = current.parent
        return candidates

    @staticmethod
    def _get_tmdbid_from_nfo(file_path: Path) -> Optional[int]:
        xpaths = [
            "uniqueid[@type='Tmdb']",
            "uniqueid[@type='tmdb']",
            "uniqueid[@type='TMDB']",
            "tmdbid",
        ]
        try:
            reader = NfoReader(file_path)
            for xpath in xpaths:
                tmdbid = LibraryScraperFix._valid_tmdbid(reader.get_element_value(xpath))
                if tmdbid:
                    return tmdbid
        except Exception as err:
            logger.warning(f"从 NFO 读取 TMDB ID 失败：{file_path} - {err}")
        return None

    @staticmethod
    def _get_doubanid_from_nfo(file_path: Path) -> Optional[str]:
        xpaths = [
            "uniqueid[@type='Douban']",
            "uniqueid[@type='douban']",
            "uniqueid[@type='DOUBAN']",
            "doubanid",
        ]
        try:
            reader = NfoReader(file_path)
            for xpath in xpaths:
                doubanid = LibraryScraperFix._valid_doubanid(
                    reader.get_element_value(xpath)
                )
                if doubanid:
                    return doubanid
        except Exception as err:
            logger.warning(f"从 NFO 读取豆瓣 ID 失败：{file_path} - {err}")
        return None

    @staticmethod
    def _valid_tmdbid(value: Any) -> Optional[int]:
        if value is None or isinstance(value, bool):
            return None
        try:
            tmdbid = int(str(value).strip())
        except (TypeError, ValueError):
            return None
        return tmdbid if tmdbid > 0 else None

    @staticmethod
    def _valid_doubanid(value: Any) -> Optional[str]:
        if value is None or isinstance(value, bool):
            return None
        doubanid = str(value).strip()
        if not doubanid.isdigit() or int(doubanid) <= 0:
            return None
        return doubanid

    def _parse_scraper_roots(
        self, summary: Dict[str, Any]
    ) -> List[Tuple[Path, Optional[MediaType]]]:
        roots = []
        seen = set()
        for raw_line in self._scraper_paths.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                path, forced_type = self._parse_scraper_line(line)
            except ValueError as err:
                summary["invalid_paths"] += 1
                self._remember_failure(summary, line, str(err))
                logger.error(f"刮削路径配置无效：{line} - {err}")
                continue
            if path.is_symlink():
                summary["invalid_paths"] += 1
                logger.error(f"刮削根目录不能是符号链接：{path}")
                continue
            if not path.exists() or not path.is_dir():
                summary["invalid_paths"] += 1
                logger.warning(f"刮削路径不存在或不是目录：{path}")
                continue
            normalized = self._normalize_path(path)
            key = (str(normalized), forced_type.value if forced_type else "")
            if key in seen:
                continue
            seen.add(key)
            roots.append((normalized, forced_type))
        return roots

    @staticmethod
    def _parse_scraper_line(line: str) -> Tuple[Path, Optional[MediaType]]:
        raw_path = line
        forced_type = None
        if "#" in line and not Path(line).exists():
            candidate_path, suffix = line.rsplit("#", 1)
            type_map = {
                MediaType.MOVIE.value: MediaType.MOVIE,
                MediaType.TV.value: MediaType.TV,
            }
            if suffix in type_map and candidate_path.strip():
                raw_path = candidate_path.strip()
                forced_type = type_map[suffix]
            elif not Path(line).exists():
                raise ValueError(f"未知媒体类型后缀：#{suffix}")
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            raise ValueError("必须使用绝对路径")
        return path, forced_type

    def _parse_exclusions(self, summary: Dict[str, Any]) -> List[Path]:
        exclusions = []
        for raw_line in self._exclude_paths.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            path = Path(line).expanduser()
            if not path.is_absolute():
                summary["invalid_paths"] += 1
                self._remember_failure(summary, line, "排除路径必须使用绝对路径")
                continue
            exclusions.append(self._normalize_path(path))
        return list(dict.fromkeys(exclusions))

    @staticmethod
    def _normalize_path(path: Path) -> Path:
        return Path(os.path.realpath(os.path.abspath(str(path))))

    @staticmethod
    def _is_within(path: Path, parent: Path) -> bool:
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False

    @classmethod
    def _is_excluded(cls, path: Path, exclusions: List[Path]) -> bool:
        if not exclusions:
            return False
        # Scanner roots and exclusions are already real paths; scanned symlinks are pruned.
        normalized = Path(os.path.abspath(str(path)))
        return any(normalized == item or cls._is_within(normalized, item) for item in exclusions)

    @staticmethod
    def _get_scrape_item(
        file_path: Path, scraper_path: Path, mtype: MediaType
    ) -> Optional[Tuple[Path, str]]:
        if mtype not in (MediaType.MOVIE, MediaType.TV):
            return None
        rename_format = (
            settings.TV_RENAME_FORMAT if mtype == MediaType.TV else settings.MOVIE_RENAME_FORMAT
        )
        rename_format_level = max(0, len(rename_format.strip("/").split("/")) - 1)
        try:
            relative_path = file_path.relative_to(scraper_path)
        except ValueError:
            return None
        if rename_format_level >= 1:
            relative_parts = relative_path.parts
            if len(relative_parts) > rename_format_level:
                media_path = scraper_path.joinpath(*relative_parts[:-rename_format_level])
                if LibraryScraperFix._is_within(media_path, scraper_path):
                    return media_path, LibraryScraperFix._target_dir
        return file_path, LibraryScraperFix._target_file

    @staticmethod
    def _match_forced_type_path(
        file_path: Path, scraper_path: Path, mtype: MediaType
    ) -> bool:
        try:
            relative_parts = file_path.relative_to(scraper_path).parts
        except ValueError:
            return False
        type_parts = {MediaType.MOVIE.value, MediaType.TV.value}.intersection(relative_parts)
        return not type_parts or mtype.value in type_parts

    @staticmethod
    def _infer_type_from_path(file_path: Path, scraper_path: Path) -> MediaType:
        try:
            relative_parts = file_path.relative_to(scraper_path).parts
        except ValueError:
            relative_parts = file_path.parts
        if MediaType.TV.value in relative_parts:
            return MediaType.TV
        if MediaType.MOVIE.value in relative_parts:
            return MediaType.MOVIE
        return MediaType.UNKNOWN

    def _should_skip_target(self, target: ScrapeTarget, state: Dict[str, Any]) -> bool:
        if not self._incremental or self._force_full_scan:
            return False
        previous = state.get(target.key)
        if not isinstance(previous, dict):
            return False
        if previous.get("status") != "success":
            return False
        if previous.get("mode", "") != self._mode:
            return False
        if previous.get("fingerprint") != target.fingerprint:
            return False
        if not self._full_scan_days:
            return True
        try:
            updated_at = datetime.fromisoformat(previous["updated_at"])
            age_seconds = (datetime.now().astimezone() - updated_at).total_seconds()
            return age_seconds < self._full_scan_days * 86400
        except (KeyError, TypeError, ValueError):
            return False

    def _candidate_reason(
        self,
        target: ScrapeTarget,
        state: Dict[str, Any],
        scraper_cached: bool,
        nfo_due: bool,
    ) -> str:
        if scraper_cached and nfo_due:
            return "nfo"
        if not self._incremental or self._force_full_scan:
            return "forced"
        previous = state.get(target.key)
        if not isinstance(previous, dict):
            return "new"
        if previous.get("status") != "success":
            return "retry"
        if previous.get("mode", "") != self._mode:
            return "policy"
        if previous.get("fingerprint") != target.fingerprint:
            return "changed"
        return "periodic"

    @staticmethod
    def _candidate_sort_key(target: ScrapeTarget, state: Dict[str, Any]) -> Tuple[str, str]:
        previous = state.get(target.key) or {}
        return str(previous.get("updated_at") or ""), target.key

    def _state_entry(self, target: ScrapeTarget, status: str) -> Dict[str, Any]:
        return {
            "fingerprint": target.fingerprint,
            "status": status,
            "mode": self._mode,
            "updated_at": self._now(),
        }

    def _load_scan_state(self) -> Dict[str, Any]:
        try:
            state = self.get_data(self._state_key)
            return state if isinstance(state, dict) else {}
        except Exception as err:
            logger.error(f"读取媒体库刮削增量缓存失败，将执行完整扫描：{err}")
            return {}

    def _save_scan_state(self, state: Dict[str, Any]) -> None:
        try:
            self.save_data(self._state_key, state)
        except Exception as err:
            logger.error(f"保存媒体库刮削增量缓存失败：{err}")

    @staticmethod
    def _prune_scan_state(
        state: Dict[str, Any],
        targets: Dict[str, ScrapeTarget],
        summary: Dict[str, Any],
    ) -> None:
        if summary.get("scan_errors") or summary.get("invalid_paths"):
            return
        stale_keys = set(state).difference(targets)
        for key in stale_keys:
            state.pop(key, None)
        summary["stale_state_removed"] = len(stale_keys)

    def _acquire_run_file_lock(self) -> Tuple[bool, Optional[int]]:
        if fcntl is None:
            return True, None
        try:
            lock_path = self.get_data_path() / "run.lock"
            lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                os.close(lock_fd)
                return False, None
            except Exception:
                os.close(lock_fd)
                raise
            return True, lock_fd
        except Exception as err:
            logger.error(f"创建媒体库刮削跨重载锁失败：{err}")
            return False, None

    @staticmethod
    def _release_run_file_lock(lock_fd: Optional[int]) -> None:
        if lock_fd is None or fcntl is None:
            return
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        except OSError as err:
            logger.warning(f"释放媒体库刮削跨重载锁失败：{err}")
        finally:
            try:
                os.close(lock_fd)
            except OSError:
                pass

    def _apply_outcome(
        self, summary: Dict[str, Any], target: ScrapeTarget, outcome: ScrapeOutcome
    ) -> None:
        if outcome.status in ("success", "partial", "dry_run", "unrecognized", "failed"):
            summary[outcome.status] += 1
        summary["scraped_files"] += outcome.scraped_files
        summary["unrecognized_files"] += outcome.unrecognized_files
        summary["failed_files"] += outcome.failed_files
        self._record_target_detail(summary, target, outcome)
        for item in outcome.item_details:
            if item.get("status") == "failed":
                self._remember_failure(
                    summary, item.get("path", str(target.path)), item.get("detail", "")
                )
        if outcome.detail:
            self._remember_failure(summary, str(target.path), outcome.detail)

    @classmethod
    def _record_target_detail(
        cls, summary: Dict[str, Any], target: ScrapeTarget, outcome: ScrapeOutcome
    ) -> None:
        details = summary.setdefault("details", [])
        issues = summary.setdefault("issues", [])

        def append_limited(collection: List[Dict[str, Any]], item: Dict[str, Any]) -> None:
            if len(collection) < cls._detail_limit:
                collection.append(item)
                return
            if item.get("status") not in ("unrecognized", "failed"):
                return
            for index, existing in enumerate(collection):
                if existing.get("status") not in ("unrecognized", "failed"):
                    collection[index] = item
                    return

        detail = outcome.detail
        if not detail and outcome.status == "unrecognized":
            detail = "未识别到媒体信息"
        elif not detail and outcome.status == "partial":
            detail = "部分媒体文件未完成"
        append_limited(
            details,
            {
                "status": outcome.status,
                "path": str(target.path),
                "files": target.file_count,
                "detail": detail[:500] if detail else "",
                "duration_seconds": outcome.duration_seconds,
            }
        )

        if outcome.item_details:
            for item in outcome.item_details:
                append_limited(
                    issues,
                    {
                        "status": item.get("status", outcome.status),
                        "target": str(target.path),
                        "path": item.get("path", str(target.path)),
                        "files": item.get("files", 1),
                        "detail": str(item.get("detail", ""))[:500],
                        "duration_seconds": item.get("duration_seconds", 0),
                    },
                )
        elif outcome.status in ("failed", "unrecognized", "partial", "cancelled"):
            append_limited(
                issues,
                {
                    "status": outcome.status,
                    "target": str(target.path),
                    "path": str(target.path),
                    "files": target.file_count,
                    "detail": detail[:500] if detail else "",
                    "duration_seconds": outcome.duration_seconds,
                },
            )

    def _save_run_summary(self, summary: Dict[str, Any]) -> None:
        try:
            self.save_data(self._last_run_key, summary)
            history = self.get_data(self._history_key) or []
            if not isinstance(history, list):
                history = []
            self.save_data(self._history_key, [summary] + history[:19])
        except Exception as err:
            logger.error(f"保存媒体库刮削运行摘要失败：{err}")

    def _send_summary(self, summary: Dict[str, Any]) -> None:
        text = self._format_notification(summary)
        logger.info(text.replace("\n", " | "))
        if not self._notify:
            return
        try:
            self.post_message(
                mtype=NotificationType.Plugin,
                title=(
                    "媒体库刮削预演完成"
                    if summary.get("dry_run_enabled")
                    else "媒体库刮削完成"
                ),
                text=text,
            )
        except Exception as err:
            logger.error(f"发送媒体库刮削摘要失败：{err}")

    @staticmethod
    def _remember_failure(summary: Dict[str, Any], path: str, detail: str) -> None:
        failures = summary.setdefault("failures", [])
        if len(failures) < 20:
            failures.append({"path": path, "detail": detail[:500]})

    @classmethod
    def _status_alert(cls, summary: Dict[str, Any]) -> dict:
        problem_count = cls._problem_count(summary)
        if summary.get("failed") or summary.get("scan_errors") or summary.get("invalid_paths"):
            alert_type = "error"
            title = f"运行完成，{problem_count} 项需要处理"
        elif problem_count:
            alert_type = "warning"
            title = f"运行完成，{problem_count} 项需要处理"
        else:
            alert_type = "success"
            title = "运行完成，未发现问题"
        mode = "预演" if summary.get("dry_run_enabled") else "执行"
        finished_at = summary.get("finished_at") or summary.get("started_at") or "-"
        return {
            "component": "VAlert",
            "props": {
                "type": alert_type,
                "variant": "tonal",
                "title": title,
                "text": (
                    f"{finished_at} | {mode} | "
                    f"总耗时 {cls._format_duration(summary.get('duration_seconds', 0))}"
                ),
            },
        }

    @staticmethod
    def _problem_count(summary: Dict[str, Any]) -> int:
        return sum(
            int(summary.get(key, 0) or 0)
            for key in ("failed", "partial", "unrecognized", "scan_errors", "invalid_paths")
        ) + int(bool(summary.get("cancelled")))

    @staticmethod
    def _format_duration(value: Any) -> str:
        try:
            seconds = max(0.0, float(value or 0))
        except (TypeError, ValueError):
            seconds = 0.0
        if seconds >= 3600:
            hours = int(seconds // 3600)
            minutes = int(seconds % 3600 // 60)
            remainder = round(seconds % 60, 1)
            return f"{hours} 小时 {minutes} 分 {remainder:g} 秒"
        if seconds >= 60:
            minutes = int(seconds // 60)
            remainder = round(seconds % 60, 1)
            return f"{minutes} 分 {remainder:g} 秒"
        return f"{round(seconds, 2):g} 秒"

    @staticmethod
    def _metric_card(title: str, primary: str, secondary: str) -> dict:
        return {
            "component": "VCol",
            "props": {"cols": 12, "sm": 6, "lg": 3},
            "content": [
                {
                    "component": "VCard",
                    "props": {"variant": "outlined", "class": "h-100"},
                    "content": [
                        {
                            "component": "VCardSubtitle",
                            "props": {"class": "pt-4"},
                            "text": title,
                        },
                        {
                            "component": "VCardTitle",
                            "props": {"class": "text-h6"},
                            "text": primary,
                        },
                        {
                            "component": "VCardText",
                            "props": {"class": "text-medium-emphasis pt-0"},
                            "text": secondary,
                        },
                    ],
                }
            ],
        }

    @classmethod
    def _overview_components(cls, summary: Dict[str, Any]) -> List[dict]:
        problems = cls._problem_count(summary)
        cards = {
            "component": "VRow",
            "props": {"class": "mt-1"},
            "content": [
                cls._metric_card(
                    "扫描范围",
                    f"{summary.get('targets', 0)} 个目标",
                    f"{summary.get('media_files', 0)} 个媒体文件",
                ),
                cls._metric_card(
                    "本轮分流",
                    f"{summary.get('eligible', 0)} 个待处理",
                    (
                        f"{summary.get('unchanged', 0)} 个目标缓存命中 | "
                        f"{summary.get('deferred', 0)} 个延后"
                    ),
                ),
                cls._metric_card(
                    "处理结果",
                    f"{summary.get('success', 0)} 个成功",
                    (
                        f"{problems} 项需处理 | "
                        f"{summary.get('deferred', 0)} 个延后"
                    ),
                ),
                cls._metric_card(
                    "总耗时",
                    cls._format_duration(summary.get("duration_seconds", 0)),
                    (
                        f"扫描 {cls._format_duration(summary.get('scan_seconds', 0))} | "
                        f"处理 {cls._format_duration(summary.get('process_seconds', 0))}"
                    ),
                ),
            ],
        }
        components = [cards, cls._cache_summary(summary), cls._eligibility_summary(summary)]

        scan_seconds = float(summary.get("scan_seconds", 0) or 0)
        process_seconds = float(summary.get("process_seconds", 0) or 0)
        measured = scan_seconds + process_seconds
        if measured:
            scan_is_slower = scan_seconds >= process_seconds
            dominant = "扫描媒体库" if scan_is_slower else "处理刮削目标"
            dominant_seconds = scan_seconds if scan_is_slower else process_seconds
            share = round(dominant_seconds / measured * 100)
            components.append(
                {
                    "component": "VAlert",
                    "props": {
                        "type": "warning" if share >= 70 else "info",
                        "variant": "tonal",
                        "title": f"主要耗时：{dominant}（{share}%）",
                        "text": (
                            "目标缓存命中可避免重复识别、下载和写入；"
                            "完整扫描仍会枚举媒体文件以发现新增或变化。"
                        ),
                    },
                }
            )
        return components

    @staticmethod
    def _cache_summary(summary: Dict[str, Any]) -> dict:
        target_problems = sum(
            int(summary.get(key, 0) or 0)
            for key in ("failed", "partial", "unrecognized")
        )
        rows = [
            {
                "component": "tr",
                "content": [
                    {"component": "td", "text": "刮削目标"},
                    {"component": "td", "text": f"{summary.get('unchanged', 0)} 个"},
                    {"component": "td", "text": f"{summary.get('eligible', 0)} 个"},
                    {
                        "component": "td",
                        "text": (
                            f"成功 {summary.get('success', 0)} | "
                            f"问题 {target_problems} | 延后 {summary.get('deferred', 0)}"
                        ),
                    },
                ],
            },
            {
                "component": "tr",
                "content": [
                    {"component": "td", "text": "NFO 文件"},
                    {"component": "td", "text": f"{summary.get('nfo_cached', 0)} 份"},
                    {"component": "td", "text": f"{summary.get('nfo_checked', 0)} 份"},
                    {
                        "component": "td",
                        "text": (
                            f"修复 {summary.get('nfo_updated', 0)} | "
                            f"预演 {summary.get('nfo_preview', 0)}"
                        ),
                    },
                ],
            },
        ]
        return {
            "component": "VSheet",
            "props": {"class": "mt-4", "color": "transparent"},
            "content": [
                {
                    "component": "div",
                    "props": {"class": "text-subtitle-1 font-weight-medium mb-2"},
                    "text": "缓存与实际处理",
                },
                {
                    "component": "VTable",
                    "props": {"density": "compact", "hover": True},
                    "content": [
                        {
                            "component": "thead",
                            "content": [
                                {
                                    "component": "tr",
                                    "content": [
                                        {"component": "th", "text": "对象"},
                                        {"component": "th", "text": "缓存命中"},
                                        {"component": "th", "text": "本轮待处理/检查"},
                                        {"component": "th", "text": "结果"},
                                    ],
                                }
                            ],
                        },
                        {"component": "tbody", "content": rows},
                    ],
                },
            ],
        }

    @staticmethod
    def _eligibility_summary(summary: Dict[str, Any]) -> dict:
        reasons = [
            ("eligible_new", "新增目标"),
            ("eligible_changed", "媒体文件变化"),
            ("eligible_retry", "上次未完成"),
            ("eligible_periodic", "目标周期复核"),
            ("eligible_nfo", "NFO 到期或变化"),
            ("eligible_policy", "写入策略变化"),
            ("eligible_forced", "强制处理"),
        ]
        rows = [
            {
                "component": "tr",
                "content": [
                    {"component": "td", "text": label},
                    {"component": "td", "text": f"{summary.get(key, 0)} 个"},
                ],
            }
            for key, label in reasons
            if int(summary.get(key, 0) or 0)
        ]
        content = [
            {
                "component": "div",
                "props": {"class": "text-subtitle-1 font-weight-medium mb-2"},
                "text": "为什么这些目标需要处理",
            }
        ]
        if rows:
            content.append(
                {
                    "component": "VTable",
                    "props": {"density": "compact", "hover": True},
                    "content": [
                        {
                            "component": "thead",
                            "content": [
                                {
                                    "component": "tr",
                                    "content": [
                                        {"component": "th", "text": "原因"},
                                        {"component": "th", "text": "目标数"},
                                    ],
                                }
                            ],
                        },
                        {"component": "tbody", "content": rows},
                    ],
                }
            )
        else:
            content.append(
                {
                    "component": "VAlert",
                    "props": {
                        "type": "info",
                        "variant": "tonal",
                        "text": "该运行记录由旧版产生；升级后的下一次运行开始统计具体原因。",
                    },
                }
            )
        return {
            "component": "VSheet",
            "props": {"class": "mt-4", "color": "transparent"},
            "content": content,
        }

    @staticmethod
    def _issue_items(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        stored_issues = summary.get("issues")
        if isinstance(stored_issues, list) and stored_issues:
            raw_items = list(stored_issues)
        else:
            raw_items = [
                dict(item)
                for item in summary.get("details") or []
                if item.get("status") in ("failed", "unrecognized", "partial", "cancelled")
            ]
            filtered = []
            for item in raw_items:
                path = str(item.get("path", "")).rstrip("/")
                has_more_specific = any(
                    other is not item
                    and other.get("status") == item.get("status")
                    and str(other.get("path", "")).startswith(f"{path}/")
                    for other in raw_items
                    if path
                )
                if not has_more_specific:
                    filtered.append(item)
            raw_items = filtered

        for failure in summary.get("failures") or []:
            raw_items.append(
                {
                    "status": "failed",
                    "target": "扫描或任务",
                    "path": failure.get("path", ""),
                    "files": 0,
                    "detail": failure.get("detail", ""),
                    "duration_seconds": 0,
                }
            )

        unique = []
        seen = set()
        for item in raw_items:
            key = (
                item.get("status", ""),
                item.get("path", ""),
                item.get("detail", ""),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    @staticmethod
    def _target_detail_items(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        details = list(summary.get("details") or [])
        if "issues" in summary:
            return details
        targets = []
        for item in details:
            path = str(item.get("path", "")).rstrip("/")
            has_parent = any(
                other is not item
                and other.get("status") == item.get("status")
                and path.startswith(f"{str(other.get('path', '')).rstrip('/')}/")
                for other in details
                if other.get("path")
            )
            if not has_parent:
                targets.append(item)
        return targets

    @staticmethod
    def _issues_panel(issues: List[Dict[str, Any]]) -> dict:
        labels = {
            "failed": "失败",
            "unrecognized": "未识别",
            "partial": "部分完成",
            "cancelled": "已取消",
        }
        grouped = {}
        for item in issues:
            grouped.setdefault(item.get("status", "failed"), []).append(item)
        panels = []
        for status in ("failed", "unrecognized", "partial", "cancelled"):
            items = grouped.get(status) or []
            if not items:
                continue
            rows = []
            for item in items:
                target = item.get("target") or "-"
                path = item.get("path", "")
                rows.append(
                    {
                        "component": "tr",
                        "content": [
                            {
                                "component": "td",
                                "props": {"class": "text-break"},
                                "text": path,
                            },
                            {
                                "component": "td",
                                "props": {"class": "text-break"},
                                "text": "-" if target == path else target,
                            },
                            {
                                "component": "td",
                                "props": {"class": "text-break"},
                                "text": item.get("detail", ""),
                            },
                            {
                                "component": "td",
                                "text": LibraryScraperFix._format_duration(
                                    item.get("duration_seconds", 0)
                                ),
                            },
                        ],
                    }
                )
            panels.append(
                {
                    "component": "VExpansionPanel",
                    "content": [
                        {
                            "component": "VExpansionPanelTitle",
                            "text": f"{labels[status]}（{len(items)} 条）",
                        },
                        {
                            "component": "VExpansionPanelText",
                            "content": [
                                LibraryScraperFix._table(
                                    ["具体文件或目标", "所属刮削目标", "原因", "耗时"],
                                    rows,
                                )
                            ],
                        },
                    ],
                }
            )
        return {
            "component": "VSheet",
            "props": {"class": "mt-4", "color": "transparent"},
            "content": [
                {
                    "component": "div",
                    "props": {"class": "text-subtitle-1 font-weight-medium mb-2"},
                    "text": f"需要处理（{len(issues)} 条记录）",
                },
                {
                    "component": "VExpansionPanels",
                    "props": {
                        "variant": "accordion",
                        "multiple": True,
                        "modelValue": list(range(len(panels))),
                    },
                    "content": panels,
                },
            ],
        }

    @staticmethod
    def _table(headers: List[str], rows: List[dict]) -> dict:
        return {
            "component": "VTable",
            "props": {"density": "compact", "hover": True},
            "content": [
                {
                    "component": "thead",
                    "content": [
                        {
                            "component": "tr",
                            "content": [
                                {"component": "th", "text": header}
                                for header in headers
                            ],
                        }
                    ],
                },
                {"component": "tbody", "content": rows},
            ],
        }

    @staticmethod
    def _details_panel(details: List[Dict[str, Any]]) -> dict:
        status_labels = {
            "success": "成功目标",
            "partial": "部分完成目标",
            "dry_run": "预演目标",
            "unrecognized": "未识别目标",
            "failed": "失败目标",
            "deferred": "延后目标",
            "cancelled": "取消目标",
        }
        grouped = {}
        for item in details:
            grouped.setdefault(item.get("status", ""), []).append(item)

        panels = []
        for status in (
            "failed",
            "unrecognized",
            "partial",
            "success",
            "dry_run",
            "deferred",
            "cancelled",
        ):
            items = grouped.get(status) or []
            if not items:
                continue
            rows = [
                {
                    "component": "tr",
                    "content": [
                        {
                            "component": "td",
                            "props": {"class": "text-break"},
                            "text": item.get("path", ""),
                        },
                        {"component": "td", "text": str(item.get("files", 0))},
                        {
                            "component": "td",
                            "text": LibraryScraperFix._format_duration(
                                item.get("duration_seconds", 0)
                            ),
                        },
                        {
                            "component": "td",
                            "props": {"class": "text-break"},
                            "text": item.get("detail", ""),
                        },
                    ],
                }
                for item in items
            ]
            panels.append(
                {
                    "component": "VExpansionPanel",
                    "content": [
                        {
                            "component": "VExpansionPanelTitle",
                            "text": f"{status_labels[status]}（{len(items)}）",
                        },
                        {
                            "component": "VExpansionPanelText",
                            "content": [
                                LibraryScraperFix._table(
                                    ["刮削目标", "媒体文件", "耗时", "结果说明"], rows
                                )
                            ],
                        },
                    ],
                }
            )
        return {
            "component": "VSheet",
            "props": {"class": "mt-4", "color": "transparent"},
            "content": [
                {
                    "component": "div",
                    "props": {"class": "text-subtitle-1 font-weight-medium mb-2"},
                    "text": f"目标结果（{len(details)} 个）",
                },
                {
                    "component": "VExpansionPanels",
                    "props": {
                        "variant": "accordion",
                        "multiple": True,
                        "modelValue": [],
                    },
                    "content": panels,
                },
            ],
        }

    @staticmethod
    def _slow_targets_panel(details: List[Dict[str, Any]]) -> Optional[dict]:
        slowest = sorted(
            (
                item
                for item in details
                if float(item.get("duration_seconds", 0) or 0) > 0
            ),
            key=lambda item: float(item.get("duration_seconds", 0) or 0),
            reverse=True,
        )[:5]
        if not slowest:
            return None
        rows = [
            {
                "component": "tr",
                "content": [
                    {
                        "component": "td",
                        "props": {"class": "text-break"},
                        "text": item.get("path", ""),
                    },
                    {
                        "component": "td",
                        "text": LibraryScraperFix._format_duration(
                            item.get("duration_seconds", 0)
                        ),
                    },
                    {"component": "td", "text": str(item.get("files", 0))},
                ],
            }
            for item in slowest
        ]
        return {
            "component": "VExpansionPanels",
            "props": {"variant": "accordion", "multiple": True, "modelValue": []},
            "content": [
                {
                    "component": "VExpansionPanel",
                    "content": [
                        {
                            "component": "VExpansionPanelTitle",
                            "text": f"耗时最久的目标（前 {len(slowest)} 个）",
                        },
                        {
                            "component": "VExpansionPanelText",
                            "content": [
                                LibraryScraperFix._table(
                                    ["刮削目标", "耗时", "媒体文件"], rows
                                )
                            ],
                        },
                    ],
                }
            ],
        }

    @staticmethod
    def _progress(callback, value: int, text: str, summary: Dict[str, Any]) -> None:
        if not callback:
            return
        data = {
            key: summary.get(key, 0)
            for key in (
                "media_files",
                "targets",
                "success",
                "partial",
                "dry_run",
                "failed",
                "unchanged",
            )
        }
        try:
            callback(value, text, data=data)
        except TypeError:
            try:
                callback(value, text)
            except Exception as err:
                logger.debug(f"更新任务进度失败：{err}")
        except Exception as err:
            logger.debug(f"更新任务进度失败：{err}")

    @staticmethod
    def _form_section(title: str, description: str, content: List[dict]) -> dict:
        return {
            "component": "VExpansionPanel",
            "content": [
                {"component": "VExpansionPanelTitle", "text": title},
                {
                    "component": "VExpansionPanelText",
                    "content": [
                        {
                            "component": "div",
                            "props": {"class": "text-body-2 text-medium-emphasis mb-4"},
                            "text": description,
                        },
                        *content,
                    ],
                },
            ],
        }

    @staticmethod
    def _switch(model: str, label: str, hint: str = "") -> dict:
        props = {"model": model, "label": label, "color": "primary"}
        if hint:
            props.update({"hint": hint, "persistentHint": True})
        return {
            "component": "VCol",
            "props": {"cols": 12, "md": 6},
            "content": [{"component": "VSwitch", "props": props}],
        }

    @staticmethod
    def _number_field(
        model: str,
        label: str,
        minimum: float,
        maximum: float,
        step: float = 1,
        hint: str = "",
    ) -> dict:
        props = {
            "model": model,
            "label": label,
            "type": "number",
            "min": minimum,
            "max": maximum,
            "step": step,
        }
        if hint:
            props.update({"hint": hint, "persistentHint": True})
        return {
            "component": "VCol",
            "props": {"cols": 12, "sm": 6, "md": 3},
            "content": [
                {
                    "component": "VTextField",
                    "props": props,
                }
            ],
        }

    @staticmethod
    def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
        try:
            result = int(value)
        except (TypeError, ValueError):
            result = default
        return max(minimum, min(maximum, result))

    @staticmethod
    def _bounded_float(
        value: Any, default: float, minimum: float, maximum: float
    ) -> float:
        try:
            result = float(value)
        except (TypeError, ValueError):
            result = default
        return max(minimum, min(maximum, result))

    def _current_config(self, force_full_scan: bool, clear_cache: bool) -> Dict[str, Any]:
        return {
            "enabled": self._enabled,
            "onlyonce": False,
            "cron": self._cron,
            "mode": self._mode,
            "scraper_paths": self._scraper_paths,
            "exclude_paths": self._exclude_paths,
            "dry_run": self._dry_run,
            "incremental": self._incremental,
            "force_full_scan": force_full_scan,
            "max_targets": self._max_targets,
            "interval_seconds": self._interval_seconds,
            "retry_count": self._retry_count,
            "full_scan_days": self._full_scan_days,
            "notify": self._notify,
            "repair_nfo_fields": self._repair_nfo_enabled,
            "nfo_audit_days": self._nfo_audit_days,
            "clear_cache": clear_cache,
        }

    @staticmethod
    def _default_config() -> Dict[str, Any]:
        return {
            "enabled": False,
            "onlyonce": False,
            "cron": "0 3 * * *",
            "mode": "",
            "scraper_paths": "",
            "exclude_paths": "",
            "dry_run": True,
            "incremental": True,
            "force_full_scan": False,
            "max_targets": 0,
            "interval_seconds": 0,
            "retry_count": 1,
            "full_scan_days": 7,
            "notify": True,
            "repair_nfo_fields": False,
            "nfo_audit_days": 30,
            "clear_cache": False,
        }

    @staticmethod
    def _new_scan_counters() -> Dict[str, Any]:
        return {
            "scan_errors": 0,
            "symlinks_skipped": 0,
            "excluded_dirs": 0,
            "excluded_files": 0,
            "failures": [],
        }

    def _new_summary(self, started_at: str) -> Dict[str, Any]:
        summary = {
            "started_at": started_at,
            "finished_at": None,
            "duration_seconds": 0,
            "scan_seconds": 0,
            "process_seconds": 0,
            "dry_run_enabled": self._dry_run,
            "cancelled": False,
            "media_files": 0,
            "targets": 0,
            "eligible": 0,
            "eligible_new": 0,
            "eligible_changed": 0,
            "eligible_retry": 0,
            "eligible_periodic": 0,
            "eligible_nfo": 0,
            "eligible_policy": 0,
            "eligible_forced": 0,
            "unchanged": 0,
            "deferred": 0,
            "success": 0,
            "partial": 0,
            "dry_run": 0,
            "unrecognized": 0,
            "failed": 0,
            "scraped_files": 0,
            "unrecognized_files": 0,
            "failed_files": 0,
            "scan_errors": 0,
            "unknown_type": 0,
            "forced_type_skipped": 0,
            "symlinks_skipped": 0,
            "excluded_roots": 0,
            "excluded_dirs": 0,
            "excluded_files": 0,
            "invalid_paths": 0,
            "stale_state_removed": 0,
            "nfo_checked": 0,
            "nfo_cached": 0,
            "nfo_preview": 0,
            "nfo_updated": 0,
            "nfo_titles_updated": 0,
            "nfo_overviews_updated": 0,
            "failures": [],
            "details": [],
            "issues": [],
        }
        return summary

    @staticmethod
    def _now() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")

    @staticmethod
    def _format_service_result(summary: Dict[str, Any]) -> str:
        if summary.get("dry_run_enabled"):
            return (
                f"预演 {summary['dry_run']} 个目标，失败 {summary['failed']} 个"
            )
        return (
            f"完成 {summary['success']} 个目标，部分完成 {summary['partial']} 个，"
            f"失败 {summary['failed']} 个"
        )

    @staticmethod
    def _format_notification(summary: Dict[str, Any]) -> str:
        mode = "预演" if summary.get("dry_run_enabled") else "执行"
        lines = [
            f"模式：{mode}",
            f"媒体文件：{summary.get('media_files', 0)}",
            f"刮削目标：{summary.get('targets', 0)}",
            f"待处理：{summary.get('eligible', 0)}",
            f"未变化跳过：{summary.get('unchanged', 0)}",
            f"成功：{summary.get('success', 0)}",
            f"部分完成：{summary.get('partial', 0)}",
            f"预演：{summary.get('dry_run', 0)}",
            f"未识别：{summary.get('unrecognized', 0)}",
            f"失败：{summary.get('failed', 0)}",
            f"延后：{summary.get('deferred', 0)}",
            f"耗时：{summary.get('duration_seconds', 0)} 秒",
            f"扫描：{summary.get('scan_seconds', 0)} 秒，处理：{summary.get('process_seconds', 0)} 秒",
        ]
        if summary.get("cancelled"):
            lines.append("状态：已取消")
        reason_labels = (
            ("eligible_new", "新增"),
            ("eligible_changed", "媒体变化"),
            ("eligible_retry", "上次未完成"),
            ("eligible_periodic", "周期复核"),
            ("eligible_nfo", "NFO 到期/变化"),
            ("eligible_policy", "策略变化"),
            ("eligible_forced", "强制处理"),
        )
        reasons = [
            f"{label} {summary.get(key, 0)}"
            for key, label in reason_labels
            if int(summary.get(key, 0) or 0)
        ]
        if reasons:
            lines.append(f"待处理原因：{'，'.join(reasons)}")
        if summary.get("nfo_checked") or summary.get("nfo_cached"):
            lines.append(
                "NFO 字段：检查 %s，缓存跳过 %s，预演 %s，已修复 %s（标题 %s，概要 %s）"
                % (
                    summary.get("nfo_checked", 0),
                    summary.get("nfo_cached", 0),
                    summary.get("nfo_preview", 0),
                    summary.get("nfo_updated", 0),
                    summary.get("nfo_titles_updated", 0),
                    summary.get("nfo_overviews_updated", 0),
                )
            )
        failures = summary.get("failures") or []
        if failures:
            lines.append("前几项问题：")
            for item in failures[:5]:
                lines.append(f"- {item.get('path')}: {item.get('detail')}")
        return "\n".join(lines)

    @staticmethod
    def _format_page_summary(summary: Dict[str, Any]) -> str:
        return (
            f"上次运行：{summary.get('finished_at') or summary.get('started_at')}\n"
            f"模式：{'预演' if summary.get('dry_run_enabled') else '执行'}\n"
            f"目标：{summary.get('targets', 0)}，成功：{summary.get('success', 0)}，"
            f"部分完成：{summary.get('partial', 0)}，"
            f"未识别：{summary.get('unrecognized', 0)}，失败：{summary.get('failed', 0)}\n"
            f"未变化跳过：{summary.get('unchanged', 0)}，耗时："
            f"{summary.get('duration_seconds', 0)} 秒"
            f"\n扫描：{summary.get('scan_seconds', 0)} 秒，处理："
            f"{summary.get('process_seconds', 0)} 秒"
            + (
                f"\nNFO：检查 {summary.get('nfo_checked', 0)}，缓存跳过 "
                f"{summary.get('nfo_cached', 0)}，修复 {summary.get('nfo_updated', 0)}"
                if summary.get("nfo_checked") or summary.get("nfo_cached")
                else ""
            )
        )
