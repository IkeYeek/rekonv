# Rekonvert
### 🎧 Convert your audio and video files to your preferred format with ease! 🎶

Rekonvert is a simple python script that serves as a wrapper for ffmpeg in order to allow converting batch of audio and video files to widely supported audio formats (aiff, aac, mp3 and flac). 

This little project was made to make DJ's life a little easier working with formats that are widely supported by most popular decks and softwares.

It uses an index allow you stopping and restarting conversion when working with many files. The index also allows the script to check at the end if the conversion was done properly. The index is of course created in chunks so we don't either perform too much I/O operations or store massive objects in memory.

The rest of this readme was AI generated, enjoy the random emojis (sry I'm lazy)
### Features
- 📁 Recursive and non-recursive conversion
- 🎹 Convert a single file (yes that's basically a fancy ffmpeg wrapper)
- 🎶 Supports a wide range of input formats (audio and video)
- 🎵 Converts to popular output formats (AIFF, MP3, AAC, FLAC)
- 🔄 Handles file name collisions by appending a suffix
- 🚀 Fast conversion using FFmpeg
- 💻 Creates an index of files to convert, allowing for resuming conversions from where you left off
- 💡 Allows copying of non-audio/video files

### Installation
Rekonvert requires Python 3.6 or higher and FFmpeg.

Install Python: Make sure you have Python installed on your system. You can download it from python.org.
Install FFmpeg: Download and install FFmpeg from ffmpeg.org.
Clone the Repository:
```
git clone https://github.com/yourusername/rekonvert.git
cd rekonvert
```
#### Start  a venv
```
python -m venv ./rekonv-venv
source ./rekonv-venv/bin/activate 
```
#### Install Dependencies:
```
python -m pip install requirements.txt
```

### Usage
```
python rekonv.py --output-format mp3 --output ./converted_files --recursive --target ./path/to/your/filesCopy
```
### Options:
- `--output-format` or `-of`: Specify the output format (default: aac).
- `--output` or `-o`: Specify the output directory (default: ./).
- `--single-file` or `-sf`: Convert a single file.
- `--target` or `-t`: Target directory or file.
- `--recursive` or `-r`: Enable recursive conversion.
- `--skip-existing-files` or `-skf`: Skip existing files in the output directory.
- `--copy-all-files` or `-cp`: Copy all files, including non-audio/video files.
### Contributing
Contributions are welcome! Please feel free to submit a pull request or open an issue.

### License
This project is licensed under the GPLV3 License. See