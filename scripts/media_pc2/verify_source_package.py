"""Verify the exact pc1 synthetic cache ZIP without extracting or generating audio."""
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import wave
import zipfile

from measure_audio import ROOT

directory = ROOT/'.local/pc2-voice-sources-20260921'
expected = {
    'demo-voice-sources-20260921.zip': ('4cce238f49c513b9ef068a8a1e5a34c4938d968b16de2a39ac245a3eaac3ac12', 3474435),
    'demo-voice-sources-20260921.manifest.json': ('6a734e6437c1e21a9a2d82c62842d58b83856798e01bb1023f914a00406fe75e', 17735),
}
sha = lambda raw: hashlib.sha256(raw).hexdigest()
for name, (digest, size) in expected.items():
    raw = (directory/name).read_bytes()
    if len(raw) != size or sha(raw) != digest:
        raise ValueError(f'Input receipt failed: {name}')
manifest_name = 'demo-voice-sources-20260921.manifest.json'
manifest_raw = (directory/manifest_name).read_bytes()
manifest = json.loads(manifest_raw)
segments, reconstructed = [], []
with zipfile.ZipFile(directory/'demo-voice-sources-20260921.zip') as archive:
    names = [segment['path'] for case in manifest['cases'] for segment in case['segments']]
    if len(names) != 16 or set(archive.namelist()) != set(names+[manifest_name]) or len(archive.infolist()) != 17:
        raise ValueError('Unexpected archive inventory')
    if archive.read(manifest_name) != manifest_raw:
        raise ValueError('Inner/outer manifest bytes differ')
    for case in manifest['cases']:
        chunks = []
        for segment in case['segments']:
            raw = archive.read(segment['path'])
            if len(raw) != segment['bytes'] or sha(raw) != segment['sha256']:
                raise ValueError('Segment bytes/hash mismatch')
            fmt = segment['format']
            with wave.open(io.BytesIO(raw), 'rb') as reader:
                if (reader.getnchannels(), reader.getsampwidth(), reader.getframerate(), reader.getcomptype()) != (1, 2, 24000, 'NONE'):
                    raise ValueError('Unsupported segment PCM format')
                # Streaming placeholders are not durations. Reading one extra
                # frame verifies EOF at the actual frame count in the manifest.
                pcm = reader.readframes(fmt['frames']+1)
            if len(pcm) != fmt['frames']*2 or len(pcm)/48000 != fmt['durationSeconds']:
                raise ValueError('Actual PCM length differs from approved manifest')
            chunks += [pcm, b'\0'*(round(case['gapAfterEverySegmentSeconds']*24000)*2)]
            segments.append({'path':segment['path'], 'sha256':sha(raw), 'bytes':len(raw),
                             'actual_frames':len(pcm)//2, 'actual_seconds':len(pcm)/48000,
                             'matches_manifest':True})
        stream = io.BytesIO()
        with wave.open(stream, 'wb') as writer:
            writer.setnchannels(1); writer.setsampwidth(2); writer.setframerate(24000)
            writer.writeframes(b''.join(chunks))
        baseline = ROOT/'.local/demo-media-backups/20260921T093437Z-iwm8nlqd'/f"{case['caseId']}.wav"
        identical = stream.getvalue() == baseline.read_bytes()
        if not identical:
            raise ValueError('Reassembled original v1 bytes differ')
        reconstructed.append({'case':case['caseId'], 'sha256':sha(stream.getvalue()), 'v1_byte_identical':identical})
result = {'at':datetime.now(timezone.utc).isoformat(),
          'source_comment':'https://github.com/cjj0202-glitch/happycall-ralphthon/issues/8#issuecomment-5759439879',
          'release':'demo-voice-sources-20260921', 'outer_files_verified':2,
          'outer_files':{name:{'sha256':v[0],'bytes':v[1]} for name,v in expected.items()},
          'segments_verified':len(segments),'segments':segments,'v1_reconstruction':reconstructed,
          'extracted':False,'generated_api_calls':0,
          'limits':'Original synthesis cache/v1 source, not v2-normalized utterance audio, STT, listening or quality acceptance.'}
(ROOT/'reports/pc2/audio-m2/source-receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'outer_verified':2,'segments_verified':16,'v1_reconstructed_identically':reconstructed},ensure_ascii=False))
