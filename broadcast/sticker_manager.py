import json
import os
from datetime import datetime
import threading

class StickerPackManager:
    def __init__(self, db_path="broadcast/sticker_packs.json"):
        self.db_path = db_path
        self.lock = threading.RLock()
        self._ensure_db()
        
    def _ensure_db(self):
        if not os.path.exists(self.db_path):
            self._save_data({"packs": {}})
            
    def _load_data_unsafe(self):
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"packs": {}}
            
    def _save_data(self, data):
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving sticker packs: {e}")

    def add_pack(self, user_id, pack_name, title=None):
        with self.lock:
            data = self._load_data_unsafe()
            uid = str(user_id)
            if uid not in data["packs"]:
                data["packs"][uid] = []
            
            # Check if exists
            for p in data["packs"][uid]:
                if p["name"] == pack_name:
                    # Update title if different and provided
                    if title and p.get("title") != title:
                        p["title"] = title
                        self._save_data(data)
                    return # Already exists
            
            new_pack = {
                "name": pack_name,
                "created_at": datetime.now().isoformat()
            }
            if title:
                new_pack["title"] = title
                
            data["packs"][uid].append(new_pack)
            self._save_data(data)
            
    def remove_pack(self, user_id, pack_name):
        with self.lock:
            data = self._load_data_unsafe()
            uid = str(user_id)
            if uid in data["packs"]:
                initial_len = len(data["packs"][uid])
                
                # Exact match on name
                data["packs"][uid] = [p for p in data["packs"][uid] if p["name"] != pack_name]
                
                self._save_data(data)
                return len(data["packs"][uid]) < initial_len
        return False

    def rename_pack(self, user_id, pack_name, new_title):
        with self.lock:
            data = self._load_data_unsafe()
            uid = str(user_id)
            if uid in data["packs"]:
                for p in data["packs"][uid]:
                    if p["name"] == pack_name:
                        p["title"] = new_title
                        self._save_data(data)
                        return True
        return False
        
    def get_user_packs(self, user_id):
        with self.lock:
            data = self._load_data_unsafe()
            return data["packs"].get(str(user_id), [])

    def get_all_data(self):
        with self.lock:
            return self._load_data_unsafe()
