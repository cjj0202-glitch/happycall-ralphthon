import { access, symlink } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../../..');
const modules = path.join(root, 'apps/web/node_modules');
const app = path.join(here, 'ui-harness');
await access(path.join(modules, 'next/dist/bin/next'));
try { await access(path.join(app, 'node_modules')); }
catch { await symlink(modules, path.join(app, 'node_modules'), process.platform === 'win32' ? 'junction' : 'dir'); }
const child = spawn(process.execPath, [path.join(modules, 'next/dist/bin/next'), 'dev', app, '--hostname', '127.0.0.1', '--port', process.env.PC4_UI_PORT || '13104'], { cwd: root, stdio: 'inherit', windowsHide: true, env: { ...process.env, NEXT_TELEMETRY_DISABLED: '1' } });
for (const signal of ['SIGINT','SIGTERM']) process.on(signal, () => child.kill(signal));
child.on('exit', code => process.exit(code ?? 1));
