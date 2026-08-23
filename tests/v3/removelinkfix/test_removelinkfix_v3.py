import ast
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[3]
V2_PACKAGE = ROOT / "package.v2.json"
V3_PACKAGE = ROOT / "package.v3.json"
V3_PLUGIN = ROOT / "plugins.v3" / "removelinkfix" / "__init__.py"
V3_README = V3_PLUGIN.parent / "README.md"


class RemoveLinkFixV3StructureTests(unittest.TestCase):
    def test_v3_directory_and_metadata_are_synced(self):
        package = json.loads(V3_PACKAGE.read_text(encoding="utf-8"))
        metadata = package["RemoveLinkFix"]
        source = V3_PLUGIN.read_text(encoding="utf-8")
        tree = ast.parse(source)
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

        self.assertEqual(V3_PLUGIN.parent.name, plugin_class.name.lower())
        self.assertTrue(V3_README.is_file())
        self.assertEqual(metadata["name"], class_values["plugin_name"])
        self.assertEqual(metadata["description"], class_values["plugin_desc"])
        self.assertEqual(metadata["version"], class_values["plugin_version"])
        self.assertEqual(metadata["author"], class_values["plugin_author"])
        self.assertEqual(metadata["level"], class_values["auth_level"])
        self.assertEqual(metadata["system_version"], ">=3.0.0")

        v2_metadata = json.loads(V2_PACKAGE.read_text(encoding="utf-8"))["RemoveLinkFix"]
        self.assertFalse(v2_metadata["v3"])

    def test_v3_uses_current_public_imports(self):
        source = V3_PLUGIN.read_text(encoding="utf-8")
        self.assertIn("from app.db.oper.transferhistory import TransferHistoryOper", source)
        self.assertIn("from app.sdk.config import settings", source)
        self.assertIn("from app.sdk.events import eventmanager", source)
        self.assertIn("from app.sdk.logging import logger", source)
        for legacy_import in (
            "app.core.",
            "app.helper.",
            "app.log",
            "app.db.transferhistory_oper",
        ):
            self.assertNotIn(legacy_import, source)


if __name__ == "__main__":
    unittest.main()
