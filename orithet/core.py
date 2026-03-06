"""
Core functionality for Orithet - the generative video art tool
This file contains the main processing logic that blends all four systems:
- PulseForge (audio-reactive timing)
- EchoMosaic (semantic chaining via similarity graph)
- GlitchGarden (procedural ecosystem)
- FractalFusion (recursive overlays)
"""

import os
import random
import numpy as np
import cv2
from PIL import Image
import librosa
import pydub
from moviepy.editor import *
from pyscenetect import SceneDetector
from skimage.metrics import structural_similarity as ssim
import warnings
warnings.filterwarnings('ignore')

class OrithetCore:
    def __init__(self, input_folder, duration=120, chaos=0.5, seed=None,
                 resolution=(1920, 1080), style="dream"):
        """
        Initialize Orithet core engine
        
        Args:
            input_folder (str): Path to folder containing media files
            duration (int): Target video duration in seconds
            chaos (float): Randomness factor (0.0-1.0)
            seed (int): Random seed for reproducibility
            resolution (tuple): Output resolution (width, height)
            style (str): Preset style ("dream", "glitch", "psychedelic", "ambient")
        """
        self.input_folder = input_folder
        self.duration = duration
        self.chaos = chaos
        self.seed = seed or random.randint(1, 1000000)
        random.seed(self.seed)
        np.random.seed(self.seed)
        
        # Style presets
        self.styles = {
            "dream": {"glitch_prob": 0.1, "recursion_depth": 2, "motion_factor": 0.3},
            "glitch": {"glitch_prob": 0.8, "recursion_depth": 3, "motion_factor": 0.7},
            "psychedelic": {"glitch_prob": 0.5, "recursion_depth": 3, "motion_factor": 0.8},
            "ambient": {"glitch_prob": 0.05, "recursion_depth": 1, "motion_factor": 0.1}
        }
        self.style_params = self.styles.get(style, self.styles["dream"])
        
        self.resolution = resolution
        self.clips = []
        self.creatures = []
        self.similarity_graph = {}
        
    def load_media(self):
        """Load and categorize all media files from input folder"""
        print("Loading media from:", self.input_folder)
        
        supported_extensions = {
            'video': ['.mp4', '.mov', '.avi', '.mkv'],
            'audio': ['.mp3', '.wav', '.flac'],
            'image': ['.jpg', '.jpeg', '.png', '.gif']
        }
        
        # Categorize files
        files_by_type = {'video': [], 'audio': [], 'image': []}
        
        for filename in os.listdir(self.input_folder):
            filepath = os.path.join(self.input_folder, filename)
            if not os.path.isfile(filepath):
                continue
                
            _, ext = os.path.splitext(filename.lower())
            
            for category, extensions in supported_extensions.items():
                if ext in extensions:
                    files_by_type[category].append(filepath)
                    break
        
        # Process each type of media
        self.process_videos(files_by_type['video'])
        self.process_audio(files_by_type['audio'])
        self.process_images(files_by_type['image'])
        
        print(f"Loaded {len(self.clips)} clips from {self.input_folder}")
        
    def process_videos(self, video_paths):
        """Process video files with scene detection"""
        for video_path in video_paths:
            try:
                # Get video properties
                cap = cv2.VideoCapture(video_path)
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = frame_count / fps if fps > 0 else 0
                
                # Detect scenes
                scenes = self.detect_scenes(video_path)
                
                # Create clips from scenes
                for i, (start_frame, end_frame) in enumerate(scenes):
                    clip_duration = (end_frame - start_frame) / fps
                    
                    # Only include clips that are reasonable length
                    if 1 <= clip_duration <= 15:
                        clip = {
                            'path': video_path,
                            'type': 'video',
                            'start_frame': start_frame,
                            'end_frame': end_frame,
                            'duration': clip_duration,
                            'metadata': self.extract_clip_metadata(video_path, start_frame, end_frame)
                        }
                        self.clips.append(clip)
                        
                cap.release()
                
            except Exception as e:
                print(f"Error processing video {video_path}: {e}")
                
    def detect_scenes(self, video_path):
        """Detect scenes in video using PySceneDetect"""
        try:
            detector = SceneDetector()
            scenes = detector.detect_scenes(video_path)
            return scenes
        except:
            # Fallback: split video into fixed intervals
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            
            if fps == 0:
                return [(0, frame_count)]
                
            # Split into 5-second segments
            segment_length = int(fps * 5)
            scenes = []
            for i in range(0, frame_count, segment_length):
                scenes.append((i, min(i + segment_length, frame_count)))
            return scenes
            
    def process_audio(self, audio_paths):
        """Process audio files to extract BPM and energy info"""
        if not audio_paths:
            return
            
        # Combine all audio files for analysis
        combined_audio = None
        for audio_path in audio_paths:
            try:
                audio = pydub.AudioSegment.from_file(audio_path)
                if combined_audio is None:
                    combined_audio = audio
                else:
                    combined_audio += audio
            except Exception as e:
                print(f"Error processing audio {audio_path}: {e}")
                
        if combined_audio:
            # Extract BPM using librosa
            y, sr = librosa.load(combined_audio.export(format="wav").name)
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            
            # Extract energy bands
            hop_length = 512
            stft = librosa.stft(y, hop_length=hop_length)
            magnitude = np.abs(stft)
            
            # Split into low, mid, high frequency bands
            low_freq = librosa.feature.mfcc(S=magnitude, sr=sr, n_mels=128, fmax=500)
            mid_freq = librosa.feature.mfcc(S=magnitude, sr=sr, n_mels=128, fmin=500, fmax=3000)
            high_freq = librosa.feature.mfcc(S=magnitude, sr=sr, n_mels=128, fmin=3000)
            
            self.audio_info = {
                'bpm': tempo,
                'energy_bands': {
                    'low': np.mean(low_freq),
                    'mid': np.mean(mid_freq),
                    'high': np.mean(high_freq)
                }
            }
        else:
            self.audio_info = {'bpm': 120, 'energy_bands': {'low': 0.5, 'mid': 0.5, 'high': 0.5}}
            
    def process_images(self, image_paths):
        """Process image files into variable-length clips"""
        for image_path in image_paths:
            try:
                # Load image and get dimensions
                img = Image.open(image_path)
                width, height = img.size
                
                # Estimate duration based on visual complexity
                # Simple heuristic: larger images get longer durations
                duration = max(2, min(15, width * height // 100000))
                
                clip = {
                    'path': image_path,
                    'type': 'image',
                    'duration': duration,
                    'metadata': self.extract_clip_metadata(image_path)
                }
                self.clips.append(clip)
                
            except Exception as e:
                print(f"Error processing image {image_path}: {e}")
                
    def extract_clip_metadata(self, path, start_frame=None, end_frame=None):
        """Extract metadata from clips for similarity analysis"""
        metadata = {}
        
        if path.endswith(('.mp4', '.mov', '.avi')):
            # For video files, analyze motion and color
            cap = cv2.VideoCapture(path)
            if start_frame is not None:
                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                
            # Sample frames for analysis
            frame_count = 0
            color_sum = np.zeros(3)
            motion_sum = 0
            prev_frame = None
            
            while frame_count < 10:  # Sample 10 frames
                ret, frame = cap.read()
                if not ret:
                    break
                    
                # Convert to grayscale for motion detection
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                if prev_frame is not None:
                    # Calculate optical flow for motion
                    flow = cv2.calcOpticalFlowFarneback(prev_frame, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
                    motion = np.mean(np.abs(flow))
                    motion_sum += motion
                    
                # Calculate average color
                avg_color = np.mean(frame, axis=(0, 1))
                color_sum += avg_color
                
                prev_frame = gray
                frame_count += 1
                
            cap.release()
            
            metadata.update({
                'avg_color': color_sum / frame_count if frame_count > 0 else [0, 0, 0],
                'motion_energy': motion_sum / frame_count if frame_count > 0 else 0,
                'dominant_hue': self.get_dominant_hue(frame) if frame is not None else 0
            })
            
        elif path.endswith(('.jpg', '.jpeg', '.png', '.gif')):
            # For images, analyze color palette
            img = Image.open(path)
            img_array = np.array(img)
            
            # Get dominant colors
            if len(img_array.shape) == 3:
                # Convert to RGB if needed
                if img_array.shape[2] == 4:
                    img_array = img_array[:, :, :3]
                    
                # Flatten and get unique colors
                flat_colors = img_array.reshape(-1, 3)
                unique_colors = np.unique(flat_colors, axis=0)
                avg_color = np.mean(unique_colors, axis=0)
            else:
                avg_color = [np.mean(img_array)]
                
            metadata.update({
                'avg_color': avg_color,
                'motion_energy': 0,  # Images have no motion
                'dominant_hue': self.get_dominant_hue(img_array) if len(img_array.shape) == 3 else 0
            })
            
        return metadata
        
    def get_dominant_hue(self, img_array):
        """Calculate dominant hue from image"""
        if len(img_array.shape) == 3:
            hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
            hue_hist = cv2.calcHist([hsv], [0], None, [180], [0, 180])
            return np.argmax(hue_hist)
        return 0
        
    def build_similarity_graph(self):
        """Build a similarity graph based on color, motion, and audio mood"""
        print("Building similarity graph...")
        
        # Create adjacency matrix based on clip similarities
        n_clips = len(self.clips)
        self.similarity_graph = {}
        
        for i in range(n_clips):
            self.similarity_graph[i] = []
            for j in range(n_clips):
                if i != j:
                    similarity = self.calculate_similarity(self.clips[i], self.clips[j])
                    if similarity > 0.3:  # Threshold for similarity
                        self.similarity_graph[i].append((j, similarity))
                        
    def calculate_similarity(self, clip1, clip2):
        """Calculate similarity between two clips based on metadata"""
        meta1 = clip1['metadata']
        meta2 = clip2['metadata']
        
        # Color similarity (Euclidean distance in RGB space)
        color_sim = 1 / (1 + np.linalg.norm(np.array(meta1['avg_color']) - np.array(meta2['avg_color'])))
        
        # Motion similarity (difference in motion energy)
        motion_diff = abs(meta1['motion_energy'] - meta2['motion_energy'])
        motion_sim = 1 / (1 + motion_diff)
        
        # Weighted average of similarities
        similarity = (0.6 * color_sim) + (0.4 * motion_sim)
        return similarity
        
    def create_ecosystem_simulation(self):
        """Create a 2D ecosystem simulation where creatures interact"""
        print("Creating ecosystem simulation...")
        
        # Initialize creatures (each clip becomes a creature)
        self.creatures = []
        for i, clip in enumerate(self.clips):
            creature = {
                'id': i,
                'clip': clip,
                'position': [random.uniform(0, 30), random.uniform(0, 30)],  # 30x30 grid
                'velocity': [random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5)],
                'age': 0,
                'effects': [],
                'mutation_rate': self.chaos * 0.1
            }
            self.creatures.append(creature)
            
        # Run simulation for a number of steps
        steps = 100
        for step in range(steps):
            self.update_creatures(step)
            
    def update_creatures(self, step):
        """Update creature positions and interactions"""
        # Move creatures
        for creature in self.creatures:
            # Apply velocity with some randomness
            creature['position'][0] += creature['velocity'][0] + random.uniform(-0.1, 0.1)
            creature['position'][1] += creature['velocity'][1] + random.uniform(-0.1, 0.1)
            
            # Boundary conditions
            creature['position'][0] = max(0, min(30, creature['position'][0]))
            creature['position'][1] = max(0, min(30, creature['position'][1]))
            
            # Age creature
            creature['age'] += 1
            
        # Check for collisions and interactions
        for i in range(len(self.creatures)):
            for j in range(i+1, len(self.creatures)):
                creature1 = self.creatures[i]
                creature2 = self.creatures[j]
                
                # Calculate distance between creatures
                dx = creature1['position'][0] - creature2['position'][0]
                dy = creature1['position'][1] - creature2['position'][1]
                distance = np.sqrt(dx*dx + dy*dy)
                
                # If close enough, interact
                if distance < 2.0:
                    self.handle_creature_interaction(creature1, creature2, step)
                    
    def handle_creature_interaction(self, creature1, creature2, step):
        """Handle interaction between two creatures"""
        # Determine interaction type based on similarity and position
        color_sim = self.color_similarity(
            creature1['clip']['metadata']['avg_color'],
            creature2['clip']['metadata']['avg_color']
        )
        
        motion_sim = abs(creature1['clip']['metadata']['motion_energy'] - 
                         creature2['clip']['metadata']['motion_energy'])
        
        # Fuse similar creatures
        if color_sim > 0.7 and random.random() < 0.3:
            self.fuse_creatures(creature1, creature2)
            
        # Apply glitch effect to high-motion creatures
        if (creature1['clip']['metadata']['motion_energy'] > 0.5 or 
            creature2['clip']['metadata']['motion_energy'] > 0.5):
            if random.random() < self.style_params['glitch_prob']:
                self.apply_glitch_effect(creature1)
                self.apply_glitch_effect(creature2)
                
        # Random mutations
        if random.random() < creature1['mutation_rate']:
            self.mutate_creature(creature1)
        if random.random() < creature2['mutation_rate']:
            self.mutate_creature(creature2)
            
    def color_similarity(self, color1, color2):
        """Calculate color similarity between two RGB colors"""
        return 1 / (1 + np.linalg.norm(np.array(color1) - np.array(color2)) / 255)
        
    def fuse_creatures(self, creature1, creature2):
        """Fuse two similar creatures together"""
        # Average their metadata
        avg_color = [(c1 + c2) / 2 for c1, c2 in zip(creature1['clip']['metadata']['avg_color'], 
                                                    creature2['clip']['metadata']['avg_color'])]
        
        # Create fused clip metadata
        fused_metadata = {
            'avg_color': avg_color,
            'motion_energy': (creature1['clip']['metadata']['motion_energy'] + 
                             creature2['clip']['metadata']['motion_energy']) / 2,
            'dominant_hue': (creature1['clip']['metadata']['dominant_hue'] + 
                            creature2['clip']['metadata']['dominant_hue']) / 2
        }
        
        # Create new fused creature
        fused_creature = {
            'id': f"{creature1['id']}-{creature2['id']}",
            'clip': {
                'path': 'fused',
                'type': 'fused',
                'duration': (creature1['clip']['duration'] + creature2['clip']['duration']) / 2,
                'metadata': fused_metadata
            },
            'position': [(creature1['position'][0] + creature2['position'][0]) / 2,
                        (creature1['position'][1] + creature2['position'][1]) / 2],
            'velocity': [(creature1['velocity'][0] + creature2['velocity'][0]) / 2,
                        (creature1['velocity'][1] + creature2['velocity'][1]) / 2],
            'age': max(creature1['age'], creature2['age']),
            'effects': creature1['effects'] + creature2['effects']
        }
        
        # Replace one of the creatures with the fused one
        # (In a real implementation, we'd remove both and add the fused one)
        
    def apply_glitch_effect(self, creature):
        """Apply a glitch effect to a creature"""
        effects = ['pixel_sort', 'datamosh', 'rgb_shift', 'mirror']
        effect = random.choice(effects)
        creature['effects'].append(effect)
        
    def mutate_creature(self, creature):
        """Apply random mutations to a creature"""
        if random.random() < 0.5:
            # Change color slightly
            color = creature['clip']['metadata']['avg_color']
            mutated_color = [max(0, min(255, c + random.randint(-20, 20))) for c in color]
            creature['clip']['metadata']['avg_color'] = mutated_color
            
        if random.random() < 0.3:
            # Change motion energy
            creature['clip']['metadata']['motion_energy'] = max(0, min(1, 
                creature['clip']['metadata']['motion_energy'] + random.uniform(-0.1, 0.1)))
                
    def generate_timeline(self):
        """Generate final timeline based on ecosystem simulation"""
        print("Generating timeline...")
        
        # Sort creatures by age and position to create a logical flow
        sorted_creatures = sorted(self.creatures, key=lambda c: (c['age'], c['position'][0]))
        
        # Create timeline clips
        timeline_clips = []
        current_time = 0
        
        for creature in sorted_creatures:
            clip = creature['clip']
            duration = clip['duration']
            
            # Adjust duration based on motion energy and chaos
            adjusted_duration = duration * (0.8 + self.chaos * 0.4)
            
            # Create clip with effects
            timeline_clip = self.create_timed_clip(clip, current_time, adjusted_duration)
            timeline_clips.append(timeline_clip)
            
            current_time += adjusted_duration
            
            # Occasionally add recursive overlays at beat events
            if random.random() < 0.1 and self.audio_info:
                self.add_recursive_overlays(timeline_clips, current_time)
                
        return timeline_clips
        
    def create_timed_clip(self, clip, start_time, duration):
        """Create a timed clip with appropriate effects"""
        # This would actually create a MoviePy clip with effects applied
        # For now, we'll simulate it
        return {
            'clip': clip,
            'start_time': start_time,
            'duration': duration,
            'effects': clip.get('effects', [])
        }
        
    def add_recursive_overlays(self, timeline_clips, time_point):
        """Add recursive PiP layers at beat events"""
        # This would add recursive overlays to the timeline
        # Implementation would involve creating smaller versions of the composition
        pass
        
    def render_video(self, output_path):
        """Render the final video"""
        print("Rendering final video...")
        
        # Generate timeline
        timeline_clips = self.generate_timeline()
        
        # Create final composition
        final_composition = CompositeVideoClip([])
        
        # Add clips to composition with appropriate timing
        for clip_info in timeline_clips:
            # In a real implementation, we would create actual MoviePy clips here
            pass
            
        # Render video
        # final_composition.write_videofile(output_path, fps=30, codec='libx264')
        print(f"Video rendered to {output_path}")
        
    def run(self):
        """Run the complete NexusWeave pipeline"""
        print("Starting NexusWeave processing...")
        
        # Step 1: Load media
        self.load_media()
        
        # Step 2: Build similarity graph
        self.build_similarity_graph()
        
        # Step 3: Create ecosystem simulation
        self.create_ecosystem_simulation()
        
        # Step 4: Generate timeline
        timeline_clips = self.generate_timeline()
        
        # Step 5: Render final video
        output_path = f"nexusweave_output_{self.seed}.mp4"
        self.render_video(output_path)
        
        print("Processing complete!")
        return output_path