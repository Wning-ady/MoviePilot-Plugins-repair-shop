<script setup>
import { computed, onMounted, ref } from 'vue'

const props = defineProps({
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: 'RemoveLinkFix' },
  sourcePluginId: { type: String, default: '' },
  navKey: { type: String, default: 'main' },
})
const emit = defineEmits(['action', 'switch', 'close'])
const loading = ref(false)
const error = ref('')
const payload = ref({ history: [] })
const filter = ref('all')
const search = ref('')
const selectedBatch = ref(0)

const history = computed(() => Array.isArray(payload.value.history) ? payload.value.history.filter(Boolean) : [])
const historyOptions = computed(() => history.value.map((item, index) => ({
  title: `${index === 0 ? '最近批次' : `第 ${index + 1} 批`} · ${item.finished_at || item.started_at || '未记录时间'}`,
  value: index,
})))
const batch = computed(() => history.value[selectedBatch.value] || {})
const items = computed(() => batch.value.items || [])
const filteredItems = computed(() => items.value.filter((item) => {
  const status = `${item.history_status || ''} ${item.torrent_status || ''}`
  const matchesFilter = filter.value === 'all' || (filter.value === 'problem' ? !['deleted', 'sent'].includes(item.history_status) || ['missing_hash', 'not_sent'].includes(item.torrent_status) : status.includes(filter.value))
  const query = search.value.trim().toLowerCase()
  return matchesFilter && (!query || `${item.source || ''} ${item.detail || ''} ${item.episode || ''}`.toLowerCase().includes(query))
}))
const historyLabels = { deleted: '已删除', retained: '仍保留', disabled: '未启用', not_processed: '未执行' }
const torrentLabels = { sent: '已发送', missing_hash: '缺少 Hash', disabled: '未启用', not_sent: '未发送' }
const statusColor = (value) => ({ deleted: 'success', sent: 'success', retained: 'warning', missing_hash: 'error', not_sent: 'warning', failed: 'error' }[value] || 'default')
const itemTimestamp = (item) => item.completed_at || item.timestamp || batch.value.finished_at || batch.value.started_at || '-'

function normalizeResponse(result) { return result?.data?.history ? result.data : result }
async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await props.api?.get?.(`plugin/${props.pluginId}/history`)
    payload.value = normalizeResponse(result) || { history: [] }
    selectedBatch.value = 0
  } catch (err) { error.value = err?.message || '读取删除结果失败' } finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <div class="plugin-page pa-4">
    <div class="d-flex flex-wrap align-center ga-3 mb-4"><div><div class="text-h5">清理媒体文件</div><div class="text-body-2 text-medium-emphasis">硬链接清理、整理记录和种子联动结果</div></div><v-spacer /><v-select v-if="historyOptions.length > 1" v-model="selectedBatch" :items="historyOptions" density="compact" hide-details label="删除批次" style="max-width: 280px" /><v-btn variant="tonal" :loading="loading" prepend-icon="mdi-refresh" @click="load">刷新</v-btn><v-btn variant="text" prepend-icon="mdi-cog" @click="emit('switch')">配置</v-btn></div>
    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">{{ error }}</v-alert>
    <v-alert v-else-if="!batch.finished_at" type="info" variant="tonal" class="mb-4">暂无删除结果。下一次安全联动删除后会显示真实的文件、整理记录和种子状态。</v-alert>
    <template v-else>
      <v-alert :type="batch.failed ? 'error' : 'success'" variant="tonal" class="mb-4"><div class="text-subtitle-1 font-weight-medium">{{ batch.failed ? `删除批次完成，${batch.failed} 项需处理` : '删除批次完成' }}</div><div class="text-body-2">{{ batch.finished_at }} · 处理 {{ batch.processed || 0 }} 个任务 · 删除 {{ batch.files_deleted || 0 }} 个硬链接文件</div></v-alert>
      <v-row><v-col cols="12" sm="4"><v-card variant="outlined"><v-card-subtitle>整理记录</v-card-subtitle><v-card-title>{{ batch.histories_deleted || 0 }} 条已删除</v-card-title><v-card-text>{{ batch.histories_retained || 0 }} 条仍保留</v-card-text></v-card></v-col><v-col cols="12" sm="4"><v-card variant="outlined"><v-card-subtitle>种子联动</v-card-subtitle><v-card-title>{{ batch.torrents_sent || 0 }} 条已发送</v-card-title><v-card-text>{{ batch.torrents_missing_hash || 0 }} 条缺少 Hash</v-card-text></v-card></v-col><v-col cols="12" sm="4"><v-card variant="outlined"><v-card-subtitle>执行结果</v-card-subtitle><v-card-title>{{ batch.success || 0 }} 项完成</v-card-title><v-card-text>{{ batch.skipped || 0 }} 项跳过 · {{ batch.failed || 0 }} 项失败</v-card-text></v-card></v-col></v-row>
      <v-card variant="outlined" class="mt-5"><v-card-title class="d-flex flex-wrap align-center ga-3"><span>最近删除明细</span><v-chip size="small">{{ filteredItems.length }} / {{ items.length }}</v-chip><v-spacer /><v-text-field v-model="search" density="compact" hide-details clearable label="搜索源文件或说明" prepend-inner-icon="mdi-magnify" style="max-width: 320px" /><v-select v-model="filter" :items="[{title:'全部',value:'all'},{title:'问题',value:'problem'},{title:'仍保留',value:'retained'},{title:'缺少 Hash',value:'missing_hash'},{title:'已删除',value:'deleted'}]" density="compact" hide-details label="状态" style="max-width: 150px" /></v-card-title><v-card-text><v-table density="comfortable"><thead><tr><th>时间</th><th>集数</th><th>记录 ID</th><th>整理记录</th><th>种子联动</th><th>源文件</th><th>说明</th></tr></thead><tbody><tr v-for="(item, index) in filteredItems" :key="index"><td class="timestamp-cell">{{ itemTimestamp(item) }}</td><td>{{ item.episode || '-' }}</td><td>{{ item.history_id || '-' }}</td><td><v-chip size="small" :color="statusColor(item.history_status)">{{ historyLabels[item.history_status] || item.history_status || '-' }}</v-chip></td><td><v-chip size="small" :color="statusColor(item.torrent_status)">{{ torrentLabels[item.torrent_status] || item.torrent_status || '-' }}</v-chip></td><td class="path-cell">{{ item.source || '-' }}</td><td class="text-cell">{{ item.detail || '-' }}</td></tr><tr v-if="!filteredItems.length"><td colspan="7" class="text-center text-medium-emphasis py-6">没有匹配的记录</td></tr></tbody></v-table></v-card-text></v-card>
    </template>
  </div>
</template>

<style scoped>
.path-cell { min-width: 220px; max-width: 460px; white-space: normal; overflow-wrap: anywhere; }
.text-cell { min-width: 180px; max-width: 360px; white-space: normal; overflow-wrap: anywhere; }
.timestamp-cell { min-width: 160px; white-space: nowrap; }
</style>
