"""Prepare two explicitly synthetic Korean calls. Paid calls require --generate.

The script is the test oracle only. The later STT request receives the WAV alone.
Cost accounting uses a conservative $1/request reservation, not a billing quote.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SPEECH_INSTRUCTIONS = '한국어로 자연스럽게 말하세요. 실제 전화 상담처럼 차분하고 또렷하게, 숫자와 단위를 정확히 읽으세요. 제공된 문장만 말하세요.'


def build_speech_parameters(text: str, voice: str, *, model: str = 'gpt-4o-mini-tts',
                            speed: float = 1.0, instructions: str = SPEECH_INSTRUCTIONS,
                            response_format: str = 'wav') -> dict[str, str | float]:
    """Return the single source of truth for the request and its cache identity."""
    return {'model': model, 'voice': voice, 'input': text,
            'response_format': response_format, 'speed': speed,
            'instructions': instructions}


def speech_cache_fingerprint(parameters: dict[str, str | float]) -> str:
    """Include every request parameter, independently of dictionary key order."""
    canonical = json.dumps(parameters, sort_keys=True, ensure_ascii=False,
                           separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate', action='store_true')
    args = parser.parse_args()
    cases = json.loads((ROOT/'data/fixtures/cases.json').read_text(encoding='utf-8'))['cases']
    output = ROOT/'apps/web/public/demo'
    cache = ROOT/'.local/tts-segments'
    output.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    planned = sum(len(c['transcript']) for c in cases)
    if planned > 16 or any(len(t['text']) > 350 for c in cases for t in c['transcript']):
        raise SystemExit('Bounded demo input exceeded: 16 turns / 350 chars each.')
    print(json.dumps({'callsAtMost':planned,'reservationUsdAtMost':planned,
                      'accounting':'reservation only, not provider billing','generate':args.generate}))
    if not args.generate:
        return
    # Importing cache helpers must not read local credentials or initialize clients.
    from server.live import demo_client
    from server.budget import Budget

    client = demo_client()
    budget = Budget()
    for case in cases:
        chunks, metadata, cursor, params = [], [], 0.0, None
        for index, turn in enumerate(case['transcript']):
            voice = 'marin' if turn['speaker'] == '상담원' else 'cedar'
            request_parameters = build_speech_parameters(turn['text'], voice)
            fingerprint = speech_cache_fingerprint(request_parameters)
            seg = cache/f'{case["id"]}-{index}-{fingerprint}.wav'
            if not seg.exists():
                rid = budget.reserve(100, 'synthetic-demo-tts')
                try:
                    response = client.audio.speech.create(**request_parameters)
                    content = response.read()
                    with wave.open(io.BytesIO(content),'rb') as check:
                        if check.getnframes() == 0:
                            raise ValueError('Empty waveform')
                    seg.write_bytes(content)
                    budget.finish(rid,True)
                except Exception as exc:
                    budget.finish(rid,False)
                    print(json.dumps({'caseId':case['id'],'turn':index,'errorType':type(exc).__name__,
                                      'status':getattr(exc,'status_code',None)},ensure_ascii=False))
                    raise SystemExit(1) from None
            with wave.open(str(seg),'rb') as wav:
                shape=(wav.getnchannels(),wav.getsampwidth(),wav.getframerate())
                if params and shape!=params:
                    raise SystemExit('Mismatched WAV parameters')
                params=shape
                content=wav.readframes(wav.getnframes())
                # Streamed WAV headers may advertise 0xffffffff frames; use decoded bytes.
                seconds=len(content)/(shape[0]*shape[1]*shape[2])
            chunks.append(content)
            metadata.append({'speaker':turn['speaker'],'start':round(cursor,3),
                             'end':round(cursor+seconds,3),'voice':voice})
            gap=int(params[2]*.35)*params[0]*params[1]
            chunks.append(bytes(gap));cursor+=seconds+.35
            print(f'{case["id"]}: segment {index+1}/{len(case["transcript"])} ready',flush=True)
        path=output/f'{case["id"]}.wav'
        with wave.open(str(path),'wb') as wav:
            wav.setnchannels(params[0]);wav.setsampwidth(params[1]);wav.setframerate(params[2])
            wav.writeframes(b''.join(chunks))
        (cache/f'{case["id"]}.metadata.json').write_text(json.dumps({'synthetic':True,'segments':metadata,'duration':cursor},ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'caseId':case['id'],'durationSeconds':round(cursor,2),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()},ensure_ascii=False),flush=True)
    print(json.dumps(budget.status()))

if __name__=='__main__':
    main()
