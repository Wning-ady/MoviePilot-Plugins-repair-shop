import { importShared } from './__federation_fn_import-JrT3xvdd.js';

const _export_sfc = (sfc, props) => {
  const target = sfc.__vccOpts || sfc;
  for (const [key, val] of props) {
    target[key] = val;
  }
  return target;
};

const {createElementVNode:_createElementVNode,resolveComponent:_resolveComponent,createVNode:_createVNode,openBlock:_openBlock,createBlock:_createBlock,createCommentVNode:_createCommentVNode,createTextVNode:_createTextVNode,withCtx:_withCtx,toDisplayString:_toDisplayString,renderList:_renderList,Fragment:_Fragment,createElementBlock:_createElementBlock} = await importShared('vue');


const _hoisted_1 = { class: "plugin-page pa-4" };
const _hoisted_2 = { class: "d-flex flex-wrap align-center ga-3 mb-4" };
const _hoisted_3 = { class: "text-subtitle-1 font-weight-medium" };
const _hoisted_4 = { class: "text-body-2" };
const _hoisted_5 = { class: "path-cell" };
const _hoisted_6 = { class: "text-cell" };
const _hoisted_7 = { key: 0 };

const {computed,onMounted,ref} = await importShared('vue');



const _sfc_main = {
  __name: 'Page',
  props: {
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: 'RemoveLinkFix' },
  sourcePluginId: { type: String, default: '' },
  navKey: { type: String, default: 'main' },
},
  emits: ['action', 'switch', 'close'],
  setup(__props, { emit: __emit }) {

const props = __props;
const emit = __emit;
const loading = ref(false);
const error = ref('');
const payload = ref({ history: [] });
const filter = ref('all');
const search = ref('');
const selectedBatch = ref(0);

const history = computed(() => Array.isArray(payload.value.history) ? payload.value.history.filter(Boolean) : []);
const historyOptions = computed(() => history.value.map((item, index) => ({
  title: `${index === 0 ? '最近批次' : `第 ${index + 1} 批`} · ${item.finished_at || item.started_at || '未记录时间'}`,
  value: index,
})));
const batch = computed(() => history.value[selectedBatch.value] || {});
const items = computed(() => batch.value.items || []);
const filteredItems = computed(() => items.value.filter((item) => {
  const status = `${item.history_status || ''} ${item.torrent_status || ''}`;
  const matchesFilter = filter.value === 'all' || (filter.value === 'problem' ? !['deleted', 'sent'].includes(item.history_status) || ['missing_hash', 'not_sent'].includes(item.torrent_status) : status.includes(filter.value));
  const query = search.value.trim().toLowerCase();
  return matchesFilter && (!query || `${item.source || ''} ${item.detail || ''} ${item.episode || ''}`.toLowerCase().includes(query))
}));
const historyLabels = { deleted: '已删除', retained: '仍保留', disabled: '未启用', not_processed: '未执行' };
const torrentLabels = { sent: '已发送', missing_hash: '缺少 Hash', disabled: '未启用', not_sent: '未发送' };
const statusColor = (value) => ({ deleted: 'success', sent: 'success', retained: 'warning', missing_hash: 'error', not_sent: 'warning', failed: 'error' }[value] || 'default');

function normalizeResponse(result) { return result?.data?.history ? result.data : result }
async function load() {
  loading.value = true;
  error.value = '';
  try {
    const result = await props.api?.get?.(`plugin/${props.pluginId}/history`);
    payload.value = normalizeResponse(result) || { history: [] };
    selectedBatch.value = 0;
  } catch (err) { error.value = err?.message || '读取删除结果失败'; } finally { loading.value = false; }
}
onMounted(load);

return (_ctx, _cache) => {
  const _component_v_spacer = _resolveComponent("v-spacer");
  const _component_v_select = _resolveComponent("v-select");
  const _component_v_btn = _resolveComponent("v-btn");
  const _component_v_alert = _resolveComponent("v-alert");
  const _component_v_card_subtitle = _resolveComponent("v-card-subtitle");
  const _component_v_card_title = _resolveComponent("v-card-title");
  const _component_v_card_text = _resolveComponent("v-card-text");
  const _component_v_card = _resolveComponent("v-card");
  const _component_v_col = _resolveComponent("v-col");
  const _component_v_row = _resolveComponent("v-row");
  const _component_v_chip = _resolveComponent("v-chip");
  const _component_v_text_field = _resolveComponent("v-text-field");
  const _component_v_table = _resolveComponent("v-table");

  return (_openBlock(), _createElementBlock("div", _hoisted_1, [
    _createElementVNode("div", _hoisted_2, [
      _cache[6] || (_cache[6] = _createElementVNode("div", null, [
        _createElementVNode("div", { class: "text-h5" }, "清理媒体文件"),
        _createElementVNode("div", { class: "text-body-2 text-medium-emphasis" }, "硬链接清理、整理记录和种子联动结果")
      ], -1)),
      _createVNode(_component_v_spacer),
      (historyOptions.value.length > 1)
        ? (_openBlock(), _createBlock(_component_v_select, {
            key: 0,
            modelValue: selectedBatch.value,
            "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => ((selectedBatch).value = $event)),
            items: historyOptions.value,
            density: "compact",
            "hide-details": "",
            label: "删除批次",
            style: {"max-width":"280px"}
          }, null, 8, ["modelValue", "items"]))
        : _createCommentVNode("", true),
      _createVNode(_component_v_btn, {
        variant: "tonal",
        loading: loading.value,
        "prepend-icon": "mdi-refresh",
        onClick: load
      }, {
        default: _withCtx(() => [...(_cache[4] || (_cache[4] = [
          _createTextVNode("刷新", -1)
        ]))]),
        _: 1
      }, 8, ["loading"]),
      _createVNode(_component_v_btn, {
        variant: "text",
        "prepend-icon": "mdi-cog",
        onClick: _cache[1] || (_cache[1] = $event => (emit('switch')))
      }, {
        default: _withCtx(() => [...(_cache[5] || (_cache[5] = [
          _createTextVNode("配置", -1)
        ]))]),
        _: 1
      })
    ]),
    (error.value)
      ? (_openBlock(), _createBlock(_component_v_alert, {
          key: 0,
          type: "error",
          variant: "tonal",
          class: "mb-4"
        }, {
          default: _withCtx(() => [
            _createTextVNode(_toDisplayString(error.value), 1)
          ]),
          _: 1
        }))
      : (!batch.value.finished_at)
        ? (_openBlock(), _createBlock(_component_v_alert, {
            key: 1,
            type: "info",
            variant: "tonal",
            class: "mb-4"
          }, {
            default: _withCtx(() => [...(_cache[7] || (_cache[7] = [
              _createTextVNode("暂无删除结果。下一次安全联动删除后会显示真实的文件、整理记录和种子状态。", -1)
            ]))]),
            _: 1
          }))
        : (_openBlock(), _createElementBlock(_Fragment, { key: 2 }, [
            _createVNode(_component_v_alert, {
              type: batch.value.failed ? 'error' : 'success',
              variant: "tonal",
              class: "mb-4"
            }, {
              default: _withCtx(() => [
                _createElementVNode("div", _hoisted_3, _toDisplayString(batch.value.failed ? `删除批次完成，${batch.value.failed} 项需处理` : '删除批次完成'), 1),
                _createElementVNode("div", _hoisted_4, _toDisplayString(batch.value.finished_at) + " · 处理 " + _toDisplayString(batch.value.processed || 0) + " 个任务 · 删除 " + _toDisplayString(batch.value.files_deleted || 0) + " 个硬链接文件", 1)
              ]),
              _: 1
            }, 8, ["type"]),
            _createVNode(_component_v_row, null, {
              default: _withCtx(() => [
                _createVNode(_component_v_col, {
                  cols: "12",
                  sm: "4"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_card, { variant: "outlined" }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_card_subtitle, null, {
                          default: _withCtx(() => [...(_cache[8] || (_cache[8] = [
                            _createTextVNode("整理记录", -1)
                          ]))]),
                          _: 1
                        }),
                        _createVNode(_component_v_card_title, null, {
                          default: _withCtx(() => [
                            _createTextVNode(_toDisplayString(batch.value.histories_deleted || 0) + " 条已删除", 1)
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_v_card_text, null, {
                          default: _withCtx(() => [
                            _createTextVNode(_toDisplayString(batch.value.histories_retained || 0) + " 条仍保留", 1)
                          ]),
                          _: 1
                        })
                      ]),
                      _: 1
                    })
                  ]),
                  _: 1
                }),
                _createVNode(_component_v_col, {
                  cols: "12",
                  sm: "4"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_card, { variant: "outlined" }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_card_subtitle, null, {
                          default: _withCtx(() => [...(_cache[9] || (_cache[9] = [
                            _createTextVNode("种子联动", -1)
                          ]))]),
                          _: 1
                        }),
                        _createVNode(_component_v_card_title, null, {
                          default: _withCtx(() => [
                            _createTextVNode(_toDisplayString(batch.value.torrents_sent || 0) + " 条已发送", 1)
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_v_card_text, null, {
                          default: _withCtx(() => [
                            _createTextVNode(_toDisplayString(batch.value.torrents_missing_hash || 0) + " 条缺少 Hash", 1)
                          ]),
                          _: 1
                        })
                      ]),
                      _: 1
                    })
                  ]),
                  _: 1
                }),
                _createVNode(_component_v_col, {
                  cols: "12",
                  sm: "4"
                }, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_card, { variant: "outlined" }, {
                      default: _withCtx(() => [
                        _createVNode(_component_v_card_subtitle, null, {
                          default: _withCtx(() => [...(_cache[10] || (_cache[10] = [
                            _createTextVNode("执行结果", -1)
                          ]))]),
                          _: 1
                        }),
                        _createVNode(_component_v_card_title, null, {
                          default: _withCtx(() => [
                            _createTextVNode(_toDisplayString(batch.value.success || 0) + " 项完成", 1)
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_v_card_text, null, {
                          default: _withCtx(() => [
                            _createTextVNode(_toDisplayString(batch.value.skipped || 0) + " 项跳过 · " + _toDisplayString(batch.value.failed || 0) + " 项失败", 1)
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
            _createVNode(_component_v_card, {
              variant: "outlined",
              class: "mt-5"
            }, {
              default: _withCtx(() => [
                _createVNode(_component_v_card_title, { class: "d-flex flex-wrap align-center ga-3" }, {
                  default: _withCtx(() => [
                    _cache[11] || (_cache[11] = _createElementVNode("span", null, "最近删除明细", -1)),
                    _createVNode(_component_v_chip, { size: "small" }, {
                      default: _withCtx(() => [
                        _createTextVNode(_toDisplayString(filteredItems.value.length) + " / " + _toDisplayString(items.value.length), 1)
                      ]),
                      _: 1
                    }),
                    _createVNode(_component_v_spacer),
                    _createVNode(_component_v_text_field, {
                      modelValue: search.value,
                      "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => ((search).value = $event)),
                      density: "compact",
                      "hide-details": "",
                      clearable: "",
                      label: "搜索源文件或说明",
                      "prepend-inner-icon": "mdi-magnify",
                      style: {"max-width":"320px"}
                    }, null, 8, ["modelValue"]),
                    _createVNode(_component_v_select, {
                      modelValue: filter.value,
                      "onUpdate:modelValue": _cache[3] || (_cache[3] = $event => ((filter).value = $event)),
                      items: [{title:'全部',value:'all'},{title:'问题',value:'problem'},{title:'仍保留',value:'retained'},{title:'缺少 Hash',value:'missing_hash'},{title:'已删除',value:'deleted'}],
                      density: "compact",
                      "hide-details": "",
                      label: "状态",
                      style: {"max-width":"150px"}
                    }, null, 8, ["modelValue"])
                  ]),
                  _: 1
                }),
                _createVNode(_component_v_card_text, null, {
                  default: _withCtx(() => [
                    _createVNode(_component_v_table, { density: "comfortable" }, {
                      default: _withCtx(() => [
                        _cache[13] || (_cache[13] = _createElementVNode("thead", null, [
                          _createElementVNode("tr", null, [
                            _createElementVNode("th", null, "集数"),
                            _createElementVNode("th", null, "记录 ID"),
                            _createElementVNode("th", null, "整理记录"),
                            _createElementVNode("th", null, "种子联动"),
                            _createElementVNode("th", null, "源文件"),
                            _createElementVNode("th", null, "说明")
                          ])
                        ], -1)),
                        _createElementVNode("tbody", null, [
                          (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(filteredItems.value, (item, index) => {
                            return (_openBlock(), _createElementBlock("tr", { key: index }, [
                              _createElementVNode("td", null, _toDisplayString(item.episode || '-'), 1),
                              _createElementVNode("td", null, _toDisplayString(item.history_id || '-'), 1),
                              _createElementVNode("td", null, [
                                _createVNode(_component_v_chip, {
                                  size: "small",
                                  color: statusColor(item.history_status)
                                }, {
                                  default: _withCtx(() => [
                                    _createTextVNode(_toDisplayString(historyLabels[item.history_status] || item.history_status || '-'), 1)
                                  ]),
                                  _: 2
                                }, 1032, ["color"])
                              ]),
                              _createElementVNode("td", null, [
                                _createVNode(_component_v_chip, {
                                  size: "small",
                                  color: statusColor(item.torrent_status)
                                }, {
                                  default: _withCtx(() => [
                                    _createTextVNode(_toDisplayString(torrentLabels[item.torrent_status] || item.torrent_status || '-'), 1)
                                  ]),
                                  _: 2
                                }, 1032, ["color"])
                              ]),
                              _createElementVNode("td", _hoisted_5, _toDisplayString(item.source || '-'), 1),
                              _createElementVNode("td", _hoisted_6, _toDisplayString(item.detail || '-'), 1)
                            ]))
                          }), 128)),
                          (!filteredItems.value.length)
                            ? (_openBlock(), _createElementBlock("tr", _hoisted_7, [...(_cache[12] || (_cache[12] = [
                                _createElementVNode("td", {
                                  colspan: "6",
                                  class: "text-center text-medium-emphasis py-6"
                                }, "没有匹配的记录", -1)
                              ]))]))
                            : _createCommentVNode("", true)
                        ])
                      ]),
                      _: 1
                    })
                  ]),
                  _: 1
                })
              ]),
              _: 1
            })
          ], 64))
  ]))
}
}

};
const Page = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-93077565"]]);

export { Page as default };
