import json
import os
import gspread
from google.oauth2.service_account import Credentials
from typing import Dict, List, Optional
import threading
from datetime import datetime


# ============================================================================
# CONFIGURATION SECTION
# ============================================================================

# Sheet ID and Service Account Configuration
SHEET_ID = "1nmmO7lFg7kQfh7OIQ7fQzQTwPvjg3UMInaKbqJIYlRA"

SERVICE_ACCOUNT_JSON = {
    "type": "service_account",
    "project_id": "gemini-api-key-473807",
    "private_key_id": "44796f08c87a1a2aaeb1f2791f1412bc03514cc5",
    "private_key": (
        "-----BEGIN PRIVATE KEY-----\n"
        "MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQC38Rf+lzqZNTV4\n"
        "XLGrqCwMUpwzo43il6QjOxBwzYghb0C6b+UHz1m0TiavzFKFb5kQEUTX5nmDvL9v\n"
        "gkOMCchc+fRn49sNvEUUJthEzfy93jyhsvNJPEICOuRmloQenXvzaxpqrd26kAy1\n"
        "YIYagDeQONR7WDG0bnLBjjsKdOxMTAkA+2il6tlR0SX3Rai+yqqULJoPy0vJNI1R\n"
        "YB564Q9rnTKkoW4WYt7Nuqez2gu3VJVIr1vZ4hsAgxAVV/exYI7ebSik9Nv+cTYx\n"
        "tpbj3idP+U3kmN5lTmTK+sLR4LYigpnPNXccebveQey6JMgOr91cdkwDRuUZGonD\n"
        "rhDRj0x5AgMBAAECggEAFXFtsqg+lI23ZgioTbKVL/qRaxOt/rRe1hyUlhHfxMYL\n"
        "bbCNqpNpibNynxvaouOXnF/m/qRHlivyxTUSWsjpKq2Y6GOPrdI821SL8blxtVCr\n"
        "EM6jve3gZBIpfiwdytPhF0dtFPKf3pfcY2iVOZGo6I83dgmaAca+agICr/1hbqNb\n"
        "tUpHrtlis6E/VzTtsraGBhxu32leDSKQMBLMs5CIbfkaBvpRH7hDx74k0e3wK8T+\n"
        "30RhqL4DsT/4l3as28bk2VlqQoma+fFU6iwkBgg9rJxsTTXAgA8q40f+lnvezS+H\n"
        "2c3Jpf+1tNtbQv8Gd6rO06PfioDqNwnMSyOhObNpgQKBgQDu481P6nielB3fm6pq\n"
        "B9OMBBdw5sEgWV8PBlZ27MP4bJNZ3VMjPztC0mtujnp65j5WrpDl0VfEtNjm97bH\n"
        "s7sx3yQ2rwAbijkaKmYu6L0nct884xMXoK8Cdd8w5cJYmOdEJopAy70W2FJJLzS2\n"
        "l95ajEM+OwhgG1PVydsSXziVlQKBgQDFHciaKzFOaNwwXIke08ZOqKmAJuMeFXnn\n"
        "0k8w260sfcfnQFMdM5cBk8XSebh9/sCk2/QTe4zefwKPREFYHjlQHz4aCanHCWLF\n"
        "Dw1zb1NFZb5bvaJEkBfp4+N7dL+P5eBTeDqClh6hp0Y4Gs+VZRVhoCAuzu416hK4\n"
        "orTTHCKaVQKBgAgE7ad5H4NzRW10NExK5vcUTBUmKeWEGoTOmah0Wj/EpU2m+Ft+\n"
        "i+a6WZDkh4gIop8WTRbp6CBaUc2vExuxFN+ftf9/8Gj8Qt51/eglN/RTDttkZAev\n"
        "BTD38/4YOGXw/BJ1mL6EGFzj9h8uzn4yquwvOTKlmKphQHc0x33eZG/hAoGAQIAX\n"
        "dUMu9i5f5r9Q6zJ3EKQmGtYeuWhjpJTv7tfjWcyqziQBTmvkPNLjB5Vm5munFAsZ\n"
        "WgqytNewubqm+zOgo3QluRVyZbvPgxYC28QQ5oN9f72UzISuHo3AkVRJnsek2Qtd\n"
        "cf+3dEQtOQyk4ojaL0DbZxW1YxT+HUa4juAE/qUCgYBHivZl2sJAlRgp8pFda1ML\n"
        "wjJNZkOJ6LNzPbxIPBECF/3MM5WFAU2IRC5WnOH/qqZNerHkk7f2r5TMvQkd5HdV\n"
        "hCBZCvjiUGnWk5KY9ss8xWtTggd+5DYN256vw9C/DtpOysBVFSNNacAtVT+eJdZD\n"
        "tpTmbvASFBujzyTq3rwlhA==\n"
        "-----END PRIVATE KEY-----\n"
    ),
    "client_email": "sheet-bot@gemini-api-key-473807.iam.gserviceaccount.com",
    "client_id": "110414284749868272392",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/sheet-bot%40gemini-api-key-473807.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}


# ============================================================================
# GOOGLE SHEETS SYNC CLASS
# ============================================================================

class GoogleSheetsSync:
    def __init__(self, sheet_id: str, service_account_json: dict):
        """
        Initialize Google Sheets sync manager.
        
        Args:
            sheet_id: Google Sheets ID
            service_account_json: Service account credentials dictionary
        """
        self.sheet_id = sheet_id
        self.service_account_json = service_account_json
        self.lock = threading.RLock()
        self.client = None
        self.spreadsheet = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Google Sheets API client"""
        try:
            scopes = ['https://www.googleapis.com/auth/spreadsheets']
            
            # Ensure private_key has proper newline formatting
            config = self.service_account_json.copy()
            if 'private_key' in config and isinstance(config['private_key'], str):
                pk = config['private_key']
                if '\\n' in pk and '\n' not in pk:
                    pk = pk.replace('\\n', '\n')
                elif pk.count('\n') < 5:  # If too few newlines, it's probably escaped
                    pk = pk.replace('\\n', '\n')
                config['private_key'] = pk
            
            creds = Credentials.from_service_account_info(
                config,
                scopes=scopes
            )
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(self.sheet_id)
            print("✅ Google Sheets client initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize Google Sheets client: {type(e).__name__}: {str(e)[:100]}")
            self.client = None
            self.spreadsheet = None
    
    def ensure_sheets_exist(self):
        """Ensure required sheets exist in the spreadsheet"""
        if not self.spreadsheet:
            print("⚠️ Google Sheets not available")
            return False
        
        try:
            existing_sheets = {ws.title for ws in self.spreadsheet.worksheets()}
            required_sheets = ['bot_users', 'sticker_packs']
            
            for sheet_name in required_sheets:
                if sheet_name not in existing_sheets:
                    self.spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
                    print(f"✅ Created sheet: {sheet_name}")
            
            return True
        except Exception as e:
            print(f"❌ Error ensuring sheets exist: {e}")
            return False
    
    def _get_sheet(self, sheet_name: str):
        """Get worksheet by name"""
        if not self.spreadsheet:
            return None
        try:
            return self.spreadsheet.worksheet(sheet_name)
        except Exception as e:
            print(f"❌ Error getting sheet {sheet_name}: {e}")
            return None
    
    def push_bot_users(self, bot_users_data: dict) -> bool:
        if not self.spreadsheet:
            return False
        
        try:
            sheet = self._get_sheet('bot_users')
            if not sheet:
                return False
            
            # Clear existing data
            sheet.clear()
            
            # Add headers
            headers = ['user_id', 'username', 'first_name', 'last_name', 'last_interaction']
            sheet.append_row(headers)
            
            # Add user data
            rows = []
            for user_id_str, user_info in bot_users_data.get('users', {}).items():
                row = [
                    str(user_info.get('user_id', '')),
                    str(user_info.get('username', '')).replace('\x00', ''),
                    str(user_info.get('first_name', '')).replace('\x00', ''),
                    str(user_info.get('last_name', '')).replace('\x00', ''),
                    str(user_info.get('last_interaction', '')).replace('\x00', '')
                ]
                rows.append(row)
            
            if rows:
                sheet.append_rows(rows)
            
            print(f"✅ Pushed {len(rows)} users to Google Sheets")
            return True
        except Exception as e:
            print(f"❌ Error pushing bot_users: {type(e).__name__}: {str(e)[:100]}")
            return False
    
    def push_sticker_packs(self, stickers_data: dict) -> bool:
        if not self.spreadsheet:
            return False
        
        try:
            sheet = self._get_sheet('sticker_packs')
            if not sheet:
                return False
            
            sheet.clear()
            headers = ['user_id', 'pack_name', 'pack_title', 'created_at']
            sheet.append_row(headers)
            
            rows = []
            for user_id, packs in stickers_data.get('packs', {}).items():
                for pack in packs:
                    rows.append([
                        str(user_id),
                        pack.get('name', ''),
                        pack.get('title', ''),
                        pack.get('created_at', '')
                    ])
            
            if rows:
                sheet.append_rows(rows)
            print(f"✅ Pushed {len(rows)} sticker packs to Google Sheets")
            return True
        except Exception as e:
            print(f"❌ Error pushing sticker_packs: {e}")
            return False
    
    def pull_bot_users(self) -> Optional[dict]:
        if not self.spreadsheet:
            return None
        
        try:
            sheet = self._get_sheet('bot_users')
            if not sheet:
                return None
            
            all_records = sheet.get_all_records()
            if not all_records:
                return {"users": {}}
            
            users = {}
            for record in all_records:
                user_id = str(int(record.get('user_id', 0)))
                if user_id == '0':
                    continue
                
                users[user_id] = {
                    'user_id': int(user_id),
                    'username': record.get('username', ''),
                    'first_name': record.get('first_name', ''),
                    'last_name': record.get('last_name', ''),
                    'last_interaction': record.get('last_interaction', ''),
                }
            
            print(f"✅ Pulled {len(users)} users from Google Sheets")
            return {"users": users}
        except Exception as e:
            print(f"❌ Error pulling bot_users: {e}")
            return None
    
    def pull_sticker_packs(self) -> Optional[dict]:
        if not self.spreadsheet:
            return None
        try:
            sheet = self._get_sheet('sticker_packs')
            if not sheet:
                return None
            
            records = sheet.get_all_records()
            data = {"packs": {}}
            for r in records:
                uid = str(r['user_id'])
                if uid not in data['packs']:
                    data['packs'][uid] = []
                data['packs'][uid].append({
                    "name": r['pack_name'],
                    "title": r.get('pack_title', ''),
                    "created_at": r['created_at']
                })
            print(f"✅ Pulled sticker packs for {len(data['packs'])} users")
            return data
        except Exception as e:
            print(f"❌ Error pulling sticker packs: {e}")
            return {"packs": {}}

    def sync_all_data(self, bot_users_data: dict, stickers_data: dict = None) -> bool:
        """Sync all data to Google Sheets"""
        with self.lock:
            try:
                self.push_bot_users(bot_users_data)
                if stickers_data:
                    self.push_sticker_packs(stickers_data)
                return True
            except Exception as e:
                print(f"❌ Error syncing all data: {e}")
                return False

    def sync_all_data_async(self, bot_users_data: dict, stickers_data: dict = None):
        """Sync data to Google Sheets in background thread (non-blocking)"""
        def _sync():
            try:
                self.sync_all_data(bot_users_data, stickers_data)
            except Exception as e:
                print(f"⚠️ Background sync error: {e}")

        thread = threading.Thread(target=_sync, daemon=True)
        thread.start()
