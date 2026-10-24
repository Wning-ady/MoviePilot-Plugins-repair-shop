# V3 Vue 联邦页面

`LibraryScraperFix` 和 `RemoveLinkFix` 共用这个前端构建目录，分别将构建产物输出到：

- `../plugins.v3/libraryscraperfix/dist/assets/`
- `../plugins.v3/removelinkfix/dist/assets/`

```bash
npm install
npm run build
python3 ../.github/scripts/check_federation_css.py
```

两个远端均暴露 `./Page` 、`./Config` 和 `./AppPage`，后端返回 `vue, dist/assets`，侧栏入口使用 `main` 。运行数据通过各自插件的 `GET /api/v1/plugin/<PluginID>/history` 读取。

构建产物只保留联邦入口、组件脚本和插件自身的 scoped CSS；不会发布 Vuetify/MDI 全局基础样式。详情页默认展示最新运行，工具栏可切换最近 20 次运行或删除批次，并支持长路径换行、搜索、状态筛选和分页。
