import ast
import importlib.util
import json
import sys
import tempfile
import threading
import types
import unittest
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from unittest import mock


class _Logger:
    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


def _module(name, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


class _MediaType(Enum):
    MOVIE = "电影"
    TV = "电视剧"
    UNKNOWN = "未知"


class _NotificationType:
    Plugin = "plugin"


class _FileItem:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _MetaInfoPath:
    def __init__(self, path):
        path = Path(path)
        if "UNKNOWN" in path.name:
            self.type = _MediaType.UNKNOWN
        elif "S0" in path.name or _MediaType.TV.value in path.parts:
            self.type = _MediaType.TV
        else:
            self.type = _MediaType.MOVIE
        self.tmdbid = None


class _NfoReader:
    def __init__(self, _path):
        pass

    def get_element_value(self, _xpath):
        return None


class _Policy:
    def __init__(self, is_skip=False, is_overwrite=True):
        self.is_skip = is_skip
        self.is_overwrite = is_overwrite
        self.type = types.SimpleNamespace(value="movie")
        self.metadata = types.SimpleNamespace(value="nfo")
        self.policy = types.SimpleNamespace(value="overwrite")


class _Policies:
    def __init__(self, option=None):
        self._option = option or _Policy()

    def option(self, *_args, **_kwargs):
        return self._option


class _MediaChain:
    instances = {}

    def __new__(cls):
        if cls not in cls.instances:
            instance = super().__new__(cls)
            instance.scraping_policies = _Policies()
            instance.calls = []
            cls.instances[cls] = instance
        return cls.instances[cls]

    def scrape_metadata(self, **kwargs):
        self.calls.append(kwargs)

    def __copy__(self):
        copied = object.__new__(type(self))
        copied.__dict__ = self.__dict__.copy()
        return copied


class _CronTrigger:
    @staticmethod
    def from_crontab(value):
        if len(str(value).split()) != 5:
            raise ValueError("invalid cron")
        return value


class _Scheduler:
    def __init__(self, **_kwargs):
        self.running = False
        self.jobs = []

    def add_job(self, **kwargs):
        self.jobs.append(kwargs)

    def start(self):
        self.running = True

    def remove_all_jobs(self):
        self.jobs = []

    def shutdown(self, wait=False):
        self.running = False


class _PluginBase:
    pass


for package in (
    "app",
    "app.chain",
    "app.core",
    "app.db",
    "app.helper",
    "app.plugins",
    "app.schemas",
    "apscheduler",
    "apscheduler.schedulers",
    "apscheduler.schedulers.background",
    "apscheduler.triggers",
    "apscheduler.triggers.cron",
):
    sys.modules.setdefault(package, types.ModuleType(package))

settings = types.SimpleNamespace(
    TZ="UTC",
    RMT_MEDIAEXT=[".mkv", ".mp4"],
    TV_RENAME_FORMAT="{{title}}/Season {{season}}/{{name}}",
    MOVIE_RENAME_FORMAT="{{title}}/{{name}}",
    SCRAP_FOLLOW_TMDB=True,
)

_module("app.chain.media", MediaChain=_MediaChain, scraping_lock=threading.Lock())
_module("app.core.config", settings=settings)
_module("app.core.metainfo", MetaInfoPath=_MetaInfoPath)
_module("app.db.transferhistory_oper", TransferHistoryOper=object)
_module("app.helper.nfo", NfoReader=_NfoReader)
_module("app.log", logger=_Logger())
_module("app.plugins", _PluginBase=_PluginBase)
_module("app.schemas", MediaType=_MediaType, NotificationType=_NotificationType, FileItem=_FileItem)
sys.modules["app"].schemas = sys.modules["app.schemas"]
_module("apscheduler.schedulers.background", BackgroundScheduler=_Scheduler)
_module("apscheduler.triggers.cron", CronTrigger=_CronTrigger)
_module("pytz", timezone=lambda _name: timezone.utc)

ROOT = Path(__file__).parents[1]
PLUGIN_PATH = ROOT / "plugins.v2" / "libraryscraperfix" / "__init__.py"
SPEC = importlib.util.spec_from_file_location("libraryscraperfix", PLUGIN_PATH)
PLUGIN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PLUGIN
SPEC.loader.exec_module(PLUGIN)
LibraryScraperFix = PLUGIN.LibraryScraperFix
ScrapeOutcome = PLUGIN.ScrapeOutcome
ScrapeTarget = PLUGIN.ScrapeTarget


class LibraryScraperFixTests(unittest.TestCase):
    def plugin(self):
        plugin = LibraryScraperFix.__new__(LibraryScraperFix)
        plugin._enabled = False
        plugin._onlyonce = False
        plugin._cron = "0 3 * * *"
        plugin._mode = ""
        plugin._scraper_paths = ""
        plugin._exclude_paths = ""
        plugin._dry_run = True
        plugin._incremental = True
        plugin._force_full_scan = False
        plugin._max_targets = 0
        plugin._interval_seconds = 0
        plugin._retry_count = 0
        plugin._full_scan_days = 7
        plugin._notify = False
        plugin._cancel_event = threading.Event()
        plugin._running_status = {}
        plugin.get_data_path = self._test_data_path
        return plugin

    @staticmethod
    def _test_data_path():
        path = Path(tempfile.gettempdir()) / "libraryscraperfix-tests"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def test_v2_repository_structure_and_metadata_are_synced(self):
        package = json.loads((ROOT / "package.v2.json").read_text(encoding="utf-8"))
        metadata = package["LibraryScraperFix"]
        tree = ast.parse(PLUGIN_PATH.read_text(encoding="utf-8"))
        plugin_class = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "LibraryScraperFix"
        )
        class_values = {}
        for node in plugin_class.body:
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
            ):
                try:
                    class_values[node.targets[0].id] = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    continue

        self.assertEqual(PLUGIN_PATH.parent.name, plugin_class.name.lower())
        self.assertEqual(metadata["name"], class_values["plugin_name"])
        self.assertEqual(metadata["description"], class_values["plugin_desc"])
        self.assertEqual(metadata["version"], class_values["plugin_version"])
        self.assertEqual(metadata["author"], class_values["plugin_author"])
        self.assertEqual(metadata["level"], class_values["auth_level"])

    def test_form_defaults_cover_every_config_model(self):
        form, defaults = self.plugin().get_form()
        models = set()

        def visit(value):
            if isinstance(value, dict):
                model = value.get("props", {}).get("model")
                if model:
                    models.add(model)
                for item in value.values():
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(form)
        self.assertEqual(models, set(defaults))
        self.assertTrue(defaults["dry_run"])
        self.assertFalse(defaults["enabled"])

    def test_path_parser_supports_forced_type_and_literal_hash(self):
        path, mtype = LibraryScraperFix._parse_scraper_line("/media/tv#电视剧")
        self.assertEqual(path, Path("/media/tv"))
        self.assertEqual(mtype, _MediaType.TV)

        with tempfile.TemporaryDirectory() as tmp:
            literal = Path(tmp) / "media#archive"
            literal.mkdir()
            path, mtype = LibraryScraperFix._parse_scraper_line(str(literal))
            self.assertEqual(path, literal)
            self.assertIsNone(mtype)

            chinese_literal = Path(tmp) / "archive#电影"
            chinese_literal.mkdir()
            path, mtype = LibraryScraperFix._parse_scraper_line(str(chinese_literal))
            self.assertEqual(path, chinese_literal)
            self.assertIsNone(mtype)

        with self.assertRaisesRegex(ValueError, "未知媒体类型"):
            LibraryScraperFix._parse_scraper_line("/missing/media#综艺")

    def test_scan_prunes_exclusions_and_symlinks(self):
        plugin = self.plugin()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            allowed = root / "allowed"
            excluded = root / "excluded"
            outside = Path(tmp) / "outside"
            allowed.mkdir(parents=True)
            excluded.mkdir()
            outside.mkdir()
            (allowed / "movie.mkv").touch()
            (excluded / "secret.mkv").touch()
            (outside / "linked.mkv").touch()
            (root / "linked-dir").symlink_to(outside, target_is_directory=True)

            counters = plugin._new_scan_counters()
            files = list(
                plugin._iter_media_files(
                    root,
                    [plugin._normalize_path(excluded)],
                    {".mkv"},
                    counters,
                    threading.Event(),
                )
            )

            self.assertEqual(files, [allowed / "movie.mkv"])
            self.assertEqual(counters["excluded_dirs"], 1)
            self.assertEqual(counters["symlinks_skipped"], 1)

    def test_discovery_deduplicates_and_aggregates_directory_fingerprint(self):
        plugin = self.plugin()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / _MediaType.TV.value
            season = root / "Show (2026)" / "Season 1"
            season.mkdir(parents=True)
            first = season / "Show.S01E01.mkv"
            second = season / "Show.S01E02.mkv"
            first.write_bytes(b"123")
            second.write_bytes(b"45678")
            plugin._scraper_paths = str(root)
            summary = plugin._new_summary(plugin._now())

            targets = plugin._discover_targets(
                [], summary, threading.Event(), progress_callback=None
            )

            self.assertEqual(len(targets), 1)
            target = next(iter(targets.values()))
            self.assertEqual(
                target.path, plugin._normalize_path(root) / "Show (2026)"
            )
            self.assertEqual(target.file_count, 2)
            self.assertEqual(target.total_size, 8)

    def test_unknown_media_type_is_blocked(self):
        plugin = self.plugin()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "library"
            root.mkdir()
            (root / "UNKNOWN.mkv").touch()
            plugin._scraper_paths = str(root)
            summary = plugin._new_summary(plugin._now())

            targets = plugin._discover_targets([], summary, threading.Event())

            self.assertEqual(targets, {})
            self.assertEqual(summary["unknown_type"], 1)

    def test_invalid_nfo_id_preserves_filename_tmdb_id(self):
        plugin = self.plugin()
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "Movie.mkv"
            nfo = media.with_suffix(".nfo")
            media.touch()
            nfo.write_text("broken", encoding="utf-8")

            with mock.patch.object(PLUGIN, "NfoReader", _NfoReader):
                result = plugin._tmdbid_for_target(
                    media, _MediaType.MOVIE, plugin._target_file, 123
                )

            self.assertEqual(result, 123)

    def test_valid_nfo_id_overrides_filename_tmdb_id(self):
        class Reader:
            def __init__(self, _path):
                pass

            def get_element_value(self, xpath):
                return "456" if xpath == "tmdbid" else None

        plugin = self.plugin()
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "Movie.mkv"
            media.touch()
            media.with_suffix(".nfo").touch()

            with mock.patch.object(PLUGIN, "NfoReader", Reader):
                result = plugin._tmdbid_for_target(
                    media, _MediaType.MOVIE, plugin._target_file, 123
                )

            self.assertEqual(result, 456)

    def test_tv_file_uses_nearest_tvshow_nfo_not_episode_nfo(self):
        class Reader:
            def __init__(self, path):
                self.path = Path(path)

            def get_element_value(self, xpath):
                if xpath != "tmdbid":
                    return None
                return "123" if self.path.name == "tvshow.nfo" else "6139006"

        plugin = self.plugin()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Show (2026)"
            season = root / "Season 1"
            season.mkdir(parents=True)
            media = season / "Show.S01E01.mkv"
            media.touch()
            media.with_suffix(".nfo").touch()
            (root / "tvshow.nfo").touch()

            with mock.patch.object(PLUGIN, "NfoReader", Reader):
                result = plugin._tmdbid_for_target(
                    media, _MediaType.TV, plugin._target_file, None, root
                )

            self.assertEqual(result, 123)

    def test_tv_file_does_not_use_episode_nfo_as_series_id(self):
        class Reader:
            def __init__(self, _path):
                pass

            def get_element_value(self, xpath):
                return "6139006" if xpath == "tmdbid" else None

        plugin = self.plugin()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Show (2026)"
            season = root / "Season 1"
            season.mkdir(parents=True)
            media = season / "Show.S01E01.mkv"
            media.touch()
            media.with_suffix(".nfo").touch()

            with mock.patch.object(PLUGIN, "NfoReader", Reader):
                result = plugin._tmdbid_for_target(
                    media, _MediaType.TV, plugin._target_file, 456, root
                )

            self.assertEqual(result, 456)

    def test_non_overwrite_policy_preserves_skip_but_disables_overwrite(self):
        overwrite = _Policy(is_skip=False, is_overwrite=True)
        wrapped = PLUGIN._NonOverwritingPolicies(_Policies(overwrite)).option(
            "movie", "nfo"
        )
        self.assertFalse(wrapped.is_skip)
        self.assertFalse(wrapped.is_overwrite)

        skip = _Policy(is_skip=True, is_overwrite=False)
        wrapped_skip = PLUGIN._NonOverwritingPolicies(_Policies(skip)).option(
            "movie", "nfo"
        )
        self.assertTrue(wrapped_skip.is_skip)
        self.assertFalse(wrapped_skip.is_overwrite)

    def test_metadata_policy_is_restored_after_scrape(self):
        plugin = self.plugin()
        media_chain = _MediaChain()
        original = _Policies()
        media_chain.scraping_policies = original

        with plugin._metadata_chain(threading.Event()) as active_chain:
            self.assertIsNot(active_chain, media_chain)
            self.assertIsNot(active_chain.scraping_policies, original)
            self.assertIs(media_chain.scraping_policies, original)

        self.assertIs(media_chain.scraping_policies, original)

    def test_incremental_cache_only_skips_recent_success(self):
        plugin = self.plugin()
        target = ScrapeTarget(
            path=Path("/media/Movie"),
            mtype=_MediaType.MOVIE,
            target_type="dir",
            source_root=Path("/media"),
            file_count=1,
            total_size=10,
            max_mtime_ns=20,
        )
        state = {
            target.key: {
                "fingerprint": target.fingerprint,
                "status": "success",
                "mode": "",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        }
        self.assertTrue(plugin._should_skip_target(target, state))

        state[target.key]["status"] = "dry_run"
        self.assertFalse(plugin._should_skip_target(target, state))
        state[target.key]["status"] = "success"
        plugin._force_full_scan = True
        self.assertFalse(plugin._should_skip_target(target, state))

    def test_partial_fallback_is_not_cached_as_success(self):
        plugin = self.plugin()
        plugin._dry_run = False
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "电视剧"
            season = root / "Show" / "Season 1"
            season.mkdir(parents=True)
            (season / "Show.S01E01.mkv").touch()
            (season / "Show.S01E02.mkv").touch()
            target = ScrapeTarget(
                path=root / "Show",
                mtype=_MediaType.TV,
                target_type=plugin._target_dir,
                source_root=root,
                file_count=2,
            )

            with mock.patch.object(
                plugin, "_scrape_one", side_effect=[False, True, False]
            ):
                outcome = plugin._scrape_target(target, [], threading.Event())

        self.assertEqual(outcome.status, "partial")
        self.assertEqual(outcome.scraped_files, 1)
        self.assertEqual(outcome.unrecognized_files, 1)
        state = {target.key: plugin._state_entry(target, outcome.status)}
        self.assertFalse(plugin._should_skip_target(target, state))

    def test_scrape_target_passes_cancel_event_before_source_root(self):
        plugin = self.plugin()
        target = ScrapeTarget(
            path=Path("/media/Show.S01E01.mkv"),
            mtype=_MediaType.TV,
            target_type=plugin._target_file,
            source_root=Path("/media"),
        )
        cancel_event = threading.Event()

        with mock.patch.object(plugin, "_scrape_one", return_value=True) as scrape:
            outcome = plugin._scrape_target(target, [], cancel_event)

        self.assertEqual(outcome.status, "success")
        args = scrape.call_args.args
        self.assertIs(args[4], cancel_event)
        self.assertEqual(args[5], target.source_root)

    def test_stale_incremental_state_is_pruned_only_after_clean_scan(self):
        target = ScrapeTarget(
            path=Path("/media/Movie"),
            mtype=_MediaType.MOVIE,
            target_type="dir",
            source_root=Path("/media"),
        )
        state = {target.key: {}, "deleted": {}}
        summary = {"scan_errors": 0, "invalid_paths": 0}

        LibraryScraperFix._prune_scan_state(state, {target.key: target}, summary)

        self.assertNotIn("deleted", state)
        self.assertEqual(summary["stale_state_removed"], 1)

        state["keep-on-error"] = {}
        summary["scan_errors"] = 1
        LibraryScraperFix._prune_scan_state(state, {target.key: target}, summary)
        self.assertIn("keep-on-error", state)

    def test_file_lock_rejects_second_instance_across_reload_boundary(self):
        first = self.plugin()
        second = self.plugin()
        acquired, lock_fd = first._acquire_run_file_lock()
        self.assertTrue(acquired)
        try:
            acquired_again, second_fd = second._acquire_run_file_lock()
            self.assertFalse(acquired_again)
            self.assertIsNone(second_fd)
        finally:
            first._release_run_file_lock(lock_fd)

    def test_dry_run_builds_baseline_without_calling_scraper(self):
        plugin = self.plugin()
        data = {}
        plugin.get_data = lambda key: data.get(key)
        plugin.save_data = lambda key, value: data.__setitem__(key, value)
        plugin.post_message = lambda **_kwargs: None
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "电影" / "Movie (2026)"
            root.mkdir(parents=True)
            (root / "Movie.mkv").write_bytes(b"content")
            plugin._scraper_paths = str(Path(tmp) / "电影")
            with mock.patch.object(
                plugin,
                "_run_target_with_retry",
                side_effect=AssertionError("dry-run must not scrape"),
            ):
                success, message = plugin.run()

        self.assertTrue(success)
        self.assertIn("预演", message)
        self.assertEqual(data[plugin._last_run_key]["dry_run"], 1)
        state = data[plugin._state_key]
        self.assertEqual(next(iter(state.values()))["status"], "dry_run")

    def test_force_full_scan_is_consumed_only_when_run_starts(self):
        plugin = self.plugin()
        updates = []
        plugin._scheduler = None
        plugin.update_config = updates.append
        plugin.init_plugin({"force_full_scan": True, "dry_run": True})
        self.assertTrue(plugin._force_full_scan)
        self.assertEqual(updates, [])

        data = {}
        plugin.get_data = lambda key: data.get(key)
        plugin.save_data = lambda key, value: data.__setitem__(key, value)
        plugin.post_message = lambda **_kwargs: None
        plugin.run()

        self.assertFalse(plugin._force_full_scan)
        self.assertEqual(updates[-1]["force_full_scan"], False)

    def test_cancelled_run_reports_failure_status(self):
        plugin = self.plugin()
        data = {}
        plugin.get_data = lambda key: data.get(key)
        plugin.save_data = lambda key, value: data.__setitem__(key, value)
        plugin.post_message = lambda **_kwargs: None
        plugin._cancel_event.set()

        success, message = plugin.run()

        self.assertFalse(success)
        self.assertEqual(message, "任务已取消")
        self.assertTrue(data[plugin._last_run_key]["cancelled"])

    def test_cancel_during_last_target_does_not_write_success_cache(self):
        plugin = self.plugin()
        plugin._dry_run = False
        data = {}
        plugin.get_data = lambda key: data.get(key)
        plugin.save_data = lambda key, value: data.__setitem__(key, value)
        plugin.post_message = lambda **_kwargs: None
        target = ScrapeTarget(
            path=Path("/media/Movie"),
            mtype=_MediaType.MOVIE,
            target_type="dir",
            source_root=Path("/media"),
            file_count=1,
        )
        plugin._discover_targets = lambda *_args, **_kwargs: {target.key: target}

        def finish_after_cancel(*_args, **_kwargs):
            plugin._cancel_event.set()
            return ScrapeOutcome(status="success", scraped_files=1)

        plugin._run_target_with_retry = finish_after_cancel

        success, _message = plugin.run()

        self.assertFalse(success)
        self.assertTrue(data[plugin._last_run_key]["cancelled"])
        self.assertEqual(data[plugin._last_run_key]["success"], 0)
        self.assertEqual(data[plugin._state_key][target.key]["status"], "cancelled")

    def test_run_lock_rejects_overlapping_trigger(self):
        plugin = self.plugin()
        self.assertTrue(plugin._run_lock.acquire(blocking=False))
        try:
            self.assertEqual(plugin.run(), (False, "已有任务运行"))
        finally:
            plugin._run_lock.release()


if __name__ == "__main__":
    unittest.main()
