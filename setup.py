from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="orithet",
    version="0.1.0",
    author="Orithet Team",
    author_email="team@orithet.ai",
    description="Generative video art tool blending PulseForge, EchoMosaic, GlitchGarden, and FractalFusion",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/orithet/orithet",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "moviepy>=1.0.3",
        "opencv-python>=4.5.1.78",
        "librosa>=0.8.0",
        "pydub>=0.25.1",
        "numpy>=1.19.0",
        "pillow>=8.0.0",
        "scikit-image>=0.18.0",
        "scenedetect>=0.6.0",
        "gradio>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "orithet=orithet.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "orithet": ["*.py"],
    },
)