"""
Gradio UI for Orithet - Generative Video Art Tool
"""

import gradio as gr
import os
import tempfile
from .core import OrithetCore

def create_gradio_interface():
    """Create a Gradio interface for Orithet"""
    
    with gr.Blocks(title="Orithet - Generative Video Art") as demo:
        gr.Markdown("# Orithet")
        gr.Markdown("Generative Video Art Tool blending PulseForge, EchoMosaic, GlitchGarden, and FractalFusion")
        
        with gr.Row():
            with gr.Column():
                input_folder = gr.Textbox(label="Input Folder Path",
                                        placeholder="Enter path to folder with media files")
                duration = gr.Slider(30, 300, value=120, label="Duration (seconds)")
                chaos = gr.Slider(0.0, 1.0, value=0.5, label="Chaos Level")
                style = gr.Radio(["dream", "glitch", "psychedelic", "ambient"],
                               value="dream", label="Style")
                seed = gr.Number(label="Seed (for reproducibility)", value=None, precision=0)
                resolution = gr.Radio([(1920, 1080), (1280, 720), (3840, 2160)],
                                    value=(1920, 1080), label="Resolution")
                submit_btn = gr.Button("Generate Video")
                
            with gr.Column():
                output_video = gr.Video(label="Generated Video")
                status_text = gr.Textbox(label="Status", interactive=False)
        
        def process_video(input_folder, duration, chaos, style, seed, resolution):
            """Process video generation"""
            try:
                # Validate input folder
                if not os.path.exists(input_folder):
                    return None, f"Error: Input folder '{input_folder}' does not exist."
                
                # Create temporary output file
                temp_dir = tempfile.mkdtemp()
                output_path = os.path.join(temp_dir, f"orithet_output_{seed or 'auto'}.mp4")
                
                # Create and run Orithet
                engine = OrithetCore(
                    input_folder=input_folder,
                    duration=duration,
                    chaos=chaos,
                    seed=seed,
                    resolution=resolution,
                    style=style
                )
                
                # Run the engine
                engine.run()
                
                # For demo purposes, we'll return a placeholder
                return output_path, "Video generated successfully!"
                
            except Exception as e:
                return None, f"Error: {str(e)}"
                
        submit_btn.click(
            fn=process_video,
            inputs=[input_folder, duration, chaos, style, seed, resolution],
            outputs=[output_video, status_text]
        )
        
        gr.Examples(
            examples=[
                ["/path/to/media/folder", 120, 0.5, "dream", 42, (1920, 1080)],
                ["/path/to/media/folder", 180, 0.8, "glitch", 12345, (1280, 720)],
            ],
            inputs=[input_folder, duration, chaos, style, seed, resolution],
            outputs=[output_video, status_text],
            fn=process_video,
            cache_examples=False
        )
        
    return demo

# Launch the interface
if __name__ == "__main__":
    demo = create_gradio_interface()
    demo.launch(server_name="0.0.0.0", server_port=7860)