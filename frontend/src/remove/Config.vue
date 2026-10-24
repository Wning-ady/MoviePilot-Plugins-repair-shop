<script setup>
import { reactive } from 'vue'

const props = defineProps({
  initialConfig: { type: Object, default: () => ({}) },
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: 'RemoveLinkFix' },
  sourcePluginId: { type: String, default: '' },
})
const emit = defineEmits(['save', 'close', 'switch'])
const config = reactive({ ...props.initialConfig })
function save() { emit('save', { ...config }) }
</script>

<template>
  <div class="plugin-config pa-4">
    <div class="d-flex align-center mb-4"><div><div class="text-h5">清理媒体文件设置</div><div class="text-body-2 text-medium-emphasis">删除联动始终以整理记录、路径、Hash、inode 和硬链接数复核为前提。</div></div><v-spacer /><v-btn variant="text" @click="emit('switch')">查看删除结果</v-btn></div>
    <v-expansion-panels multiple :model-value="[0, 1, 2]">
      <v-expansion-panel title="运行与删除策略"><v-expansion-panel-text>
        <v-row><v-col cols="12" md="6"><v-switch v-model="config.enabled" label="启用插件" color="primary" /><v-switch v-model="config.notify" label="发送运行通知" color="primary" /><v-switch v-model="config.delete_scrap_infos" label="清理 NFO、图片等刮削文件" color="primary" /></v-col><v-col cols="12" md="6"><v-switch v-model="config.delete_torrents" label="联动删除种子" color="warning" /><v-switch v-model="config.delete_history" label="删除整理记录" color="warning" /><v-switch v-model="config.delayed_deletion" label="延迟删除" color="primary" /><v-text-field v-model.number="config.delay_seconds" type="number" label="延迟秒数" /></v-col></v-row>
      </v-expansion-panel-text></v-expansion-panel>
      <v-expansion-panel title="监控与排除范围"><v-expansion-panel-text>
        <v-textarea v-model="config.monitor_dirs" label="监控目录" rows="4" hint="每行一个下载根或媒体库根" persistent-hint /><v-textarea v-model="config.exclude_dirs" label="排除目录" rows="3" /><v-textarea v-model="config.exclude_keywords" label="排除关键词" rows="2" /><v-textarea v-model="config.custom_scrap_extensions" label="自定义刮削文件扩展名" rows="2" />
      </v-expansion-panel-text></v-expansion-panel>
      <v-expansion-panel title="STRM 监控"><v-expansion-panel-text><v-switch v-model="config.monitor_strm_deletion" label="监控 STRM 删除" color="primary" /><v-textarea v-model="config.strm_path_mappings" label="路径映射" rows="3" hint="格式：STRM目录:存储类型:网盘目录" persistent-hint /></v-expansion-panel-text></v-expansion-panel>
    </v-expansion-panels>
    <div class="d-flex justify-end ga-2 mt-5"><v-btn variant="text" @click="emit('close')">取消</v-btn><v-btn color="primary" @click="save">保存设置</v-btn></div>
  </div>
</template>
