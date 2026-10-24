<script setup>
import { computed, onMounted, ref } from 'vue'

const props = defineProps({
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: 'LibraryScraperFix' },
  sourcePluginId: { type: String, default: '' },
  navKey: { type: String, default: 'main' },
})
const emit = defineEmits(['action', 'switch', 'close'])

const loading = ref(false)
const error = ref('')
const payload = ref({ last_run: {}, history: [], running: {} })
const filter = ref('all')
const search = ref('')
const detailPage = ref(1)
const selectedRun = ref(0)

const history = computed(() => {
  const records = Array.isArray(payload.value.history) ? payload.value.history.filter(Boolean) : []
  if (records.length) return records
  return payload.value.last_run && Object.keys(payload.value.last_run).length ? [payload.value.last_run] : []
})
const historyOptions = computed(() => history.value.map((item, index) => ({
  title: `${index === 0 ? '最近一次' : `第 ${index + 1} 次`} · ${item.finished_at || item.started_at || '未记录时间'}`,
  value: index,
})))
const summary = computed(() => history.value[selectedRun.value] || payload.value.last_run || {})
const running = computed(() => payload.value.running || {})
const details = computed(() => (summary.value.details || []).filter(Boolean))
const issues = computed(() => (summary.value.issues || []).filter(Boolean))
const problemCount = computed(() => Number(summary.value.failed || 0) + Number(summary.value.partial || 0) + Number(summary.value.unrecognized || 0) + Number(summary.value.scan_errors || 0) + Number(summary.value.invalid_paths || 0) + (summary.value.cancelled ? 1 : 0))
const filteredDetails = computed(() => {
  const query = search.value.trim().toLowerCase()
  return details.value.filter((item) => {
    const status = item.status || ''
    const matchesFilter = filter.value === 'all' || (filter.value === 'problem' ? ['failed', 'partial', 'unrecognized', 'cancelled'].includes(status) : status === filter.value)
    const text = `${item.path || ''} ${item.detail || ''}`.toLowerCase()
    return matchesFilter && (!query || text.includes(query))
  })
})
const pageSize = 20
const pageCount = computed(() => Math.max(1, Math.ceil(filteredDetails.value.length / pageSize)))
const pagedDetails = computed(() => filteredDetails.value.slice((detailPage.value - 1) * pageSize, detailPage.value * pageSize))
const nfoChanges = computed(() => summary.value.nfo_changes || [])

const statusLabels = {
  success: '成功',
  failed: '失败',
  partial: '部分完成',
  unrecognized: '未识别',
  dry_run: '预演',
  deferred: '延后',
  cancelled: '已取消',
}

function statusColor(status) {
  return { success: 'success', failed: 'error', partial: 'warning', unrecognized: 'warning', dry_run: 'info', deferred: 'secondary', cancelled: 'error' }[status] || 'default'
}

function duration(value) {
  const seconds = Number(value || 0)
  if (seconds >= 3600) return `${Math.floor(seconds / 3600)} 小时 ${Math.floor(seconds % 3600 / 60)} 分`
  if (seconds >= 60) return `${Math.floor(seconds / 60)} 分 ${Math.round(seconds % 60)} 秒`
  return `${Math.round(seconds * 100) / 100} 秒`
}

function normalizeResponse(result) {
  return result?.data?.last_run || result?.data?.history ? result.data : result
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await props.api?.get?.(`plugin/${props.pluginId}/history`)
    payload.value = normalizeResponse(result) || { last_run: {}, history: [], running: {} }
    selectedRun.value = 0
    detailPage.value = Math.min(detailPage.value, pageCount.value)
  } catch (err) {
    error.value = err?.message || '读取运行记录失败'
  } finally {
    loading.value = false
  }
}

function resetFilter(value) {
  filter.value = value
  detailPage.value = 1
}

onMounted(load)
</script>

<template>
  <div class="plugin-page pa-4">
    <div class="d-flex flex-wrap align-center ga-3 mb-4">
      <div>
        <div class="text-h5">媒体库刮削</div>
        <div class="text-body-2 text-medium-emphasis">增量刮削、NFO 修复与运行记录</div>
      </div>
      <v-spacer />
      <v-select v-if="historyOptions.length > 1" v-model="selectedRun" :items="historyOptions" density="compact" hide-details label="运行记录" style="max-width: 280px" />
      <v-btn variant="tonal" :loading="loading" prepend-icon="mdi-refresh" @click="load">刷新</v-btn>
      <v-btn variant="text" prepend-icon="mdi-cog" @click="emit('switch')">配置</v-btn>
    </div>

    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">{{ error }}</v-alert>
    <v-alert v-else-if="running.current || running.stage" type="info" variant="tonal" class="mb-4">
      <div class="d-flex justify-space-between align-center">
        <span>运行中：{{ running.stage || '处理中' }}</span>
        <span>{{ running.current || 0 }} / {{ running.total || 0 }}</span>
      </div>
      <v-progress-linear class="mt-3" :model-value="running.total ? running.current / running.total * 100 : undefined" :indeterminate="!running.total" />
    </v-alert>
    <v-alert v-else-if="!summary.started_at && !summary.finished_at" type="info" variant="tonal" class="mb-4">暂无运行记录。下一次运行后会显示结果、缓存命中和问题明细。</v-alert>

    <template v-if="summary.started_at || summary.finished_at">
      <v-alert :type="problemCount ? 'warning' : 'success'" variant="tonal" class="mb-4">
        <div class="text-subtitle-1 font-weight-medium">{{ problemCount ? `运行完成，${problemCount} 项需要处理` : '运行完成，未发现问题' }}</div>
        <div class="text-body-2">{{ summary.finished_at || summary.started_at }} · {{ summary.dry_run_enabled ? '预演' : '执行' }} · 总耗时 {{ duration(summary.duration_seconds) }}</div>
      </v-alert>

      <v-row>
        <v-col cols="12" sm="6" lg="3"><v-card variant="outlined"><v-card-subtitle>扫描范围</v-card-subtitle><v-card-title>{{ summary.targets || 0 }} 个目标</v-card-title><v-card-text>{{ summary.media_files || 0 }} 个媒体文件</v-card-text></v-card></v-col>
        <v-col cols="12" sm="6" lg="3"><v-card variant="outlined"><v-card-subtitle>本轮分流</v-card-subtitle><v-card-title>{{ summary.eligible || 0 }} 个待处理</v-card-title><v-card-text>{{ summary.unchanged || 0 }} 个缓存命中 · {{ summary.deferred || 0 }} 个延后</v-card-text></v-card></v-col>
        <v-col cols="12" sm="6" lg="3"><v-card variant="outlined"><v-card-subtitle>处理结果</v-card-subtitle><v-card-title class="text-success">{{ summary.success || 0 }} 个成功</v-card-title><v-card-text>{{ problemCount }} 项问题</v-card-text></v-card></v-col>
        <v-col cols="12" sm="6" lg="3"><v-card variant="outlined"><v-card-subtitle>总耗时</v-card-subtitle><v-card-title>{{ duration(summary.duration_seconds) }}</v-card-title><v-card-text>扫描 {{ duration(summary.scan_seconds) }} · 处理 {{ duration(summary.process_seconds) }}</v-card-text></v-card></v-col>
      </v-row>

      <v-card v-if="issues.length" variant="outlined" class="mt-5">
        <v-card-title class="d-flex align-center"><span>需要处理</span><v-chip class="ml-2" color="error" size="small">{{ issues.length }}</v-chip></v-card-title>
        <v-card-text>
          <v-table density="comfortable"><thead><tr><th>状态</th><th>文件或目标</th><th>原因</th><th>耗时</th></tr></thead><tbody>
            <tr v-for="(item, index) in issues.slice(0, 50)" :key="`issue-${index}`"><td><v-chip size="small" :color="statusColor(item.status)">{{ statusLabels[item.status] || item.status }}</v-chip></td><td class="path-cell">{{ item.path || item.target || '-' }}</td><td>{{ item.detail || '-' }}</td><td>{{ duration(item.duration_seconds) }}</td></tr>
          </tbody></v-table>
          <div v-if="issues.length > 50" class="text-caption text-medium-emphasis mt-2">还有 {{ issues.length - 50 }} 条问题，请查看运行日志。</div>
        </v-card-text>
      </v-card>

      <v-card variant="outlined" class="mt-5">
        <v-card-title class="d-flex flex-wrap align-center ga-3"><span>目标结果</span><v-chip size="small">{{ filteredDetails.length }} / {{ details.length }}</v-chip><v-spacer /><v-text-field v-model="search" density="compact" hide-details clearable label="搜索路径或说明" prepend-inner-icon="mdi-magnify" style="max-width: 320px" @update:model-value="detailPage = 1" /><v-select :model-value="filter" :items="[{title:'全部',value:'all'},{title:'问题',value:'problem'},{title:'成功',value:'success'},{title:'预演',value:'dry_run'},{title:'延后',value:'deferred'}]" density="compact" hide-details label="状态" style="max-width: 150px" @update:model-value="resetFilter" /></v-card-title>
        <v-card-text>
          <v-table density="comfortable"><thead><tr><th>状态</th><th>刮削目标</th><th>媒体文件</th><th>耗时</th><th>说明</th></tr></thead><tbody>
            <tr v-for="(item, index) in pagedDetails" :key="`detail-${index}`"><td><v-chip size="small" :color="statusColor(item.status)">{{ statusLabels[item.status] || item.status }}</v-chip></td><td class="path-cell">{{ item.path }}</td><td>{{ item.files || 0 }}</td><td>{{ duration(item.duration_seconds) }}</td><td>{{ item.detail || '-' }}</td></tr>
            <tr v-if="!pagedDetails.length"><td colspan="5" class="text-center text-medium-emphasis py-6">没有匹配的目标</td></tr>
          </tbody></v-table>
          <div class="d-flex justify-center mt-3"><v-pagination v-model="detailPage" :length="pageCount" density="compact" :total-visible="5" /></div>
        </v-card-text>
      </v-card>

      <v-card v-if="nfoChanges.length" variant="outlined" class="mt-5">
        <v-card-title>NFO 实际变更 <v-chip class="ml-2" size="small" color="info">{{ nfoChanges.length }} 个文件</v-chip></v-card-title>
        <v-card-text><v-table density="comfortable"><thead><tr><th>文件</th><th>字段</th><th>修改前</th><th>修改后</th><th>状态</th></tr></thead><tbody>
          <template v-for="(change, index) in nfoChanges.slice(0, 100)" :key="`nfo-${index}`"><tr v-for="field in change.fields || []" :key="`${index}-${field.field}`"><td class="path-cell">{{ change.path }}</td><td>{{ field.field }}</td><td class="text-cell">{{ field.before || '（空）' }}</td><td class="text-cell">{{ field.after || '（空）' }}</td><td>{{ change.status === 'dry_run' ? '预演' : '已写入' }}</td></tr></template>
        </tbody></v-table></v-card-text>
      </v-card>
    </template>
  </div>
</template>

<style scoped>
.path-cell { min-width: 220px; max-width: 460px; white-space: normal; overflow-wrap: anywhere; }
.text-cell { min-width: 180px; max-width: 360px; white-space: normal; overflow-wrap: anywhere; }
</style>
