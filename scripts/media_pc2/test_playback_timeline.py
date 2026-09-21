import unittest
from prepare_playback import map_interval


class FrameTimelineTests(unittest.TestCase):
    def test_before_and_touching_end(self):
        self.assertEqual(map_interval(0,10,10,2),(0,10))

    def test_after_and_touching_start(self):
        self.assertEqual(map_interval(10,20,10,2),(12,22))

    def test_crossing_gets_end_shift_only(self):
        self.assertEqual(map_interval(5,15,10,2),(5,17))

    def test_invalid_interval(self):
        for a,b in [(5,5),(6,5),(-1,2)]:
            with self.subTest(a=a,b=b), self.assertRaises(ValueError):
                map_interval(a,b,10,2)


if __name__=='__main__':
    unittest.main()
