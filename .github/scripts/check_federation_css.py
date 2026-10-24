#!/usr/bin/env python3
"""检查 Vue 联邦插件是否把 Vuetify 基础 CSS 带入宿主页面。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

FEDERATION_CONFIG = re.compile(r"\bfederation\s*\(")
DYNAMIC_CSS = re.compile(r"dynamicLoadingCss\s*\(\s*\[([^]]*)]", re.DOTALL)
CSS_PATH = re.compile(r"['\"]([^'\"]+\.css)['\"]")
SELECTOR = re.compile(r"(?:^|})\s*([^@{}][^{}]*)\{", re.MULTILINE)
GLOBAL = re.compile(
    r"^(?:html\b|body\b|:root\b|\*\s*(?:$|[,>+~.#[:])|"
    r"\.v-|\.mdi-|\.rounded(?:\b|-)|\.elevation-\d+\b)"
)


def plugin_dirs(root: Path) -> list[Path]:
    found: set[Path] = set()
    for config in root.glob("plugins*/**/vite.config.*"):
        if "node_modules" not in config.parts and FEDERATION_CONFIG.search(
            config.read_text(encoding="utf-8")
        ):
            found.add(config.parent)
    for remote in root.glob("plugins*/**/remoteEntry.js"):
        if "node_modules" not in remote.parts and len(remote.relative_to(root).parts) >= 2:
            relative = remote.relative_to(root)
            found.add(root / relative.parts[0] / relative.parts[1])
    return sorted(found)


def css_files(remote: Path) -> list[Path]:
    source = remote.read_text(encoding="utf-8")
    paths: set[Path] = set()
    for source_list in DYNAMIC_CSS.findall(source):
        for value in CSS_PATH.findall(source_list):
            paths.add((remote.parent / value).resolve())
    return sorted(paths)


def global_selectors(css: Path) -> list[str]:
    source = re.sub(r"/\*.*?\*/", "", css.read_text(encoding="utf-8"), flags=re.DOTALL)
    violations: set[str] = set()
    for group in SELECTOR.findall(source):
        for value in group.split(","):
            normalized = re.sub(r"\s+", " ", value).strip()
            if GLOBAL.match(normalized):
                violations.add(normalized)
    return sorted(violations)


def check(root: Path) -> list[str]:
    errors: list[str] = []
    for directory in plugin_dirs(root):
        relative = directory.relative_to(root)
        package_name = {"plugins": "package.json", "plugins.v2": "package.v2.json", "plugins.v3": "package.v3.json"}.get(relative.parts[0])
        package = root / package_name if package_name else None
        if package is None or not package.is_file():
            errors.append(f"{relative}: 找不到市场索引")
        else:
            metadata = json.loads(package.read_text(encoding="utf-8"))
            match = next((value for key, value in metadata.items() if key.casefold() == directory.name.casefold()), None)
            if not isinstance(match, dict) or match.get("release") is not True:
                errors.append(f"{package_name}: 联邦插件 {directory.name} 必须设置 release=true")
        for shared in directory.glob("**/__federation_shared_vuetify/styles-*.css"):
            errors.append(f"{shared.relative_to(root)}: 不得发布 Vuetify 共享基础样式")
        remotes = [path for path in directory.glob("**/remoteEntry.js") if "node_modules" not in path.parts]
        for remote in remotes:
            for css in css_files(remote):
                try:
                    relative_css = css.relative_to(root)
                except ValueError:
                    errors.append(f"{remote.relative_to(root)}: CSS 引用越出仓库：{css}")
                    continue
                if not css.is_file():
                    errors.append(f"{remote.relative_to(root)}: CSS 文件不存在：{relative_css}")
                else:
                    selectors = global_selectors(css)
                    if selectors:
                        errors.append(f"{relative_css}: 包含未限定的宿主样式选择器：{', '.join(selectors[:3])}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    errors = check(args.root.resolve())
    if errors:
        print("联邦 CSS 门禁失败：")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("联邦 CSS 门禁通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
