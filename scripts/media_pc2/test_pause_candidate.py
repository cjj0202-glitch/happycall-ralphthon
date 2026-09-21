from array import array
import unittest
from make_pause_candidate import insert_silence


class PauseCandidateTests(unittest.TestCase):
    def test_exact_recovery_and_no_source_mutation(self):
        original = array('h', [-32768, -600, 0, 0, 0, 0, 700, 32767])
        before = original.tobytes()
        result = insert_silence(original, 4, 3, 2)
        self.assertEqual(result[:4]+result[7:], original)
        self.assertEqual(result[4:7], array('h', [0, 0, 0]))
        self.assertEqual(original.tobytes(), before)

    def test_non_silent_boundary_rejected(self):
        with self.assertRaises(ValueError):
            insert_silence(array('h', [0, 0, 1, 0, 0, 0]), 3, 2, 2)

    def test_tail_boundary_rejected(self):
        with self.assertRaises(ValueError):
            insert_silence(array('h', [0]*10), 9, 2, 2)

    def test_zero_negative_and_empty_edits_rejected(self):
        for amount in [0, -1]:
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                insert_silence(array('h', [0]*10), 5, amount, 2)

    def test_zero_guard_rejected(self):
        with self.assertRaises(ValueError):
            insert_silence(array('h', [1]*10), 5, 2, 0)

    def test_wrong_pcm_format_rejected(self):
        with self.assertRaises(ValueError):
            insert_silence(array('i', [0]*10), 5, 2, 2)


if __name__ == '__main__':
    unittest.main()
