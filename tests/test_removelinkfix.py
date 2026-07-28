import importlib.util
import ast
import json
import os
import struct
import sys
import tempfile
import threading
import types
import unittest
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


class _Logger:
    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


def _module(name, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


class _Dummy:
    SiteMessage = "site"
    DownloadFileDeleted = "downloadfile.deleted"


for package in (
    "app",
    "app.db",
    "app.db.models",
    "app.plugins",
    "app.schemas",
    "app.core",
    "app.chain",
):
    sys.modules.setdefault(package, types.ModuleType(package))

_module("app.db.transferhistory_oper", TransferHistoryOper=object)


class _DestinationColumn:
    def __eq__(self, destination):
        return destination


class _TransferHistoryModel:
    dest = _DestinationColumn()


_module("app.db.models.transferhistory", TransferHistory=_TransferHistoryModel)
_module("app.log", logger=_Logger())
_module("app.plugins", _PluginBase=object)
_module("app.schemas", NotificationType=_Dummy, FileItem=object)
_module("app.schemas.types", EventType=_Dummy)
_module("app.core.event", eventmanager=types.SimpleNamespace(send_event=lambda *args: None))
_module("app.chain.storage", StorageChain=object)
sys.modules["app"].schemas = sys.modules["app.schemas"]

ROOT = Path(__file__).parents[1]
PLUGIN_PATH = ROOT / "plugins.v2" / "removelinkfix" / "__init__.py"
SPEC = importlib.util.spec_from_file_location("removelinkfix", PLUGIN_PATH)
PLUGIN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PLUGIN
SPEC.loader.exec_module(PLUGIN)
RemoveLinkFix = PLUGIN.RemoveLinkFix


class _History:
    def __init__(
        self,
        record_id,
        src="/downloads/example.mkv",
        dest="/media/example.mkv",
        status=True,
        mode="link",
        download_hash="example-hash",
    ):
        self.id = record_id
        self.src = src
        self.dest = dest
        self.status = status
        self.mode = mode
        self.download_hash = download_hash


class _HistoryStore:
    def __init__(self, src=None, dest=None, histories=None):
        self.src = src
        self.dest = dest
        self.histories = list(histories or [])
        for history in (src, dest):
            if history and all(item.id != history.id for item in self.histories):
                self.histories.append(history)
        self.deleted = []
        self._db = _HistoryDatabase(self.histories)
        sys.modules["app.db"].ScopedSession = lambda: self._db

    def get(self, record_id):
        return next((item for item in self.histories if item.id == record_id), None)

    def get_by_src(self, path):
        return next((item for item in self.histories if item.src == path), None)

    def get_by_dest(self, path):
        return next((item for item in self.histories if item.dest == path), None)

    def list_success_by_src(self, path):
        return [
            item for item in self.histories if item.src == path and item.status is True
        ]

    def delete(self, record_id):
        self.deleted.append(record_id)


class _HistoryQuery:
    def __init__(self, histories):
        self.histories = histories
        self.destination = None
        self.maximum = None

    def filter(self, destination):
        self.destination = destination
        return self

    def limit(self, maximum):
        self.maximum = maximum
        return self

    def all(self):
        matches = [
            history
            for history in self.histories
            if history.dest == self.destination
        ]
        return matches[: self.maximum]


class _HistoryDatabase:
    def __init__(self, histories):
        self.histories = histories

    def query(self, _model):
        return _HistoryQuery(self.histories)

    def close(self):
        pass


class RemoveLinkFixTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        PLUGIN.eventmanager = types.SimpleNamespace(
            send_event=lambda event_type, data: self.events.append((event_type, data))
        )

    def plugin(self):
        plugin = RemoveLinkFix.__new__(RemoveLinkFix)
        plugin._delete_history = True
        plugin._delete_torrents = False
        plugin._delete_scrap_infos = False
        plugin._delayed_deletion = True
        plugin._delay_seconds = 30
        plugin._custom_scrap_extensions = []
        plugin.exclude_dirs = ""
        plugin.monitor_dirs = ""
        plugin._notify = False
        plugin._observer = []
        plugin._deletion_timer = None
        plugin._stop_event = threading.Event()
        plugin._lifecycle_lock = threading.Lock()
        plugin.deletion_queue = []
        plugin.file_state = {}
        return plugin

    def test_episode_thumbnail_and_media_extension_guard(self):
        plugin = self.plugin()
        self.assertTrue(plugin._is_scrap_file(Path("episode-thumb-40")))
        self.assertFalse(plugin._is_scrap_file(Path("episode-thumb-final")))
        self.assertEqual(
            plugin._parse_custom_scrap_extensions("mkv, .mp4, strm, .jpg"),
            [".jpg"],
        )

    def test_cleanup_stops_at_monitor_root(self):
        plugin = self.plugin()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "library"
            season = root / "show" / "Season 1"
            season.mkdir(parents=True)
            (season / "episode-thumb-1").touch()
            plugin.monitor_dirs = str(root)

            plugin.delete_empty_folders(season / "removed.mkv")

            self.assertTrue(root.exists())
            self.assertFalse((root / "show").exists())

    def test_symlink_blocks_directory_cleanup(self):
        plugin = self.plugin()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "library"
            season = root / "show" / "Season 1"
            season.mkdir(parents=True)
            target = Path(tmp) / "outside.nfo"
            target.touch()
            (season / "linked.nfo").symlink_to(target)
            plugin.monitor_dirs = str(root)

            plugin.delete_empty_folders(season / "removed.mkv")

            self.assertTrue(season.exists())
            self.assertTrue(target.exists())

    def test_video_or_unknown_file_blocks_directory_cleanup(self):
        plugin = self.plugin()
        for remaining_name in ("episode.mkv", "keep.me"):
            with self.subTest(remaining_name=remaining_name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "library"
                season = root / "show" / "Season 1"
                season.mkdir(parents=True)
                (season / remaining_name).touch()
                plugin.monitor_dirs = str(root)

                plugin.delete_empty_folders(season / "removed.mkv")

                self.assertTrue(season.exists())
                self.assertTrue((season / remaining_name).exists())

    def test_initial_scan_and_created_event_ignore_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "library"
            root.mkdir()
            target = Path(tmp) / "outside.mkv"
            target.touch()
            real_file = root / "real.mkv"
            real_file.touch()
            linked_file = root / "linked.mkv"
            linked_file.symlink_to(target)

            state = PLUGIN.updateState([str(root)])
            self.assertIn(str(real_file), state)
            self.assertNotIn(str(linked_file), state)

            sync = types.SimpleNamespace(exclude_keywords="", file_state={})
            handler = PLUGIN.FileMonitorHandler(str(root), sync)
            handler._add_file_to_state(linked_file)
            self.assertEqual(sync.file_state, {})

    def test_stopping_plugin_discards_pending_delayed_deletions(self):
        plugin = self.plugin()
        plugin._observer = []
        plugin._deletion_timer = None
        plugin.deletion_queue = [
            PLUGIN.DeletionTask(
                file_path=Path("/downloads/example.mkv"),
                deleted_dev=1,
                deleted_inode=2,
                deleted_add_time=datetime.now(),
                timestamp=datetime.now(),
            )
        ]
        executed = []
        plugin._execute_delayed_deletion = executed.append

        plugin.stop_service()

        self.assertEqual(executed, [])
        self.assertEqual(plugin.deletion_queue, [])

    def test_directory_deletion_never_emits_torrent_event(self):
        sync = types.SimpleNamespace(_delete_torrents=True)
        handler = PLUGIN.FileMonitorHandler("/media", sync)

        handler.on_deleted(
            types.SimpleNamespace(is_directory=True, src_path="/media/show")
        )

        self.assertEqual(self.events, [])

    def test_stop_service_waits_for_running_timer_callback(self):
        plugin = self.plugin()
        started = threading.Event()
        finished = threading.Event()

        def running_callback():
            started.set()
            plugin._stop_event.wait(2)
            finished.set()

        timer = threading.Timer(0, running_callback)
        plugin._deletion_timer = timer
        timer.start()
        self.assertTrue(started.wait(1))

        plugin.stop_service()

        self.assertTrue(finished.is_set())
        self.assertFalse(timer.is_alive())
        self.assertIsNone(plugin._deletion_timer)

    def test_library_target_deletion_preserves_source_history_and_torrent(self):
        for delayed in (False, True):
            with self.subTest(delayed=delayed), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root / "downloads" / "episode.mkv"
                destination = root / "media" / "episode.mkv"
                source.parent.mkdir()
                destination.parent.mkdir()
                source.write_bytes(b"episode")
                os.link(source, destination)
                target_stat = destination.lstat()
                history = _History(24007, src=str(source), dest=str(destination))
                store = _HistoryStore(src=history, dest=history)
                plugin = self.plugin()
                plugin._delayed_deletion = delayed
                plugin._delete_torrents = True
                plugin._transferhistory = store
                plugin.file_state = {
                    str(source): PLUGIN.FileInfo(
                        target_stat.st_dev, target_stat.st_ino, datetime.now()
                    ),
                    str(destination): PLUGIN.FileInfo(
                        target_stat.st_dev, target_stat.st_ino, datetime.now()
                    ),
                }

                destination.unlink()
                plugin.handle_deleted(destination)

                self.assertTrue(source.exists())
                self.assertEqual(store.deleted, [])
                self.assertEqual(plugin.deletion_queue, [])
                self.assertEqual(self.events, [])

    def test_source_deletion_requires_unique_successful_link_record(self):
        cases = (
            ([], "missing"),
            ([_History(1, status=False)], "failed"),
            ([_History(1, mode="copy")], "copy"),
            ([_History(1), _History(2)], "ambiguous"),
        )
        for histories, label in cases:
            with self.subTest(case=label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root / "downloads" / "episode.mkv"
                destination = root / "media" / "episode.mkv"
                source.parent.mkdir()
                destination.parent.mkdir()
                source.write_bytes(b"episode")
                os.link(source, destination)
                source_stat = source.lstat()
                for history in histories:
                    history.src = str(source)
                    history.dest = str(destination)
                store = _HistoryStore(histories=histories)
                plugin = self.plugin()
                plugin._delete_torrents = True
                plugin._transferhistory = store
                plugin.file_state = {
                    str(source): PLUGIN.FileInfo(
                        source_stat.st_dev, source_stat.st_ino, datetime.now()
                    ),
                    str(destination): PLUGIN.FileInfo(
                        source_stat.st_dev, source_stat.st_ino, datetime.now()
                    ),
                }

                source.unlink()
                plugin.handle_deleted(source)

                self.assertTrue(destination.exists())
                self.assertEqual(store.deleted, [])
                self.assertEqual(plugin.deletion_queue, [])
                self.assertEqual(self.events, [])

    def test_source_path_that_is_also_a_destination_is_protected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "stage" / "episode.mkv"
            destination = root / "media" / "episode.mkv"
            source.parent.mkdir()
            destination.parent.mkdir()
            source.write_bytes(b"episode")
            os.link(source, destination)
            source_stat = source.lstat()
            previous = _History(
                1,
                src=str(root / "original" / "episode.mkv"),
                dest=str(source),
                mode="move",
            )
            current = _History(2, src=str(source), dest=str(destination))
            store = _HistoryStore(histories=[previous, current])
            plugin = self.plugin()
            plugin._delete_torrents = True
            plugin._transferhistory = store
            plugin.file_state = {
                str(source): PLUGIN.FileInfo(
                    source_stat.st_dev, source_stat.st_ino, datetime.now()
                ),
                str(destination): PLUGIN.FileInfo(
                    source_stat.st_dev, source_stat.st_ino, datetime.now()
                ),
            }

            source.unlink()
            plugin.handle_deleted(source)

            self.assertTrue(destination.exists())
            self.assertEqual(plugin.deletion_queue, [])
            self.assertEqual(store.deleted, [])
            self.assertEqual(self.events, [])

    def test_duplicate_destination_records_cancel_source_deletion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "downloads" / "episode.mkv"
            destination = root / "media" / "episode.mkv"
            source.parent.mkdir()
            destination.parent.mkdir()
            source.write_bytes(b"episode")
            os.link(source, destination)
            source_stat = source.lstat()
            current = _History(1, src=str(source), dest=str(destination))
            duplicate = _History(
                2,
                src=str(root / "other" / "episode.mkv"),
                dest=str(destination),
            )
            store = _HistoryStore(histories=[current, duplicate])
            plugin = self.plugin()
            plugin._delete_torrents = True
            plugin._transferhistory = store
            plugin.file_state = {
                str(source): PLUGIN.FileInfo(
                    source_stat.st_dev, source_stat.st_ino, datetime.now()
                ),
                str(destination): PLUGIN.FileInfo(
                    source_stat.st_dev, source_stat.st_ino, datetime.now()
                ),
            }

            source.unlink()
            plugin.handle_deleted(source)

            self.assertTrue(destination.exists())
            self.assertEqual(plugin.deletion_queue, [])
            self.assertEqual(store.deleted, [])
            self.assertEqual(self.events, [])

    def test_verified_source_deletion_is_identical_in_immediate_and_delayed_modes(self):
        for delayed in (False, True):
            with self.subTest(delayed=delayed), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root / "downloads" / "episode.mkv"
                destination = root / "media" / "episode.mkv"
                source.parent.mkdir()
                destination.parent.mkdir()
                source.write_bytes(b"episode")
                os.link(source, destination)
                source_stat = source.lstat()
                history = _History(
                    7,
                    src=str(source),
                    dest=str(destination),
                    download_hash="torrent-hash",
                )
                store = _HistoryStore(src=history, dest=history)
                plugin = self.plugin()
                plugin._delayed_deletion = delayed
                plugin._delete_torrents = True
                plugin._transferhistory = store
                plugin.file_state = {
                    str(source): PLUGIN.FileInfo(
                        source_stat.st_dev, source_stat.st_ino, datetime.now()
                    ),
                    str(destination): PLUGIN.FileInfo(
                        source_stat.st_dev, source_stat.st_ino, datetime.now()
                    ),
                }

                source.unlink()
                plugin.handle_deleted(source)
                if delayed:
                    self.assertEqual(len(plugin.deletion_queue), 1)
                    plugin._execute_delayed_deletion(plugin.deletion_queue[0])

                self.assertFalse(destination.exists())
                self.assertEqual(store.deleted, [7])
                self.assertEqual(
                    self.events,
                    [
                        (
                            _Dummy.DownloadFileDeleted,
                            {"src": str(source), "hash": "torrent-hash"},
                        )
                    ],
                )
                self.events.clear()

    def test_recreated_source_path_cancels_verified_deletion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "downloads" / "episode.mkv"
            destination = root / "media" / "episode.mkv"
            source.parent.mkdir()
            destination.parent.mkdir()
            source.write_bytes(b"old")
            os.link(source, destination)
            source_stat = source.lstat()
            history = _History(7, src=str(source), dest=str(destination))
            store = _HistoryStore(src=history, dest=history)
            plugin = self.plugin()
            plugin._delete_torrents = True
            plugin._transferhistory = store
            plugin.file_state = {
                str(source): PLUGIN.FileInfo(
                    source_stat.st_dev, source_stat.st_ino, datetime.now()
                ),
                str(destination): PLUGIN.FileInfo(
                    source_stat.st_dev, source_stat.st_ino, datetime.now()
                ),
            }

            source.unlink()
            evidence = plugin._capture_source_deletion_evidence(source)
            source.write_bytes(b"replacement")
            result = plugin._execute_verified_source_deletion(
                source,
                source_stat.st_dev,
                source_stat.st_ino,
                evidence,
                "立即删除",
            )

            self.assertEqual(result, ([], 0, False))
            self.assertEqual(source.read_bytes(), b"replacement")
            self.assertTrue(destination.exists())
            self.assertEqual(store.deleted, [])
            self.assertEqual(self.events, [])

    def test_untracked_extra_hardlink_cancels_deletion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "downloads" / "episode.mkv"
            destination = root / "media" / "episode.mkv"
            hidden = root / "hidden" / "episode.mkv"
            source.parent.mkdir()
            destination.parent.mkdir()
            hidden.parent.mkdir()
            source.write_bytes(b"episode")
            os.link(source, destination)
            os.link(source, hidden)
            source_stat = source.lstat()
            history = _History(7, src=str(source), dest=str(destination))
            store = _HistoryStore(src=history, dest=history)
            plugin = self.plugin()
            plugin._delete_torrents = True
            plugin._transferhistory = store
            plugin.file_state = {
                str(source): PLUGIN.FileInfo(
                    source_stat.st_dev, source_stat.st_ino, datetime.now()
                ),
                str(destination): PLUGIN.FileInfo(
                    source_stat.st_dev, source_stat.st_ino, datetime.now()
                ),
            }

            source.unlink()
            plugin.handle_deleted(source)
            plugin._execute_delayed_deletion(plugin.deletion_queue[0])

            self.assertTrue(destination.exists())
            self.assertTrue(hidden.exists())
            self.assertEqual(store.deleted, [])
            self.assertEqual(self.events, [])

    def test_replaced_destination_inode_cancels_deletion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "downloads" / "episode.mkv"
            destination = root / "media" / "episode.mkv"
            source.parent.mkdir()
            destination.parent.mkdir()
            source.write_bytes(b"old")
            os.link(source, destination)
            source_stat = source.lstat()
            history = _History(7, src=str(source), dest=str(destination))
            store = _HistoryStore(src=history, dest=history)
            plugin = self.plugin()
            plugin._delete_torrents = True
            plugin._transferhistory = store
            plugin.file_state = {
                str(source): PLUGIN.FileInfo(
                    source_stat.st_dev, source_stat.st_ino, datetime.now()
                ),
                str(destination): PLUGIN.FileInfo(
                    source_stat.st_dev, source_stat.st_ino, datetime.now()
                ),
            }

            source.unlink()
            plugin.handle_deleted(source)
            destination.unlink()
            destination.write_bytes(b"replacement")
            plugin._execute_delayed_deletion(plugin.deletion_queue[0])

            self.assertEqual(destination.read_bytes(), b"replacement")
            self.assertEqual(store.deleted, [])
            self.assertEqual(self.events, [])

    def test_destination_replaced_after_validation_is_restored_not_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "downloads" / "episode.mkv"
            destination = root / "media" / "episode.mkv"
            source.parent.mkdir()
            destination.parent.mkdir()
            source.write_bytes(b"old")
            os.link(source, destination)
            source_stat = source.lstat()
            history = _History(7, src=str(source), dest=str(destination))
            store = _HistoryStore(src=history, dest=history)
            plugin = self.plugin()
            plugin._delete_torrents = True
            plugin._transferhistory = store
            plugin.file_state = {
                str(source): PLUGIN.FileInfo(
                    source_stat.st_dev, source_stat.st_ino, datetime.now()
                ),
                str(destination): PLUGIN.FileInfo(
                    source_stat.st_dev, source_stat.st_ino, datetime.now()
                ),
            }

            source.unlink()
            plugin.handle_deleted(source)
            validate_destination = plugin._validated_link_destination

            def replace_after_validation(evidence, deleted_dev, deleted_inode):
                result = validate_destination(evidence, deleted_dev, deleted_inode)
                destination.unlink()
                destination.write_bytes(b"replacement")
                return result

            plugin._validated_link_destination = replace_after_validation
            plugin._execute_delayed_deletion(plugin.deletion_queue[0])

            self.assertEqual(destination.read_bytes(), b"replacement")
            self.assertEqual(store.deleted, [])
            self.assertEqual(self.events, [])
            self.assertEqual(
                list(destination.parent.glob("*.removelinkfix-recovered-*")), []
            )

    def test_record_change_after_file_validation_blocks_event_and_history_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "downloads" / "episode.mkv"
            destination = root / "media" / "episode.mkv"
            source.parent.mkdir()
            destination.parent.mkdir()
            source.write_bytes(b"old")
            os.link(source, destination)
            source_stat = source.lstat()
            history = _History(7, src=str(source), dest=str(destination))
            store = _HistoryStore(src=history, dest=history)
            plugin = self.plugin()
            plugin._delete_torrents = True
            plugin._transferhistory = store
            plugin.file_state = {
                str(source): PLUGIN.FileInfo(
                    source_stat.st_dev, source_stat.st_ino, datetime.now()
                ),
                str(destination): PLUGIN.FileInfo(
                    source_stat.st_dev, source_stat.st_ino, datetime.now()
                ),
            }

            source.unlink()
            plugin.handle_deleted(source)
            validate_destination = plugin._validated_link_destination

            def change_record_after_validation(evidence, deleted_dev, deleted_inode):
                result = validate_destination(evidence, deleted_dev, deleted_inode)
                history.download_hash = "changed-hash"
                return result

            plugin._validated_link_destination = change_record_after_validation
            plugin._execute_delayed_deletion(plugin.deletion_queue[0])

            self.assertFalse(destination.exists())
            self.assertEqual(store.deleted, [])
            self.assertEqual(self.events, [])

    def test_scrap_file_deletion_never_enters_media_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            nfo = Path(tmp) / "episode.nfo"
            nfo.write_text("metadata", encoding="utf-8")
            nfo_stat = nfo.lstat()
            plugin = self.plugin()
            plugin._transferhistory = _HistoryStore()
            plugin.file_state = {
                str(nfo): PLUGIN.FileInfo(
                    nfo_stat.st_dev, nfo_stat.st_ino, datetime.now()
                )
            }

            nfo.unlink()
            plugin.handle_deleted(nfo)

            self.assertEqual(plugin.deletion_queue, [])
            self.assertEqual(self.events, [])

    def test_new_media_created_during_scrap_cleanup_is_preserved(self):
        plugin = self.plugin()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "library"
            season = root / "show" / "Season 1"
            season.mkdir(parents=True)
            (season / "episode.nfo").write_text("metadata", encoding="utf-8")
            plugin.monitor_dirs = str(root)
            snapshot_entries = plugin._snapshot_scrap_entries

            def snapshot_then_create(path):
                snapshot = snapshot_entries(path)
                (path / "new-episode.mkv").write_bytes(b"new")
                return snapshot

            plugin._snapshot_scrap_entries = snapshot_then_create

            plugin.delete_empty_folders(season / "removed.mkv")

            self.assertTrue((season / "new-episode.mkv").exists())
            self.assertTrue(season.exists())

    def test_v2_repository_structure_and_metadata_are_synced(self):
        package = json.loads((ROOT / "package.v2.json").read_text(encoding="utf-8"))
        metadata = package["RemoveLinkFix"]
        tree = ast.parse(PLUGIN_PATH.read_text(encoding="utf-8"))
        plugin_class = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "RemoveLinkFix"
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
        self.assertFalse((ROOT / "package.json").exists())
        self.assertFalse((ROOT / "plugins").exists())
        self.assertEqual(metadata["name"], class_values["plugin_name"])
        self.assertEqual(metadata["description"], class_values["plugin_desc"])
        self.assertEqual(metadata["version"], class_values["plugin_version"])
        self.assertEqual(metadata["icon"], class_values["plugin_icon"])
        self.assertEqual(metadata["author"], class_values["plugin_author"])
        self.assertEqual(metadata["level"], class_values["auth_level"])
        icon_url = metadata["icon"]
        self.assertEqual(
            icon_url,
            "https://raw.githubusercontent.com/Wning-ady/"
            "MoviePilot-Plugins-repair-shop/main/icons/Ombi_A.png",
        )
        icon_path = ROOT / "icons" / Path(urlparse(icon_url).path).name
        icon_data = icon_path.read_bytes()
        self.assertEqual(icon_data[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", icon_data[16:24])
        self.assertGreater(width, 0)
        self.assertGreater(height, 0)


if __name__ == "__main__":
    unittest.main()
