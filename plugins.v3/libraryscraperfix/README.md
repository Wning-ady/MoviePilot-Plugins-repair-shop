# LibraryScraperFix V3

MoviePilot V3“媒体库刮削(魔改版)”安全增量插件。

V3 版本与 V2 版本使用独立实现：

- 显式媒体识别统一使用 `media_source + media_id`，支持 TMDB 与豆瓣 ID。
- 元数据写入使用 MoviePilot V3 的 `ScrapingChain`，不再调用已拆分的旧刮削入口。
- 整理历史按规范媒体来源和原生媒体 ID 查询。
- 大目录扫描流式消费 `os.scandir` 条目，降低内存占用并更早产出媒体文件。
- 配置、增量缓存、运行结果面板、NFO 修复和安全策略与 V2 版本保持一致。

建议先开启预演、只配置一个小目录并将单次处理目标设为 `1`，确认结果后再扩大范围。
