<script setup>
import { reactive } from 'vue'

const props = defineProps({
  initialConfig: { type: Object, default: () => ({}) },
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: 'LibraryScraperFix' },
  sourcePluginId: { type: String, default: '' },
})
const emit = defineEmits(['save', 'close', 'switch'])
const config = reactive({ ...props.initialConfig })
function save() { emit('save', { ...config }) }
</script>

<template>
  <div class="plugin-config pa-4">
    <div class="d-flex align-center mb-4"><div><div class="text-h5">媒体库刮削设置</div><div class="text-body-2 text-medium-emphasis">先使用预演和单目录验证，再扩大扫描范围。</div></div><v-spacer /><v-btn variant="text" @click="emit('switch')">查看运行结果</v-btn></div>
    <v-expansion-panels multiple :model-value="[0, 1, 2]">
      <v-expansion-panel title="运行与扫描范围"><v-expansion-panel-text>
        <v-row><v-col cols="12" md="4"><v-switch v-model="config.enabled" label="启用定时任务" color="primary" /><v-switch v-model="config.onlyonce" label="保存后运行一次" color="primary" /><v-switch v-model="config.notify" label="发送运行摘要" color="primary" /></v-col><v-col cols="12" md="8"><v-text-field v-model="config.cron" label="执行周期" hint="5 位 Cron，例如 0 3 * * *" persistent-hint /><v-textarea v-model="config.scraper_paths" label="刮削路径" rows="4" hint="每行一个容器内绝对路径，可追加 #电影 或 #电视剧" persistent-hint /><v-textarea v-model="config.exclude_paths" label="排除路径" rows="2" /></v-col></v-row>
      </v-expansion-panel-text></v-expansion-panel>
      <v-expansion-panel title="刮削与增量策略"><v-expansion-panel-text>
        <v-row><v-col cols="12" md="6"><v-switch v-model="config.dry_run" label="预演模式" color="primary" /><v-switch v-model="config.incremental" label="启用目标缓存" color="primary" /><v-select v-model="config.mode" :items="[{title:'仅补齐缺失元数据（推荐）',value:''},{title:'覆盖未被全局禁用的元数据',value:'force_all'}]" label="元数据写入策略" /></v-col><v-col cols="12" md="6"><v-text-field v-model.number="config.max_targets" type="number" label="单次最多处理目标" /><v-text-field v-model.number="config.interval_seconds" type="number" step="0.1" label="目标间隔（秒）" /><v-text-field v-model.number="config.retry_count" type="number" label="异常重试次数" /><v-text-field v-model.number="config.full_scan_days" type="number" label="目标完整复核（天）" /></v-col></v-row>
      </v-expansion-panel-text></v-expansion-panel>
      <v-expansion-panel title="NFO 修复与一次性维护"><v-expansion-panel-text>
        <v-switch v-model="config.repair_nfo_fields" label="修复空白概要和通用标题" color="primary" /><v-text-field v-model.number="config.nfo_audit_days" type="number" label="NFO 完整复核（天）" /><v-divider class="my-3" /><v-switch v-model="config.force_full_scan" label="下次忽略目标缓存" color="warning" /><v-switch v-model="config.clear_cache" label="清空全部增量缓存" color="error" />
      </v-expansion-panel-text></v-expansion-panel>
    </v-expansion-panels>
    <div class="d-flex justify-end ga-2 mt-5"><v-btn variant="text" @click="emit('close')">取消</v-btn><v-btn color="primary" @click="save">保存设置</v-btn></div>
  </div>
</template>
