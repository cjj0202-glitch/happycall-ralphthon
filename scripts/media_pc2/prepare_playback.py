"""Make an isolated bfc8543 product snapshot and verified candidate timeline."""
from pathlib import Path
import copy
import hashlib
import json
import subprocess
import wave

from measure_audio import ROOT, load_pcm, digest

BASE = 'bfc8543aa65316682948f2e3d5b77a3ee56b21ff'
OUT = ROOT/'.local/pc2-m2-playback'
REPORT = ROOT/'reports/pc2/audio-m2'


def map_interval(start: int, end: int, insertion: int, added: int) -> tuple[int, int]:
    if not 0 <= start < end or added <= 0 or insertion < 0:
        raise ValueError('Invalid frame interval')
    # Half-open interval: an interval ending AT the insertion is unchanged.
    return start+(added if start >= insertion else 0), end+(added if end > insertion else 0)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tracked = ['apps/web/components/CallReview.tsx', 'apps/web/components/CallReview.module.css',
               'apps/web/app/tokens.css', 'apps/web/app/globals.css', 'apps/web/lib/types.ts',
               'data/fixtures/cases.json']
    sources = {}
    for name in tracked:
        raw = subprocess.check_output(['git', 'show', f'{BASE}:{name}'], cwd=ROOT)
        path = OUT/'product'/name
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_bytes() != raw:
            raise ValueError('Existing product snapshot differs; preserve it')
        path.write_bytes(raw)
        sources[name] = {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    fixture = json.loads((OUT/'product/data/fixtures/cases.json').read_text(encoding='utf-8'))
    original_case = next(c for c in fixture['cases'] if c['id']=='CASE-0002')
    prior = json.loads((REPORT/'candidate.json').read_text(encoding='utf-8'))
    source_meta = ROOT/'.local/pc2-voice-sources-20260921/demo-voice-sources-20260921.manifest.json'
    if digest(source_meta) != '6a734e6437c1e21a9a2d82c62842d58b83856798e01bb1023f914a00406fe75e':
        raise ValueError('Unapproved generation metadata')
    original_turns = next(c['segments'] for c in json.loads(source_meta.read_text(encoding='utf-8'))['cases'] if c['caseId']=='CASE-0002')
    assets, samples = {}, {}
    for name, prior_name in [('A','full_A'),('B','full_B')]:
        data = prior['measurements'][prior_name]
        p = ROOT/data['path']
        if digest(p)!=data['sha256'] or p.stat().st_size!=data['bytes']:
            raise ValueError('Candidate or original asset mismatch')
        shape, pcm = load_pcm(p)
        assets[name] = {'localPath':data['path'], 'url':f'/audio/{name}.wav', 'sha256':digest(p),
                        'bytes':p.stat().st_size,'duration':shape['duration_seconds'],'frames':shape['frames'],
                        'sampleRate':shape['sample_rate_hz'], 'channels':shape['channels']}
        samples[name] = pcm
    cases = {'A':copy.deepcopy(original_case),'B':copy.deepcopy(original_case)}
    rows = []
    insertion, added, rate = 417000, 4800, 24000
    for index, (turn, meta) in enumerate(zip(original_case['transcript'],original_turns)):
        if turn['text']!=meta['text'] or turn['speaker']!=meta['speaker']:
            raise ValueError('Source script and speaker do not match')
        a0,a1 = round(meta['startSeconds']*rate),round(meta['endSeconds']*rate)
        if (turn['start'],turn['end'])!=(a0/rate,a1/rate):
            raise ValueError('Product generation timing differs from received metadata')
        b0,b1 = map_interval(a0,a1,insertion,added)
        a_pcm,b_pcm = samples['A'][a0:a1],samples['B'][b0:b1]
        if a_pcm!=b_pcm:
            raise ValueError('Actual utterance samples changed')
        cases['B']['transcript'][index].update(start=b0/rate,end=b1/rate)
        rows.append({'index':index,'speaker':turn['speaker'],'text':turn['text'],
                     'A':{'start':a0/rate,'end':a1/rate,'startFrame':a0,'endFrame':a1},
                     'B':{'start':b0/rate,'end':b1/rate,'startFrame':b0,'endFrame':b1},
                     'pcm_frames':a1-a0, 'pcm_sha256':hashlib.sha256(a_pcm.tobytes()).hexdigest(),
                     'actual_pcm_identical':True})
    if len(rows)!=8 or samples['B'][:insertion]+samples['B'][insertion+added:]!=samples['A']:
        raise ValueError('Whole source sample/turn preservation failed')
    for name in cases:
        cases[name]['audioUrl']=assets[name]['url']
        cases[name]['analysisMode']='replay'
        cases[name]['transcriptTiming']['audioSha256']=assets[name]['sha256']
    cases['B']['transcriptTiming'].update(source='synthetic-tts-segment-boundaries-with-pause020',
        notice='합성 발화 경계에 후보 쉼0.20초를 반영했습니다. STT·단어 정렬 결과가 아닙니다.',
        originalAudioSha256=assets['A']['sha256'],insertionFrame=insertion,addedFrames=added)
    data={'schemaVersion':1,'synthetic':True,'productCommit':BASE,'candidateCommit':'309867bf0930d9c20deee12023125c91cf6e8f6a',
          'productSources':sources,'assets':assets,'cases':cases,'turns':rows,
          'timelineBasis':'Verified original generation segment metadata plus integer-frame silence insertion; not ASR or forced alignment.',
          'checks':{'text_and_speaker_unchanged':8,'utterance_pcm_identical':8,'whole_pcm_recoverable':True,
                    'no_production_files_modified':True},
          'map':{'insertionFrame':insertion,'addedFrames':added,'sampleRate':rate,'intervalConvention':'[start,end)'}}
    (REPORT/'playback-manifest.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'product':BASE,'assets':assets,'turns_verified':len(rows)},ensure_ascii=False))


if __name__=='__main__':
    main()
