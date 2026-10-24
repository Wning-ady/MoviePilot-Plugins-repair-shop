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
  pluginId: { type: String, default: 'LibraryScraperFix' },
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
  const _component_v_textarea = _resolveComponent("v-textarea");
  const _component_v_row = _resolveComponent("v-row");
  const _component_v_expansion_panel_text = _resolveComponent("v-expansion-panel-text");
  const _component_v_expansion_panel = _resolveComponent("v-expansion-panel");
  const _component_v_select = _resolveComponent("v-select");
  const _component_v_divider = _resolveComponent("v-divider");
  const _component_v_expansion_panels = _resolveComponent("v-expansion-panels");

  return (_openBlock(), _createElementBlock("div", _hoisted_1, [
    _createElementVNode("div", _hoisted_2, [
      _cache[20] || (_cache[20] = _createElementVNode("div", null, [
        _createElementVNode("div", { class: "text-h5" }, "媒体库刮削设置"),
        _createElementVNode("div", { class: "text-body-2 text-medium-emphasis" }, "先使用预演和单目录验证，再扩大扫描范围。")
      ], -1)),
      _createVNode(_component_v_spacer),
      _createVNode(_component_v_btn, {
        variant: "text",
        onClick: _cache[0] || (_cache[0] = $event => (emit('switch')))
      }, {
        default: _withCtx(() => [...(_cache[19] || (_cache[19] = [
          _createTextVNode("查看运行结果", -1)
        ]))]),
        _: 1
      })
    ]),
    _createVNode(_component_v_expansion_panels, {
      multiple: "",
      "model-value": [0, 1, 2]
    }, {
      default: _withCtx(() => [
        _createVNode(_component_v_expansion_panel, { title: "运行与扫描范围" }, {
          default: _withCtx(() => [
            _createVNode(_component_v_expansion_panel_text, null, {
              default: _withCtx(() => [
                _createVNode(_component_v_row, null, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_col, {
                      cols: "12",
                      md: "4"
                    }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_switch, {
                          modelValue: config.enabled,
                          "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => ((config.enabled) = $event)),
                          label: "启用定时任务",
                          color: "primary"
                        }, null, 8, ["modelValue"]),
                        _createVNode(_component_v_switch, {
                          modelValue: config.onlyonce,
                          "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => ((config.onlyonce) = $event)),
                          label: "保存后运行一次",
                          color: "primary"
                        }, null, 8, ["modelValue"]),
                        _createVNode(_component_v_switch, {
                          modelValue: config.notify,
                          "onUpdate:modelValue": _cache[3] || (_cache[3] = $event => ((config.notify) = $event)),
                          label: "发送运行摘要",
                          color: "primary"
                        }, null, 8, ["modelValue"])
                      ]),
                      _: 1
                    }),
                    _createVNode(_component_v_col, {
                      cols: "12",
                      md: "8"
                    }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_text_field, {
                          modelValue: config.cron,
                          "onUpdate:modelValue": _cache[4] || (_cache[4] = $event => ((config.cron) = $event)),
                          label: "执行周期",
                          hint: "5 位 Cron，例如 0 3 * * *",
                          "persistent-hint": ""
                        }, null, 8, ["modelValue"]),
                        _createVNode(_component_v_textarea, {
                          modelValue: config.scraper_paths,
                          "onUpdate:modelValue": _cache[5] || (_cache[5] = $event => ((config.scraper_paths) = $event)),
                          label: "刮削路径",
                          rows: "4",
                          hint: "每行一个容器内绝对路径，可追加 #电影 或 #电视剧",
                          "persistent-hint": ""
                        }, null, 8, ["modelValue"]),
                        _createVNode(_component_v_textarea, {
                          modelValue: config.exclude_paths,
                          "onUpdate:modelValue": _cache[6] || (_cache[6] = $event => ((config.exclude_paths) = $event)),
                          label: "排除路径",
                          rows: "2"
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
        _createVNode(_component_v_expansion_panel, { title: "刮削与增量策略" }, {
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
                          modelValue: config.dry_run,
                          "onUpdate:modelValue": _cache[7] || (_cache[7] = $event => ((config.dry_run) = $event)),
                          label: "预演模式",
                          color: "primary"
                        }, null, 8, ["modelValue"]),
                        _createVNode(_component_v_switch, {
                          modelValue: config.incremental,
                          "onUpdate:modelValue": _cache[8] || (_cache[8] = $event => ((config.incremental) = $event)),
                          label: "启用目标缓存",
                          color: "primary"
                        }, null, 8, ["modelValue"]),
                        _createVNode(_component_v_select, {
                          modelValue: config.mode,
                          "onUpdate:modelValue": _cache[9] || (_cache[9] = $event => ((config.mode) = $event)),
                          items: [{title:'仅补齐缺失元数据（推荐）',value:''},{title:'覆盖未被全局禁用的元数据',value:'force_all'}],
                          label: "元数据写入策略"
                        }, null, 8, ["modelValue"])
                      ]),
                      _: 1
                    }),
                    _createVNode(_component_v_col, {
                      cols: "12",
                      md: "6"
                    }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_text_field, {
                          modelValue: config.max_targets,
                          "onUpdate:modelValue": _cache[10] || (_cache[10] = $event => ((config.max_targets) = $event)),
                          modelModifiers: { number: true },
                          type: "number",
                          label: "单次最多处理目标"
                        }, null, 8, ["modelValue"]),
                        _createVNode(_component_v_text_field, {
                          modelValue: config.interval_seconds,
                          "onUpdate:modelValue": _cache[11] || (_cache[11] = $event => ((config.interval_seconds) = $event)),
                          modelModifiers: { number: true },
                          type: "number",
                          step: "0.1",
                          label: "目标间隔（秒）"
                        }, null, 8, ["modelValue"]),
                        _createVNode(_component_v_text_field, {
                          modelValue: config.retry_count,
                          "onUpdate:modelValue": _cache[12] || (_cache[12] = $event => ((config.retry_count) = $event)),
                          modelModifiers: { number: true },
                          type: "number",
                          label: "异常重试次数"
                        }, null, 8, ["modelValue"]),
                        _createVNode(_component_v_text_field, {
                          modelValue: config.full_scan_days,
                          "onUpdate:modelValue": _cache[13] || (_cache[13] = $event => ((config.full_scan_days) = $event)),
                          modelModifiers: { number: true },
                          type: "number",
                          label: "目标完整复核（天）"
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
        _createVNode(_component_v_expansion_panel, { title: "NFO 修复与一次性维护" }, {
          default: _withCtx(() => [
            _createVNode(_component_v_expansion_panel_text, null, {
              default: _withCtx(() => [
                _createVNode(_component_v_switch, {
                  modelValue: config.repair_nfo_fields,
                  "onUpdate:modelValue": _cache[14] || (_cache[14] = $event => ((config.repair_nfo_fields) = $event)),
                  label: "修复空白概要和通用标题",
                  color: "primary"
                }, null, 8, ["modelValue"]),
                _createVNode(_component_v_text_field, {
                  modelValue: config.nfo_audit_days,
                  "onUpdate:modelValue": _cache[15] || (_cache[15] = $event => ((config.nfo_audit_days) = $event)),
                  modelModifiers: { number: true },
                  type: "number",
                  label: "NFO 完整复核（天）"
                }, null, 8, ["modelValue"]),
                _createVNode(_component_v_divider, { class: "my-3" }),
                _createVNode(_component_v_switch, {
                  modelValue: config.force_full_scan,
                  "onUpdate:modelValue": _cache[16] || (_cache[16] = $event => ((config.force_full_scan) = $event)),
                  label: "下次忽略目标缓存",
                  color: "warning"
                }, null, 8, ["modelValue"]),
                _createVNode(_component_v_switch, {
                  modelValue: config.clear_cache,
                  "onUpdate:modelValue": _cache[17] || (_cache[17] = $event => ((config.clear_cache) = $event)),
                  label: "清空全部增量缓存",
                  color: "error"
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
        onClick: _cache[18] || (_cache[18] = $event => (emit('close')))
      }, {
        default: _withCtx(() => [...(_cache[21] || (_cache[21] = [
          _createTextVNode("取消", -1)
        ]))]),
        _: 1
      }),
      _createVNode(_component_v_btn, {
        color: "primary",
        onClick: save
      }, {
        default: _withCtx(() => [...(_cache[22] || (_cache[22] = [
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
