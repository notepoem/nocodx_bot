import json
import threading
from typing import List, Dict, Optional
from datetime import datetime
import os
import tempfile
import shutil

class UserDatabase:
    def __init__(self, db_path: str = "bot_users.json"):
        self.db_path = db_path
        self.lock = threading.RLock()
        self._init_db()
    
    def _init_db(self):
        if not os.path.exists(self.db_path):
            with self.lock:
                self._save_data_unsafe({"users": {}}, create_backup=False)
    
    def _try_load_backup(self) -> Optional[dict]:
        backup_files = [
            f"{self.db_path}.backup",
            f"{self.db_path}.corrupted",
            f"{self.db_path}.invalid"
        ]
        
        for backup_path in backup_files:
            if os.path.exists(backup_path):
                try:
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, dict) and "users" in data:
                            print(f"✅ Successfully loaded backup from: {backup_path}")
                            return data
                except Exception as e:
                    print(f"⚠️ Failed to load backup {backup_path}: {e}")
                    continue
        
        return None
    
    def _load_data_unsafe(self) -> dict:
        try:
            if not os.path.exists(self.db_path):
                backup_data = self._try_load_backup()
                if backup_data:
                    return backup_data
                return {"users": {}}
            
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, dict) or "users" not in data:
                    print("⚠️ Warning: Invalid database structure")
                    backup_path = f"{self.db_path}.invalid"
                    shutil.copy2(self.db_path, backup_path)
                    print(f"⚠️ Backed up invalid file to: {backup_path}")
                    
                    backup_data = self._try_load_backup()
                    if backup_data:
                        self._save_data_unsafe(backup_data, create_backup=False)
                        return backup_data
                    
                    return {"users": {}}
                return data
        except json.JSONDecodeError as e:
            print(f"⚠️ Warning: JSON decode error: {e}")
            backup_path = f"{self.db_path}.corrupted"
            if os.path.exists(self.db_path):
                try:
                    shutil.copy2(self.db_path, backup_path)
                    print(f"⚠️ Backed up corrupted file to: {backup_path}")
                except Exception as backup_error:
                    print(f"⚠️ Failed to create backup: {backup_error}")
            
            backup_data = self._try_load_backup()
            if backup_data:
                self._save_data_unsafe(backup_data, create_backup=False)
                return backup_data
            
            return {"users": {}}
        except Exception as e:
            print(f"⚠️ Warning: Error loading database: {e}")
            
            backup_data = self._try_load_backup()
            if backup_data:
                return backup_data
            
            return {"users": {}}
    
    def _save_data_unsafe(self, data: dict, create_backup: bool = True):
        dir_path = os.path.dirname(self.db_path) or '.'
        
        if create_backup and os.path.exists(self.db_path):
            backup_path = f"{self.db_path}.backup"
            try:
                shutil.copy2(self.db_path, backup_path)
            except Exception as e:
                print(f"⚠️ Warning: Failed to create pre-write backup: {e}")
        
        temp_fd, temp_path = tempfile.mkstemp(dir=dir_path, suffix='.tmp', text=True)
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            shutil.move(temp_path, self.db_path)
        except Exception as e:
            print(f"❌ Error saving database: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise
    
    def add_or_update_user(self, user_id: int, username: Optional[str] = None, 
                          first_name: Optional[str] = None, last_name: Optional[str] = None):
        with self.lock:
            data = self._load_data_unsafe()
            user_id_str = str(user_id)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if user_id_str in data["users"]:
                data["users"][user_id_str].update({
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "last_interaction": now
                })
            else:
                data["users"][user_id_str] = {
                    "user_id": user_id,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_banned": False,
                    "first_interaction": now,
                    "last_interaction": now
                }
            
            self._save_data_unsafe(data, create_backup=False)
    
    def get_all_users(self) -> List[tuple]:
        with self.lock:
            data = self._load_data_unsafe()
            users = []
            for user_id_str, user_info in data["users"].items():
                users.append((
                    user_info.get("user_id"),
                    user_info.get("username"),
                    user_info.get("first_name"),
                    user_info.get("last_name")
                ))
            return users
    
    def get_user_count(self) -> int:
        with self.lock:
            data = self._load_data_unsafe()
            return len(data["users"])
    
    def get_user_info(self, user_id: int) -> Optional[Dict]:
        with self.lock:
            data = self._load_data_unsafe()
            return data["users"].get(str(user_id))

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Alias for get_user_info to maintain compatibility."""
        return self.get_user_info(user_id)

    def update_user_field(self, user_id: int, field: str, value):
        with self.lock:
            data = self._load_data_unsafe()
            user_id_str = str(user_id)
            if user_id_str in data["users"]:
                data["users"][user_id_str][field] = value
                self._save_data_unsafe(data, create_backup=False)

    def get_json_file_path(self) -> str:
        return self.db_path
    
    def get_json_content_safely(self) -> str:
        with self.lock:
            if not os.path.exists(self.db_path):
                return json.dumps({"users": {}}, ensure_ascii=False, indent=2)
            
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                print(f"❌ Error reading database file: {e}")
                return json.dumps({"users": {}, "error": str(e)}, ensure_ascii=False, indent=2)
