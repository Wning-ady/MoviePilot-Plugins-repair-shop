# MoviePilot Plugins Repair Shop

用于发布经过针对性修复和回归测试的 MoviePilot V2 专用插件。仓库采用官方的 `package.v2.json` 与 `plugins.v2/` 结构。

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

原插件作者为 [DzAvril](https://github.com/DzAvril/MoviePilot-Plugins)。本仓库保留原项目 GPL-3.0 许可，修改内容同样以 GPL-3.0 发布。
