import json
from broadcast.sheets_manager import GoogleSheetsSync, SHEET_ID, SERVICE_ACCOUNT_JSON

def upload_initial_data():
    print("🚀 Starting initial data upload to Google Sheets...\n")
    
    try:
        # Initialize Sheets sync
        gs_sync = GoogleSheetsSync(SHEET_ID, SERVICE_ACCOUNT_JSON)
        gs_sync.ensure_sheets_exist()
        print("✅ Google Sheets initialized\n")
        
        # Load local data
        print("📂 Loading local data files...")
        with open("broadcast/handler_credits.json", "r", encoding='utf-8') as f:
            handler_credits_data = json.load(f)
        print(f"✅ Loaded handler_credits.json")
        
        with open("broadcast/bot_users.json", "r", encoding='utf-8') as f:
            bot_users_data = json.load(f)
        print(f"✅ Loaded bot_users.json\n")
        
        # Upload to Sheets
        print("📤 Uploading to Google Sheets...")
        
        # Clear existing sheets first
        try:
            sheets_to_clear = ['handler_credits', 'bot_users']
            for sheet_name in sheets_to_clear:
                sheet = gs_sync._get_sheet(sheet_name)
                if sheet:
                    try:
                        # Clear all rows except header
                        all_values = sheet.get_all_values()
                        if len(all_values) > 1:
                            sheet.delete_rows(2, len(all_values))
                            print(f"✅ Cleared {sheet_name} sheet")
                    except:
                        pass
        except Exception as e:
            print(f"⚠️ Could not clear sheets: {e}")
        
        # Upload handler_credits
        print("\n📊 Uploading handler credits...")
        gs_sync.push_handler_credits(handler_credits_data)
        print(f"✅ Handler credits uploaded ({len(handler_credits_data.get('credits_usage', {}))} users)")
        
        # Upload bot_users
        print("\n👥 Uploading bot users...")
        gs_sync.push_bot_users(bot_users_data)
        print(f"✅ Bot users uploaded ({len(bot_users_data.get('users', {}))} users)")
        
        print("\n" + "="*60)
        print("✨ Initial data upload completed successfully!")
        print("="*60)
        print("\nYou can now restart the bot.")
        print("On restart, it will pull fresh data from Google Sheets.")
        
    except Exception as e:
        print(f"\n❌ Error during upload: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    upload_initial_data()
