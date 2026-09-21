"""No paid calls. Fixtures and failures run in temporary private directories."""
from __future__ import annotations

from array import array
import contextlib
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch
import wave

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


n = load_script('normalize_demo_audio')
g = load_script('generate_demo_audio')


def wav_bytes(samples, rate=24000):
    target = io.BytesIO()
    with wave.open(target, 'wb') as writer:
        writer.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        values = array('h', samples)
        if sys.byteorder != 'little':
            values.byteswap()
        writer.writeframes(values.tobytes())
    return target.getvalue()


class AudioPreparationTests(unittest.TestCase):
    def setUp(self):
        # Keep test media under the assigned ignored directory.
        n.OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix='selftest-', dir=n.OUTPUT_ROOT)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.input = self.root / 'input'
        self.input.mkdir()
        self.source = self.input / 'TEST.wav'
        self.source.write_bytes(wav_bytes([round(3000 * math.sin(i / 12)) for i in range(24000 * 6)]))
        self.original = self.source.read_bytes()
        self.digest = n.sha256(self.source)
        self.metadata = self.input / 'TEST.metadata.json'
        n.write_json(self.metadata, {'synthetic': True, 'duration': 6,
                                    'segments': [{'start': 0, 'end': 6, 'speaker': 'test'}]})

    def valid_metrics(self):
        return dict(sample_rate=24000, channels=1, bits=16, frames=144000,
                    integrated_lufs=-18.0, true_peak_dbtp=-1.2, rms_dbfs=-19,
                    peak_dbfs=-1.3, clipped_samples=0)

    def test_pcm_clipping_positive_and_negative_controls(self):
        clean = n.pcm_metrics(self.source)
        self.assertEqual(clean['clipped_samples'], 0)
        self.assertEqual(clean['frames'], 144000)
        self.source.write_bytes(wav_bytes([-32768, 32767, -32767, 32766]))
        self.assertEqual(n.pcm_metrics(self.source)['clipped_samples'], 2)

    def test_pcm_quiet_and_fullscale_measurements(self):
        self.source.write_bytes(wav_bytes([0] * 480 + [16384] * 480))
        result = n.pcm_metrics(self.source)
        self.assertEqual(result['quiet_20ms_percent'], 50)
        self.assertEqual(result['exact_zero_percent'], 50)
        self.assertAlmostEqual(result['peak_dbfs'], -6.0206, places=3)
        self.assertAlmostEqual(result['rms_dbfs'], -9.0309, places=3)

    def test_truncated_wave_and_invalid_segment_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'boundaries'):
            n.pcm_metrics(self.source, 4, 3)
        self.source.write_bytes(self.original[:-20])
        with self.assertRaisesRegex(ValueError, 'Truncated'):
            n.pcm_metrics(self.source)

    def test_candidate_acceptance_boundaries(self):
        before = self.valid_metrics()
        for loudness in (-18.3, -18, -17.7):
            n.validate_candidate(before, {**before, 'integrated_lufs': loudness, 'true_peak_dbtp': -1.1})
        for key, value in [('integrated_lufs', -17.69), ('true_peak_dbtp', -1.0), ('true_peak_dbtp', -.99),
                           ('clipped_samples', 1), ('frames', 143999), ('sample_rate', 48000),
                           ('channels', 2), ('bits', 24), ('rms_dbfs', float('nan')),
                           ('true_peak_dbtp', float('inf'))]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                n.validate_candidate(before, {**before, key: value})

    def test_open_ended_segment_uses_same_start_for_pcm_and_loudness(self):
        summary = 'Summary:\n I: -18.0 LUFS\n Peak: -1.2 dBFS\n'
        with patch.object(n, 'run_ffmpeg', return_value=summary) as runner:
            result = n.measure('fake', self.source, self.root / 'segment.log', start=3)
        self.assertEqual(result['frames'], 72000)
        self.assertIn('atrim=start_sample=72000,asetpts=PTS-STARTPTS,ebur128=peak=true', runner.call_args.args[1])

    def test_loudnorm_missing_and_silent_input_are_rejected(self):
        values = dict(input_i='-22', input_tp='-3', input_lra='3', input_thresh='-32', target_offset='0.1')
        self.assertEqual(n.parse_loudnorm(json.dumps(values))['input_i'], -22)
        for invalid in ['no measurements', json.dumps({**values, 'input_i': '-inf'})]:
            with self.assertRaises(ValueError):
                n.parse_loudnorm(invalid)

    def test_changed_source_hash_is_rejected_before_output(self):
        destination = self.root / 'case'
        with self.assertRaisesRegex(ValueError, 'SHA-256 changed'):
            n.prepare_case('not-used', self.source, self.metadata, destination, '0' * 64)
        self.assertFalse(destination.exists())
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_output_inside_source_directory_and_empty_input_rejected(self):
        cases = [(self.source, self.metadata, self.digest)]
        with self.assertRaisesRegex(ValueError, 'separate'):
            n.prepare_run('not-used', cases, self.input / 'output')
        with self.assertRaisesRegex(ValueError, 'At least one'):
            n.prepare_run('not-used', [], self.root / 'output')

    def test_ffmpeg_failure_retains_original_and_previous_candidate(self):
        output = self.root / 'output'
        previous = output / 'previous-success'
        previous.mkdir(parents=True)
        sentinel = previous / 'candidate.wav'
        sentinel.write_bytes(b'previous approved bytes')
        with patch.object(n, 'run_ffmpeg', side_effect=RuntimeError('injected encoder failure')):
            with self.assertRaisesRegex(RuntimeError, 'originals retained'):
                n.prepare_run('not-used', [(self.source, self.metadata, self.digest)], output)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(sentinel.read_bytes(), b'previous approved bytes')
        failed = list(output.glob('*.failed'))
        self.assertEqual(len(failed), 1)
        self.assertEqual(n.sha256(failed[0] / 'TEST/original.wav'), self.digest)
        self.assertEqual(list(output.glob('*.incomplete')), [])
        self.assertFalse((failed[0] / 'comparison.json').exists())
        self.assertEqual(json.loads((failed[0] / 'failure.json').read_text())['status'], 'failed_not_for_use')

    def test_ffmpeg_nonzero_exit_is_not_accepted(self):
        completed = types.SimpleNamespace(returncode=7, stderr='injected invalid codec')
        with patch.object(n.subprocess, 'run', return_value=completed):
            with self.assertRaisesRegex(RuntimeError, 'exit 7'):
                n.run_ffmpeg('fake', [], self.root / 'ffmpeg.log')
        self.assertIn('invalid codec', (self.root / 'ffmpeg.log').read_text())

    def test_second_pass_partial_output_is_quarantined(self):
        first_pass = json.dumps(dict(input_i='-22', input_tp='-3', input_lra='3',
                                     input_thresh='-32', target_offset='0.1'))
        def fail_second_pass(executable, args, log):
            if '-c:a' in args:
                Path(args[-1]).write_bytes(b'partial, not a playable WAV')
                raise RuntimeError('injected second-pass failure')
            return first_pass
        metrics = {**self.valid_metrics(), 'duration_seconds': 6}
        output = self.root / 'output'
        with patch.object(n, 'measure', return_value=metrics), \
             patch.object(n, 'run_ffmpeg', side_effect=fail_second_pass):
            with self.assertRaises(RuntimeError):
                n.prepare_run('fake', [(self.source, self.metadata, self.digest)], output)
        failed = next(output.glob('*.failed'))
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(n.sha256(failed / 'TEST/original.wav'), self.digest)
        self.assertTrue((failed / 'TEST/candidate.wav').read_bytes().startswith(b'partial'))
        self.assertFalse((failed / 'comparison.json').exists())
        self.assertEqual(len(list(output.iterdir())), 1)

    def test_final_source_check_detects_change_after_case_work(self):
        def mutation(*args):
            self.source.write_bytes(b'changed by competing writer')
            return {}
        with patch.object(n, 'prepare_case', side_effect=mutation):
            with self.assertRaisesRegex(RuntimeError, 'originals retained'):
                n.prepare_run('not-used', [(self.source, self.metadata, self.digest)], self.root / 'output')
        failure = next((self.root / 'output').glob('*.failed/failure.json'))
        self.assertIn('changed before final promotion', failure.read_text())

    def test_real_ffmpeg_two_pass_preserves_source_and_exact_frames(self):
        try:
            ffmpeg = n.find_ffmpeg()
        except ValueError as error:
            self.skipTest(str(error))
        output = n.prepare_run(ffmpeg, [(self.source, self.metadata, self.digest)], self.root / 'output')
        result = json.loads((output / 'comparison.json').read_text(encoding='utf-8'))['cases'][0]
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(n.sha256(output / 'TEST/original.wav'), self.digest)
        self.assertEqual(result['before']['frames'], result['after']['frames'])
        self.assertNotEqual(result['original_sha256'], result['candidate_sha256'])
        self.assertEqual(result['listening_acceptance'], 'not_evaluated')
        n.validate_candidate(result['before'], result['after'])


class SpeechCacheTests(unittest.TestCase):
    def test_defaults_and_all_six_parameters_change_identity(self):
        request = g.build_speech_parameters('한 박스입니다.', 'cedar')
        self.assertEqual(request, {'model': 'gpt-4o-mini-tts', 'voice': 'cedar',
                                  'input': '한 박스입니다.', 'speed': 1.0,
                                  'instructions': g.SPEECH_INSTRUCTIONS, 'response_format': 'wav'})
        baseline = g.speech_cache_fingerprint(request)
        self.assertEqual(baseline, g.speech_cache_fingerprint(dict(reversed(list(request.items())))))
        for key, value in [('model', 'different-model'), ('speed', .9), ('instructions', '또렷하게'),
                           ('input', '한 개입니다.'), ('voice', 'marin'), ('response_format', 'mp3')]:
            with self.subTest(key=key):
                self.assertNotEqual(baseline, g.speech_cache_fingerprint({**request, key: value}))
        self.assertNotEqual(g.speech_cache_fingerprint(g.build_speech_parameters('bc', 'a')),
                            g.speech_cache_fingerprint(g.build_speech_parameters('c', 'ab')))
        with self.assertRaises(ValueError):
            g.speech_cache_fingerprint({**request, 'speed': float('nan')})

    def test_actual_request_uses_hashed_parameters_and_cached_second_run(self):
        n.OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='cache-selftest-', dir=n.OUTPUT_ROOT) as temp:
            root = Path(temp)
            (root / 'data/fixtures').mkdir(parents=True)
            text = '휴지 한 개가 아니라 한 박스예요.'
            n.write_json(root / 'data/fixtures/cases.json', {'cases': [
                {'id': 'TEST', 'transcript': [{'speaker': '경영주', 'text': text}]}]})
            create = Mock(return_value=types.SimpleNamespace(read=lambda: wav_bytes([1000, -1000] * 2400)))
            client = types.SimpleNamespace(audio=types.SimpleNamespace(speech=types.SimpleNamespace(create=create)))
            budget = Mock()
            budget.reserve.return_value = 'fake-reservation'
            budget.status.return_value = {'test': True}
            fake_live = types.ModuleType('server.live')
            fake_live.demo_client = lambda: client
            fake_budget = types.ModuleType('server.budget')
            fake_budget.Budget = lambda: budget
            with patch.object(g, 'ROOT', root), patch.object(sys, 'argv', ['generate_demo_audio.py', '--generate']), \
                 patch.dict(sys.modules, {'server.live': fake_live, 'server.budget': fake_budget}), \
                 contextlib.redirect_stdout(io.StringIO()):
                g.main()
                g.main()
            request = g.build_speech_parameters(text, 'cedar')
            create.assert_called_once_with(**request)
            fingerprint = g.speech_cache_fingerprint(request)
            self.assertTrue((root / f'.local/tts-segments/TEST-0-{fingerprint}.wav').is_file())
            budget.reserve.assert_called_once()


if __name__ == '__main__':
    unittest.main()
