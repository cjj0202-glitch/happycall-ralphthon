"""Render an observed browser demonstration with unchanged CLOVA speech and concise gaps.

python scripts/render_dynamic_demo.py .local/demo-video/dynamic-.../timeline.json
Original timing is the default. Optional dynamic gap compression has a 3x ceiling.
Audience recordings always preserve the complete original timeline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import subprocess
import textwrap
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = (ROOT / '.local/demo-video').resolve()
FFMPEG = Path('C:/Users/choi8/AppData/Local/Programs/Python/Python314/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe')


def duration(file: Path, ffmpeg: Path) -> float:
    run = subprocess.run([str(ffmpeg), '-hide_banner', '-nostdin', '-v', 'error', '-i', str(file),
                          '-map', '0:a:0', '-ac', '1', '-ar', '48000', '-f', 's16le', 'pipe:1'],
                         capture_output=True, check=True, timeout=60)
    result = len(run.stdout) / 96000
    assert result > 0, f'Empty audio: {file}'
    return result


def seconds(value: float, ass: bool = False) -> str:
    precision = 100 if ass else 1000
    ticks = max(0, round(value * precision))
    hours, remain = divmod(ticks, 3600 * precision)
    minutes, remain = divmod(remain, 60 * precision)
    secs, decimals = divmod(remain, precision)
    return f'{hours}:{minutes:02}:{secs:02}.{decimals:02}' if ass else f'{hours:02}:{minutes:02}:{secs:02},{decimals:03}'


def ass_text(value: str) -> str:
    return str(value).replace('\\', '\\\\').replace('{', '(').replace('}', ')').replace('\n', '\\N')


def time_segments(speech: list[dict], total: float, keep_gaps: bool) -> list[dict]:
    intervals = sorted((max(0, c['startSeconds'] - .08), min(total, c['endSeconds'] + .08)) for c in speech)
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    segments, cursor, output = [], 0.0, 0.0

    def add(start: float, end: float, spoken: bool) -> None:
        nonlocal output
        if end - start < .001:
            return
        length = end - start
        result_length = max(1.0, length / 3) if not spoken and length >= 3 and not keep_gaps else length
        segments.append({'start': start, 'end': end, 'speech': spoken, 'outputStart': output,
                         'outputEnd': output + result_length, 'speed': length / result_length})
        output += result_length

    for start, end in merged:
        add(cursor, start, False)
        add(start, end, True)
        cursor = end
    add(cursor, total, False)
    return segments


def map_time(value: float, segments: list[dict]) -> float:
    for segment in segments:
        if value <= segment['end']:
            return segment['outputStart'] + max(0, value - segment['start']) / segment['speed']
    return segments[-1]['outputEnd']


def subtitles(data: dict, narration: list[dict], segments: list[dict], directory: Path) -> list[dict]:
    epoch = data['recordingEpochMs']
    source_total = segments[-1]['end']
    stages = [{**s, 'start': (s['epochMs'] - epoch) / 1000} for s in data['stages']]
    points = sorted({0.0, source_total, *(s['start'] for s in stages),
                     *(n['startSeconds'] for n in narration), *(n['endSeconds'] for n in narration)})
    cues = []
    for start, end in zip(points, points[1:]):
        active = next((n for n in narration if n['startSeconds'] <= start + .00001 < n['endSeconds']), None)
        if active and active.get('text'):
            # Narration replaces the stage text instead of adding a third text block.
            text = '\n'.join(textwrap.wrap(active['text'], width=61, break_long_words=True, break_on_hyphens=False))
        else:
            prior = [s for s in stages if s['start'] <= start + .00001]
            if not prior:
                continue
            stage = prior[-1]
            text = stage['title'] + ('\n' + stage['detail'] if stage.get('detail') else '')
        cues.append({'start': map_time(start, segments), 'end': map_time(end, segments), 'text': text})
    header = '''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Malgun Gothic,27,&H00FFFFFF,&H00FFFFFF,&H70000000,&H70000000,0,0,0,0,100,100,0,0,3,5,0,2,70,70,34,1
Style: Footer,Malgun Gothic,15,&H00FFFFFF,&H00FFFFFF,&H70000000,&H70000000,0,0,0,0,100,100,0,0,3,3,0,2,20,20,5,1
Style: Ring,Arial,20,&H00FFD34D,&H00FFD34D,&H00FFD34D,&HFF000000,0,0,0,0,100,100,0,0,1,2,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    lines = [header]
    for cue in cues:
        lines.append(f"Dialogue: 0,{seconds(cue['start'], True)},{seconds(cue['end'], True)},Caption,,0,0,0,,{ass_text(cue['text'])}\n")
    lines.append(f"Dialogue: 1,0:00:00.00,{seconds(segments[-1]['outputEnd'], True)},Footer,,0,0,0,,해설: CLOVA Dubbing · 통화: 별도 합성 시연 음성 · 저장 결과 재생\n")
    if not data.get('clickRingsRecorded'):
        for event in data.get('interactions', []):
            if event.get('type') != 'click' or 'x' not in event or 'y' not in event:
                continue
            start = map_time((event['epochMs'] - epoch) / 1000, segments)
            for phase, radius in enumerate((12, 19, 26)):
                k = radius * .5523
                path = f'm {radius} 0 b {radius} {k} {k} {radius} 0 {radius} b {-k} {radius} {-radius} {k} {-radius} 0 b {-radius} {-k} {-k} {-radius} 0 {-radius} b {k} {-radius} {radius} {-k} {radius} 0'
                style = '{\\an7\\pos(' + f"{event['x']},{event['y']}" + ')\\p1\\1a&HFF&\\3c&HFFD34D&\\bord2}'
                lines.append(f'Dialogue: 2,{seconds(start + phase*.10, True)},{seconds(start + (phase+1)*.10, True)},Ring,,0,0,0,,{style}{path}\n')
    (directory / 'dynamic-captions.ass').write_text(''.join(lines), encoding='utf-8')
    (directory / 'dynamic-captions.srt').write_text('\n'.join(f"{i}\n{seconds(c['start'])} --> {seconds(c['end'])}\n{c['text']}\n" for i, c in enumerate(cues, 1)), encoding='utf-8')
    return cues


def audience_subtitles(data: dict, narration: list[dict], total: float, directory: Path) -> list[dict]:
    """Editorial text lives outside the complete 1728x864 application recording."""
    epoch = data['recordingEpochMs']
    stages = [{**stage, 'start': (stage['epochMs'] - epoch) / 1000} for stage in data['stages']]
    chapters = list(dict.fromkeys(stage.get('chapter', stage['title']) for stage in stages))
    points = sorted({0.0, total, *(stage['start'] for stage in stages),
                     *(clip['startSeconds'] for clip in narration), *(clip['endSeconds'] for clip in narration)})
    header = '''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Brand,Malgun Gothic,29,&H00FFFFFF,&H00FFFFFF,&HFF000000,&HFF000000,-1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Chapter,Malgun Gothic,26,&H0071C5F9,&H0071C5F9,&HFF000000,&HFF000000,-1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Caption,Malgun Gothic,34,&H00FFFFFF,&H00FFFFFF,&HFF000000,&HFF000000,0,0,0,0,100,100,0,0,1,0,0,8,0,0,0,1
Style: Detail,Malgun Gothic,22,&H00CDBBAD,&H00CDBBAD,&HFF000000,&HFF000000,0,0,0,0,100,100,0,0,1,0,0,8,0,0,0,1
Style: Progress,Malgun Gothic,21,&H00CDBBAD,&H00CDBBAD,&HFF000000,&HFF000000,0,0,0,0,100,100,0,0,1,0,0,9,0,0,0,1
Style: Credit,Malgun Gothic,16,&H00CDBBAD,&H00CDBBAD,&HFF000000,&HFF000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    lines = [header]
    cues = []

    def line(start, end, style, text):
        lines.append(f'Dialogue: 0,{seconds(start, True)},{seconds(end, True)},{style},,0,0,0,,{text}\n')

    def accent(text, words):
        # At most two exact words are accented; all ordinary text remains unchanged.
        selected = [str(word) for word in words if str(word) and str(word) in text][:2]
        if not selected:
            return ass_text(text)
        pattern = re.compile('|'.join(re.escape(word) for word in sorted(selected, key=len, reverse=True)))
        result, cursor, count = [], 0, 0
        for match in pattern.finditer(text):
            if count == 2:
                break
            result.append(ass_text(text[cursor:match.start()]))
            result.append('{\\c&HE8D548&\\b1}' + ass_text(match.group()) + '{\\c&HFFFFFF&\\b0}')
            cursor, count = match.end(), count + 1
        result.append(ass_text(text[cursor:]))
        return ''.join(result)

    line(0, total, 'Brand', '{\\pos(96,17)}AI-GO')
    line(0, total, 'Detail', '{\\an7\\pos(215,24)}무엇이든 물어보살')
    # Required source credit appears only in the final chapter's upper canvas.
    credit_start = max(stages[-1]['start'], total - 4)
    line(credit_start, total, 'Credit', '{\\pos(1320,24)}음성 제작 · CLOVA Dubbing')
    # Fine frame border and chapter progress strip use the reserved canvas only.
    line(0, total, 'Brand', '{\\pos(95,69)\\p1\\bord1\\1a&HFF&\\3c&H58402B&}m 0 0 l 1730 0 1730 866 0 866 0 0')
    for start, end in zip(points, points[1:]):
        prior = [stage for stage in stages if stage['start'] <= start + .00001]
        stage = prior[-1] if prior else stages[0]
        chapter = stage.get('chapter', stage['title'])
        number = chapters.index(chapter) + 1
        active = next((clip for clip in narration if clip['startSeconds'] <= start + .00001 < clip['endSeconds']), None)
        text = active.get('text', '') if active else stage.get('keyMessage', stage['title'])
        wrapped = '\n'.join(textwrap.wrap(text, width=49, break_long_words=True, break_on_hyphens=False))
        assert len(wrapped.splitlines()) <= 2, f'Audience caption exceeds two lines: {text}'
        text_position = 963 if '\n' in wrapped else 978
        line(start, end, 'Caption', '{\\pos(960,' + str(text_position) + ')}' + accent(wrapped, stage.get('accentWords', [])))
        if not active and '\n' not in wrapped and stage.get('detail'):
            line(start, end, 'Detail', '{\\pos(960,1030)}' + ass_text(stage['detail']))
        line(start, end, 'Chapter', '{\\pos(650,18)}' + ass_text(chapter))
        line(start, end, 'Progress', '{\\pos(1824,23)}' + f'{number:02} / {len(chapters):02}')
        width = 400 * number / len(chapters)
        line(start, end, 'Brand', '{\\pos(1330,48)\\p1\\c&H58402B&}m 0 0 l 400 0 400 3 0 3')
        line(start, end, 'Brand', '{\\pos(1330,48)\\p1\\c&HE8D548&}' + f'm 0 0 l {width} 0 {width} 3 0 3')
        cues.append({'start': start, 'end': end, 'text': wrapped})
    (directory / 'audience-captions.ass').write_text(''.join(lines), encoding='utf-8')
    (directory / 'audience-captions.srt').write_text('\n'.join(f"{i}\n{seconds(c['start'])} --> {seconds(c['end'])}\n{c['text']}\n" for i, c in enumerate(cues, 1)), encoding='utf-8')
    return cues


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('timeline', type=Path)
    parser.add_argument('--ffmpeg', type=Path, default=FFMPEG)
    parser.add_argument('--keep-gaps', action='store_true')
    parser.add_argument('--compress-gaps', action='store_true', help='Opt in to 3x maximum gap compression for dynamic recordings only')
    parser.add_argument('--plan-only', action='store_true')
    args = parser.parse_args()
    timeline = args.timeline.resolve()
    assert timeline.is_relative_to(OUTPUT_ROOT) and timeline.parent.name.startswith(('dynamic-', 'audience-'))
    directory = timeline.parent
    data = json.loads(timeline.read_text(encoding='utf-8'))
    audience = data.get('pace') == 'audience' or data.get('schemaVersion') == 3
    if audience:
        assert timeline.parent.name.startswith('audience-'), 'Audience recordings require a separate audience-* directory'
        assert not args.compress_gaps, 'Audience timing must never be compressed'
        assert data.get('viewport') == {'width': 1600, 'height': 800}, 'Audience frame requires the complete 1600x800 application viewport'
    assert data.get('complete') and not data.get('failure') and not data.get('errors'), 'Recording did not complete'
    raw = Path(data['rawVideo']).resolve()
    assert raw.is_relative_to(directory) and raw.is_file()
    total = (data['endEpochMs'] - data['recordingEpochMs']) / 1000
    assert math.isfinite(total) and total > 0
    output = directory / ('ai-go-demo-audience-ko.mp4' if audience else 'ai-go-demo-dynamic-ko.mp4')
    assert not output.exists(), 'Preserve the existing final file before rerendering'
    speech = []
    for item in data['audio']:
        file = Path(item['file']).resolve()
        assert hashlib.sha256(file.read_bytes()).hexdigest() == item['sha256'], 'Call hash mismatch'
        events = [e for e in data['audioEvents'] if f"{item['caseId']}.wav" in e['src']]
        playing = [e for e in events if e['type'] == 'playing']
        assert len(playing) == 1 and any(e['type'] == 'ended' for e in events), 'Call must play fully without interruption'
        event = playing[0]
        rate = 1.25 if audience else 1.5
        assert event['playbackRate'] == rate
        start = (event['epochMs'] - data['recordingEpochMs']) / 1000 - event['currentTime'] / rate
        length = duration(file, args.ffmpeg) / rate
        speech.append({'file': str(file), 'source': 'synthetic call', 'startSeconds': start, 'endSeconds': start + length, 'rate': rate})
    for item in data['narration']:
        assert item['source'] == 'CLOVA Dubbing'
        file = Path(item['file'])
        if not file.is_absolute():
            file = timeline.parent / file
        file = file.resolve()
        assert file.is_relative_to(OUTPUT_ROOT) and file.suffix.lower() in ('.wav', '.mp3')
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        assert not item.get('sha256') or item['sha256'] == digest, 'CLOVA audio hash mismatch'
        start = (item['epochMs'] - data['recordingEpochMs']) / 1000
        length = duration(file, args.ffmpeg)
        speech.append({'file': str(file), 'source': 'CLOVA Dubbing', 'sha256': digest,
                       'projectUrl': item.get('projectUrl'), 'startSeconds': start, 'endSeconds': start + length,
                       'rate': 1, 'text': item.get('text', '')})
    ordered = sorted(speech, key=lambda s: s['startSeconds'])
    for i, item in enumerate(ordered):
        assert 0 <= item['startSeconds'] < item['endSeconds'] <= total, 'Speech outside recording'
        if i:
            assert ordered[i-1]['endSeconds'] <= item['startSeconds'], f'Speech overlap: {ordered[i-1]} / {item}'
    segments = time_segments(speech, total, audience or args.keep_gaps or not args.compress_gaps)
    narration = [s for s in speech if s['source'] == 'CLOVA Dubbing']
    cues = audience_subtitles(data, narration, total, directory) if audience else subtitles(data, narration, segments, directory)
    command = [str(args.ffmpeg), '-hide_banner', '-nostdin', '-n', '-i', str(raw)]
    filters, tracks = [], []
    for i, item in enumerate(speech, 1):
        command += ['-i', item['file']]
        tempo = f"atempo={item['rate']}," if item['rate'] != 1 else ''
        filters.append(f"[{i}:a]{tempo}adelay={round(item['startSeconds']*1000)}:all=1[a{i}]")
        tracks.append(f'[a{i}]')
    filters.append(''.join(tracks) + f'amix=inputs={len(tracks)}:normalize=0,apad[fullaudio]')
    # One continuous frame clock avoids per-segment frame rounding accumulating A/V drift.
    last = segments[-1]
    expression = f"({last['outputStart']}+(T-{last['start']})/{last['speed']})"
    for segment in reversed(segments[:-1]):
        mapped = f"({segment['outputStart']}+(T-{segment['start']})/{segment['speed']})"
        expression = f"if(lt(T,{segment['end']}),{mapped},{expression})"
    filters.append('[0:v]setpts=PTS-STARTPTS[editedvideo]' if audience else f"[0:v]setpts=PTS-STARTPTS,setpts='{expression}/TB'[editedvideo]")
    regular = [i for i, s in enumerate(segments) if s['speed'] == 1]
    if audience:
        filters.append(f'[fullaudio]atrim=duration={total},asetpts=PTS-STARTPTS[editedaudio]')
    else:
        filters.append(f'[fullaudio]asplit={len(regular)}' + ''.join(f'[as{i}]' for i in regular))
        for i, segment in enumerate(segments):
            start, end, speed = segment['start'], segment['end'], segment['speed']
            if speed == 1:
                filters.append(f'[as{i}]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[au{i}]')
            else:
                length = segment['outputEnd'] - segment['outputStart']
                filters.append(f'anullsrc=r=24000:cl=mono,atrim=duration={length}[au{i}]')
        filters.append(''.join(f'[au{i}]' for i in range(len(segments))) + f'concat=n={len(segments)}:v=0:a=1[editedaudio]')
    clicks = [e for e in data.get('interactions', []) if e.get('type') == 'click']
    # A quiet 35ms pulse is an editorial UI sound, never a replacement for recorded speech.
    pulse = directory / 'click-pulse.wav'
    with wave.open(str(pulse), 'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(24000)
        wav.writeframes(b''.join(struct.pack('<h', round(32767*.027*math.sin(2*math.pi*1050*n/24000)*math.sin(math.pi*n/840)**2)) for n in range(840)))
    if clicks:
        command += ['-i', str(pulse)]
        filters.append(f'[{len(speech)+1}:a]asplit={len(clicks)}' + ''.join(f'[pulse{i}]' for i in range(len(clicks))))
        for i, click in enumerate(clicks):
            at = map_time((click['epochMs'] - data['recordingEpochMs']) / 1000, segments)
            filters.append(f'[pulse{i}]adelay={round(at*1000)}:all=1[c{i}]')
        filters.append('[editedaudio]' + ''.join(f'[c{i}]' for i in range(len(clicks))) + f'amix=inputs={len(clicks)+1}:normalize=0[aout]')
    else:
        filters.append('[editedaudio]anull[aout]')
    filters.append('[editedvideo]scale=1728:864:flags=lanczos,pad=1920:1080:96:70:color=0x081B2C,ass=audience-captions.ass[vout]' if audience else '[editedvideo]ass=dynamic-captions.ass[vout]')
    command += ['-filter_complex', ';'.join(filters), '-map', '[vout]', '-map', '[aout]', '-r', '25',
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '192k', '-t', str(segments[-1]['outputEnd']), '-movflags', '+faststart', str(output)]
    plan = {'command': command, 'sourceSeconds': total, 'outputSeconds': segments[-1]['outputEnd'], 'segments': segments,
            'speech': speech, 'narrationCount': len(narration), 'clickCount': len(clicks), 'captionCues': len(cues),
            'clickRingsRecorded': bool(data.get('clickRingsRecorded')), 'maxGapPlaybackRate': 1 if audience or not args.compress_gaps else 3,
            'pace': 'audience' if audience else 'dynamic', 'sourceTimingPreserved': audience or args.keep_gaps or not args.compress_gaps,
            'speechOverlap': False, 'clovaTimeStretch': False, 'clovaGainDb': 0,
            'maxScheduledSpeechGapSeconds': max([map_time(ordered[0]['startSeconds'], segments), segments[-1]['outputEnd']-map_time(ordered[-1]['endSeconds'], segments)] + [map_time(b['startSeconds'], segments)-map_time(a['endSeconds'], segments) for a,b in zip(ordered, ordered[1:])])}
    (directory / 'dynamic-render-plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
    if args.plan_only:
        print(json.dumps({k: v for k, v in plan.items() if k not in ('command','speech','segments')}, ensure_ascii=False))
        return
    with (directory / 'dynamic-ffmpeg.log').open('w', encoding='utf-8') as log:
        subprocess.run(command, cwd=directory, stdout=log, stderr=subprocess.STDOUT, check=True)
    print(output)


if __name__ == '__main__':
    main()
