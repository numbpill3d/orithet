"""
Core functionality for Orithet - the generative video art tool
This file contains the main processing logic that blends all four systems:
- PulseForge (audio-reactive timing)
- EchoMosaic (semantic chaining via similarity graph)
- GlitchGarden (procedural ecosystem)
- FractalFusion (recursive overlays)
"""

import logging
import os
import random
import tempfile
from itertools import combinations
from pathlib import Path

import numpy as np

try:
    import cv2
except ImportError:  # Rendering and image analysis report a useful error later.
    cv2 = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import librosa
except ImportError:
    librosa = None

try:
    import pydub
except ImportError:
    pydub = None

try:
    from moviepy.editor import (
        VideoFileClip, ImageClip, ColorClip, CompositeVideoClip, AudioFileClip
    )
except ImportError:
    VideoFileClip = ImageClip = ColorClip = CompositeVideoClip = AudioFileClip = None

try:
    from scenedetect import detect, ContentDetector
    SCENEDETECT_AVAILABLE = True
except ImportError:
    SCENEDETECT_AVAILABLE = False


logger = logging.getLogger(__name__)


class OrithetCore:
    def __init__(self, input_folder, duration=120, chaos=0.5, seed=None,
                 resolution=(1920, 1080), style="dream"):
        self.input_folder = Path(input_folder).expanduser().resolve()
        if not self.input_folder.is_dir():
            raise ValueError(f"Input folder does not exist or is not a directory: {input_folder}")
        if duration <= 0:
            raise ValueError("duration must be greater than zero")
        if not 0.0 <= chaos <= 1.0:
            raise ValueError("chaos must be between 0.0 and 1.0")
        if len(resolution) != 2 or any(int(value) <= 0 for value in resolution):
            raise ValueError("resolution must contain two positive integers")
        if style not in {"dream", "glitch", "psychedelic", "ambient"}:
            raise ValueError(f"unknown style: {style}")

        self.duration = float(duration)
        self.chaos = chaos
        self.seed = random.randint(1, 1000000) if seed is None else int(seed)
        self.rng = random.Random(self.seed)
        self.np_rng = np.random.default_rng(self.seed)

        self.styles = {
            "dream":       {"glitch_prob": 0.1, "recursion_depth": 2, "motion_factor": 0.3},
            "glitch":      {"glitch_prob": 0.8, "recursion_depth": 3, "motion_factor": 0.7},
            "psychedelic": {"glitch_prob": 0.5, "recursion_depth": 3, "motion_factor": 0.8},
            "ambient":     {"glitch_prob": 0.05, "recursion_depth": 1, "motion_factor": 0.1},
        }
        self.style_params = self.styles.get(style, self.styles["dream"])

        self.resolution = tuple(int(value) for value in resolution)
        self.style = style
        self.clips = []
        self.creatures = []
        self.audio_paths = []
        self.similarity_graph = {}
        self.audio_info = {
            'bpm': 120,
            'energy_bands': {'low': 0.5, 'mid': 0.5, 'high': 0.5}
        }

    # -------------------------------------------------------------------------
    # Media loading
    # -------------------------------------------------------------------------

    def load_media(self):
        logger.info("loading media from %s", self.input_folder)
        # Make repeated calls safe for UI previews and notebook workflows.
        self.clips = []
        self.audio_paths = []

        supported = {
            'video': ['.mp4', '.mov', '.avi', '.mkv'],
            'audio': ['.mp3', '.wav', '.flac'],
            'image': ['.jpg', '.jpeg', '.png', '.gif'],
        }
        files = {'video': [], 'audio': [], 'image': []}

        for filepath in sorted(self.input_folder.rglob("*")):
            if not filepath.is_file():
                continue
            ext = filepath.suffix.lower()
            for category, exts in supported.items():
                if ext in exts:
                    files[category].append(str(filepath))
                    break

        self.process_videos(files['video'])
        self.audio_paths = files['audio']
        self.process_audio(files['audio'])
        self.process_images(files['image'])

        if not self.clips:
            raise ValueError(
                f"No supported media found in {self.input_folder}. "
                "Supported formats: mp4, mov, avi, mkv, jpg, jpeg, png, gif, mp3, wav, flac."
            )
        logger.info("loaded %d clips", len(self.clips))

    def process_videos(self, video_paths):
        if cv2 is None:
            logger.warning("opencv-python is not installed; skipping video inputs")
            return
        for video_path in video_paths:
            try:
                cap = cv2.VideoCapture(video_path)
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.release()

                scenes = self.detect_scenes(video_path)

                for start_frame, end_frame in scenes:
                    clip_duration = (end_frame - start_frame) / fps if fps > 0 else 0
                    if 1 <= clip_duration <= 15:
                        self.clips.append({
                            'path': video_path,
                            'type': 'video',
                            'start_frame': start_frame,
                            'end_frame': end_frame,
                            'duration': clip_duration,
                            'fps': fps,
                            'metadata': self.extract_clip_metadata(video_path, start_frame, end_frame),
                        })
            except Exception as e:
                logger.warning("error processing video %s: %s", video_path, e)

    def detect_scenes(self, video_path):
        if cv2 is None:
            return []
        if SCENEDETECT_AVAILABLE:
            try:
                scene_list = detect(video_path, ContentDetector())
                if scene_list:
                    return [(s.get_frames(), e.get_frames()) for s, e in scene_list]
            except Exception:
                pass

        # fallback: fixed 5-second segments
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

        if fps == 0:
            return [(0, frame_count)]

        segment_length = max(1, int(fps * 5))
        return [(i, min(i + segment_length, frame_count))
                for i in range(0, frame_count, segment_length)]

    def process_audio(self, audio_paths):
        if not audio_paths or pydub is None or librosa is None:
            if audio_paths:
                logger.warning("audio analysis unavailable; install pydub and librosa to analyze audio")
            return

        combined_audio = None
        for audio_path in audio_paths:
            try:
                audio = pydub.AudioSegment.from_file(audio_path)
                combined_audio = audio if combined_audio is None else combined_audio + audio
            except Exception as e:
                logger.warning("error processing audio %s: %s", audio_path, e)

        if combined_audio is None:
            return

        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                tmp_path = tmp.name
            combined_audio.export(tmp_path, format="wav")

            y, sr = librosa.load(tmp_path)
            os.unlink(tmp_path)

            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

            stft = librosa.stft(y)
            magnitude = np.abs(stft)
            freqs = librosa.fft_frequencies(sr=sr)

            low_mask  = freqs < 500
            mid_mask  = (freqs >= 500) & (freqs < 3000)
            high_mask = freqs >= 3000

            self.audio_info = {
                'bpm': float(tempo),
                'energy_bands': {
                    'low':  float(np.mean(magnitude[low_mask]))  if low_mask.any()  else 0.5,
                    'mid':  float(np.mean(magnitude[mid_mask]))  if mid_mask.any()  else 0.5,
                    'high': float(np.mean(magnitude[high_mask])) if high_mask.any() else 0.5,
                }
            }
            logger.info("audio: %.1f bpm", self.audio_info['bpm'])
        except Exception as e:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            logger.warning("audio analysis failed: %s", e)

    def process_images(self, image_paths):
        if Image is None:
            logger.warning("pillow is not installed; skipping image inputs")
            return
        for image_path in image_paths:
            try:
                with Image.open(image_path) as img:
                    w, h = img.size
                duration = max(2, min(15, w * h // 100000))
                self.clips.append({
                    'path': image_path,
                    'type': 'image',
                    'duration': duration,
                    'metadata': self.extract_clip_metadata(image_path),
                })
            except Exception as e:
                logger.warning("error processing image %s: %s", image_path, e)

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------

    def extract_clip_metadata(self, path, start_frame=None, end_frame=None):
        metadata = {'avg_color': [128, 128, 128], 'motion_energy': 0, 'dominant_hue': 0}
        _, ext = os.path.splitext(path.lower())

        if ext in ('.mp4', '.mov', '.avi', '.mkv'):
            if cv2 is None:
                return metadata
            try:
                cap = cv2.VideoCapture(path)
                if start_frame is not None:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

                frame_count = 0
                color_sum = np.zeros(3)
                motion_sum = 0.0
                prev_gray = None
                last_frame = None

                while frame_count < 10:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    # Metadata does not need source resolution. Keep analysis
                    # bounded so portrait/4K media cannot stall the pipeline.
                    height, width = frame.shape[:2]
                    max_dimension = 320
                    if max(height, width) > max_dimension:
                        scale = max_dimension / max(height, width)
                        analysis_frame = cv2.resize(
                            frame, (max(1, int(width * scale)), max(1, int(height * scale)))
                        )
                    else:
                        analysis_frame = frame
                    last_frame = analysis_frame
                    gray = cv2.cvtColor(analysis_frame, cv2.COLOR_BGR2GRAY)
                    if prev_gray is not None:
                        flow = cv2.calcOpticalFlowFarneback(
                            prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
                        )
                        motion_sum += float(np.mean(np.abs(flow)))
                    color_sum += np.mean(analysis_frame, axis=(0, 1))
                    prev_gray = gray
                    frame_count += 1

                cap.release()

                if frame_count > 0:
                    metadata['avg_color'] = (color_sum / frame_count).tolist()
                    metadata['motion_energy'] = motion_sum / frame_count
                if last_frame is not None:
                    metadata['dominant_hue'] = self.get_dominant_hue(last_frame)
            except Exception:
                pass

        elif ext in ('.jpg', '.jpeg', '.png', '.gif'):
            if Image is None:
                return metadata
            try:
                with Image.open(path) as img:
                    arr = np.array(img.convert('RGB'))
                metadata['avg_color'] = np.mean(arr, axis=(0, 1)).tolist()
                metadata['dominant_hue'] = self.get_dominant_hue(arr)
            except Exception:
                pass

        return metadata

    def get_dominant_hue(self, img_array):
        try:
            if cv2 is None or not isinstance(img_array, np.ndarray) or img_array.ndim != 3:
                return 0
            if img_array.shape[2] >= 3:
                img_array = img_array[:, :, :3]
                hsv = cv2.cvtColor(img_array.astype(np.uint8), cv2.COLOR_RGB2HSV)
                hue_hist = cv2.calcHist([hsv], [0], None, [180], [0, 180])
                return int(np.argmax(hue_hist))
        except Exception:
            pass
        return 0

    # -------------------------------------------------------------------------
    # EchoMosaic: similarity graph
    # -------------------------------------------------------------------------

    def build_similarity_graph(self):
        logger.info("building similarity graph...")
        n = len(self.clips)
        self.similarity_graph = {}
        for i in range(n):
            self.similarity_graph[i] = []
            for j in range(n):
                if i != j:
                    sim = self.calculate_similarity(self.clips[i], self.clips[j])
                    if sim > 0.3:
                        self.similarity_graph[i].append((j, sim))

    def calculate_similarity(self, clip1, clip2):
        m1, m2 = clip1['metadata'], clip2['metadata']
        color_sim = 1.0 / (1.0 + np.linalg.norm(
            np.array(m1['avg_color']) - np.array(m2['avg_color'])
        ))
        motion_sim = 1.0 / (1.0 + abs(m1['motion_energy'] - m2['motion_energy']))
        return 0.6 * color_sim + 0.4 * motion_sim

    # -------------------------------------------------------------------------
    # GlitchGarden: ecosystem simulation
    # -------------------------------------------------------------------------

    def create_ecosystem_simulation(self):
        logger.info("creating ecosystem simulation...")
        self.creatures = []
        for i, clip in enumerate(self.clips):
            self.creatures.append({
                'id': i,
                'clip': clip,
                'position': [self.rng.uniform(0, 30), self.rng.uniform(0, 30)],
                'velocity': [self.rng.uniform(-0.5, 0.5), self.rng.uniform(-0.5, 0.5)],
                'age': 0,
                'effects': [],
                'mutation_rate': self.chaos * 0.1,
            })

        for step in range(100):
            self.update_creatures(step)

    def update_creatures(self, step):
        for c in self.creatures:
            c['position'][0] = max(0, min(30, c['position'][0] + c['velocity'][0] + self.rng.uniform(-0.1, 0.1)))
            c['position'][1] = max(0, min(30, c['position'][1] + c['velocity'][1] + self.rng.uniform(-0.1, 0.1)))
            c['age'] += 1

        # Interactions can fuse and remove creatures. Iterate a snapshot so a
        # removal cannot invalidate the live list's numeric indices mid-step.
        for c1, c2 in combinations(list(self.creatures), 2):
            if not any(creature is c1 for creature in self.creatures):
                continue
            if not any(creature is c2 for creature in self.creatures):
                continue
            dx = c1['position'][0] - c2['position'][0]
            dy = c1['position'][1] - c2['position'][1]
            if (dx * dx + dy * dy) < 4.0:
                self.handle_creature_interaction(c1, c2, step)

    def handle_creature_interaction(self, c1, c2, step):
        color_sim = self.color_similarity(
            c1['clip']['metadata']['avg_color'],
            c2['clip']['metadata']['avg_color']
        )

        if color_sim > 0.7 and self.rng.random() < 0.3:
            self.fuse_creatures(c1, c2)

        if (c1['clip']['metadata']['motion_energy'] > 0.5 or
                c2['clip']['metadata']['motion_energy'] > 0.5):
            if self.rng.random() < self.style_params['glitch_prob']:
                self.apply_glitch_effect(c1)
                self.apply_glitch_effect(c2)

        if self.rng.random() < c1['mutation_rate']:
            self.mutate_creature(c1)
        if self.rng.random() < c2['mutation_rate']:
            self.mutate_creature(c2)

    def color_similarity(self, c1, c2):
        return 1.0 / (1.0 + np.linalg.norm(np.array(c1) - np.array(c2)) / 255.0)

    def fuse_creatures(self, c1, c2):
        idx1 = next((index for index, creature in enumerate(self.creatures)
                     if creature is c1), None)
        if idx1 is None or not any(creature is c2 for creature in self.creatures):
            return
        avg_color = [(a + b) / 2 for a, b in zip(
            c1['clip']['metadata']['avg_color'],
            c2['clip']['metadata']['avg_color']
        )]
        fused_meta = {
            'avg_color': avg_color,
            'motion_energy': (c1['clip']['metadata']['motion_energy'] +
                              c2['clip']['metadata']['motion_energy']) / 2,
            'dominant_hue': (c1['clip']['metadata']['dominant_hue'] +
                             c2['clip']['metadata']['dominant_hue']) / 2,
        }
        fused = {
            'id': f"{c1['id']}-{c2['id']}",
            'clip': {
                'path': c1['clip']['path'],
                'type': c1['clip']['type'],
                'start_frame': c1['clip'].get('start_frame'),
                'end_frame': c1['clip'].get('end_frame'),
                'fps': c1['clip'].get('fps', 30),
                'duration': (c1['clip']['duration'] + c2['clip']['duration']) / 2,
                'metadata': fused_meta,
            },
            'position': [
                (c1['position'][0] + c2['position'][0]) / 2,
                (c1['position'][1] + c2['position'][1]) / 2,
            ],
            'velocity': [
                (c1['velocity'][0] + c2['velocity'][0]) / 2,
                (c1['velocity'][1] + c2['velocity'][1]) / 2,
            ],
            'age': max(c1['age'], c2['age']),
            'effects': list(set(c1['effects'] + c2['effects'])),
            'mutation_rate': (c1['mutation_rate'] + c2['mutation_rate']) / 2,
        }
        # replace c1 with fused, mark c2 for removal
        self.creatures[idx1] = fused
        self.creatures[:] = [creature for creature in self.creatures if creature is not c2]

    def apply_glitch_effect(self, creature):
        effect = self.rng.choice(['pixel_sort', 'datamosh', 'rgb_shift', 'mirror'])
        if effect not in creature['effects']:
            creature['effects'].append(effect)

    def mutate_creature(self, creature):
        if self.rng.random() < 0.5:
            color = creature['clip']['metadata']['avg_color']
            creature['clip']['metadata']['avg_color'] = [
                max(0, min(255, c + self.rng.randint(-20, 20))) for c in color
            ]
        if self.rng.random() < 0.3:
            me = creature['clip']['metadata']['motion_energy']
            creature['clip']['metadata']['motion_energy'] = max(0, min(1, me + self.rng.uniform(-0.1, 0.1)))

    # -------------------------------------------------------------------------
    # GlitchGarden: frame-level effects
    # -------------------------------------------------------------------------

    def _rgb_shift(self, frame):
        if frame.ndim != 3 or frame.shape[1] < 2:
            return frame
        shift = max(2, int(self.chaos * 12))
        shift = min(shift, frame.shape[1] - 1)
        result = frame.copy()
        result[:, shift:, 0] = frame[:, :-shift, 0]
        result[:, :-shift, 2] = frame[:, shift:, 2]
        return result

    def _mirror(self, frame):
        if frame.ndim != 3 or frame.shape[1] < 2:
            return frame
        result = frame.copy()
        half = frame.shape[1] // 2
        result[:, half:] = frame[:, :half][:, ::-1]
        return result

    def _pixel_sort(self, frame):
        if cv2 is None or frame.ndim != 3 or frame.shape[0] == 0:
            return frame
        result = frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        for i in range(0, frame.shape[0], 3):
            idx = np.argsort(gray[i])
            result[i] = frame[i][idx]
        return result

    def _datamosh(self, frame):
        if cv2 is None or frame.ndim != 3 or frame.shape[0] == 0:
            return frame
        shift = max(8, int(self.chaos * 20))
        shifted = np.roll(frame, shift, axis=0)
        return cv2.addWeighted(frame, 0.75, shifted.astype(np.uint8), 0.25, 0)

    def apply_effects_to_clip(self, clip, effects):
        effect_fns = {
            'rgb_shift':  self._rgb_shift,
            'mirror':     self._mirror,
            'pixel_sort': self._pixel_sort,
            'datamosh':   self._datamosh,
        }
        for effect in effects:
            fn = effect_fns.get(effect)
            if fn:
                def safe_effect(frame, effect_name=effect, effect_fn=fn):
                    try:
                        return effect_fn(frame)
                    except (IndexError, ValueError, TypeError) as exc:
                        logger.warning("skipping %s effect for malformed frame: %s", effect_name, exc)
                        return frame

                clip = clip.fl_image(safe_effect)
        return clip

    # -------------------------------------------------------------------------
    # PulseForge: beat-snapped timeline
    # -------------------------------------------------------------------------

    def generate_timeline(self):
        logger.info("generating timeline...")
        bpm = self.audio_info.get('bpm', 120)
        beat_interval = 60.0 / max(bpm, 1)

        sorted_creatures = sorted(self.creatures, key=lambda c: (c['age'], c['position'][0]))

        timeline_clips = []
        current_time = 0.0

        index = 0
        while current_time < self.duration and sorted_creatures:
            creature = sorted_creatures[index % len(sorted_creatures)]
            index += 1

            clip = creature['clip']
            raw_duration = min(
                clip['duration'] * (0.8 + self.chaos * 0.4),
                self.duration - current_time,
            )

            # snap to beat grid
            beats = max(1, round(raw_duration / beat_interval))
            snapped_duration = beats * beat_interval

            clip['effects'] = creature.get('effects', [])
            timed = self.create_timed_clip(clip, current_time, snapped_duration)
            if timed is not None:
                timeline_clips.append(timed)

            current_time += snapped_duration

            # FractalFusion: spawn recursive overlays ~10% of the time at beat boundaries
            if self.rng.random() < 0.1:
                self.add_recursive_overlays(timeline_clips, current_time)

        return timeline_clips

    def create_timed_clip(self, clip, start_time, duration):
        try:
            if any(dep is None for dep in (VideoFileClip, ImageClip, ColorClip)):
                raise RuntimeError("moviepy is not installed; install project requirements to render")
            if clip['type'] == 'video':
                fps = clip.get('fps', 30)
                t_start = clip['start_frame'] / fps
                t_end = clip['end_frame'] / fps
                mc = (VideoFileClip(clip['path'])
                      .subclip(t_start, t_end)
                      .set_start(start_time)
                      .set_duration(duration))
            elif clip['type'] == 'image':
                mc = (ImageClip(clip['path'])
                      .set_duration(duration)
                      .set_start(start_time))
            else:
                color = [int(c) for c in clip['metadata'].get('avg_color', [100, 100, 100])[:3]]
                mc = (ColorClip(size=self.resolution, color=color, duration=duration)
                      .set_start(start_time))

            effects = clip.get('effects', [])
            if effects:
                mc = self.apply_effects_to_clip(mc, effects)

            return {
                'clip': clip,
                'start_time': start_time,
                'duration': duration,
                'moviepy_clip': mc,
            }
        except Exception as e:
            logger.warning("error creating clip from %s: %s", clip.get('path', '?'), e)
            return None

    # -------------------------------------------------------------------------
    # FractalFusion: recursive PiP overlays
    # -------------------------------------------------------------------------

    def add_recursive_overlays(self, timeline_clips, time_point):
        depth = self.style_params['recursion_depth']
        if not timeline_clips or depth == 0:
            return

        w, h = self.resolution
        corners = [(0, 0), (w // 2, 0), (0, h // 2), (w // 2, h // 2)]

        sources = timeline_clips[-min(depth, len(timeline_clips)):]

        for d, source in enumerate(sources[:depth], 1):
            mc = source.get('moviepy_clip')
            if mc is None:
                continue

            scale = 0.5 ** d
            ow = max(64, int(w * scale * 0.5))
            oh = max(36, int(h * scale * 0.5))
            pos = corners[d % 4]
            overlay_dur = max(0.1, min(2.0 / d, mc.duration))
            opacity = max(0.15, 0.6 / d)

            try:
                overlay = (mc
                           .subclip(0, overlay_dur)
                           .resize((ow, oh))
                           .set_start(time_point)
                           .set_position(pos)
                           .set_opacity(opacity))
                timeline_clips.append({
                    'clip': source['clip'],
                    'start_time': time_point,
                    'duration': overlay_dur,
                    'moviepy_clip': overlay,
                })
            except Exception as e:
                logger.warning("fractalfusion overlay failed at depth %d: %s", d, e)

    # -------------------------------------------------------------------------
    # Render
    # -------------------------------------------------------------------------

    def render_video(self, output_path):
        logger.info("rendering final video...")
        timeline_clips = self.generate_timeline()

        moviepy_clips = [tc['moviepy_clip'] for tc in timeline_clips
                         if tc.get('moviepy_clip') is not None]

        if not moviepy_clips:
            raise RuntimeError("No valid clips could be created from the input media")

        moviepy_clips.sort(key=lambda c: c.start)

        final = None
        soundtrack = None
        try:
            final = CompositeVideoClip(moviepy_clips, size=self.resolution)
            final = final.set_duration(self.duration)
            if self.audio_paths and AudioFileClip is not None:
                try:
                    soundtrack = AudioFileClip(self.audio_paths[0])
                    if soundtrack.duration > self.duration:
                        soundtrack = soundtrack.subclip(0, self.duration)
                    final = final.set_audio(soundtrack)
                except Exception as exc:
                    logger.warning("could not attach soundtrack: %s", exc)
            Path(output_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="orithet-render-") as temp_dir:
                final.write_videofile(
                    output_path,
                    fps=30,
                    codec='libx264',
                    audio_codec='aac',
                    temp_audiofile=str(Path(temp_dir) / 'audio.m4a'),
                    remove_temp=True,
                )
        finally:
            if soundtrack is not None:
                try:
                    soundtrack.close()
                except Exception:
                    logger.debug("soundtrack cleanup failed", exc_info=True)
            if final is not None:
                try:
                    final.close()
                except Exception:
                    logger.debug("final clip cleanup failed", exc_info=True)
        logger.info("rendered to %s", output_path)

    # -------------------------------------------------------------------------
    # Entry point
    # -------------------------------------------------------------------------

    def run(self, output_path=None):
        logger.info("starting orithet...")
        if output_path is None:
            output_path = f"orithet_output_{self.seed}.mp4"

        self.load_media()
        self.build_similarity_graph()
        self.create_ecosystem_simulation()
        self.render_video(output_path)

        logger.info("done")
        return output_path
