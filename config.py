import base64
import os

def decode_key(encoded_key):
    try:
        return base64.b64decode(encoded_key).decode('utf-8')
    except Exception as e:
        print(f"Error decoding key: {e}")
        return None

_ENCODED_OPENROUTER_API_KEY = "c2stb3ItdjEtZDQ4YzhkMWM1Y2JmZDM4ZGZiMDNlMzZjYTk4ZmNiYTM2ODJiMDk1N2Y2ZmViMjEwN2VjODFmMGQzMjg5YmY5OA=="
_ENCODED_GROQ_API_KEY = "Z3NrX08xenlyQ2dub0xPNWtGS3ZjV3FDV0dkeWIzRlk1YTZxMTBuR3o2ajBsN0xnTGl2UmJqeVA="
_ENCODED_BOT_TOKEN = "ODI4OTQyODQ5NTpBQUZydF9uTllkdFdnSzNnZWQzb3MwZ2g4dlFUUkpGWEY4Yw=="
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", decode_key(_ENCODED_OPENROUTER_API_KEY))
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", decode_key(_ENCODED_GROQ_API_KEY))
BOT_TOKEN = os.environ.get("BOT_TOKEN", decode_key(_ENCODED_BOT_TOKEN))

CHANNEL_ID = -1003487277001
ID_SALT = 's3cr3t_s4lt_f0r_f1l3sh4r3_b0t' 
MIN_LENGTH = 10
