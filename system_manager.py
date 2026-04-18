import os
import platform
import shutil
import requests
import zipfile
import tarfile
import subprocess
import sys
import telebot
from telebot import apihelper
import json
import io
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SYSTEM_OS = platform.system()
ARCH = platform.machine().lower()

if SYSTEM_OS == "Windows":
    LOCAL_FFMPEG = os.path.join(BASE_DIR, "ffmpeg.exe")
else:
    LOCAL_FFMPEG = os.path.join(BASE_DIR, "ffmpeg")

FFMPEG_EXE = None

FFMPEG_URLS = {
    "Windows": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
    "Linux_x86_64": "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz",
    "Linux_aarch64": "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz"
}

def get_system_diagnostics():
    diagnostics = {
        "OS": f"{SYSTEM_OS} {platform.release()} ({platform.version()})",
        "Architecture": f"{ARCH} (Processor: {platform.processor()})",
        "Python Version": sys.version,
        "Executable": sys.executable,
        "Working Directory": os.getcwd(),
        "Local FFmpeg Path": LOCAL_FFMPEG,
        "PATH": os.environ.get("PATH", "Not Found")
    }
    report = "\n" + "="*60 + "\n"
    report += "🔍 SYSTEM DIAGNOSTICS\n"
    report += "="*60 + "\n"
    for key, value in diagnostics.items():
        report += f"● {key}: {value}\n"
    report += "="*60 + "\n"
    return report

def patch_telebot():
    """Monkey patches telebot to handle sticker_format and cross-version compatibility."""
    print("🩹 Patching telebot library at runtime (Universal)...")

    def _prepare_request_data(method_url, kwargs):
        payload = {}
        files = {}
        
        sticker_keys = ['png_sticker', 'webm_sticker', 'tgs_sticker', 'sticker']
        
        for key, value in kwargs.items():
            if value is None: continue
            
            is_file = False
            if isinstance(value, (io.IOBase, bytes)):
                is_file = True
            elif hasattr(value, 'read') and callable(value.read):
                is_file = True
            
            if key in sticker_keys:
                if is_file:
                    files[key] = value
                else:
                    payload[key] = value
            elif key == 'stickers' and isinstance(value, list):
                if hasattr(apihelper, '_get_stickers_payload'):
                    payload['stickers'] = apihelper._get_stickers_payload(value)
                else:
                    payload['stickers'] = json.dumps([s.to_dict() if hasattr(s, 'to_dict') else s for s in value])
                
                for i, s in enumerate(value):
                    s_val = getattr(s, 'sticker', None)
                    if s_val and not isinstance(s_val, str):
                        files[f'sticker{i}'] = s_val
            else:
                if is_file:
                    files[key] = value
                else:
                    payload[key] = value
        
        return payload, files

    def patched_create_new(token, user_id, name, title, stickers=None, **kwargs):
        method_url = 'createNewStickerSet'
        payload = {'user_id': user_id, 'name': name, 'title': title}
        if stickers: kwargs['stickers'] = stickers
        p, f = _prepare_request_data(method_url, kwargs)
        payload.update(p)
        return apihelper._make_request(token, method_url, params=payload, files=f or None, method='post')

    apihelper.create_new_sticker_set = patched_create_new

    def patched_add(token, user_id, name, emojis=None, **kwargs):
        method_url = 'addStickerToSet'
        payload = {'user_id': user_id, 'name': name}
        if emojis: payload['emojis'] = emojis
        p, f = _prepare_request_data(method_url, kwargs)
        payload.update(p)
        return apihelper._make_request(token, method_url, params=payload, files=f or None, method='post')

    apihelper.add_sticker_to_set = patched_add
    
    telebot.TeleBot.create_new_sticker_set = lambda self, *args, **kwargs: apihelper.create_new_sticker_set(self.token, *args, **kwargs)
    telebot.TeleBot.add_sticker_to_set = lambda self, *args, **kwargs: apihelper.add_sticker_to_set(self.token, *args, **kwargs)

    print("✅ telebot library patched successfully (Universal).")

def initialize_ffmpeg():
    """Finds or downloads FFmpeg."""
    global FFMPEG_EXE
    
    print("🛠 Initializing FFmpeg...")
    ffmpeg_in_path = shutil.which("ffmpeg")
    if ffmpeg_in_path:
        print(f"✅ FFmpeg found in PATH: {ffmpeg_in_path}")
        FFMPEG_EXE = ffmpeg_in_path
    elif os.path.exists(LOCAL_FFMPEG):
        print(f"✅ FFmpeg found locally: {LOCAL_FFMPEG}")
        FFMPEG_EXE = LOCAL_FFMPEG
    else:
        print(f"🔍 Downloading FFmpeg for {SYSTEM_OS}...")
        download_url = FFMPEG_URLS.get(SYSTEM_OS) if SYSTEM_OS == "Windows" else None
        if not download_url and SYSTEM_OS == "Linux":
            if "x86_64" in ARCH or "amd64" in ARCH:
                download_url = FFMPEG_URLS["Linux_x86_64"]
            elif "aarch64" in ARCH or "arm64" in ARCH:
                download_url = FFMPEG_URLS["Linux_aarch64"]

        if download_url:
            try:
                response = requests.get(download_url, stream=True, timeout=30)
                temp_archive = os.path.join(BASE_DIR, "ffmpeg_download")
                with open(temp_archive, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                if SYSTEM_OS == "Windows":
                    with zipfile.ZipFile(temp_archive, 'r') as zip_ref:
                        for file in zip_ref.namelist():
                            if file.endswith("ffmpeg.exe"):
                                with zip_ref.open(file) as src, open(LOCAL_FFMPEG, "wb") as tgt:
                                    tgt.write(src.read())
                                break
                else:
                    with tarfile.open(temp_archive, "r:xz") as tar:
                        for member in tar.getmembers():
                            if member.name.endswith("/ffmpeg"):
                                member.name = os.path.basename(member.name)
                                tar.extract(member, path=BASE_DIR)
                                break
                    os.chmod(LOCAL_FFMPEG, 0o755)
                
                os.remove(temp_archive)
                FFMPEG_EXE = LOCAL_FFMPEG
                print(f"✅ FFmpeg setup complete: {LOCAL_FFMPEG}")
            except Exception as e:
                print(f"❌ FFmpeg setup failed: {e}")
        else:
            print(f"⚠️ OS {SYSTEM_OS} {ARCH} not supported for auto-download.")

def setup():
    print("\n" + "="*60)
    print("🚀 SYSTEM MANAGER: Initializing components...")
    patch_telebot()
    initialize_ffmpeg()
    print("="*60 + "\n")

if __name__ == "__main__":
    setup()
else:
    setup()
