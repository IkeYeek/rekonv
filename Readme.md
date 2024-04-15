# Rekonvert

🎧 Convert your audio and video files to your preferred format with ease! 🎶

Rekonvert is a simple yet powerful Python script that allows you to recursively or non-recursively convert directories of audio (or video files that will be converted to audio files) to a specific format, respecting the nesting of folders if done recursively.

## Features

- 📁 Recursive and non-recursive conversion
- 🎶 Supports a wide range of input formats (audio and video)
- 🎵 Converts to popular output formats (AIFF, MP3, M4A, FLAC)
- 🔄 Handles file name collisions by appending a suffix
- 🚀 Fast conversion using FFmpeg

## Installation

Rekonvert requires Python 3.6 or higher and FFmpeg.

1. **Install Python**: Make sure you have Python installed on your system. You can download it from [python.org](https://www.python.org/downloads/).

2. **Install FFmpeg**: Download and install FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html).

3. **Clone the Repository**:
`git clone https://github.com/yourusername/rekonvert.git cd rekonvert`

4. **Install Dependencies**:
`pip install click`

## Usage
`bash python rekonv.py --output-format mp3 --output ./converted_files --recursive --target ./path/to/your/files`

### Options

- `--output-format` or `-of`: Specify the output format (default: `aiff`).
- `--output` or `-o`: Specify the output directory (default: `./`).
- `--single-file` or `-sf`: Convert a single file.
- `--target` or `-t`: Target directory or file.
- `--recursive` or `-r`: Enable recursive conversion.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.

## License

This project is licensed under the GPLV3 License. See the [LICENSE](LICENSE) file for details.

## Contact

If you have any questions or suggestions, feel free to reach out!

---

🚀 Happy converting!