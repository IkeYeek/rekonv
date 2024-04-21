# Rekonvert
### 🎧 Convert your audio and video files to your preferred format with ease! 🎶

#### Rekonvert is a powerful Python script that allows you to recursively or non-recursively convert directories of audio (or video files that will be converted to audio files) to a specific format, respecting the nesting of folders if done recursively.

### Features
- 📁 Recursive and non-recursive conversion
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