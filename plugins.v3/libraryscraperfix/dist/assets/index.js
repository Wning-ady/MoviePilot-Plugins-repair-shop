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
const _hoisted_3 = { class: "d-flex justify-space-between align-center" };
const _hoisted_4 = { class: "text-subtitle-1 font-weight-medium" };
const _hoisted_5 = { class: "text-body-2" };
const _hoisted_6 = { class: "path-cell" };
const _hoisted_7 = {
  key: 0,
  class: "text-caption text-medium-emphasis mt-2"
};
const _hoisted_8 = { class: "path-cell" };
const _hoisted_9 = { key: 0 };
const _hoisted_10 = { class: "d-flex justify-center mt-3" };
const _hoisted_11 = { class: "path-cell" };
const _hoisted_12 = { class: "text-cell" };
const _hoisted_13 = { class: "text-cell" };

const {computed,onMounted,ref} = await importShared('vue');


const pageSize = 20;

const _sfc_main = {
  __name: 'Page',
  props: {
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: 'LibraryScraperFix' },
  sourcePluginId: { type: String, default: '' },
  navKey: { type: String, default: 'main' },
},
  emits: ['action', 'switch', 'close'],
  setup(__props, { emit: __emit }) {

const props = __props;
const emit = __emit;

const loading = ref(false);
const error = ref('');
const payload = ref({ last_run: {}, history: [], running: {} });
const filter = ref('all');
const search = ref('');
const detailPage = ref(1);
const selectedRun = ref(0);

const history = computed(() => {
  const records = Array.isArray(payload.value.history) ? payload.value.history.filter(Boolean) : [];
  if (records.length) return records
  return payload.value.last_run && Object.keys(payload.value.last_run).length ? [payload.value.last_run] : []
});
const historyOptions = computed(() => history.value.map((item, index) => ({
  title: `${index === 0 ? '最近一次' : `第 ${index + 1} 次`} · ${item.finished_at || item.started_at || '未记录时间'}`,
  value: index,
})));
const summary = computed(() => history.value[selectedRun.value] || payload.value.last_run || {});
const running = computed(() => payload.value.running || {});
const details = computed(() => (summary.value.details || []).filter(Boolean));
const issues = computed(() => (summary.value.issues || []).filter(Boolean));
const problemCount = computed(() => Number(summary.value.failed || 0) + Number(summary.value.partial || 0) + Number(summary.value.unrecognized || 0) + Number(summary.value.scan_errors || 0) + Number(summary.value.invalid_paths || 0) + (summary.value.cancelled ? 1 : 0));
const filteredDetails = computed(() => {
  const query = search.value.trim().toLowerCase();
  return details.value.filter((item) => {
    const status = item.status || '';
    const matchesFilter = filter.value === 'all' || (filter.value === 'problem' ? ['failed', 'partial', 'unrecognized', 'cancelled'].includes(status) : status === filter.value);
    const text = `${item.path || ''} ${item.detail || ''}`.toLowerCase();
    return matchesFilter && (!query || text.includes(query))
  })
});
const pageCount = computed(() => Math.max(1, Math.ceil(filteredDetails.value.length / pageSize)));
const pagedDetails = computed(() => filteredDetails.value.slice((detailPage.value - 1) * pageSize, detailPage.value * pageSize));
const nfoChanges = computed(() => summary.value.nfo_changes || []);

const statusLabels = {
  success: '成功',
  failed: '失败',
  partial: '部分完成',
  unrecognized: '未识别',
  dry_run: '预演',
  deferred: '延后',
  cancelled: '已取消',
};

function statusColor(status) {
  return { success: 'success', failed: 'error', partial: 'warning', unrecognized: 'warning', dry_run: 'info', deferred: 'secondary', cancelled: 'error' }[status] || 'default'
}

function duration(value) {
  const seconds = Number(value || 0);
  if (seconds >= 3600) return `${Math.floor(seconds / 3600)} 小时 ${Math.floor(seconds % 3600 / 60)} 分`
  if (seconds >= 60) return `${Math.floor(seconds / 60)} 分 ${Math.round(seconds % 60)} 秒`
  return `${Math.round(seconds * 100) / 100} 秒`
}

function normalizeResponse(result) {
  return result?.data?.last_run || result?.data?.history ? result.data : result
}

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const result = await props.api?.get?.(`plugin/${props.pluginId}/history`);
    payload.value = normalizeResponse(result) || { last_run: {}, history: [], running: {} };
    selectedRun.value = 0;
    detailPage.value = Math.min(detailPage.value, pageCount.value);
  } catch (err) {
    error.value = err?.message || '读取运行记录失败';
  } finally {
    loading.value = false;
  }
}

function resetFilter(value) {
  filter.value = value;
  detailPage.value = 1;
}

onMounted(load);

return (_ctx, _cache) => {
  const _component_v_spacer = _resolveComponent("v-spacer");
  const _component_v_select = _resolveComponent("v-select");
  const _component_v_btn = _resolveComponent("v-btn");
  const _component_v_alert = _resolveComponent("v-alert");
  const _component_v_progress_linear = _resolveComponent("v-progress-linear");
  const _component_v_card_subtitle = _resolveComponent("v-card-subtitle");
  const _component_v_card_title = _resolveComponent("v-card-title");
  const _component_v_card_text = _resolveComponent("v-card-text");
  const _component_v_card = _resolveComponent("v-card");
  const _component_v_col = _resolveComponent("v-col");
  const _component_v_row = _resolveComponent("v-row");
  const _component_v_chip = _resolveComponent("v-chip");
  const _component_v_table = _resolveComponent("v-table");
  const _component_v_text_field = _resolveComponent("v-text-field");
  const _component_v_pagination = _resolveComponent("v-pagination");

  return (_openBlock(), _createElementBlock("div", _hoisted_1, [
    _createElementVNode("div", _hoisted_2, [
      _cache[7] || (_cache[7] = _createElementVNode("div", null, [
        _createElementVNode("div", { class: "text-h5" }, "媒体库刮削"),
        _createElementVNode("div", { class: "text-body-2 text-medium-emphasis" }, "增量刮削、NFO 修复与运行记录")
      ], -1)),
      _createVNode(_component_v_spacer),
      (historyOptions.value.length > 1)
        ? (_openBlock(), _createBlock(_component_v_select, {
            key: 0,
            modelValue: selectedRun.value,
            "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => ((selectedRun).value = $event)),
            items: historyOptions.value,
            density: "compact",
            "hide-details": "",
            label: "运行记录",
            style: {"max-width":"280px"}
          }, null, 8, ["modelValue", "items"]))
        : _createCommentVNode("", true),
      _createVNode(_component_v_btn, {
        variant: "tonal",
        loading: loading.value,
        "prepend-icon": "mdi-refresh",
        onClick: load
      }, {
        default: _withCtx(() => [...(_cache[5] || (_cache[5] = [
          _createTextVNode("刷新", -1)
        ]))]),
        _: 1
      }, 8, ["loading"]),
      _createVNode(_component_v_btn, {
        variant: "text",
        "prepend-icon": "mdi-cog",
        onClick: _cache[1] || (_cache[1] = $event => (emit('switch')))
      }, {
        default: _withCtx(() => [...(_cache[6] || (_cache[6] = [
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
      : (running.value.current || running.value.stage)
        ? (_openBlock(), _createBlock(_component_v_alert, {
            key: 1,
            type: "info",
            variant: "tonal",
            class: "mb-4"
          }, {
            default: _withCtx(() => [
              _createElementVNode("div", _hoisted_3, [
                _createElementVNode("span", null, "运行中：" + _toDisplayString(running.value.stage || '处理中'), 1),
                _createElementVNode("span", null, _toDisplayString(running.value.current || 0) + " / " + _toDisplayString(running.value.total || 0), 1)
              ]),
              _createVNode(_component_v_progress_linear, {
                class: "mt-3",
                "model-value": running.value.total ? running.value.current / running.value.total * 100 : undefined,
                indeterminate: !running.value.total
              }, null, 8, ["model-value", "indeterminate"])
            ]),
            _: 1
          }))
        : (!summary.value.started_at && !summary.value.finished_at)
          ? (_openBlock(), _createBlock(_component_v_alert, {
              key: 2,
              type: "info",
              variant: "tonal",
              class: "mb-4"
            }, {
              default: _withCtx(() => [...(_cache[8] || (_cache[8] = [
                _createTextVNode("暂无运行记录。下一次运行后会显示结果、缓存命中和问题明细。", -1)
              ]))]),
              _: 1
            }))
          : _createCommentVNode("", true),
    (summary.value.started_at || summary.value.finished_at)
      ? (_openBlock(), _createElementBlock(_Fragment, { key: 3 }, [
          _createVNode(_component_v_alert, {
            type: problemCount.value ? 'warning' : 'success',
            variant: "tonal",
            class: "mb-4"
          }, {
            default: _withCtx(() => [
              _createElementVNode("div", _hoisted_4, _toDisplayString(problemCount.value ? `运行完成，${problemCount.value} 项需要处理` : '运行完成，未发现问题'), 1),
              _createElementVNode("div", _hoisted_5, _toDisplayString(summary.value.finished_at || summary.value.started_at) + " · " + _toDisplayString(summary.value.dry_run_enabled ? '预演' : '执行') + " · 总耗时 " + _toDisplayString(duration(summary.value.duration_seconds)), 1)
            ]),
            _: 1
          }, 8, ["type"]),
          _createVNode(_component_v_row, null, {
            default: _withCtx(() => [
              _createVNode(_component_v_col, {
                cols: "12",
                sm: "6",
                lg: "3"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_v_card, { variant: "outlined" }, {
                    default: _withCtx(() => [
                      _createVNode(_component_v_card_subtitle, null, {
                        default: _withCtx(() => [...(_cache[9] || (_cache[9] = [
                          _createTextVNode("扫描范围", -1)
                        ]))]),
                        _: 1
                      }),
                      _createVNode(_component_v_card_title, null, {
                        default: _withCtx(() => [
                          _createTextVNode(_toDisplayString(summary.value.targets || 0) + " 个目标", 1)
                        ]),
                        _: 1
                      }),
                      _createVNode(_component_v_card_text, null, {
                        default: _withCtx(() => [
                          _createTextVNode(_toDisplayString(summary.value.media_files || 0) + " 个媒体文件", 1)
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
                sm: "6",
                lg: "3"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_v_card, { variant: "outlined" }, {
                    default: _withCtx(() => [
                      _createVNode(_component_v_card_subtitle, null, {
                        default: _withCtx(() => [...(_cache[10] || (_cache[10] = [
                          _createTextVNode("本轮分流", -1)
                        ]))]),
                        _: 1
                      }),
                      _createVNode(_component_v_card_title, null, {
                        default: _withCtx(() => [
                          _createTextVNode(_toDisplayString(summary.value.eligible || 0) + " 个待处理", 1)
                        ]),
                        _: 1
                      }),
                      _createVNode(_component_v_card_text, null, {
                        default: _withCtx(() => [
                          _createTextVNode(_toDisplayString(summary.value.unchanged || 0) + " 个缓存命中 · " + _toDisplayString(summary.value.deferred || 0) + " 个延后", 1)
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
                sm: "6",
                lg: "3"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_v_card, { variant: "outlined" }, {
                    default: _withCtx(() => [
                      _createVNode(_component_v_card_subtitle, null, {
                        default: _withCtx(() => [...(_cache[11] || (_cache[11] = [
                          _createTextVNode("处理结果", -1)
                        ]))]),
                        _: 1
                      }),
                      _createVNode(_component_v_card_title, { class: "text-success" }, {
                        default: _withCtx(() => [
                          _createTextVNode(_toDisplayString(summary.value.success || 0) + " 个成功", 1)
                        ]),
                        _: 1
                      }),
                      _createVNode(_component_v_card_text, null, {
                        default: _withCtx(() => [
                          _createTextVNode(_toDisplayString(problemCount.value) + " 项问题", 1)
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
                sm: "6",
                lg: "3"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_v_card, { variant: "outlined" }, {
                    default: _withCtx(() => [
                      _createVNode(_component_v_card_subtitle, null, {
                        default: _withCtx(() => [...(_cache[12] || (_cache[12] = [
                          _createTextVNode("总耗时", -1)
                        ]))]),
                        _: 1
                      }),
                      _createVNode(_component_v_card_title, null, {
                        default: _withCtx(() => [
                          _createTextVNode(_toDisplayString(duration(summary.value.duration_seconds)), 1)
                        ]),
                        _: 1
                      }),
                      _createVNode(_component_v_card_text, null, {
                        default: _withCtx(() => [
                          _createTextVNode("扫描 " + _toDisplayString(duration(summary.value.scan_seconds)) + " · 处理 " + _toDisplayString(duration(summary.value.process_seconds)), 1)
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
          (issues.value.length)
            ? (_openBlock(), _createBlock(_component_v_card, {
                key: 0,
                variant: "outlined",
                class: "mt-5"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_v_card_title, { class: "d-flex align-center" }, {
                    default: _withCtx(() => [
                      _cache[13] || (_cache[13] = _createElementVNode("span", null, "需要处理", -1)),
                      _createVNode(_component_v_chip, {
                        class: "ml-2",
                        color: "error",
                        size: "small"
                      }, {
                        default: _withCtx(() => [
                          _createTextVNode(_toDisplayString(issues.value.length), 1)
                        ]),
                        _: 1
                      })
                    ]),
                    _: 1
                  }),
                  _createVNode(_component_v_card_text, null, {
                    default: _withCtx(() => [
                      _createVNode(_component_v_table, { density: "comfortable" }, {
                        default: _withCtx(() => [
                          _cache[14] || (_cache[14] = _createElementVNode("thead", null, [
                            _createElementVNode("tr", null, [
                              _createElementVNode("th", null, "状态"),
                              _createElementVNode("th", null, "文件或目标"),
                              _createElementVNode("th", null, "原因"),
                              _createElementVNode("th", null, "耗时")
                            ])
                          ], -1)),
                          _createElementVNode("tbody", null, [
                            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(issues.value.slice(0, 50), (item, index) => {
                              return (_openBlock(), _createElementBlock("tr", {
                                key: `issue-${index}`
                              }, [
                                _createElementVNode("td", null, [
                                  _createVNode(_component_v_chip, {
                                    size: "small",
                                    color: statusColor(item.status)
                                  }, {
                                    default: _withCtx(() => [
                                      _createTextVNode(_toDisplayString(statusLabels[item.status] || item.status), 1)
                                    ]),
                                    _: 2
                                  }, 1032, ["color"])
                                ]),
                                _createElementVNode("td", _hoisted_6, _toDisplayString(item.path || item.target || '-'), 1),
                                _createElementVNode("td", null, _toDisplayString(item.detail || '-'), 1),
                                _createElementVNode("td", null, _toDisplayString(duration(item.duration_seconds)), 1)
                              ]))
                            }), 128))
                          ])
                        ]),
                        _: 1
                      }),
                      (issues.value.length > 50)
                        ? (_openBlock(), _createElementBlock("div", _hoisted_7, "还有 " + _toDisplayString(issues.value.length - 50) + " 条问题，请查看运行日志。", 1))
                        : _createCommentVNode("", true)
                    ]),
                    _: 1
                  })
                ]),
                _: 1
              }))
            : _createCommentVNode("", true),
          _createVNode(_component_v_card, {
            variant: "outlined",
            class: "mt-5"
          }, {
            default: _withCtx(() => [
              _createVNode(_component_v_card_title, { class: "d-flex flex-wrap align-center ga-3" }, {
                default: _withCtx(() => [
                  _cache[15] || (_cache[15] = _createElementVNode("span", null, "目标结果", -1)),
                  _createVNode(_component_v_chip, { size: "small" }, {
                    default: _withCtx(() => [
                      _createTextVNode(_toDisplayString(filteredDetails.value.length) + " / " + _toDisplayString(details.value.length), 1)
                    ]),
                    _: 1
                  }),
                  _createVNode(_component_v_spacer),
                  _createVNode(_component_v_text_field, {
                    modelValue: search.value,
                    "onUpdate:modelValue": [
                      _cache[2] || (_cache[2] = $event => ((search).value = $event)),
                      _cache[3] || (_cache[3] = $event => (detailPage.value = 1))
                    ],
                    density: "compact",
                    "hide-details": "",
                    clearable: "",
                    label: "搜索路径或说明",
                    "prepend-inner-icon": "mdi-magnify",
                    style: {"max-width":"320px"}
                  }, null, 8, ["modelValue"]),
                  _createVNode(_component_v_select, {
                    "model-value": filter.value,
                    items: [{title:'全部',value:'all'},{title:'问题',value:'problem'},{title:'成功',value:'success'},{title:'预演',value:'dry_run'},{title:'延后',value:'deferred'}],
                    density: "compact",
                    "hide-details": "",
                    label: "状态",
                    style: {"max-width":"150px"},
                    "onUpdate:modelValue": resetFilter
                  }, null, 8, ["model-value"])
                ]),
                _: 1
              }),
              _createVNode(_component_v_card_text, null, {
                default: _withCtx(() => [
                  _createVNode(_component_v_table, { density: "comfortable" }, {
                    default: _withCtx(() => [
                      _cache[17] || (_cache[17] = _createElementVNode("thead", null, [
                        _createElementVNode("tr", null, [
                          _createElementVNode("th", null, "状态"),
                          _createElementVNode("th", null, "刮削目标"),
                          _createElementVNode("th", null, "媒体文件"),
                          _createElementVNode("th", null, "耗时"),
                          _createElementVNode("th", null, "说明")
                        ])
                      ], -1)),
                      _createElementVNode("tbody", null, [
                        (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(pagedDetails.value, (item, index) => {
                          return (_openBlock(), _createElementBlock("tr", {
                            key: `detail-${index}`
                          }, [
                            _createElementVNode("td", null, [
                              _createVNode(_component_v_chip, {
                                size: "small",
                                color: statusColor(item.status)
                              }, {
                                default: _withCtx(() => [
                                  _createTextVNode(_toDisplayString(statusLabels[item.status] || item.status), 1)
                                ]),
                                _: 2
                              }, 1032, ["color"])
                            ]),
                            _createElementVNode("td", _hoisted_8, _toDisplayString(item.path), 1),
                            _createElementVNode("td", null, _toDisplayString(item.files || 0), 1),
                            _createElementVNode("td", null, _toDisplayString(duration(item.duration_seconds)), 1),
                            _createElementVNode("td", null, _toDisplayString(item.detail || '-'), 1)
                          ]))
                        }), 128)),
                        (!pagedDetails.value.length)
                          ? (_openBlock(), _createElementBlock("tr", _hoisted_9, [...(_cache[16] || (_cache[16] = [
                              _createElementVNode("td", {
                                colspan: "5",
                                class: "text-center text-medium-emphasis py-6"
                              }, "没有匹配的目标", -1)
                            ]))]))
                          : _createCommentVNode("", true)
                      ])
                    ]),
                    _: 1
                  }),
                  _createElementVNode("div", _hoisted_10, [
                    _createVNode(_component_v_pagination, {
                      modelValue: detailPage.value,
                      "onUpdate:modelValue": _cache[4] || (_cache[4] = $event => ((detailPage).value = $event)),
                      length: pageCount.value,
                      density: "compact",
                      "total-visible": 5
                    }, null, 8, ["modelValue", "length"])
                  ])
                ]),
                _: 1
              })
            ]),
            _: 1
          }),
          (nfoChanges.value.length)
            ? (_openBlock(), _createBlock(_component_v_card, {
                key: 1,
                variant: "outlined",
                class: "mt-5"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_v_card_title, null, {
                    default: _withCtx(() => [
                      _cache[18] || (_cache[18] = _createTextVNode("NFO 实际变更 ", -1)),
                      _createVNode(_component_v_chip, {
                        class: "ml-2",
                        size: "small",
                        color: "info"
                      }, {
                        default: _withCtx(() => [
                          _createTextVNode(_toDisplayString(nfoChanges.value.length) + " 个文件", 1)
                        ]),
                        _: 1
                      })
                    ]),
                    _: 1
                  }),
                  _createVNode(_component_v_card_text, null, {
                    default: _withCtx(() => [
                      _createVNode(_component_v_table, { density: "comfortable" }, {
                        default: _withCtx(() => [
                          _cache[19] || (_cache[19] = _createElementVNode("thead", null, [
                            _createElementVNode("tr", null, [
                              _createElementVNode("th", null, "文件"),
                              _createElementVNode("th", null, "字段"),
                              _createElementVNode("th", null, "修改前"),
                              _createElementVNode("th", null, "修改后"),
                              _createElementVNode("th", null, "状态")
                            ])
                          ], -1)),
                          _createElementVNode("tbody", null, [
                            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(nfoChanges.value.slice(0, 100), (change, index) => {
                              return (_openBlock(), _createElementBlock(_Fragment, {
                                key: `nfo-${index}`
                              }, [
                                (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(change.fields || [], (field) => {
                                  return (_openBlock(), _createElementBlock("tr", {
                                    key: `${index}-${field.field}`
                                  }, [
                                    _createElementVNode("td", _hoisted_11, _toDisplayString(change.path), 1),
                                    _createElementVNode("td", null, _toDisplayString(field.field), 1),
                                    _createElementVNode("td", _hoisted_12, _toDisplayString(field.before || '（空）'), 1),
                                    _createElementVNode("td", _hoisted_13, _toDisplayString(field.after || '（空）'), 1),
                                    _createElementVNode("td", null, _toDisplayString(change.status === 'dry_run' ? '预演' : '已写入'), 1)
                                  ]))
                                }), 128))
                              ], 64))
                            }), 128))
                          ])
                        ]),
                        _: 1
                      })
                    ]),
                    _: 1
                  })
                ]),
                _: 1
              }))
            : _createCommentVNode("", true)
        ], 64))
      : _createCommentVNode("", true)
  ]))
}
}

};
const Page = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-3de1365a"]]);

export { Page as default };
