import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const frontendDir = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const projectDir = resolve(frontendDir, '..')
const children = [
  spawn('uv.exe', ['run', 'uvicorn', 'baseball_analysis.app:app', '--reload'], { cwd: projectDir, stdio: 'inherit' }),
  spawn(process.execPath, [resolve(frontendDir, 'node_modules/vite/bin/vite.js')], { cwd: frontendDir, stdio: 'inherit' }),
]

function stop() {
  children.forEach(child => child.kill())
  process.exit()
}

process.on('SIGINT', stop)
process.on('SIGTERM', stop)
