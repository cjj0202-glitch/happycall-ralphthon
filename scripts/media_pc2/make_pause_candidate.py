"""N02-M2: insert silence only, preserve every approved PCM frame, no APIs.

python scripts/media_pc2/make_pause_candidate.py
Requires the approved v2 input and local imageio-ffmpeg==0.6.0 for measurement.
No input, manifest, fixture or transcript is rewritten. Outputs must not exist.
"""
from __future__ import annotations

import argparse
from array import array
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import wave

from measure_audio import ROOT, SOURCE_TURNS, digest, load_pcm, metrics

EXPECTED = '333897f4f10426674ec97b9e3a44c2f8da21f1f7931b4f911c82a29abcf6b914'
INSERT_TIME = 17.375
EXTRA_TIME = .20
CLIP_START, CLIP_END = 12.25, 29.95


def insert_silence(samples: array, frame: int, extra_frames: int, guard_frames: int) -> array:
    """Mono PCM16 only: reject speech/nonzero cut, invalid boundary or duration."""
    if samples.typecode != 'h':
        raise ValueError('PCM16 array required')
    if not (extra_frames > 0 and guard_frames > 0 and guard_frames <= frame <= len(samples)-guard_frames):
        raise ValueError('Invalid edit boundary, guard or inserted frame count')
    if any(samples[frame-guard_frames:frame+guard_frames]):
        raise ValueError('Edit must be surrounded by exact digital silence')
    return samples[:frame] + array('h', [0]) * extra_frames + samples[frame:]


def write_wave(path: Path, samples: array, rate: int) -> None:
    raw = array('h', samples)
    if sys.byteorder != 'little':
        raw.byteswap()
    with path.open('xb') as stream, wave.open(stream, 'wb') as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        writer.writeframes(raw.tobytes())


def loudness(exe: str, source: Path, log: Path) -> dict:
    command = [exe, '-hide_banner', '-nostdin', '-i', str(source),
               '-af', 'ebur128=peak=true', '-f', 'null', '-']
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
    log.write_text(result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'FFmpeg failed: {source.name}; inspect {log}')
    summary = result.stderr.rsplit('Summary:', 1)[-1]
    integrated = re.search(r'I:\s+([-+\d.]+) LUFS', summary)
    peak = re.search(r'Peak:\s+([-+\d.]+) dBFS', summary)
    lra = re.search(r'LRA:\s+([-+\d.]+) LU', summary)
    if not all((integrated, peak, lra)):
        raise RuntimeError(f'Incomplete EBU R128 summary: {log}')
    return {'integrated_lufs': float(integrated[1]), 'true_peak_dbtp': float(peak[1]),
            'loudness_range_lu': float(lra[1]), 'exit_code': result.returncode,
            'command': ['<ffmpeg>'] + command[1:], 'raw_log': log.relative_to(ROOT).as_posix()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, default=ROOT/'.local/pc2-n02-m2-pause-v1')
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if not output.is_relative_to(ROOT/'.local'):
        raise ValueError('Candidate output must stay inside repository .local')
    if output.exists():
        raise FileExistsError('Preserve prior outputs; use a new candidate directory')
    source = ROOT/'apps/web/public/demo/CASE-0002.wav'
    if digest(source) != EXPECTED:
        raise ValueError('Input differs from approved v2 SHA256')
    shape, original = load_pcm(source)
    if shape['channels'] != 1 or shape['sample_rate_hz'] != 24000 or shape['frames'] != 1189200:
        raise ValueError('Expected approved mono 24kHz v2 shape')
    rate = shape['sample_rate_hz']
    frame, added = round(INSERT_TIME*rate), round(EXTRA_TIME*rate)
    candidate = insert_silence(original, frame, added, round(.025*rate))
    if candidate[:frame] + candidate[frame+added:] != original:
        raise RuntimeError('Round-trip PCM preservation failure')
    tools = ROOT/'.local/audio-tools'
    sys.path.insert(0, str(tools))
    import imageio_ffmpeg
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    version = subprocess.check_output([exe, '-version'], text=True).splitlines()[0]
    protected = [source, ROOT/'apps/web/public/demo/CASE-0001.wav', ROOT/'data/demo-media-manifest.json',
                 ROOT/'data/fixtures/cases.json', ROOT/'reports/e2e/normalized-voice-live.json']
    before = {p.relative_to(ROOT).as_posix(): digest(p) for p in protected}
    output.mkdir(parents=True)
    report_dir = ROOT/'reports/pc2/audio-m2'
    report_dir.mkdir(exist_ok=True, parents=True)
    first, last = round(CLIP_START*rate), round(CLIP_END*rate)
    paths = {'full_A': source, 'full_B': output/'CASE-0002-pause020-v1.wav',
             'clip_A': output/'CASE-0002-units-A-v2.wav', 'clip_B': output/'CASE-0002-units-B-pause020.wav'}
    write_wave(paths['full_B'], candidate, rate)
    write_wave(paths['clip_A'], original[first:last], rate)
    write_wave(paths['clip_B'], candidate[first:last+added], rate)
    measurements = {}
    for name, path in paths.items():
        current_shape, pcm = load_pcm(path)
        measurements[name] = {'file': path.name, 'path': path.relative_to(ROOT).as_posix(),
                             'bytes': path.stat().st_size, 'sha256': digest(path),
                             'codec': 'pcm_s16le', 'shape': current_shape,
                             'pcm': metrics(current_shape, pcm),
                             'ebur128': loudness(exe, path, report_dir/f'{name}-ebur128.txt')}
    _, written_full = load_pcm(paths['full_B'])
    _, written_clip_a = load_pcm(paths['clip_A'])
    _, written_clip_b = load_pcm(paths['clip_B'])
    mapped_turns = []
    for index, (start, end) in enumerate(SOURCE_TURNS['CASE-0002'], 1):
        mapped_turns.append({'turn': index, 'source_start': start, 'source_end': end,
                             'candidate_start': start+(EXTRA_TIME if start >= INSERT_TIME else 0),
                             'candidate_end': end+(EXTRA_TIME if end >= INSERT_TIME else 0),
                             'basis': 'pc1 generation timing table citation; not new STT or human-aligned boundaries'})
    after = {p.relative_to(ROOT).as_posix(): digest(p) for p in protected}
    checks = {
        'approved_source_sha': before[source.relative_to(ROOT).as_posix()] == EXPECTED,
        'all_original_frames_recoverable_in_order': candidate[:frame]+candidate[frame+added:] == original,
        'written_wav_round_trip_pcm_exact': written_full == candidate and written_full[:frame]+written_full[frame+added:] == original,
        'written_comparison_clips_exact': written_clip_a == original[first:last] and written_clip_b == candidate[first:last+added],
        'inserted_frames_exactly_zero': candidate[frame:frame+added].count(0) == added,
        'no_original_samples_changed_or_removed': candidate[:frame] == original[:frame] and candidate[frame+added:] == original[frame:],
        'full_tail_one_second_byte_identical': candidate[-rate:] == original[-rate:],
        'expected_full_duration_49_75': len(candidate)/rate == 49.75,
        'digital_rail_zero_all_outputs': all(m['pcm']['digital_rail_samples'] == 0 for m in measurements.values()),
        'full_loudness_delta_at_most_point2_lu': abs(measurements['full_A']['ebur128']['integrated_lufs']-measurements['full_B']['ebur128']['integrated_lufs']) <= .2,
        'clip_loudness_delta_at_most_point2_lu': abs(measurements['clip_A']['ebur128']['integrated_lufs']-measurements['clip_B']['ebur128']['integrated_lufs']) <= .2,
        'candidate_full_lufs_near_minus18': -18.5 <= measurements['full_B']['ebur128']['integrated_lufs'] <= -17.5,
        'candidate_true_peak_no_more_minus1': measurements['full_B']['ebur128']['true_peak_dbtp'] <= -1,
        'protected_inputs_unchanged': before == after,
    }
    result = {'created_at': datetime.now(timezone.utc).isoformat(), 'candidate': 'N02-M2-pause020-v1',
              'python': platform.python_version(), 'imageio_ffmpeg': imageio_ffmpeg.__version__,
              'ffmpeg_version': version, 'ffmpeg_binary_sha256': digest(Path(exe)),
              'edit': {'source_case': 'CASE-0002', 'insertion_source_time': INSERT_TIME,
                       'insertion_frame': frame, 'added_seconds': EXTRA_TIME, 'added_frames': added,
                       'silence_guard_frames_each_side': round(.025*rate), 'speed': 1, 'gain_db': 0,
                       'intent': 'Test whether a 0.35-to-0.55 second pause before the EA-to-BOX correction helps listeners separate the two speakers. Improvement is unproven.',
                       'clip_source_range': [CLIP_START, CLIP_END]},
              'candidate_time_map': [{'source_frames':[0,frame], 'candidate_frames':[0,frame]},
                                     {'source_frames':None, 'candidate_frames':[frame,frame+added], 'kind':'inserted digital silence'},
                                     {'source_frames':[frame,len(original)], 'candidate_frames':[frame+added,len(candidate)]}],
              'generation_turns': mapped_turns, 'measurements': measurements, 'checks': checks,
              'passed': sum(checks.values()), 'total': len(checks), 'protected_before': before, 'protected_after': after,
              'limits': {'human_listening_trials':0,'intelligibility_improvement':'UNVERIFIED','stt_calls':0,
                         'tts_calls':0,'browser_playback_runs':0,'production_assets_changed':False,
                         'no_cut_claim':'No additional full-file cut: every original sample is recoverable. Original speech quality and old truncation, if any, are not evaluated.'}}
    (report_dir/'candidate.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(output), 'checks':checks, 'assets':{k:{'sha256':v['sha256'],'seconds':v['shape']['duration_seconds'],'lufs':v['ebur128']['integrated_lufs']} for k,v in measurements.items()}},ensure_ascii=False,indent=2))
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
