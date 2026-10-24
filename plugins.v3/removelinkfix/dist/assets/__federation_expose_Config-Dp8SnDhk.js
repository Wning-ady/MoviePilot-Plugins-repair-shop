import { importShared } from './__federation_fn_import-JrT3xvdd.js';

const {createElementVNode:_createElementVNode,resolveComponent:_resolveComponent,createVNode:_createVNode,createTextVNode:_createTextVNode,withCtx:_withCtx,openBlock:_openBlock,createElementBlock:_createElementBlock} = await importShared('vue');


const _hoisted_1 = { class: "plugin-config pa-4" };
const _hoisted_2 = { class: "d-flex align-center mb-4" };
const _hoisted_3 = { class: "d-flex justify-end ga-2 mt-5" };

const {reactive} = await importShared('vue');



const _sfc_main = {
  __name: 'Config',
  props: {
  initialConfig: { type: Object, default: () => ({}) },
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: 'RemoveLinkFix' },
  sourcePluginId: { type: String, default: '' },
},
  emits: ['save', 'close', 'switch'],
  setup(__props, { emit: __emit }) {

const props = __props;
const emit = __emit;
const config = reactive({ ...props.initialConfig });
function save() { emit('save', { ...config }); }

return (_ctx, _cache) => {
  const _component_v_spacer = _resolveComponent("v-spacer");
  const _component_v_btn = _resolveComponent("v-btn");
  const _component_v_switch = _resolveComponent("v-switch");
  const _component_v_col = _resolveComponent("v-col");
  const _component_v_text_field = _resolveComponent("v-text-field");
  const _component_v_row = _resolveComponent("v-row");
  const _component_v_expansion_panel_text = _resolveComponent("v-expansion-panel-text");
  const _component_v_expansion_panel = _resolveComponent("v-expansion-panel");
  const _component_v_textarea = _resolveComponent("v-textarea");
  const _component_v_expansion_panels = _resolveComponent("v-expansion-panels");

  return (_openBlock(), _createElementBlock("div", _hoisted_1, [
    _createElementVNode("div", _hoisted_2, [
      _cache[16] || (_cache[16] = _createElementVNode("div", null, [
        _createElementVNode("div", { class: "text-h5" }, "清理媒体文件设置"),
        _createElementVNode("div", { class: "text-body-2 text-medium-emphasis" }, "删除联动始终以整理记录、路径、Hash、inode 和硬链接数复核为前提。")
      ], -1)),
      _createVNode(_component_v_spacer),
      _createVNode(_component_v_btn, {
        variant: "text",
        onClick: _cache[0] || (_cache[0] = $event => (emit('switch')))
      }, {
        default: _withCtx(() => [...(_cache[15] || (_cache[15] = [
          _createTextVNode("查看删除结果", -1)
        ]))]),
        _: 1
      })
    ]),
    _createVNode(_component_v_expansion_panels, {
      multiple: "",
      "model-value": [0, 1, 2]
    }, {
      default: _withCtx(() => [
        _createVNode(_component_v_expansion_panel, { title: "运行与删除策略" }, {
          default: _withCtx(() => [
            _createVNode(_component_v_expansion_panel_text, null, {
              default: _withCtx(() => [
                _createVNode(_component_v_row, null, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_col, {
                      cols: "12",
                      md: "6"
                    }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_switch, {
                          modelValue: config.enabled,
                          "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => ((config.enabled) = $event)),
                          label: "启用插件",
                          color: "primary"
                        }, null, 8, ["modelValue"]),
                        _createVNode(_component_v_switch, {
                          modelValue: config.notify,
                          "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => ((config.notify) = $event)),
                          label: "发送运行通知",
                          color: "primary"
                        }, null, 8, ["modelValue"]),
                        _createVNode(_component_v_switch, {
                          modelValue: config.delete_scrap_infos,
                          "onUpdate:modelValue": _cache[3] || (_cache[3] = $event => ((config.delete_scrap_infos) = $event)),
                          label: "清理 NFO、图片等刮削文件",
                          color: "primary"
                        }, null, 8, ["modelValue"])
                      ]),
                      _: 1
                    }),
                    _createVNode(_component_v_col, {
                      cols: "12",
                      md: "6"
                    }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_switch, {
                          modelValue: config.delete_torrents,
                          "onUpdate:modelValue": _cache[4] || (_cache[4] = $event => ((config.delete_torrents) = $event)),
                          label: "联动删除种子",
                          color: "warning"
                        }, null, 8, ["modelValue"]),
                        _createVNode(_component_v_switch, {
                          modelValue: config.delete_history,
                          "onUpdate:modelValue": _cache[5] || (_cache[5] = $event => ((config.delete_history) = $event)),
                          label: "删除整理记录",
                          color: "warning"
                        }, null, 8, ["modelValue"]),
                        _createVNode(_component_v_switch, {
                          modelValue: config.delayed_deletion,
                          "onUpdate:modelValue": _cache[6] || (_cache[6] = $event => ((config.delayed_deletion) = $event)),
                          label: "延迟删除",
                          color: "primary"
                        }, null, 8, ["modelValue"]),
                        _createVNode(_component_v_text_field, {
                          modelValue: config.delay_seconds,
                          "onUpdate:modelValue": _cache[7] || (_cache[7] = $event => ((config.delay_seconds) = $event)),
                          modelModifiers: { number: true },
                          type: "number",
                          label: "延迟秒数"
                        }, null, 8, ["modelValue"])
                      ]),
                      _: 1
                    })
                  ]),
                  _: 1
                })
              ]),
              _: 1
            })
          ]),
          _: 1
        }),
        _createVNode(_component_v_expansion_panel, { title: "监控与排除范围" }, {
          default: _withCtx(() => [
            _createVNode(_component_v_expansion_panel_text, null, {
              default: _withCtx(() => [
                _createVNode(_component_v_textarea, {
                  modelValue: config.monitor_dirs,
                  "onUpdate:modelValue": _cache[8] || (_cache[8] = $event => ((config.monitor_dirs) = $event)),
                  label: "监控目录",
                  rows: "4",
                  hint: "每行一个下载根或媒体库根",
                  "persistent-hint": ""
                }, null, 8, ["modelValue"]),
                _createVNode(_component_v_textarea, {
                  modelValue: config.exclude_dirs,
                  "onUpdate:modelValue": _cache[9] || (_cache[9] = $event => ((config.exclude_dirs) = $event)),
                  label: "排除目录",
                  rows: "3"
                }, null, 8, ["modelValue"]),
                _createVNode(_component_v_textarea, {
                  modelValue: config.exclude_keywords,
                  "onUpdate:modelValue": _cache[10] || (_cache[10] = $event => ((config.exclude_keywords) = $event)),
                  label: "排除关键词",
                  rows: "2"
                }, null, 8, ["modelValue"]),
                _createVNode(_component_v_textarea, {
                  modelValue: config.custom_scrap_extensions,
                  "onUpdate:modelValue": _cache[11] || (_cache[11] = $event => ((config.custom_scrap_extensions) = $event)),
                  label: "自定义刮削文件扩展名",
                  rows: "2"
                }, null, 8, ["modelValue"])
              ]),
              _: 1
            })
          ]),
          _: 1
        }),
        _createVNode(_component_v_expansion_panel, { title: "STRM 监控" }, {
          default: _withCtx(() => [
            _createVNode(_component_v_expansion_panel_text, null, {
              default: _withCtx(() => [
                _createVNode(_component_v_switch, {
                  modelValue: config.monitor_strm_deletion,
                  "onUpdate:modelValue": _cache[12] || (_cache[12] = $event => ((config.monitor_strm_deletion) = $event)),
                  label: "监控 STRM 删除",
                  color: "primary"
                }, null, 8, ["modelValue"]),
                _createVNode(_component_v_textarea, {
                  modelValue: config.strm_path_mappings,
                  "onUpdate:modelValue": _cache[13] || (_cache[13] = $event => ((config.strm_path_mappings) = $event)),
                  label: "路径映射",
                  rows: "3",
                  hint: "格式：STRM目录:存储类型:网盘目录",
                  "persistent-hint": ""
                }, null, 8, ["modelValue"])
              ]),
              _: 1
            })
          ]),
          _: 1
        })
      ]),
      _: 1
    }),
    _createElementVNode("div", _hoisted_3, [
      _createVNode(_component_v_btn, {
        variant: "text",
        onClick: _cache[14] || (_cache[14] = $event => (emit('close')))
      }, {
        default: _withCtx(() => [...(_cache[17] || (_cache[17] = [
          _createTextVNode("取消", -1)
        ]))]),
        _: 1
      }),
      _createVNode(_component_v_btn, {
        color: "primary",
        onClick: save
      }, {
        default: _withCtx(() => [...(_cache[18] || (_cache[18] = [
          _createTextVNode("保存设置", -1)
        ]))]),
        _: 1
      })
    ])
  ]))
}
}

};

export { _sfc_main as default };
