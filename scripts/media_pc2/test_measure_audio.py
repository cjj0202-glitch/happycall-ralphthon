"""Analytic PCM controls; no project media writes or network access."""
from array import array
import math
from pathlib import Path
import tempfile
import unittest
import wave

from measure_audio import dbfs, load_pcm, metrics


class PcmMeasurementTests(unittest.TestCase):
    def test_known_half_scale_signal(self):
        shape = {"sample_rate_hz": 1000, "channels": 1, "frames": 40, "duration_seconds": .04}
        result = metrics(shape, array("h", [16384, -16384] * 20))
        self.assertAlmostEqual(result["rms_dbfs"], -6.020599913279624)
        self.assertEqual(result["sample_peak_dbfs"], result["rms_dbfs"])
        self.assertEqual(result["digital_rail_samples"], 0)
        self.assertEqual(result["quiet_20ms_windows"], 0)

    def test_digital_silence_is_not_finite_loudness(self):
        shape = {"sample_rate_hz": 1000, "channels": 1, "frames": 41, "duration_seconds": .041}
        result = metrics(shape, array("h", [0] * 41))
        self.assertIsNone(result["rms_dbfs"])
        self.assertIsNone(dbfs(0))
        self.assertEqual(result["exact_zero_percent"], 100)
        self.assertEqual(result["quiet_20ms_windows"], 2)
        self.assertEqual(result["complete_20ms_windows"], 2)
        self.assertEqual(result["excluded_tail_frames"], 1)

    def test_both_pcm_rails_are_counted(self):
        shape = {"sample_rate_hz": 1000, "channels": 1, "frames": 4, "duration_seconds": .004}
        result = metrics(shape, array("h", [-32768, 32767, -32767, 0]))
        self.assertEqual(result["digital_rail_samples"], 2)
        self.assertEqual(result["sample_peak_dbfs"], 0)
        self.assertEqual(result["sample_count"], 4)

    def test_stereo_segments_count_frames_and_samples_separately(self):
        shape = {"sample_rate_hz": 1000, "channels": 2, "frames": 100, "duration_seconds": .1}
        result = metrics(shape, array("h", [16384, 0] * 100), .02, .06)
        self.assertEqual(result["frames"], 40)
        self.assertEqual(result["sample_count"], 80)
        self.assertAlmostEqual(result["rms_dbfs"], 20 * math.log10(.5 / math.sqrt(2)))

    def test_invalid_segment_boundaries_rejected(self):
        shape = {"sample_rate_hz": 1000, "channels": 1, "frames": 100, "duration_seconds": .1}
        for start, end in [(-.1, .1), (0, .11), (.1, .1), (.09, .02), (math.nan, .1), (0, math.inf), (0, .0001)]:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                metrics(shape, array("h", [1] * 100), start, end)

    def test_truncated_pcm_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "truncated.wav"
            with wave.open(str(path), "wb") as writer:
                writer.setnchannels(1)
                writer.setsampwidth(2)
                writer.setframerate(1000)
                writer.writeframes(array("h", [12] * 100).tobytes())
            path.write_bytes(path.read_bytes()[:-2])
            with self.assertRaisesRegex(ValueError, "Truncated"):
                load_pcm(path)

    def test_unsupported_empty_and_8bit_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for width, raw in [(2, b""), (1, b"\x80" * 10)]:
                path = Path(directory) / f"{width}.wav"
                with wave.open(str(path), "wb") as writer:
                    writer.setnchannels(1)
                    writer.setsampwidth(width)
                    writer.setframerate(1000)
                    writer.writeframes(raw)
                with self.assertRaises(ValueError):
                    load_pcm(path)


if __name__ == "__main__":
    unittest.main()
