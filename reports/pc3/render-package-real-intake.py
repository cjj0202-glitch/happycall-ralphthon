from pathlib import Path, PurePosixPath
import hashlib, json, re, shutil, stat, subprocess, sys, zipfile
from datetime import datetime, timezone

ROOT = Path('.local/pc3-real-short-intake').resolve()
DOWNLOAD = ROOT / 'download'
RAW = ROOT / 'raw'
STRICT = ROOT / 'strict-package'
PINNED = {
 'wms-short-33fa0e4-review.zip': (82333801, '10fa9981105eaecfe07a5c715d19c3e7bd932f8aa4b8bb375f93447f73f80891'),
 'intake-expected.json': (2067, 'c7066902302d770290bdb28a79cb4ebac2428c3963428ecb66c2236ddbd8e81f'),
 'case-0002-ww3-short-review.mp4': (544733, '21ac21351803125334deba303fd249909774aba98058bc787e38121058f70ccf'),
}
SOURCE = '33fa0e4edeb88c0d4ad5e9cc0194ffc7e96cebcd'
FIXTURE_SHA = '79c3b01aed139352b5cc0a695f2829e76f78eabb61d7cfd6b8055db32f61a73b'
TRACKS_SHA = '9fb424be0fd212bbf3faa057097bec56c63a89e4b8ae08c524e5fd76b80fd44b'
LAYOUT_SHA = 'c6aece6692c6b78beb85d4f1167868f2bd095b3ab8366e837466715b82bd6cb6'

def digest(data):
 return {'bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest()}
def measure(path):
 return digest(path.read_bytes())
def strict_json(data):
 def pairs(items):
  result={}
  for key,value in items:
   if key in result: raise ValueError('Duplicate JSON key: '+key)
   result[key]=value
  return result
 return json.loads(data.decode('utf-8-sig'), object_pairs_hook=pairs, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
def save(path, value):
 with path.open('x',encoding='utf-8',newline='\n') as f:
  json.dump(value,f,indent=2,ensure_ascii=False)
  f.write('\n')
def safe_name(name):
 assert isinstance(name,str) and name and '\\' not in name and ':' not in name and not name.startswith('/')
 parts=name.split('/')
 for part in parts:
  assert re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',part) and not part.endswith(('.', ' '))
  assert part.split('.')[0].upper() not in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}
 assert str(PurePosixPath(name))==name
 return name

def clean_ancestors(path):
 for ancestor in [path,*path.parents]:
  if ancestor.exists():
   info=ancestor.lstat()
   assert not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400

clean_ancestors(ROOT)
REUSE_RAW = '--reuse-verified-raw' in sys.argv
assert not STRICT.exists()
assert (RAW.is_dir() if REUSE_RAW else not RAW.exists())
assert {p.name for p in DOWNLOAD.iterdir()}==set(PINNED)
assets=[]
for name,(size,sha) in PINNED.items():
 p=DOWNLOAD/name
 before=p.stat()
 assert before.st_nlink==1
 got=measure(p)
 assert got=={'bytes':size,'sha256':sha}
 assets.append({'name':name,**got,'mtimeNs':before.st_mtime_ns})
external=strict_json((DOWNLOAD/'intake-expected.json').read_bytes())
assert external['sourceCommit']==SOURCE and external['mode']=='short'
assert external['inputFixtureSha256']==FIXTURE_SHA and external['inputLayoutSha256']==LAYOUT_SHA
assert external['tracksSha256']==TRACKS_SHA and external['frameIds']==list(range(73,145))
with zipfile.ZipFile(DOWNLOAD/'wms-short-33fa0e4-review.zip') as z:
 infos=z.infolist()
 assert 0<len(infos)<1000 and sum(i.file_size for i in infos)<500_000_000
 names=[]
 for info in infos:
  safe_name(info.filename)
  assert not info.is_dir() and not info.flag_bits&1
  assert info.file_size<100_000_000
  mode=info.external_attr>>16
  assert stat.S_IFMT(mode) in (0,stat.S_IFREG)
  names.append(info.filename)
 assert len(names)==len(set(n.casefold() for n in names))
 manifest_bytes=z.read('package-files.json')
 manifest=strict_json(manifest_bytes)
 assert set(manifest)=={'files'}
 table={}
 for row in manifest['files']:
  assert set(row)=={'path','bytes','sha256'}
  name=safe_name(row['path'])
  assert name not in table and type(row['bytes']) is int and row['bytes']>=0
  assert re.fullmatch('[0-9a-f]{64}',row['sha256'])
  table[name]=row
 assert set(names)==set(table)|{'package-files.json'}
 # Validate every archive byte/CRC and the entire manifest before writing an extracted file.
 inventory=[]
 for info in infos:
  got=digest(z.read(info))
  assert got['bytes']==info.file_size
  if info.filename in table:
   assert got=={k:table[info.filename][k] for k in ('bytes','sha256')}
  inventory.append({'path':info.filename,**got})
 if not REUSE_RAW:
  RAW.mkdir()
  for info in infos:
   dest=RAW.joinpath(*info.filename.split('/'))
   assert dest.resolve().is_relative_to(RAW)
   dest.parent.mkdir(parents=True,exist_ok=True)
   clean_ancestors(dest.parent)
   with dest.open('xb') as f:
    f.write(z.read(info))
 assert {p.relative_to(RAW).as_posix() for p in RAW.rglob('*') if p.is_file()}==set(names)
 for item in inventory:
  raw_file=RAW/item['path']
  clean_ancestors(raw_file)
  assert raw_file.stat().st_nlink==1
  assert measure(raw_file)=={k:item[k] for k in ('bytes','sha256')}
fixture=measure(RAW/'input/cases.json')
layout=measure(RAW/'input/scene-layout-v1.json')
assert fixture['sha256']==FIXTURE_SHA and layout['sha256']==LAYOUT_SHA
assert measure(RAW/'short/tracks.json')['sha256']==TRACKS_SHA
assert (RAW/'intake-expected.json').read_bytes()==(DOWNLOAD/'intake-expected.json').read_bytes()
assert (RAW/'review-video/case-0002-ww3-short-review.mp4').read_bytes()==(DOWNLOAD/'case-0002-ww3-short-review.mp4').read_bytes()
source_intake=strict_json((RAW/'source-intake.json').read_bytes())
assert source_intake['commit']==SOURCE
assert source_intake['inputs']['cases.json']==fixture
assert source_intake['inputs']['scene-layout-v1.json']==layout
expected=strict_json(subprocess.check_output(['git','show','9be72090021c550c6e27746469f926baf57fea2e:reports/pc3/render-package-expectations.json']))
assert expected['sourceCommit']==SOURCE and expected['fixture'] is None and expected['mode']=='representatives'
source_checks=[]
for desc in [expected['generator'],*expected['sourceDependencies']]:
 rel='scripts/media_pc3/'+desc['name']
 git_digest=digest(subprocess.check_output(['git','show',SOURCE+':'+rel]))
 assert git_digest=={k:desc[k] for k in ('bytes','sha256')}==source_intake['sources'][rel]
 source_checks.append({'path':rel,**git_digest})
expected['mode']='short'
expected['fixture']={'name':'cases.json',**fixture}
save(ROOT/'expected-short.json',expected)
strict_names={'render-report.json','tracks.json','case-0002-ww3.blend'}|{f'frame-{i:04}.png' for i in range(73,145)}
actual_short={p.name for p in (RAW/'short').iterdir()}
assert actual_short==strict_names|{'independent-scene-readback.json'}
STRICT.mkdir()
copy_checks=[]
for name in sorted(strict_names):
 src=RAW/'short'/name
 before=measure(src)
 with (STRICT/name).open('xb') as target:
  target.write(src.read_bytes())
 assert before==measure(src)==measure(STRICT/name)
 copy_checks.append({'path':name,**before})
for asset in assets:
 p=DOWNLOAD/asset['name']
 assert measure(p)=={k:asset[k] for k in ('bytes','sha256')}
 assert p.stat().st_mtime_ns==asset['mtimeNs']
save(ROOT/'intake-before.json',{
 'at':datetime.now(timezone.utc).isoformat(),'sourceCommit':SOURCE,'checkerCommit':'9be72090021c550c6e27746469f926baf57fea2e',
 'assets':assets,'zipEntries':len(inventory),'manifestRows':len(table),'manifestSelfExcluded':True,
 'allPathsSafe':True,'allZipCrcAndManifestBytesMatched':True,'allExtractedBytesMatched':True,
 'files':inventory,'sourceChecks':source_checks,'fixture':fixture,'layout':layout,'tracksSha256':TRACKS_SHA,
 'strictCopy':copy_checks,'strictCopyCount':len(copy_checks),'preservedAdditionalShortFile':'short/independent-scene-readback.json',
 'additionalRawFilesOutsideStrict':len(inventory)-len(copy_checks),'inputsUnmodified':True,
 'expectationsDerivedFromReceivedReport':False,'actualRenderPackageReceived':True,'finalAccepted':False})
print(json.dumps({'assets':len(assets),'archiveFiles':len(inventory),'manifestRows':len(table),'strictCopied':len(copy_checks),'fixture':fixture,'raw':str(RAW),'expected':str(ROOT/'expected-short.json')}))
