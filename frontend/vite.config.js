import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import federation from '@originjs/vite-plugin-federation'
import path from 'node:path'

const vuetifyCssFilter = {
  postcssPlugin: 'moviepilot-federation-vuetify-css-filter',
  Root(root) {
    const sourcePath = root.source?.input?.file?.replaceAll('\\', '/') || ''
    if (sourcePath.includes('/node_modules/vuetify/') || sourcePath.includes('/node_modules/@mdi/')) {
      root.nodes = []
      return
    }
    root.walkRules((rule) => {
      if (rule.selector && (rule.selector.includes('.v-') || rule.selector.includes('.mdi-'))) {
        rule.remove()
      }
    })
  },
}

const target = process.env.PLUGIN_TARGET || 'library'
const configs = {
  library: {
    name: 'LibraryScraperFix',
    source: './src/library/Page.vue',
    config: './src/library/Config.vue',
    output: '../plugins.v3/libraryscraperfix/dist/assets',
  },
  remove: {
    name: 'RemoveLinkFix',
    source: './src/remove/Page.vue',
    config: './src/remove/Config.vue',
    output: '../plugins.v3/removelinkfix/dist/assets',
  },
}

const plugin = configs[target]
if (!plugin) {
  throw new Error(`Unknown PLUGIN_TARGET: ${target}`)
}

export default defineConfig({
  plugins: [
    vue(),
    federation({
      name: plugin.name,
      filename: 'remoteEntry.js',
      exposes: {
        './Page': plugin.source,
        './AppPage': plugin.source,
        './Config': plugin.config,
      },
      shared: {
        vue: { requiredVersion: false, generate: false },
        vuetify: { requiredVersion: false, generate: false, singleton: true },
        'vuetify/styles': { requiredVersion: false, generate: false, singleton: true },
      },
      format: 'esm',
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(process.cwd(), 'src'),
    },
  },
  css: {
    postcss: {
      plugins: [vuetifyCssFilter],
    },
  },
  build: {
    target: 'esnext',
    minify: false,
    cssCodeSplit: true,
    assetsDir: '',
    outDir: path.resolve(process.cwd(), plugin.output),
    emptyOutDir: true,
    rollupOptions: {
      input: path.resolve(process.cwd(), plugin.source),
      output: {
        entryFileNames: '[name].js',
        chunkFileNames: '[name]-[hash].js',
        assetFileNames: '[name]-[hash][extname]',
      },
    },
  },
})
