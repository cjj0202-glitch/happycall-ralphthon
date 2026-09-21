"""Read-only final-release gates; preparation is never a product test pass."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
PRODUCT_PATHS = ('apps/web', 'server', 'data', 'scripts', 'pyproject.toml', 'uv.lock')
REQUIRED_SELECTORS = ('naturalCompletionControl', 'segmentControl', 'differentToteNotice', 'tmsRegion', 'tmsRawSourceControl')
BOUNDARY_IDS = {
    'audio-end-seek-must-not-complete', 'audio-segment-must-not-complete',
    'previous-case-native-ended-must-not-complete-current',
    'new-text-different-day-no-implicit-evidence', 'explicit-reference-text-media-missing',
    'media-404-and-retry', 'api-error-and-recovery-no-false-save',
    'api-offline-example-and-reconnect', 'browser-offline-save-and-recovery',
    'two-ui-editors-real-409-no-overwrite', 'future-evidence-hidden-in-investigation-ui',
    'different-business-totes-not-continuous-tracking',
    *(f'responsive-keyboard-reduced-motion-{width}' for width in (1365, 921, 390)),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(root), *args], text=True, encoding='utf-8').strip()


def safe_name(name: object) -> bool:
    return (isinstance(name, str) and bool(name) and '\\' not in name and ':' not in name
            and '%' not in name and not name.startswith('/')
            and all(p not in ('', '.', '..') for p in name.split('/'))
            and all(ord(c) >= 32 for c in name))


def required_inputs(contract: dict) -> list[str]:
    problems = []
    if contract.get('schema') != 'pc4-final-release-v1':
        problems.append('SCHEMA_REQUIRED')
    if not HEX40.fullmatch(str(contract.get('finalSha', ''))):
        problems.append('FINAL_INTEGRATION_SHA_REQUIRED')
    for name in ('fixtureSha256', 'manifestSha256', 'frontendSourceFingerprint', 'frontendOutputFingerprint'):
        if not HEX64.fullmatch(str(contract.get(name, ''))):
            problems.append(name + '_REQUIRED')
    parsed = urlsplit(str(contract.get('targetUrl') or ''))
    try:
        port = parsed.port
    except ValueError:
        port = None
    if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not port
            or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        problems.append('ISOLATED_LOOPBACK_ORIGIN_REQUIRED')
    if contract.get('apiBase') != 'same-origin':
        problems.append('SAME_ORIGIN_PRODUCTION_BUILD_REQUIRED')
    components = contract.get('integratedComponents', {})
    if not all(components.get(name) is True for name in ('CallReview', 'WmsScene', 'TmsScene')):
        problems.append('FINAL_MODULE_INTEGRATION_REQUIRED')
    selectors = contract.get('capabilities', {}).get('selectors', {})
    for name in REQUIRED_SELECTORS:
        if not isinstance(selectors.get(name), str) or not selectors[name].strip():
            problems.append('REAL_UI_SELECTOR_REQUIRED:' + name)
    assets = contract.get('assets', [])
    if not isinstance(assets, list) or not assets:
        problems.append('FINAL_ASSET_INVENTORY_REQUIRED')
        return problems
    names = set()
    voices = set()
    videos = 0
    for asset in assets:
        if not isinstance(asset, dict):
            problems.append('ASSET_ENTRY_INVALID')
            continue
        name = asset.get('path')
        if not safe_name(name) or not str(name).startswith('demo/'):
            problems.append('ASSET_PATH_OR_DUPLICATE_INVALID')
        elif name in names:
            problems.append('ASSET_PATH_OR_DUPLICATE_INVALID')
        else:
            names.add(name)
        if (not HEX64.fullmatch(str(asset.get('sha256', '')))
                or type(asset.get('bytes')) is not int or asset['bytes'] <= 0
                or asset.get('synthetic') is not True):
            problems.append('ASSET_DIGEST_SIZE_OR_SYNTHETIC_INVALID')
        if asset.get('kind') == 'audio':
            voices.add(asset.get('caseId'))
        if asset.get('kind') == 'video':
            videos += 1
    if not {'CASE-0001', 'CASE-0002'} <= voices or not videos:
        problems.append('TWO_CASE_AUDIO_AND_REGISTERED_VIDEO_REQUIRED')
    return sorted(set(problems))


def inventory(root: Path) -> dict:
    """All tracked product bytes, including overlays, plus approved public media."""
    names = git(root, '-c', 'core.quotePath=false', 'ls-files', '--', *PRODUCT_PATHS).splitlines()
    result = {}
    for name in names:
        if not safe_name(name):
            raise ValueError('UNSAFE_TRACKED_NAME')
        path = root / name
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            raise ValueError('LINKED_PRODUCT_INPUT')
        if path.is_file():
            result[name] = sha(path.read_bytes())
    return result


def build_provenance_errors(record: dict, final_sha: str, hashes: dict, output_fingerprint: str) -> list[str]:
    errors = []
    if record.get('status') != 'complete' or record.get('buildExitCode') != 0:
        errors.append('NO_SUCCESSFUL_Q2_BUILD_RECORD')
    if record.get('headBefore') != final_sha or record.get('headAfter') != final_sha:
        errors.append('BUILD_NOT_FROM_FINAL_SHA')
    if record.get('productBefore') != hashes or record.get('productAfter') != hashes:
        errors.append('BUILD_PRODUCT_INPUT_MISMATCH')
    if record.get('outputFingerprint') != output_fingerprint or record.get('nextPublicApiBase') != '':
        errors.append('BUILD_OUTPUT_OR_ORIGIN_MISMATCH')
    return errors


def inspect_release(root: Path, contract: dict) -> tuple[dict, dict[str, bytes]]:
    problems = required_inputs(contract)
    if problems:
        raise ValueError('; '.join(problems))
    root = root.resolve(strict=True)
    if git(root, 'rev-parse', 'HEAD') != contract['finalSha']:
        raise ValueError('HEAD_NOT_FINAL_INTEGRATION_SHA')
    if git(root, 'diff', '--name-only', 'HEAD', '--', *PRODUCT_PATHS):
        raise ValueError('TRACKED_PRODUCT_CHANGES_PRESENT')
    extra = git(root, 'ls-files', '--others', '--exclude-standard', '--', *PRODUCT_PATHS)
    if extra:
        raise ValueError('UNTRACKED_PRODUCT_INPUT_PRESENT')
    if sha((root / 'data/fixtures/cases.json').read_bytes()) != contract['fixtureSha256']:
        raise ValueError('FIXTURE_DIGEST_MISMATCH')
    if sha((root / 'data/demo-media-manifest.json').read_bytes()) != contract['manifestSha256']:
        raise ValueError('MANIFEST_DIGEST_MISMATCH')
    helper = root / 'scripts/build_deployment_bundle.py'
    spec = importlib.util.spec_from_file_location('pc4_final_build_verifier', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = module._output_files(root)
    stamp = module._verified_stamp(root, output)
    canonical_media = module._media(root, root / 'data/demo-media-manifest.json')
    fixture_bytes = (root / 'data/fixtures/cases.json').read_bytes()
    if fixture_bytes != (root / 'apps/web/public/cases.json').read_bytes() or fixture_bytes != output['cases.json']:
        raise ValueError('FIXTURE_COPIES_DIFFER')
    if stamp['sourceAfter'] != contract['frontendSourceFingerprint']:
        raise ValueError('FRONTEND_SOURCE_FINGERPRINT_MISMATCH')
    if stamp['outputFingerprint'] != contract['frontendOutputFingerprint']:
        raise ValueError('PRODUCTION_OUTPUT_FINGERPRINT_MISMATCH')
    # All served audio/video must be declared; extra stale media cannot hide in out.
    declared = {a['path']: a for a in contract['assets']}
    if set(declared) != {'demo/' + n for n in canonical_media}:
        raise ValueError('CANONICAL_MANIFEST_ASSET_SET_MISMATCH')
    actual = {n for n in output if PurePosixPath(n).suffix.lower() in ('.wav', '.mp3', '.mp4', '.webm', '.ogg')}
    if actual != set(declared):
        raise ValueError('SERVED_MEDIA_INVENTORY_MISMATCH')
    for name, asset in declared.items():
        content = output[name]
        if len(content) != asset['bytes'] or sha(content) != asset['sha256'] or content != canonical_media[name.removeprefix('demo/')]:
            raise ValueError('SERVED_ASSET_DIGEST_MISMATCH:' + name)
        source = root / 'apps/web/public' / name
        if not source.is_file() or sha(source.read_bytes()) != asset['sha256']:
            raise ValueError('SOURCE_ASSET_DIGEST_MISMATCH:' + name)
    # Claims in the contract are prerequisites, not evidence of integration.
    # Page source must reference new components; their actual controls are checked in the browser.
    page = (root / 'apps/web/app/page.tsx').read_text(encoding='utf-8')
    for component in ('CallReview', 'WmsScene', 'TmsScene'):
        if component not in page:
            raise ValueError('MODULE_REFERENCE_MISSING:' + component)
    hashes = inventory(root)
    record = json.loads((root / '.local/pc4-q2-build.json').read_text(encoding='utf-8'))
    provenance_errors = build_provenance_errors(record, contract['finalSha'], hashes, stamp['outputFingerprint'])
    if provenance_errors:
        raise ValueError('; '.join(provenance_errors))
    return {'finalSha': contract['finalSha'], 'buildStamp': stamp, 'q2BuildRecord': record,
            'productHashes': hashes, 'assets': contract['assets'],
            'targetUrl': contract['targetUrl'], 'head': git(root, 'rev-parse', 'HEAD')}, output


def aggregate_guard(report: dict, browser: dict | None) -> list[str]:
    failures = []
    for key in ('sameSource', 'sameBuild', 'sameTester', 'originalStatePreserved', 'apiStopped'):
        if report.get(key) is not True:
            failures.append(key)
    if report.get('paidAnalyzerInvocations') != 0 or report.get('blockedExternalConnections'):
        failures.append('COST_OR_NETWORK_GUARD')
    if report.get('fatal') or report.get('browserExitCode') != 0:
        failures.append('SETUP_OR_BROWSER_FAILED')
    if not browser or browser.get('fatal') or browser.get('setupErrors'):
        failures.append('BROWSER_EVIDENCE_MISSING_OR_SETUP_FAILED')
    else:
        if browser.get('status') != 'PASS':
            failures.append('BROWSER_NOT_PASS')
        identity = report.get('identity', {})
        guard = browser.get('guard', {}) or {}
        if (not identity or any(not identity.get(k) or guard.get(k) != identity[k]
                               for k in ('runNonce', 'finalSha', 'buildFingerprint'))
                or guard.get('ready') is not True or guard.get('paidAnalyzerInvocations') != 0
                or guard.get('externalConnectionsBlocked') != 0):
            failures.append('BROWSER_IDENTITY_OR_GUARD_MISSING')
        flows = browser.get('flows', [])
        if len(flows) != 6 or any(x.get('status') != 'PASS' for x in flows):
            failures.append('SIX_COMPLETE_FLOWS_REQUIRED')
        if any(sum(x.get('caseId') == case for x in flows) != 3 for case in ('CASE-0001', 'CASE-0002')):
            failures.append('THREE_PER_CASE_REQUIRED')
        expected_runs = {(case, repeat) for case in ('CASE-0001', 'CASE-0002') for repeat in (1, 2, 3)}
        if {(x.get('caseId'), x.get('repetition')) for x in flows} != expected_runs:
            failures.append('SIX_UNIQUE_CASE_REPETITIONS_REQUIRED')
        stores = [x.get('store', {}).get('store') for x in flows]
        if len(set(stores)) != 6 or any(not x for x in stores):
            failures.append('SIX_FRESH_STORES_REQUIRED')
        if any(x.get('audio', {}).get('judgement', {}).get('accepted') is not True for x in flows):
            failures.append('ALL_SIX_NATURAL_AUDIO_PROOFS_REQUIRED')
        boundaries = browser.get('boundaries', [])
        if ({x.get('id') for x in boundaries} != BOUNDARY_IDS or len(boundaries) != len(BOUNDARY_IDS)
                or set(browser.get('plannedBoundaryIds', [])) != BOUNDARY_IDS
                or any(x.get('status') != 'PASS' for x in boundaries)):
            failures.append('BOUNDARY_NOT_PASS')
        if browser.get('blockedLive') or browser.get('blockedExternal'):
            failures.append('BROWSER_NETWORK_GUARD')
        if any(x.get('kind') == 'pageerror' for x in browser.get('consoleErrors', [])):
            failures.append('BROWSER_PAGEERROR')
    return failures
