import ast
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
V2_PACKAGE = ROOT / "package.v2.json"
V3_PACKAGE = ROOT / "package.v3.json"
V3_PLUGIN = ROOT / "plugins.v3" / "libraryscraperfix" / "__init__.py"


class LibraryScraperFixV3StructureTests(unittest.TestCase):
    def test_v3_package_and_class_metadata_are_synced(self):
        package = json.loads(V3_PACKAGE.read_text(encoding="utf-8"))
        metadata = package["LibraryScraperFix"]
        tree = ast.parse(V3_PLUGIN.read_text(encoding="utf-8"))
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

        self.assertEqual(V3_PLUGIN.parent.name, plugin_class.name.lower())
        self.assertEqual(metadata["name"], class_values["plugin_name"])
        self.assertEqual(metadata["description"], class_values["plugin_desc"])
        self.assertEqual(metadata["version"], class_values["plugin_version"])
        self.assertEqual(metadata["author"], class_values["plugin_author"])
        self.assertEqual(metadata["level"], class_values["auth_level"])
        self.assertTrue(metadata["release"])
        self.assertEqual(metadata["system_version"], ">=3.0.0")

        v2_metadata = json.loads(V2_PACKAGE.read_text(encoding="utf-8"))[
            "LibraryScraperFix"
        ]
        self.assertFalse(v2_metadata["v3"])

    def test_v3_uses_explicit_identity_and_scraping_chain(self):
        source = V3_PLUGIN.read_text(encoding="utf-8")
        self.assertIn("from app.sdk.config import settings", source)
        self.assertIn("from app.sdk.media import MetaInfoPath, NfoReader", source)
        self.assertIn("from app.sdk.logging import logger", source)
        self.assertIn("from app.db.oper.transferhistory import TransferHistoryOper", source)
        self.assertIn("from app.chain.scraping import ScrapingChain, scraping_lock", source)
        self.assertIn("copy(ScrapingChain())", source)
        self.assertIn("get_by_media_identity", source)
        for legacy_import in (
            "app.core.",
            "app.helper.",
            "app.utils.",
            "app.log",
            "app.db.transferhistory_oper",
        ):
            self.assertNotIn(legacy_import, source)

        tree = ast.parse(source)
        recognition_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "recognize_media"
        ]
        self.assertGreaterEqual(len(recognition_calls), 3)
        for call in recognition_calls:
            keyword_names = {keyword.arg for keyword in call.keywords}
            self.assertNotIn("tmdbid", keyword_names)
            self.assertNotIn("doubanid", keyword_names)

    def test_v3_page_prioritizes_summary_and_paginates_details(self):
        source = V3_PLUGIN.read_text(encoding="utf-8")
        tree = ast.parse(source)
        plugin_class = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "LibraryScraperFix"
        )
        get_page = next(
            node
            for node in plugin_class.body
            if isinstance(node, ast.FunctionDef) and node.name == "get_page"
        )
        calls = [
            (node.func.attr, node.lineno)
            for node in ast.walk(get_page)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"_overview_components", "_issue_items"}
        ]
        lines = dict(calls)
        self.assertLess(lines["_overview_components"], lines["_issue_items"])
        self.assertIn('"modelValue": [0] if len(panels) == 1 else []', source)
        self.assertIn("page_size = 20", source)

    def test_v3_exposes_vue_federation_contract(self):
        source = V3_PLUGIN.read_text(encoding="utf-8")
        self.assertIn('return "vue", "dist/assets"', source)
        self.assertIn('"nav_key": "main"', source)
        self.assertIn('"path": "/history"', source)
        remote_entry = V3_PLUGIN.parent / "dist" / "assets" / "remoteEntry.js"
        self.assertTrue(remote_entry.is_file())
        self.assertIn('"./Config"', remote_entry.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
