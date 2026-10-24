import { readdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'

const targets = [
  path.resolve('..', 'plugins.v3', 'libraryscraperfix', 'dist', 'assets'),
  path.resolve('..', 'plugins.v3', 'removelinkfix', 'dist', 'assets'),
]

for (const directory of targets) {
  const entries = await readdir(directory, { withFileTypes: true })
  for (const entry of entries) {
    if (!entry.isFile() || !entry.name.endsWith('.js')) continue
    const file = path.join(directory, entry.name)
    const source = await readFile(file, 'utf8')
    await writeFile(file, source.replace(/[ \t]+$/gm, ''), 'utf8')
  }
}
