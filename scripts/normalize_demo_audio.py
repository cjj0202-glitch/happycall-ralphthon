"""Create measured A/B candidates only; never replace public media or call APIs.

python scripts/normalize_demo_audio.py --ffmpeg C:/path/to/ffmpeg.exe
"""
from __future__ import annotations

import argparse
from array import array
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
import wave

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / '.local/audio-normalized'
TARGET_I = -18.0
TARGET_TP = -1.2  # Leave margin for the final 24 kHz resampling.
TARGET_LRA = 7.0
# ebur128 summary is rounded to 0.1 dB; -1.0 alone could hide -0.96 dBTP.
MAX_REPORTED_TP = -1.1
BASELINES = {
    'CASE-0001': '1432d1b44b66d7edd53408811ab73ede98303555235b14b4587671a390a51b92',
    'CASE-0002': 'f9fa70afaeb575876ab2dd18f1f395fbd38d6fec99b7cc0f70cb723650fb2e0c',
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def db(amplitude):
    return 20 * math.log10(amplitude) if amplitude > 0 else None


def pcm_metrics(path: Path, start: float = 0, end: float | None = None) -> dict:
    with wave.open(str(path), 'rb') as reader:
        rate, channels, width, frames = (reader.getframerate(), reader.getnchannels(),
                                          reader.getsampwidth(), reader.getnframes())
        if width != 2 or reader.getcomptype() != 'NONE' or not frames:
            raise ValueError('Expected nonempty uncompressed PCM16 WAV.')
        begin = round(start * rate)
        finish = round(end * rate) if end is not None else frames
        if not 0 <= begin < finish <= frames:
            raise ValueError('Invalid audio segment boundaries.')
        reader.setpos(begin)
        raw = reader.readframes(finish - begin)
    if len(raw) != (finish - begin) * channels * width:
        raise ValueError('Truncated WAV data.')
    samples = array('h', raw)
    if sys.byteorder != 'little':
        samples.byteswap()
    squares = sum(x * x for x in samples)
    window = max(1, round(rate * .02)) * channels
    quiet = total = 0
    for pos in range(0, len(samples) - window + 1, window):
        total += 1
        quiet += sum(x * x for x in samples[pos:pos + window]) / window / 32768**2 < 1e-5
    return {
        'sample_rate': rate, 'channels': channels, 'bits': width * 8,
        'frames': finish - begin, 'duration_seconds': (finish - begin) / rate,
        'peak_dbfs': db(max(abs(x) for x in samples) / 32768),
        'rms_dbfs': db(math.sqrt(squares / len(samples)) / 32768),
        'clipped_samples': sum(x <= -32768 or x >= 32767 for x in samples),
        'exact_zero_percent': 100 * samples.count(0) / len(samples),
        'quiet_20ms_percent': 100 * quiet / total if total else None,
    }


def find_ffmpeg(explicit: str | None = None) -> str:
    if explicit:
        resolved = shutil.which(explicit)
        if not resolved:
            raise ValueError('The supplied FFmpeg executable was not found.')
        return resolved
    executable = shutil.which('ffmpeg')
    if executable:
        return executable
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as exc:
        raise ValueError('FFmpeg is required. Supply an existing executable with --ffmpeg.') from exc


def run_ffmpeg(executable: str, args: list[str], log: Path) -> str:
    command = [executable, '-hide_banner', '-nostdin', '-nostats', *args]
    write_json(log.with_suffix('.command.json'), command)
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8',
                                errors='replace', timeout=90,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except subprocess.TimeoutExpired as exc:
        log.write_text('FFmpeg timed out after 90 seconds.', encoding='utf-8')
        raise RuntimeError('FFmpeg timed out; no candidate was promoted.') from exc
    log.write_text(result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'FFmpeg failed with exit {result.returncode}; see {log.name}.')
    return result.stderr


def parse_loudnorm(stderr: str) -> dict:
    candidates = re.findall(r'\{[^{}]*"input_i"[^{}]*\}', stderr, flags=re.S)
    if not candidates:
        raise ValueError('FFmpeg did not return loudnorm measurements.')
    values = json.loads(candidates[-1])
    for key in ('input_i', 'input_tp', 'input_lra', 'input_thresh', 'target_offset'):
        value = float(values[key])
        if not math.isfinite(value):
            raise ValueError(f'Non-finite loudnorm value: {key}.')
        values[key] = value
    return values


def measure(ffmpeg: str, path: Path, log: Path, start=0, end=None) -> dict:
    metrics = pcm_metrics(path, start, end)
    trim = ''
    if start or end is not None:
        finish = f':end_sample={round(end * metrics["sample_rate"])}' if end is not None else ''
        trim = f'atrim=start_sample={round(start * metrics["sample_rate"])}{finish},asetpts=PTS-STARTPTS,'
    # The separate ebur128 analysis reads the final quantized/resampled WAV.
    output = run_ffmpeg(ffmpeg, ['-i', str(path), '-map', '0:a:0', '-af',
                                trim + 'ebur128=peak=true', '-f', 'null', '-'], log)
    summary = output[output.rfind('Summary:'):]
    loudness = re.search(r'\bI:\s+([-+\d.]+) LUFS', summary)
    peak = re.search(r'Peak:\s+([-+\d.]+) dBFS', summary)
    if not loudness or not peak:
        raise ValueError('Missing finite EBU R128 summary.')
    metrics.update(integrated_lufs=float(loudness.group(1)), true_peak_dbtp=float(peak.group(1)))
    return metrics


def validate_candidate(before: dict, after: dict) -> None:
    if any(before[key] != after[key] for key in ('sample_rate', 'channels', 'bits', 'frames')):
        raise ValueError('Candidate changed the source format or exact sample count.')
    for key in ('integrated_lufs', 'true_peak_dbtp', 'rms_dbfs', 'peak_dbfs'):
        if after.get(key) is None or not math.isfinite(after[key]):
            raise ValueError(f'Candidate lacks finite {key}.')
    if abs(after['integrated_lufs'] - TARGET_I) > .3000001:
        raise ValueError('Candidate is outside the -18 +/- 0.3 LUFS range.')
    if after['true_peak_dbtp'] > MAX_REPORTED_TP or after['clipped_samples'] != 0:
        raise ValueError('Candidate exceeds the true-peak/clipping limit.')


def prepare_case(ffmpeg: str, source: Path, metadata_path: Path, target: Path, expected_sha: str) -> dict:
    actual_sha = sha256(source)
    if actual_sha != expected_sha:
        raise ValueError(f'{source.name}: original SHA-256 changed; inspect instead of overwriting.')
    target.mkdir(exist_ok=False)
    original = target / 'original.wav'
    shutil.copyfile(source, original)
    if sha256(original) != expected_sha:
        raise ValueError('Original preservation copy failed SHA-256 verification.')
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    write_json(target / 'source-metadata.json', metadata)
    before = measure(ffmpeg, original, target / 'before.log')
    if (metadata.get('synthetic') is not True or not math.isfinite(metadata['duration'])
            or abs(metadata['duration'] - before['duration_seconds']) > .001):
        raise ValueError('Synthetic metadata duration does not match the source WAV.')
    previous_end = 0.0
    segments = metadata.get('segments', [])
    if not segments:
        raise ValueError('No source segments to verify.')
    for segment in segments:
        start, end = segment['start'], segment['end']
        if not 0 <= previous_end <= start < end <= before['duration_seconds']:
            raise ValueError('Invalid or overlapping source segments.')
        previous_end = end
    prefix = f'loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}'
    pass1 = parse_loudnorm(run_ffmpeg(ffmpeg, ['-i', str(original), '-map', '0:a:0', '-af',
                                             prefix + ':print_format=json', '-f', 'null', '-'],
                                    target / 'pass1.log'))
    candidate = target / 'candidate.wav'
    filter2 = (prefix + f':measured_I={pass1["input_i"]}:measured_TP={pass1["input_tp"]}'
               f':measured_LRA={pass1["input_lra"]}:measured_thresh={pass1["input_thresh"]}'
               f':offset={pass1["target_offset"]}:linear=true:print_format=json')
    pass2 = parse_loudnorm(run_ffmpeg(ffmpeg, ['-n', '-i', str(original), '-map', '0:a:0', '-af',
                                             filter2, '-ar', str(before['sample_rate']), '-ac',
                                             str(before['channels']), '-c:a', 'pcm_s16le', str(candidate)],
                                    target / 'pass2.log'))
    after = measure(ffmpeg, candidate, target / 'after.log')
    validate_candidate(before, after)
    comparison = []
    for index, segment in enumerate(segments, 1):
        start, end = segment['start'], segment['end']
        comparison.append({**segment, 'turn': index,
                           'before': measure(ffmpeg, original, target / f'turn-{index}-before.log', start, end),
                           'after': measure(ffmpeg, candidate, target / f'turn-{index}-after.log', start, end)})
    if sha256(source) != expected_sha or sha256(original) != expected_sha:
        raise ValueError('Source changed during preparation; candidate not promoted.')
    result = {'case_id': source.stem, 'source_path': str(source.resolve()),
              'original_sha256': expected_sha, 'candidate_sha256': sha256(candidate),
              'original_file': str(original.name), 'candidate_file': str(candidate.name),
              'before': before, 'after': after, 'pass1': pass1, 'pass2': pass2, 'segments': comparison,
              'numerical_acceptance': True, 'listening_acceptance': 'not_evaluated'}
    write_json(target / 'metrics.json', result)
    return result


def prepare_run(ffmpeg: str, cases: list[tuple[Path, Path, str]], output_root: Path) -> Path:
    if not cases:
        raise ValueError('At least one source case is required.')
    output_root = output_root.resolve()
    for source, metadata, _ in cases:
        for protected in (source.resolve(), metadata.resolve()):
            if protected.is_relative_to(output_root) or output_root.is_relative_to(protected.parent):
                raise ValueError('Output must be separate from protected source/metadata directories.')
    output_root.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    staging = output_root / (run_id + '.incomplete')
    staging.mkdir()
    try:
        results = [prepare_case(ffmpeg, source, metadata, staging / source.stem, expected)
                   for source, metadata, expected in cases]
        # Recheck both sources after the second case, not merely after each copy.
        if any(sha256(source) != expected for source, _, expected in cases):
            raise ValueError('A protected source changed before final promotion.')
        write_json(staging / 'comparison.json', {'created_utc': datetime.now(timezone.utc).isoformat(),
                   'ffmpeg': ffmpeg, 'targets': {'integrated_lufs': TARGET_I, 'true_peak_dbtp': TARGET_TP},
                   'cases': results, 'status': 'numerically_accepted_listening_pending'})
        complete = output_root / run_id
        staging.rename(complete)
        return complete
    except BaseException as exc:
        write_json(staging / 'failure.json', {'status': 'failed_not_for_use', 'error_type': type(exc).__name__,
                                            'message': str(exc), 'public_media_written': False})
        failed = output_root / (run_id + '.failed')
        staging.rename(failed)
        raise RuntimeError(f'Preparation failed; originals retained. Evidence: {failed}') from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ffmpeg', help='Existing FFmpeg executable; otherwise PATH or installed imageio_ffmpeg.')
    args = parser.parse_args()
    # Output location is fixed; reject a symlink/junction redirect outside .local.
    if not OUTPUT_ROOT.resolve().is_relative_to((ROOT / '.local').resolve()):
        raise ValueError('Output directory resolves outside the repository .local directory.')
    cases = [(ROOT / f'apps/web/public/demo/{case_id}.wav',
              ROOT / f'.local/tts-segments/{case_id}.metadata.json', digest)
             for case_id, digest in BASELINES.items()]
    complete = prepare_run(find_ffmpeg(args.ffmpeg), cases, OUTPUT_ROOT)
    print(json.dumps({'candidate_directory': str(complete), 'numerical_acceptance': True,
                      'listening_acceptance': 'not_evaluated', 'public_media_written': False}))


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, OSError, wave.Error) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
