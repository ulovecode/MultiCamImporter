import os
import time
import shutil
import psutil
import subprocess
import schedule
from datetime import datetime
from PIL import Image, ExifTags
import tempfile

# ======= 配置区域 =======
PHOTO_DIR = r'D:\\photo'
VIDEO_DIR = r'D:\\video'
LOCK_FILE = os.path.join(tempfile.gettempdir(), 'media_import.lock')
LOCK_TIMEOUT = 10 * 60  # 超过10分钟自动清理锁
SCAN_INTERVAL = 60  # 每次间隔秒数
DELETE_ORIGINAL = True

PHOTO_EXTS = ['.jpg', '.jpeg', '.png', '.cr2', '.nef', '.arw', '.dng']
VIDEO_EXTS = ['.mp4', '.mov', '.avi', '.mkv', '.m4v']

FOLDER_BRAND_HINTS = {
    'DCIM': 'Generic',
    'AVCHD': 'Sony',
    'PRIVATE': 'Panasonic',
    'MP_ROOT': 'Sony',
    'CANON': 'Canon',
    'FUJI': 'Fujifilm',
    'GOPRO': 'GoPro',
    'DJI': 'DJI'
}

# ======= 工具函数 =======
def is_photo(file): return any(file.lower().endswith(ext) for ext in PHOTO_EXTS)
def is_video(file): return any(file.lower().endswith(ext) for ext in VIDEO_EXTS)

def get_removable_drives():
    return [p.device for p in psutil.disk_partitions() if 'removable' in p.opts]

def get_exif_info(photo_path):
    try:
        image = Image.open(photo_path)
        exif_data = image._getexif()
        if not exif_data: return None, None
        exif = {ExifTags.TAGS.get(k): v for k, v in exif_data.items() if k in ExifTags.TAGS}
        make = exif.get('Make', 'Unknown').strip().capitalize()
        date_str = exif.get('DateTimeOriginal') or exif.get('DateTime')
        if date_str:
            date = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S').date()
            return make, str(date)
        return make, None
    except Exception as e:
        print(f"[Exif] Failed to read {photo_path}: {e}")
        return None, None

def guess_brand_by_path(path):
    for key, brand in FOLDER_BRAND_HINTS.items():
        if key.lower() in path.lower():
            return brand
    return "Unknown"

def get_file_date(path):
    try:
        t = os.path.getmtime(path)
        return datetime.fromtimestamp(t).strftime('%Y-%m-%d')
    except Exception:
        return datetime.today().strftime('%Y-%m-%d')

def copy_files(drive):
    copied = []

    for root, _, files in os.walk(drive):
        for file in files:
            src = os.path.join(root, file)
            if is_photo(file):
                make, date = get_exif_info(src)
                if not make: make = 'Unknown'
                if not date: date = get_file_date(src)
                dest_dir = os.path.join(PHOTO_DIR, make, date)
            elif is_video(file):
                make = guess_brand_by_path(src)
                date = get_file_date(src)
                dest_dir = os.path.join(VIDEO_DIR, make, date)
            else:
                continue

            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, file)
            try:
                shutil.copy2(src, dest_path)
                print(f'[Copied] {src} -> {dest_path}')
                copied.append(src)
            except Exception as e:
                print(f'[Error] Copy failed: {e}')
    return copied

def delete_files(file_list):
    for f in file_list:
        try:
            os.remove(f)
            print(f'[Deleted] {f}')
        except Exception as e:
            print(f'[Error] Delete failed: {e}')

def eject_drive(drive_letter):
    try:
        cmd = f'powershell "(New-Object -comObject Shell.Application).NameSpace(17).ParseName(\\\"{drive_letter}\\\").InvokeVerb(\\\"弹出(&E)\\\")"'
        subprocess.run(cmd, shell=True)
        print(f'[Ejected] {drive_letter}')
    except Exception as e:
        print(f'[Error] Eject failed: {e}')

def is_lock_stale():
    if not os.path.exists(LOCK_FILE): return False
    mtime = os.path.getmtime(LOCK_FILE)
    age = time.time() - mtime
    return age > LOCK_TIMEOUT

def acquire_lock():
    if os.path.exists(LOCK_FILE):
        if is_lock_stale():
            print(f"[Lock] Removing stale lock file.")
            os.remove(LOCK_FILE)
        else:
            print(f"[Lock] Task already running. Skipping.")
            return False
    with open(LOCK_FILE, 'w') as f:
        f.write(str(os.getpid()))
    return True

def release_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

# ======= 主任务函数 =======
known_drives = set()

def check_and_process():
    if not acquire_lock():
        return
    try:
        global known_drives
        current_drives = set(get_removable_drives())
        new_drives = current_drives - known_drives
        known_drives = current_drives

        for drive in new_drives:
            print(f'[Detected] New drive: {drive}')
            copied = copy_files(drive)
            if copied and DELETE_ORIGINAL:
                delete_files(copied)
            time.sleep(2)
            eject_drive(drive)
    finally:
        release_lock()

# ======= 主程序入口 =======
def main_loop():
    print("[Init] Media Auto Import Service Running (every 60s)...")
    os.makedirs(PHOTO_DIR, exist_ok=True)
    os.makedirs(VIDEO_DIR, exist_ok=True)
    schedule.every(SCAN_INTERVAL).seconds.do(check_and_process)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    main_loop()