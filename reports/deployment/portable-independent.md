# Portable 배포 앱 독립 적대검증

검증 일시: 2026-09-21 18:05–18:13 KST. 검증자: 대기세션4, pc1 CJJ. 범위: `server/deployment_app.py`, `server/deployment_access.py`, `tests/test_deployment_app.py`, `reports/deployment/portable-app.md`.

## 판정

현재 검증 범위에서 재현된 제품 결함은 **0건**입니다. 합성 ASGI/Connexion 환경의 접근제어·정적 파일 경계·미디어 응답은 통과했습니다. 이는 외부 HTTPS 배포 또는 원격 영속성의 승인 판정이 아닙니다. 실물 링크 검사 3건과 호스트 인수 검증은 미완료 상태로 유지합니다.

제품·테스트·설정을 수정하지 않았습니다. 저장소에서는 이 보고서만 작성했습니다. 합성 자격증명, OS 임시 디렉터리의 합성 export, 인메모리 API를 사용했습니다. 실제 비밀설정·운영 상태·실제 API·live 모델·외부 배포·원격 CAS 검증을 수행하지 않았습니다.

## 독립 재실행 결과

실행 디렉터리는 `C:/00.프로젝트/happycall-ralphthon`입니다. 아래 pytest는 수정된 최신 격리 fixture에서 실행했습니다.

```powershell
.venv/Scripts/python.exe -B -m pytest tests/test_deployment_app.py -q -p no:cacheprovider
```

```text
119 passed, 3 skipped, 5 warnings in 7.20s
```

- 이전 `handlers.Budget` 패치는 공용 runtime-storage 연결 뒤 사라진 속성을 참조했습니다. 담당자가 `handlers.get_runtime_storage` 금지 mock으로 정합화한 후 재실행했습니다. 확인된 통합 fixture 변경이며 새로운 제품 결함으로 중복 등록하지 않습니다.
- 실제 Connexion 경로, 인증 양성/음성, revision·역할 거부 응답, 기동 실패, 4개 메모리 변이와 동일 소스 대조군이 포함되어 있습니다. 변이 사본은 저장소에 쓰지 않습니다.
- 3 skipped는 Windows 실물 symlink 생성 권한 부족입니다. 별도의 합성 is_symlink/is_junction 분기 검사는 실제 링크 검사의 대체 완료로 세지 않습니다.
- 5 warnings는 Connexion/Starlette/AnyIO/jsonschema 관련 deprecation입니다.

## 별도 라우팅·파일·미디어 실측

기존 테스트를 그대로 재사용하지 않고 별도 임시 export와 raw ASGI/HTTPX를 구성했습니다. raw ASGI는 클라이언트가 `..`를 먼저 정리해 버리는 문제를 피하고 앱에 전달되는 경로 자체를 검사합니다.

| 검증 | 양성·음성 대조 및 실측 |
|---|---|
| 파일 경계 | 내부 canary 파일을 실제 생성하고 traversal, 역슬래시, 이중 인코딩 잔존, ADS colon, 후행 점/공백, 제어문자 등 19건 모두 404. 내부/외부 canary 비노출 |
| 인증 이전 파일 정보 | 6개 경로 × GET/HEAD/POST/OPTIONS/TRACE = 30건 모두 401. Range 정보 없음, 하위 API 호출 0회 |
| 정상 export | HTML/JSON/JS/CSS/WOFF2/SVG/ICO/WAV/MP4 9종 모두 GET/HEAD 200, 명시 MIME, HEAD 빈 본문·동일 길이, 공통 응답 헤더 일치 |
| 미디어 | 부분·후미·열린 범위 206 및 정확한 바이트, multipart 206·실제 본문 길이 일치, 잘못된 문법/역전 범위 400, 범위 초과 416 |
| If-Range | 현재 ETag/Last-Modified는 206, stale ETag는 200 |
| /api 원래 경로 | /api, /api/, 쿼리를 포함한 하위 경로 3종이 원래 path/query로 하위 앱에 도달. Authorization 전달 없음 |
| 실제 Connexion | /api/cases 미인증 401, 합성 핸들러 양성 200, 없는 API 404, 잘못된 메서드 405. 핸들러 호출 1회, 인증 헤더 None, 실제 runtime-storage 호출 0회 |

실제 오디오/영상 재생 대신 합성 바이트로 HTTP 전달 계약을 검사했습니다. 이 결과를 브라우저 디코딩·재생 성공으로 표현하지 않습니다.

```text
VERSIONS 1.6.0 3.3.0
RAW_PATH_BOUNDARY 19 blocked=404
UNAUTH_METHOD_PATH 30 blocked=401 downstream_calls=0
STATIC_MIME_HEAD 9 PASS
RANGE_IF_RANGE partial/suffix/open/multipart/malformed/416/validators PASS
ORIGINAL_API_SCOPE 3 routes PASS; authorization stripped
REAL_CONNEXION 401/200/404/405 PASS; synthetic_handler_calls=1 auth=None runtime_calls=0
RESULT independent deployment routing/media checks PASS
```

첫 버전은 Starlette, 둘째는 Connexion입니다. 추가 stderr는 swagger-ui 미설치 안내 및 의도한 404/405 로그였습니다.

## 인증 계층 분담 적대검증

읽기 전용 하위 검증자 `deployment_auth_critic`가 같은 인증 소스 해시를 대상으로 별도 실행했습니다. 재현된 결함은 없었습니다.

| 확인 대상 | 실측 |
|---|---|
| 인증 헤더 단일 바이트 교체 | 16,896건, 기대와 다른 판정 0건 |
| 인증 헤더 바이트 삽입·삭제 | 17,218건 모두 거부 |
| 중복 Authorization 대소문자·값·순서 | 80건 모두 거부 |
| 누락·자료형·제어문자 등 잘못된 설정 | 27건 모두 동일한 비노출 오류 |
| 미인증 경로 × 메서드 | 154건 중 공개는 GET/HEAD /healthz 2건뿐, 하위 호출 0회 |
| path/raw_path 불일치 | 3건 모두 고정 health 응답만 반환, 하위 호출 0회 |
| 인증 성공 양성 대조 | 하위 앱 호출 1회, 전달 Authorization 0개, 원래 입력 scope 유지 |
| 공통 응답 헤더 | 하위 앱의 다른 값과 중복을 제거하고 지정한 3개 헤더를 각각 1개로 강제 |
| WebSocket | 인증 유무 2건 모두 1008 종료 |
| 유효 설정 경계 | 사용자 길이 4/64, 암호 길이 24/256 및 콜론 포함 6건 정상 인증 |
| 변이 탐지력 | 중복 헤더, 비정규 Base64 pad bits, 두 자격값 AND, 약한 기본설정, health prefix, Authorization 제거 가드의 메모리 변이 6/6 탐지 |

광범위 입력 검사 뒤 첫 `asyncio.run()` 시도는 자체 네트워크 금지 감사 훅이 Windows 내부 socketpair까지 막아 중단됐습니다. 해당 시도에서 ASGI 검증이 완료됐다고 세지 않았으며, 소켓 없는 직접 코루틴 실행으로 위 ASGI 검사를 따로 완료했습니다.

```text
{"single_byte_auth_substitutions": 16896, "incorrect_decisions": 0}
{"single_byte_auth_insertions_and_deletions": 17218, "accepted": 0}
{"duplicate_authorization_variants": 80, "accepted": 0}
{"invalid_configuration_variants": 27, "stable_errors": 27}
{"unauthenticated_path_method_combinations": 154, "public_health_combinations": 2, "downstream_calls": 0}
{"raw_path_disagreements": 3, "constant_public_response_only": 3}
{"authenticated_downstream_calls": 1, "downstream_authorization_headers": 0, "original_request_preserved": true, "overridden_security_header_names": 3, "credential_repr": "AccessCredentials()"}
{"websocket_authenticated_and_anonymous_denied": 2}
```

인증 핵심 가드 6종과 유효 설정의 실제 실행 명령은 문서 끝에 수록했습니다. 광범위 입력 수치는 분담 검증자의 별도 실행 로그이며 아래 핵심 재현 코드 한 번의 실행 건수로 혼동하지 않습니다.

## 소스 식별과 한계

| 파일 | SHA-256 |
|---|---|
| server/deployment_app.py | `0e576b81725f83434d459f201075de4ff03f635f800d59d49ef0c11b08db0382` |
| server/deployment_access.py | `299c1432484598c86b9ec19541f8a187404eb6907f2fe140775901910fee1935` |
| tests/test_deployment_app.py (fixture 정합화 후) | `d5fc9ce9544a4df497ab47546056ddb5d0437da657c9e869e5bdfd46b1f22a7e` |
| reports/deployment/portable-app.md | `0070c07c14573b454082fb560dbc6a446362ecd283befb9d126f275c65c3cb66` |

제품 두 파일의 해시는 검증 시작과 18:09 재확인에서 같았습니다. 테스트는 담당자 fixture 정합화로 시작 시 `ab24d5d0...`에서 위 해시로 변경됐으며, 통과 결과는 변경 후 파일 기준입니다. 18:13 최종 확인에서 표의 네 파일 해시가 모두 같았고, 보고서의 UTF-8·코드펜스·두 재현 코드의 Python 구문도 확인했습니다.

남은 인수 확인은 최종 호스트의 실물 링크 3건, TLS/프록시 정규화·인증 헤더 로그 정책, 브라우저 Basic 인증·미디어 재생입니다. 실제 배포 URL, 원격 저장소/CAS, live 분석은 이 보고서의 통과 항목에 넣지 않습니다. 정적 export를 읽기 전용으로 제공하고 요청 처리 중 교체하지 않는다는 문서의 전제 아래 검증했습니다. 인증된 사용자의 업무 역할 인증은 이 공유 Basic 인증의 범위 밖이며 기존 합성 역할 검사와 구분합니다.

## 재현 코드: 독립 라우팅 검사

아래 Python 코드는 위 디렉터리에서 PowerShell here-string으로 `.venv/Scripts/python.exe -B -X utf8 -`에 전달해 실행했습니다. 실제 설정을 읽는 대신 명시적인 합성 환경 dict를 전달합니다.

```python
import asyncio, base64, json, tempfile, hashlib, importlib.metadata
from pathlib import Path
from unittest.mock import patch, Mock
import httpx
from starlette.responses import JSONResponse
from server.deployment_app import create_deployment_app, REQUIRED_FILES

USER = "independent-47"
PASSWORD = "V9!gT2@xK5#nW8$mC1%qR4&zY7"
TOKEN = "Basic " + base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()
MEDIA = b"0123456789abcdefghijklmnopqrstuvwxyz"
events = []
async def echo(scope, receive, send):
    events.append(scope)
    await JSONResponse({"path": scope["path"], "root_path": scope.get("root_path", ""),
                        "query": scope["query_string"].decode(),
                        "auth": any(k.lower() == b"authorization" for k,v in scope["headers"])})(scope,receive,send)
async def raw(app, path, *, method="GET", headers=(), raw_path=None):
    sent = []
    async def receive(): return {"type":"http.request","body":b"","more_body":False}
    async def send(message): sent.append(message)
    scope = {"type":"http","asgi":{"version":"3.0","spec_version":"2.3"},
             "http_version":"1.1","method":method,"scheme":"https","path":path,
             "raw_path":raw_path or path.encode("utf-8"),"root_path":"","query_string":b"",
             "headers":list(headers),"client":("127.0.0.1",12345),"server":("synthetic.invalid",443)}
    await app(scope,receive,send)
    start = next(m for m in sent if m["type"]=="http.response.start")
    return start["status"], dict(start["headers"]), b"".join(m.get("body",b"") for m in sent)
async def main():
  with tempfile.TemporaryDirectory(prefix="portable-independent-") as td:
    root=Path(td)/"out"
    files={name:MEDIA for name in REQUIRED_FILES}
    files.update({"index.html":b"<title>synthetic</title>","cases.json":b'{"cases":[]}',
      "_next/static/chunks/app.js":b"void 0;", "_next/static/css/app.css":b"body{}",
      "_next/static/media/font.woff2":b"synthetic-font",
      "icon.svg":b"<svg/>", "favicon.ico":b"synthetic-icon",
      ".env":b"INTERNAL-SECRET-CANARY", "server.py":b"INTERNAL-SECRET-CANARY",
      "_next/static/chunks/app.js.map":b"INTERNAL-SECRET-CANARY",
      "demo/private.json":b"INTERNAL-SECRET-CANARY"})
    for name,content in files.items():
      p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content)
    (Path(td)/"outside.wav").write_bytes(b"OUTSIDE-SECRET-CANARY")
    env={"ONEFLOW_STATIC_DIR":str(root),"ONEFLOW_ACCESS_USER":USER,"ONEFLOW_ACCESS_PASSWORD":PASSWORD}
    app=create_deployment_app(environ=env,api_app=echo)
    h={"Authorization":TOKEN}
    badpaths=["/.env","/server.py","/_next/static/chunks/app.js.map","/demo/private.json",
      "/demo/../../outside.wav","/demo/../outside.wav","/demo/./CASE-0001.wav",
      "//demo/CASE-0001.wav","/demo//CASE-0001.wav","/demo/CASE-0001.wav/",
      "/demo/CASE-0001.wav.","/demo/CASE-0001.wav ","/demo/CASE-0001.wav:secret",
      "/demo\\..\\outside.wav","/demo/%2e%2e/outside.wav","/%252e%252e/outside.wav",
      "/demo/CASE-0001.wav\x00","/demo/CASE-0001.wav\n","/demo/\u2215outside.wav"]
    for p in badpaths:
      status,headers,body=await raw(app,p,headers=[(b"authorization",TOKEN.encode())])
      assert status==404,(repr(p),status)
      assert b"SECRET-CANARY" not in body
    print("RAW_PATH_BOUNDARY",len(badpaths),"blocked=404")
    for p in ["/","/.env","/api/health","/demo/CASE-0001.wav","/healthz/","/HEALTHZ"]:
      for method in ["GET","HEAD","POST","OPTIONS","TRACE"]:
        s,hh,bb=await raw(app,p,method=method,headers=[(b"range",b"bytes=0-3")])
        assert s==401 and b"content-range" not in hh,(p,method,s)
    assert not events
    print("UNAUTH_METHOD_PATH",30,"blocked=401 downstream_calls=0")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="https://synthetic.invalid") as c:
      for p,mime in [("/", "text/html"),("/cases.json","application/json"),
          ("/_next/static/chunks/app.js","text/javascript"),("/_next/static/css/app.css","text/css"),
          ("/_next/static/media/font.woff2","font/woff2"),("/icon.svg","image/svg+xml"),
          ("/favicon.ico","image/x-icon"),("/demo/CASE-0001.wav","audio/wav"),
          ("/demo/sorter-demo.mp4","video/mp4")]:
        g=await c.get(p,headers=h); head=await c.head(p,headers=h)
        assert g.status_code==head.status_code==200,(p,g.status_code,head.status_code)
        assert g.headers["content-type"].split(";")[0]==mime
        assert head.content==b"" and head.headers["content-length"]==g.headers["content-length"]
        for name,value in [("cache-control","private, no-store"),("x-content-type-options","nosniff"),("referrer-policy","no-referrer")]:
          assert g.headers[name]==head.headers[name]==value
      print("STATIC_MIME_HEAD",9,"PASS")
      p="/demo/CASE-0001.wav"
      full=await c.get(p,headers=h)
      for rv,expected in [("bytes=0-3",MEDIA[:4]),("bytes=-4",MEDIA[-4:]),("bytes=32-",MEDIA[32:])]:
        g=await c.get(p,headers={**h,"Range":rv});head=await c.head(p,headers={**h,"Range":rv})
        assert g.status_code==head.status_code==206 and g.content==expected
        assert head.content==b"" and int(head.headers["content-length"])==len(expected)
      g=await c.get(p,headers={**h,"Range":"bytes=0-2,10-12"})
      assert g.status_code==206 and b"012" in g.content and b"abc" in g.content
      assert int(g.headers["content-length"])==len(g.content)
      for rv,code in [("bytes=999-1000",416),("bytes=4-2",400),("nonsense",400),("bytes=0-",206)]:
        g=await c.get(p,headers={**h,"Range":rv});assert g.status_code==code,(rv,g.status_code)
      for ir,expected in [(full.headers["etag"],206),('"stale"',200),(full.headers["last-modified"],206)]:
        g=await c.get(p,headers={**h,"Range":"bytes=0-3","If-Range":ir})
        assert g.status_code==expected
      print("RANGE_IF_RANGE","partial/suffix/open/multipart/malformed/416/validators PASS")
      for p in ["/api","/api/","/api/cases/INT-SYN?sort=a%2Fb&limit=3"]:
        g=await c.get(p,headers=h);v=g.json()
        assert v["path"]==p.split("?")[0] and v["auth"] is False
        assert v["query"]==(p.split("?",1)[1] if "?" in p else "")
      print("ORIGINAL_API_SCOPE","3 routes PASS; authorization stripped")
    # Positive control and negative controls use the real Connexion routing layer.
    from server import handlers
    calls=[]
    async def cases():
      from connexion import request
      calls.append(request.headers.get("Authorization"))
      return {"cases":[{"id":"INT-SYN-47"}]},200
    forbidden=Mock(side_effect=AssertionError("Real runtime state forbidden"))
    with patch.object(handlers,"list_cases",cases),patch.object(handlers,"service",forbidden),patch.object(handlers,"get_runtime_storage",forbidden):
      actual=create_deployment_app(environ=env)
      async with httpx.AsyncClient(transport=httpx.ASGITransport(app=actual),base_url="https://synthetic.invalid") as c:
        for method,p,hh,status in [("GET","/api/cases",{},401),("GET","/api/cases",h,200),
            ("GET","/api/not-a-route",h,404),("DELETE","/api/cases",h,405)]:
          response=await c.request(method,p,headers=hh)
          assert response.status_code==status,(method,p,response.status_code)
          if status==200:assert response.json()=={"cases":[{"id":"INT-SYN-47"}]}
      assert calls==[None] and forbidden.call_count==0
    print("REAL_CONNEXION","401/200/404/405 PASS; synthetic_handler_calls=1 auth=None runtime_calls=0")
    print("RESULT independent deployment routing/media checks PASS")
print("VERSIONS",importlib.metadata.version("starlette"),importlib.metadata.version("connexion"))
asyncio.run(main())

```

## 재현 코드: 인증 핵심 가드 및 변이 대조

분담 검증자가 실제 실행한 명령이며 종료 코드는 0이었습니다. 원본 6종 대조군이 모두 기대대로 동작하고, 가드를 제거한 메모리 변이체 6종은 모두 탐지했습니다.

```powershell
@'
import base64, hashlib, json, sys, types
from pathlib import Path

def audit(event, args):
    if event.startswith('socket.'):
        raise RuntimeError('network forbidden')
    if event == 'open' and isinstance(args[0], (str, bytes)):
        name = str(args[0]).lower().replace('\\', '/')
        if '/.local/' in name or name.endswith('/.local') or '/.env' in name or 'currentstate' in name:
            raise RuntimeError('private runtime access forbidden')
sys.addaudithook(audit)
from server import deployment_access as m
source = Path(m.__file__).read_text(encoding='utf-8')
env = {'ONEFLOW_ACCESS_USER': 'audit-synth-73', 'ONEFLOW_ACCESS_PASSWORD': 'Q3!rT5@uY7#iO9$pA1%sD2&fG4:h'}
raw = (env['ONEFLOW_ACCESS_USER'] + ':' + env['ONEFLOW_ACCESS_PASSWORD']).encode()
token = base64.b64encode(raw)
auth = b'Basic ' + token
alphabet = b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
last = len(token.rstrip(b'=')) - 1
alternate = token[:last] + bytes([alphabet[alphabet.index(token[last]) + 1]]) + token[last + 1:]
assert base64.b64decode(alternate, validate=True) == raw and alternate != token

def direct(coroutine):
    try: coroutine.send(None)
    except StopIteration as result: return result.value
    else:
        coroutine.close()
        raise AssertionError('unexpected suspended await')

def probe(module, kind):
    c = module.AccessCredentials.from_environment(env)
    if kind == 'duplicate':
        assert not c.accepts([(b'authorization', auth), (b'Authorization', b'bad')])
    elif kind == 'pad_bits':
        assert not c.accepts([(b'authorization', b'Basic ' + alternate)])
    elif kind == 'two_components':
        incorrect = b'Basic ' + base64.b64encode(b'wrong:' + env['ONEFLOW_ACCESS_PASSWORD'].encode())
        assert not c.accepts([(b'authorization', incorrect)])
    elif kind == 'weak_config':
        try: module.AccessCredentials.from_environment({**env, 'ONEFLOW_ACCESS_USER': 'demo'})
        except ValueError: pass
        else: raise AssertionError('weak config accepted')
    else:
        calls, messages = [], []
        async def app(scope, receive, send):
            calls.append(scope)
            await send({'type': 'http.response.start', 'status': 209, 'headers': []})
            await send({'type': 'http.response.body', 'body': b'synthetic'})
        async def send(message): messages.append(message)
        path = '/healthz/private' if kind == 'health_prefix' else '/api/cases'
        headers = [] if kind == 'health_prefix' else [(b'Authorization', auth)]
        direct(module.DeploymentAccess(app, c)({'type': 'http', 'method': 'GET', 'path': path, 'headers': headers}, None, send))
        if kind == 'health_prefix':
            assert messages[0]['status'] == 401 and not calls
        else:
            assert calls and all(k.lower() != b'authorization' for k, v in calls[0]['headers'])

mutations = [
    ('duplicate', 'if len(authorization) != 1:', 'if len(authorization) < 1:'),
    ('pad_bits', 'if base64.b64encode(decoded) != token:', 'if False:'),
    ('two_components', 'return bool(username_matches & password_matches)', 'return bool(username_matches | password_matches)'),
    ('weak_config', 'if not valid:', 'if False:'),
    ('health_prefix', 'if scope["path"] == "/healthz" and', 'if scope["path"].startswith("/healthz") and'),
    ('credential_forward', 'if key.lower() != b"authorization"]}', 'if True]}'),
]
results = []
for kind, before, after in mutations:
    assert source.count(before) == 1, kind
    probe(m, kind)
    mutant = types.ModuleType(m.__name__)
    exec(compile(source.replace(before, after), '<memory-only-access-mutant>', 'exec'), mutant.__dict__)
    try: probe(mutant, kind)
    except AssertionError: results.append({'guard': kind, 'original': 'expected behavior', 'mutant': 'detected'})
    else: raise AssertionError(('surviving mutant', kind))
print(json.dumps({'guard_mutations': results, 'detected': len(results), 'total': len(mutations)}))
valid = 0
for user in ['audit', 'a' * 64]:
    for password in ['aB3!cD5@eF7#gH9$jK1%mN2%', 'aB3!cD5@eF7#gH9$jK1%mN2%' + 'Z' * 232, 'aB3!cD5@eF7#gH9$jK1%mN2%:']:
        c = m.AccessCredentials.from_environment({'ONEFLOW_ACCESS_USER': user, 'ONEFLOW_ACCESS_PASSWORD': password})
        assert c.accepts([(b'authorization', b'Basic ' + base64.b64encode((user + ':' + password).encode()))])
        valid += 1
print(json.dumps({'valid_boundary_configurations_and_authentication': valid, 'lengths': [4, 64, 24, 256], 'password_colon_supported': True}))
print(json.dumps({'source_unchanged': Path(m.__file__).read_text(encoding='utf-8') == source, 'source_sha256': hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()}))
'@ | ./.venv/Scripts/python.exe -B -
```

```text
{"guard_mutations": [{"guard": "duplicate", "original": "expected behavior", "mutant": "detected"}, {"guard": "pad_bits", "original": "expected behavior", "mutant": "detected"}, {"guard": "two_components", "original": "expected behavior", "mutant": "detected"}, {"guard": "weak_config", "original": "expected behavior", "mutant": "detected"}, {"guard": "health_prefix", "original": "expected behavior", "mutant": "detected"}, {"guard": "credential_forward", "original": "expected behavior", "mutant": "detected"}], "detected": 6, "total": 6}
{"valid_boundary_configurations_and_authentication": 6, "lengths": [4, 64, 24, 256], "password_colon_supported": true}
{"source_unchanged": true, "source_sha256": "299c1432484598c86b9ec19541f8a187404eb6907f2fe140775901910fee1935"}
```
