# LibraryScraperFix V3

MoviePilot V3“媒体库刮削(魔改版)”安全增量插件。

V3 版本：`3.1.1`。使用 Vue 联邦详情页和侧栏全页，支持运行摘要、路径搜索、状态筛选和目标分页。

## Vue 联邦页面

- 侧栏入口：整理 → **媒体库刮削**（`nav_key=main`）。
- 联邦暴露：`./Page`、`./Config`、`./AppPage`。
- 数据接口：`GET /api/v1/plugin/LibraryScraperFix/history`，使用宿主 Bearer 认证。
- 页面默认显示最近一次运行，也可以切换最近 20 次运行记录。
- 运行摘要置顶显示扫描范围、缓存命中、成功/问题数量和分段耗时。
- 目标结果支持路径搜索、状态筛选和每页 20 条分页；问题明细和 NFO 实际字段变更单独展示。
- 长路径和 NFO 长文本自动换行，预演状态与实际写入状态明确区分。

前端源码位于 `frontend/src/library/`，构建产物位于 `plugins.v3/libraryscraperfix/dist/assets/`。在仓库根目录执行：

```bash
npm ci --prefix frontend
npm run build --prefix frontend
python3 .github/scripts/check_federation_css.py
```

V3 版本与 V2 版本使用独立实现：

- 显式媒体识别统一使用 `media_source + media_id`，支持 TMDB 与豆瓣 ID。
- 元数据写入使用 MoviePilot V3 的 `ScrapingChain`，不再调用已拆分的旧刮削入口。
- 整理历史按规范媒体来源和原生媒体 ID 查询。
- 大目录扫描流式消费 `os.scandir` 条目，降低内存占用并更早产出媒体文件。
- 配置、增量缓存、运行结果面板、NFO 修复和安全策略与 V2 版本保持一致。

`3.1.1` 修复了 `Page` 与 `AppPage` 联邦入口的独立构建，避免详情页加载占位符而显示组件加载错误。

建议先开启预演、只配置一个小目录并将单次处理目标设为 `1`，确认结果后再扩大范围。
