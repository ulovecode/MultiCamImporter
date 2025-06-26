# MultiCamImporter

**Automated Photo and Video Importer for Removable Storage Devices**

---

## Table of Contents

- [MultiCamImporter](#multicamimporter)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [Features](#features)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Configuration](#configuration)
  - [Supported Formats and Brands](#supported-formats-and-brands)
  - [Contributing](#contributing)
  - [License](#license)
  - [Contact](#contact)

---

## Introduction

AutoMediaImport is a smart and automated media management tool designed to seamlessly import photos and videos from removable devices such as SD cards and USB drives. It supports multiple camera brands and media formats, organizing your files by brand and capture date automatically. The tool also safely ejects the device after import, providing a streamlined workflow for photographers and videographers.

---

## Features

- Automatically detects removable drives on Windows  
- Supports common photo formats (JPEG, RAW, PNG, etc.)  
- Supports common video formats (MP4, MOV, AVI, etc.)  
- Organizes files into folders by brand and capture date  
- Deletes source files after successful import (optional)  
- Automatically ejects removable storage after processing  
- Prevents concurrent executions using lock files  
- Runs as a scheduled task every 60 seconds  

---

## Installation

1. Ensure you have Python 3.6+ installed.  
2. Clone this repository or download the script.  
3. Install required dependencies:

```bash
pip install schedule psutil pillow
````

---

## Usage

Run the script with:

```bash
python media_auto_import.py
```

**Recommended:** Run the terminal as Administrator to allow safe device ejection.

The script will monitor for newly inserted removable drives every 60 seconds and automatically import media files.

---

## Configuration

You can configure paths and options in the top section of `media_auto_import.py`:

```python
PHOTO_DIR = r'D:\photo'      # Destination folder for photos  
VIDEO_DIR = r'D:\video'      # Destination folder for videos  
DELETE_ORIGINAL = True       # Delete files after import  
SCAN_INTERVAL = 60           # Scan interval in seconds  
```

---

## Supported Formats and Brands

* **Photo Formats:** `.jpg`, `.jpeg`, `.png`, `.cr2`, `.nef`, `.arw`, `.dng`

* **Video Formats:** `.mp4`, `.mov`, `.avi`, `.mkv`, `.m4v`

* Recognized camera brands based on folder names and EXIF:
  Sony, Canon, Fujifilm, GoPro, DJI, Panasonic, and others.

---

## Contributing

Contributions, issues, and feature requests are welcome!
Feel free to fork the repository and submit pull requests.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Contact

Created by \[Your Name] - feel free to reach out!

---
