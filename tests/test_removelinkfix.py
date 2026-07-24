import importlib.util
import sys
import tempfile
import types
import unittest
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

PLUGIN_PATH = Path(__file__).parents[1] / "plugins" / "removelinkfix" / "__init__.py"
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

    def test_history_reports_no_match(self):
        plugin = self.plugin()
        plugin._transferhistory = _HistoryStore()
        self.assertFalse(plugin.delete_history("/media/missing.mkv"))
        self.assertEqual(plugin._transferhistory.deleted, [])

    def test_episode_thumbnail_and_media_extension_guard(self):
        plugin = self.plugin()
        self.assertTrue(plugin._is_scrap_file(Path("episode-thumb-40")))
        self.assertFalse(plugin._is_scrap_file(Path("episode-thumb-final")))
        self.assertEqual(plugin._parse_custom_scrap_extensions("mkv, .jpg"), [".jpg"])

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


if __name__ == "__main__":
    unittest.main()
