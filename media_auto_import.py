import ctypes
import os
import platform
import time
import shutil
import psutil
import subprocess
import schedule
from datetime import datetime
from PIL import Image, ExifTags
import tempfile
from tqdm import tqdm
import win32api
import win32file
import win32con
import ctypes

# ======= 配置区域 =======
PHOTO_DIR = r'Z:\\media\\photo'
VIDEO_DIR = r'Z:\\media\\video'
LOCK_FILE = os.path.join(tempfile.gettempdir(), 'media_import.lock')
LOCK_TIMEOUT = 10 * 60  # 超过10分钟自动清理锁
SCAN_INTERVAL = 1  # 每次间隔秒数
DELETE_ORIGINAL = True
MIN_FILE_SIZE = 1 * 1024 * 1024  # 1MB in bytes

PHOTO_EXTS = ['.jpg', '.jpeg', '.png', '.cr2', '.nef', '.arw', '.dng']
VIDEO_EXTS = ['.mp4', '.mov', '.avi', '.mkv', '.m4v']

FOLDER_BRAND_HINTS = {
    'DCIM': 'DJI',
    'AVCHD': 'Sony',
    'PRIVATE': 'Sony',
    'MP_ROOT': 'Sony',
    'CANON': 'Canon',
    'FUJI': 'Fujifilm',
    'GOPRO': 'GoPro',
    'DJI': 'DJI'
}

# ======= 工具函数 =======


def is_photo(file): return any(file.lower().endswith(ext)
                               for ext in PHOTO_EXTS)


def is_video(file): return any(file.lower().endswith(ext)
                               for ext in VIDEO_EXTS)


def get_removable_drives():
    return [p.device for p in psutil.disk_partitions() if 'removable' in p.opts]


def get_exif_info(photo_path):
    try:
        image = Image.open(photo_path)
        exif_data = image._getexif()
        if not exif_data:
            return None, None
        exif = {ExifTags.TAGS.get(k): v for k,
                v in exif_data.items() if k in ExifTags.TAGS}
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
    # 收集所有需要处理的文件
    files = [(root, f) for root, _, fs in os.walk(drive)
             for f in fs if is_photo(f) or is_video(f)]

    # 使用tqdm显示进度条
    for root, file in tqdm(files, desc=f"Copying from {drive}", unit="file"):
        src = os.path.join(root, file)
        # 检查文件大小，跳过小于1MB的文件
        if os.path.getsize(src) < MIN_FILE_SIZE:
            print(f"[Skipped] {src} (size < 1MB)")
            continue

        if is_photo(file):
            make, date = get_exif_info(src)
            if not make:
                make = 'Unknown'
            if not date:
                date = get_file_date(src)
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

            import os

            import os


def eject_disk(drive_letter):
    # 驱动器字母应以 : 结尾
    if not drive_letter.endswith('\\\\'):
        drive_letter = drive_letter[:-1]

    # 检查驱动器是否存在
    if not os.path.exists(drive_letter):
        print(f"驱动器 {drive_letter} 不存在或未连接.")
        return False

    try:
        # 获取驱动器的句柄
        drive_handle = win32file.CreateFile(
            f'\\\\.\\{drive_letter}',
            win32con.GENERIC_READ | win32con.GENERIC_WRITE,
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
            None,
            win32con.OPEN_EXISTING,
            0,
            None
        )

        # 使用 DeviceIoControl 发送弹出请求，调用 Eject
        result = win32file.DeviceIoControl(
            drive_handle,
            0x2D4808,  # IOCTL_STORAGE_EJECT_MEDIA
            None,
            0
        )

        # 关闭驱动器句柄
        win32file.CloseHandle(drive_handle)

        print(f"驱动器 {drive_letter} 已成功弹出.")
        return True

    except Exception as e:
        print(f"弹出驱动器 {drive_letter} 失败: {e}")
        return False


def is_lock_stale():
    if not os.path.exists(LOCK_FILE):
        return False
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


release_lock()
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
            eject_disk(drive)
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
