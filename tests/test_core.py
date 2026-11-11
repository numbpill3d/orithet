import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from orithet.core import OrithetCore


class FakeMoviePyClip:
    def __init__(self, *args, **kwargs):
        self.duration = kwargs.get("duration", 2)
        self.start = 0

    def set_duration(self, duration):
        self.duration = duration
        return self

    def set_start(self, start):
        self.start = start
        return self


class OrithetCoreTests(unittest.TestCase):
    def make_engine(self, folder, **kwargs):
        return OrithetCore(folder, duration=4, resolution=(320, 180), **kwargs)

    def test_seed_zero_is_preserved_and_validation_is_centralized(self):
        with tempfile.TemporaryDirectory() as folder:
            engine = self.make_engine(folder, seed=0)
            self.assertEqual(engine.seed, 0)
            with self.assertRaises(ValueError):
                OrithetCore(folder, duration=0)
            with self.assertRaises(ValueError):
                OrithetCore(folder, chaos=1.1)

    def test_media_discovery_is_recursive_and_deterministic(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "nested").mkdir()
            Image.new("RGB", (20, 20), "red").save(root / "z.png")
            Image.new("RGB", (20, 20), "blue").save(root / "nested" / "a.png")

            engine = self.make_engine(folder, seed=12)
            engine.load_media()

            self.assertEqual(
                [Path(clip["path"]).name for clip in engine.clips], ["a.png", "z.png"]
            )

    def test_timeline_repeats_sources_to_target_duration(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            Image.new("RGB", (20, 20), "red").save(root / "one.png")
            engine = self.make_engine(folder, seed=7)
            engine.load_media()
            engine.create_ecosystem_simulation()
            with patch("orithet.core.VideoFileClip", FakeMoviePyClip), \
                    patch("orithet.core.ImageClip", FakeMoviePyClip), \
                    patch("orithet.core.ColorClip", FakeMoviePyClip):
                timeline = engine.generate_timeline()

            self.assertGreater(len(timeline), 1)
            self.assertLessEqual(
                max(item["start_time"] + item["duration"] for item in timeline),
                engine.duration + 1e-6,
            )


if __name__ == "__main__":
    unittest.main()
