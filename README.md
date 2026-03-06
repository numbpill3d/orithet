# Orithet - Generative Video Art Tool

[![GitHub](https://img.shields.io/github/license/orithet/orithet)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/)
[![FFmpeg](https://img.shields.io/badge/ffmpeg-required-orange)](https://ffmpeg.org/)

Orithet is a cutting-edge generative video art tool that seamlessly blends four conceptual systems to create mesmerizing, algorithmic visual experiences:

- **PulseForge**: Beat-driven, audio-reactive timing & pulses
- **EchoMosaic**: Semantic dream-like chaining via similarity graph + emotional flow
- **GlitchGarden**: Procedural ecosystem where clips act like living creatures that collide, fuse, mutate
- **FractalFusion**: Recursive picture-in-picture layers and infinite-depth echoes

Transform any collection of media files into hypnotic generative music videos or visual albums that feel like living digital organisms.

## 🎨 Features Overview

### 🔊 Audio Master Clock (PulseForge)
- Analyzes strongest audio file for BPM, beat grid, and energy bands
- All cuts and transitions lock to beat boundaries or sub-beats
- Energy bands: low/mid/high frequency analysis for dynamic visual responses

### 🎬 Smart + Random Chopping
- Videos: PySceneDetect + extra random "memory cuts" every 3–12 seconds
- Images/GIFs: Variable-length clips (2–15 seconds) based on visual energy
- All clips become "creatures" with metadata (avg color palette, motion energy, dominant hue)

### 🌱 Hybrid Assembly Engine
- Build a similarity graph (color + motion + audio mood)
- Lightweight 2D "ecosystem simulation" (30×30 grid) where creatures move, collide, and evolve
- Same-color creatures fuse (cross-fade + palette average)
- High-motion creatures "infect" others with glitch effects
- Random mutations (pixel sort, datamosh, RGB shift, mirror) are inherited

### 🌀 Recursive Fractal Overlays (FractalFusion)
- At every major beat or collision event, spawn recursive PiP layers (up to depth 3)
- Each smaller layer shows a mutated version of the entire current composition
- Overlays pulse and scale with audio energy

### 🎭 Effects Pipeline
- Beat-reactive zoom/pulse, color bleed between adjacent clips
- Echo trails, chromatic aberration, glitch probability
- Dream dissolves, vignette that reacts to bass

## 📦 Installation

### Prerequisites
- Python 3.7+
- FFmpeg (required for video processing)

### Install Dependencies
```bash
# Clone the repository
git clone https://github.com/orithet/orithet.git
cd orithet

# Install Python dependencies
pip install -r requirements.txt
```

### Optional: Install Gradio for Web Interface
```bash
pip install gradio
```

## 🚀 Quick Start

### Command Line Usage
```bash
python orithet/cli.py --input_folder /path/to/media/folder --duration 120 --chaos 0.5 --seed 42 --resolution 1920 1080 --style dream
```

### Web Interface (Gradio)
```bash
python orithet/gradio_ui.py
```
Then visit `http://localhost:7860` in your browser.

## 📁 Input Media Support

NexusWeave accepts a diverse mix of media files:
- **Videos**: .mp4, .mov, .avi, .mkv
- **Images**: .jpg, .jpeg, .png, .gif
- **Audio**: .mp3, .wav, .flac

**Recommended**: 5-200 files in a single folder for best results.

## ⚙️ Configuration Options

### Command Line Arguments
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--input_folder` | *(required)* | Path to folder containing media files |
| `--duration` | 120 | Target video duration in seconds |
| `--chaos` | 0.5 | Randomness factor (0.0-1.0) |
| `--seed` | Random | Random seed for reproducibility |
| `--resolution` | 1920 1080 | Output resolution (width height) |
| `--style` | dream | Preset style ("dream", "glitch", "psychedelic", "ambient") |

### Style Presets
- **Dream**: Subtle effects, moderate chaos, 2-level recursion
- **Glitch**: Heavy glitch effects, high chaos, 3-level recursion
- **Psychedelic**: Intense visual transformations, high motion sensitivity
- **Ambient**: Minimal effects, low chaos, 1-level recursion

## 🧠 How It Works

### Phase 1: Media Processing
1. **Load Media**: Scan input folder for supported file types
2. **Scene Detection**: Use PySceneDetect to identify scene changes in videos
3. **Metadata Extraction**: Calculate color palettes, motion energy, and dominant hues
4. **Audio Analysis**: Extract BPM and energy bands from audio files

### Phase 2: Ecosystem Simulation
1. **Creature Creation**: Each clip becomes a "creature" with unique properties
2. **Similarity Graph**: Build relationships between clips based on visual/audio characteristics
3. **Ecosystem Dynamics**: Creatures move, interact, and evolve over time:
   - Same-color creatures fuse together
   - High-motion creatures spread glitch effects
   - Random mutations occur with configurable probability
4. **Behavioral Rules**: Creatures follow physics-inspired movement and interaction rules

### Phase 3: Timeline Generation
1. **Ordering**: Sort creatures by age and position to create logical flow
2. **Timing**: Adjust clip durations based on motion energy and chaos factor
3. **Beat Synchronization**: Align transitions with audio beats
4. **Recursive Layers**: Add PiP overlays at beat events

### Phase 4: Final Rendering
1. **Composition**: Layer all elements with appropriate timing
2. **Effects Application**: Apply beat-reactive visual effects
3. **Output**: Generate final high-quality MP4 video (1920×1080, 30 fps)

## 🎥 Example Commands

### Basic Generation
```bash
python orithet/cli.py --input_folder ./media_samples --duration 180
```

### Psychedelic Experience
```bash
python orithet/cli.py --input_folder ./media_samples --duration 120 --chaos 0.8 --style psychedelic
```

### Reproducible Result
```bash
python orithet/cli.py --input_folder ./media_samples --seed 12345 --style glitch
```

### Custom Resolution
```bash
python orithet/cli.py --input_folder ./media_samples --resolution 3840 2160 --duration 240
```

## 📁 Project Structure

```
orithet/
├── __init__.py              # Package initialization
├── core.py                  # Core processing logic implementing all systems
├── cli.py                   # Command-line interface
├── gradio_ui.py             # Web interface using Gradio
├── requirements.txt         # Python dependencies
├── setup.py                 # Package installation configuration
└── README.md                # This file
```

## 🛠️ Development

### Adding New Effects
To add new visual effects, modify the effects pipeline in `core.py`:
1. Add effect function to the creature processing logic
2. Include in the effect application stage
3. Configure via style presets or command-line parameters

### Extending Systems
Each system is modular:
- **PulseForge**: Modify audio analysis in `process_audio()` method
- **EchoMosaic**: Adjust similarity calculation in `calculate_similarity()` method
- **GlitchGarden**: Extend creature interaction logic in `handle_creature_interaction()` method
- **FractalFusion**: Modify recursive overlay generation in `add_recursive_overlays()` method

## 📊 Performance Considerations

- **Memory Usage**: Processes media files in chunks to manage memory efficiently
- **CPU Usage**: Optimized for parallel processing where possible
- **Recursion Depth**: Limited to 3 levels to prevent render explosion
- **Frame Rate**: Default 30fps for smooth playback

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

NexusWeave draws inspiration from:
- Audio-reactive visualizations
- Generative art principles
- Procedural content generation
- Digital ecosystems and evolution theory

Created with ❤️ for artists, musicians, and creators exploring the intersection of technology and creativity.