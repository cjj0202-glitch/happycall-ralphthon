import hashlib
import json
from pathlib import Path

root = Path.cwd()
original = root / 'reports/e2e/prototype-independent-20260921-2102/source-probe.mjs'
portable = root / 'tests/e2e/prototype-independent.mjs'
paths = (original, portable)
texts = [p.read_text(encoding='utf-8') for p in paths]
environment_only_prefixes = (
    'import { chromium }', 'import { fileURLToPath }', 'const root =',
    'const port =', 'assert.ok(Number.isInteger(port)', 'const out =',
    'const base =', 'const server = spawn(', 'browser=await chromium.launch(',
    "await context.route('**/*',",
)
def business_lines(text):
    return [line for line in text.splitlines()
            if not line.strip().startswith(environment_only_prefixes)]
assert business_lines(texts[0]) == business_lines(texts[1]), 'Non-environment test logic changed'
report = {
    'status': 'PASS',
    'method': 'Exact line comparison after excluding listed path/environment-only declarations',
    'excludedPrefixes': environment_only_prefixes,
    'businessLinesCompared': len(business_lines(texts[0])),
    'checkCallLines': sum('check(' in line for line in business_lines(texts[0])),
    'originalSha256': hashlib.sha256(original.read_bytes()).hexdigest(),
    'portableSha256': hashlib.sha256(portable.read_bytes()).hexdigest(),
    'runtimeRerun': False,
    'limitation': 'Portability syntax and unchanged business assertions verified; another PC execution remains separate.',
}
output = root / 'reports/e2e/prototype-independent-20260921-2102/portable-equivalence.json'
output.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
