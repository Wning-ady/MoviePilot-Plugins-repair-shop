# MoviePilot Plugins Repair Shop

用于发布经过针对性修复和回归测试的 MoviePilot V2 专用插件。仓库采用官方的 `package.v2.json` 与 `plugins.v2/` 结构。

## 媒体库刮削（修复版）

插件 ID：`LibraryScraperFix`，当前版本：`1.0.2`。

本插件基于官方 [LibraryScraper 2.1.3](https://github.com/jxxghp/MoviePilot-Plugins/tree/main/plugins.v2/libraryscraper)，使用独立插件 ID，不覆盖官方插件。主要改进：

- “仅补齐缺失元数据”独立于 MoviePilot 全局覆盖策略，同时保留全局禁用项。
- 主扫描与目录识别失败后的回退扫描使用相同的排除路径和强制媒体类型规则。
- 损坏、空白或缺少 ID 的 NFO 不再覆盖文件名中已解析出的有效 TMDB ID。
- 只扫描真实媒体文件；符号链接、未知媒体类型和越界路径不会进入刮削链。
- 使用集合去重和目录级组合指纹，成功且未变化的目标在每日任务中直接跳过。
- 增加预演、单次上限、目标间隔、异常重试、周期完整复核、任务进度和运行摘要。
- 使用进程内锁和文件锁阻止 Cron、立即运行、插件热重载之间的任务重叠。
- 单个目标异常不会中断整批；部分完成不会写入成功缓存，下次会继续重试。

### 安全启用顺序

1. 安装后保持插件停用，并保留默认的“预演模式”。
2. 先只配置一个小目录，勾选“立即运行一次”，检查插件页面、日志和通知摘要。
3. 关闭预演，对同一个小目录再次运行，确认只补齐缺失文件且没有覆盖已有 NFO。
4. 验证成功后再扩大路径范围。
5. 最后停用官方“媒体库刮削”，再启用修复版定时任务，避免两个插件同时处理相同目录。

增量扫描仍会枚举配置目录中的媒体文件，但不会对未变化且近期成功的目标调用识别、图片和写入流程。默认每 7 天完整复核一次，以恢复被单独删除的 NFO 或图片；设置为 `0` 可关闭周期复核。

## 清理媒体文件（修复版）

插件 ID：`RemoveLinkFix`，当前版本：`2.17`。

本插件基于 [DzAvril/MoviePilot-Plugins](https://github.com/DzAvril/MoviePilot-Plugins) 的 `RemoveLink 2.16`，并非基于 `jxxghp/MoviePilot-Plugins` 当前的 `RemoveLink 2.3.1`。主要修复：

- 下载器删除时使用临时源目录，导致转移记录按 `src` 无法命中的问题。
- 删除媒体库硬链接时未按转移记录 `dest` 回退查找的问题。
- 通知无条件显示“已清理转移记录”的误报。
- Emby `episode-thumb-N` 无扩展名缩略图阻止季目录收尾的问题。
- 监控根路径比较失效导致目录清理可能越界的问题。
- 符号链接被当成真实硬链接，以及自定义视频扩展被当成刮削文件的风险。
- 插件停止时提前执行尚未到期的延迟删除任务的问题。

## 安装

1. 在 MoviePilot 的插件市场设置中添加仓库：
   `https://github.com/Wning-ady/MoviePilot-Plugins-repair-shop`
2. 刷新插件市场，安装“清理媒体文件（修复版）”。
3. 停用原版“清理媒体文件”，避免两个插件同时监听同一目录。
4. 在修复版中重新配置监控目录、排除目录和删除选项，再启用插件。

修复版使用独立插件 ID 和配置前缀，不会覆盖原版配置。完成一次小范围验证后再扩大监控范围。

## 仓库结构

```text
MoviePilot-Plugins-repair-shop/
├── icons/Ombi_A.png
├── plugins.v2/libraryscraperfix/__init__.py
├── plugins.v2/removelinkfix/__init__.py
└── package.v2.json
```

插件目录名、类名、索引 ID、版本、名称、描述、图标、作者和权限级别均由自动化测试检查一致性。

## 验证重点

- `src` 精确命中、`dest` 回退命中和无匹配三种转移记录结果。
- 最后一个视频删除后可清理 `episode-thumb-N`、元数据和空目录。
- 存在视频、未知文件或符号链接时不清理目录。
- 清理不会删除监控根，也不会向监控根外递归。

## 致谢与许可

`RemoveLinkFix` 上游作者为 [DzAvril](https://github.com/DzAvril/MoviePilot-Plugins)，`LibraryScraperFix` 上游作者为 [jxxghp](https://github.com/jxxghp/MoviePilot-Plugins)。本仓库保留原项目 GPL-3.0 许可，修改内容同样以 GPL-3.0 发布。
