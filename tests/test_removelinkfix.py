import importlib.util
import ast
import json
import sys
import tempfile
import types
import unittest
from datetime import datetime
from pathlib import Path


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


for package in ("app", "app.db", "app.plugins", "app.schemas", "app.core", "app.chain"):
    sys.modules.setdefault(package, types.ModuleType(package))

_module("app.db.transferhistory_oper", TransferHistoryOper=object)
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
    def __init__(self, record_id):
        self.id = record_id


class _HistoryStore:
    def __init__(self, src=None, dest=None):
        self.src = src
        self.dest = dest
        self.deleted = []

    def get_by_src(self, _path):
        return self.src

    def get_by_dest(self, _path):
        return self.dest

    def delete(self, record_id):
        self.deleted.append(record_id)


class RemoveLinkFixTests(unittest.TestCase):
    def plugin(self):
        plugin = RemoveLinkFix.__new__(RemoveLinkFix)
        plugin._delete_history = True
        plugin._custom_scrap_extensions = []
        plugin.exclude_dirs = ""
        plugin._notify = False
        return plugin

    def test_history_falls_back_to_destination(self):
        plugin = self.plugin()
        plugin._transferhistory = _HistoryStore(dest=_History(42))
        self.assertTrue(plugin.delete_history("/media/example.mkv"))
        self.assertEqual(plugin._transferhistory.deleted, [42])

    def test_history_prefers_exact_source_match(self):
        plugin = self.plugin()
        plugin._transferhistory = _HistoryStore(src=_History(7), dest=_History(42))
        self.assertTrue(plugin.delete_history("/downloads/example.mkv"))
        self.assertEqual(plugin._transferhistory.deleted, [7])

    def test_history_reports_no_match(self):
        plugin = self.plugin()
        plugin._transferhistory = _HistoryStore()
        self.assertFalse(plugin.delete_history("/media/missing.mkv"))
        self.assertEqual(plugin._transferhistory.deleted, [])

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
        self.assertTrue((ROOT / "icons" / metadata["icon"]).is_file())


if __name__ == "__main__":
    unittest.main()
