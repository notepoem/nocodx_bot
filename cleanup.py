import os
import json
import time
import shutil
import threading
from pathlib import Path
from typing import Dict, Any

CACHE_DIR = "cache"
CACHE_CLEANUP_INTERVAL = 1800  # 30 minutes in seconds
CACHE_EXPIRY_TIME = 1800       # 30 minutes in seconds

os.makedirs(CACHE_DIR, exist_ok=True)

class CacheManager:
    """Manages cache storage with auto-cleanup for chat histories and temporary files."""
    
    def __init__(self):
        self.cleanup_thread = None
        self.running = False
        
    def start_cleanup_task(self):
        """Start background cleanup task."""
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            return
            
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        print(f"✅ Cache cleanup task started (every {CACHE_CLEANUP_INTERVAL//60} minutes)")
    
    def _cleanup_loop(self):
        """Background loop to clean up expired cache."""
        while self.running:
            self.cleanup_expired_cache()
            time.sleep(CACHE_CLEANUP_INTERVAL)
    
    def cleanup_expired_cache(self):
        """Remove expired cache files (24 hours old) and empty directories."""
        current_time = time.time()
        cleaned_count = 0
        
        for root, dirs, files in os.walk(CACHE_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > CACHE_EXPIRY_TIME:
                        os.remove(file_path)
                        cleaned_count += 1
                except Exception as e:
                    print(f"Error removing cache file {file_path}: {e}")
        
        for root, dirs, files in os.walk(CACHE_DIR, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                except Exception as e:
                    print(f"Error removing empty dir {dir_path}: {e}")
        
        if cleaned_count > 0:
            print(f"🧹 Cleaned {cleaned_count} expired cache files")
    
    def save_chat_history(self, ai_name: str, chat_id: int, history: Any):
        """Save chat history to cache/{ai_name}/{chat_id}.json"""
        ai_cache_dir = os.path.join(CACHE_DIR, ai_name)
        os.makedirs(ai_cache_dir, exist_ok=True)
        
        file_path = os.path.join(ai_cache_dir, f"{chat_id}.json")
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving {ai_name} history for {chat_id}: {e}")
    
    def load_chat_history(self, ai_name: str, chat_id: int) -> Any:
        """Load chat history from cache/{ai_name}/{chat_id}.json"""
        file_path = os.path.join(CACHE_DIR, ai_name, f"{chat_id}.json")
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {ai_name} history for {chat_id}: {e}")
            return None
    
    def delete_chat_history(self, ai_name: str, chat_id: int):
        """Delete specific chat history. Auto-reply off করলে history automatic delete হয়"""
        file_path = os.path.join(CACHE_DIR, ai_name, f"{chat_id}.json")
        
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"✅ Deleted {ai_name} history for chat {chat_id}")
            except Exception as e:
                print(f"Error deleting {ai_name} history for {chat_id}: {e}")
    
    def get_temp_file_path(self, subfolder: str, filename: str) -> str:
        """Get path for temporary files in cache."""
        temp_dir = os.path.join(CACHE_DIR, subfolder)
        os.makedirs(temp_dir, exist_ok=True)
        return os.path.join(temp_dir, filename)
    
    def cleanup_temp_folder(self, subfolder: str):
        """Clean up specific temp folder."""
        temp_dir = os.path.join(CACHE_DIR, subfolder)
        
        if os.path.exists(temp_dir):
            try:
                for file in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
            except Exception as e:
                print(f"Error cleaning up {subfolder}: {e}")

cache_manager = CacheManager()

def cleanup_project():
    """Clean up project files and folders to free space."""

    # 1. Clean log files
    logs_dir = Path("logs")
    if logs_dir.exists():
        for log_file in logs_dir.glob("*.log"):
            try:
                log_file.unlink()
                print(f"✅ Deleted {log_file}")
            except Exception as e:
                print(f"❌ Error deleting {log_file}: {e}")

    # 2. Clean gemini histories (delete files >1MB)
    gemini_dir = Path("gemini_histories")
    if gemini_dir.exists():
        for history_file in gemini_dir.glob("*.json"):
            try:
                if history_file.stat().st_size > 1024 * 1024:  # 1MB
                    history_file.unlink()
                    print(f"✅ Deleted large history {history_file}")
            except Exception as e:
                print(f"❌ Error processing {history_file}: {e}")

    # 3. Clean gpt_history folder (delete everything inside)
    gpt_history_dir = Path("gpt_history")
    if gpt_history_dir.exists():
        for file in gpt_history_dir.glob("*"):
            try:
                if file.is_file():
                    file.unlink()
                elif file.is_dir():
                    shutil.rmtree(file)
                print(f"✅ Deleted {file}")
            except Exception as e:
                print(f"❌ Error deleting {file}: {e}")

    # 4. Clean cache, imagine_cache and downloads folders
    for folder_name in ["cache", "imagine_cache", "downloads"]:
        target_dir = Path(folder_name)
        if target_dir.exists():
            try:
                shutil.rmtree(target_dir)
                target_dir.mkdir(exist_ok=True)
                print(f"✅ Cleaned {folder_name}/")
            except Exception as e:
                print(f"❌ Error cleaning {folder_name}/: {e}")

    print("\n🧹 Cleanup completed!")

if __name__ == "__main__":
    cleanup_project()
