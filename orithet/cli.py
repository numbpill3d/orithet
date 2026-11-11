#!/usr/bin/env python3
"""
Command-line interface for Orithet - Generative Video Art Tool
"""

import argparse
import sys
import logging
from pathlib import Path

try:
    from .core import OrithetCore
except ImportError:  # Support the documented `python orithet/cli.py ...` form.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from orithet.core import OrithetCore

def main():
    parser = argparse.ArgumentParser(description='Orithet - Generative Video Art Tool')
    parser.add_argument('--input_folder', required=True,
                       help='Path to folder containing media files (.mp4, .mov, .gif, .jpg, .png, .mp3, .wav)')
    parser.add_argument('--duration', type=float, default=120,
                       help='Target video duration in seconds (default: 120)')
    parser.add_argument('--chaos', type=float, default=0.5,
                       help='Randomness factor (0.0-1.0, default: 0.5)')
    parser.add_argument('--seed', type=int,
                       help='Random seed for reproducibility')
    parser.add_argument('--resolution', nargs=2, type=int, default=[1920, 1080],
                       help='Output resolution (width height, default: 1920 1080)')
    parser.add_argument('--style', choices=['dream', 'glitch', 'psychedelic', 'ambient'],
                       default='dream',
                       help='Preset style (default: dream)')
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
        
    # Create and run Orithet
    try:
        engine = OrithetCore(
            input_folder=args.input_folder,
            duration=args.duration,
            chaos=args.chaos,
            seed=args.seed,
            resolution=tuple(args.resolution),
            style=args.style
        )
        
        output_path = engine.run()
        print(f"Successfully generated video: {output_path}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
