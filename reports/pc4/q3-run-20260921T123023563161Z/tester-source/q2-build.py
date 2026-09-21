"""Explicit final-SHA production build with all tracked external imports recorded.

Run only after pc1 declares the final SHA/assets, in a separate clean checkout.
No install, server start, API/model request, git mutation or deployment.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from q2_contract import HEX40, PRODUCT_PATHS, git, inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--product-root', type=Path, required=True)
    parser.add_argument('--final-sha', required=True)
    parser.add_argument('--npm-cli', type=Path, help='Portable npm-cli.js, run by installed Node; no installer is invoked')
    args = parser.parse_args()
    root = args.product_root.resolve(strict=True)
    if not HEX40.fullmatch(args.final_sha) or git(root, 'rev-parse', 'HEAD') != args.final_sha:
        parser.error('Explicit final SHA must match checkout HEAD')
    if git(root, 'diff', '--name-only', 'HEAD', '--', *PRODUCT_PATHS) or git(root, 'ls-files', '--others', '--exclude-standard', '--', *PRODUCT_PATHS):
        parser.error('Clean final product checkout required')
    for dependency in ('next/dist/bin/next', 'typescript/lib/typescript.js'):
        if not (root / 'apps/web/node_modules' / dependency).is_file():
            parser.error('Existing locked dependencies required; no automatic installation')
    node = shutil.which('node')
    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    if args.npm_cli:
        if not node or not args.npm_cli.is_file():
            parser.error('Installed node and actual npm-cli.js required')
        command = [node, str(args.npm_cli.resolve()), 'run', 'build']
    elif npm:
        command = [npm, 'run', 'build']
    else:
        parser.error('npm unavailable; provide installed portable --npm-cli')
    spec = importlib.util.spec_from_file_location('pc4_build_helper', root / 'scripts/build_deployment_bundle.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    source_before = helper.source_fingerprint(root)  # also rejects frontend .env and linked paths
    record = {'status': 'started', 'headBefore': args.final_sha, 'productBefore': inventory(root),
              'command': command, 'startedAt': datetime.now(timezone.utc).isoformat(), 'nextPublicApiBase': ''}
    path = root / '.local/pc4-q2-build.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    def save():
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    save()
    allowed = {'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'TEMP', 'TMP', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'HOME'}
    env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    env.update(CI='1', NEXT_TELEMETRY_DISABLED='1', NODE_ENV='production', NEXT_PUBLIC_API_BASE='', NPM_CONFIG_UPDATE_NOTIFIER='false')
    try:
        helper._invalidate_stamp(root)
        with (path.parent / 'pc4-q2-build.log').open('wb') as log:
            completed = subprocess.run(command, cwd=root / 'apps/web', env=env, stdout=log, stderr=subprocess.STDOUT,
                                       timeout=900, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        record.update(buildExitCode=completed.returncode, headAfter=git(root, 'rev-parse', 'HEAD'), productAfter=inventory(root))
        if completed.returncode or record['headBefore'] != record['headAfter'] or record['productBefore'] != record['productAfter']:
            raise RuntimeError('Build failed or final product inputs changed during build')
        helper.write_build_stamp(root, source_before)
        output = helper._output_files(root)
        stamp = helper._verified_stamp(root, output)
        record.update(status='complete', outputFingerprint=stamp['outputFingerprint'], frontendSourceFingerprint=stamp['sourceAfter'])
    except Exception as error:
        record.update(status='failed', error={'type': type(error).__name__, 'message': str(error)})
    record['finishedAt'] = datetime.now(timezone.utc).isoformat()
    save()
    print(json.dumps({'status': record['status'], 'evidence': str(path), 'outputFingerprint': record.get('outputFingerprint')}, ensure_ascii=False))
    return 0 if record['status'] == 'complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
