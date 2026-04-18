"""
Language preference stored as a 'lang' field inside each user's record
in broadcast/bot_users.json — no separate file needed.

Call init(user_db) once after UserDatabase is created (done in main.py).
"""
_user_db = None


def init(user_db):
    """Wire lang_manager to the shared UserDatabase instance."""
    global _user_db
    _user_db = user_db


def get_lang(user_id) -> str:
    """Return 'en' or 'bn'. Defaults to 'en' if not yet set."""
    if _user_db is None:
        return "en"
    user = _user_db.get_user(user_id)
    if user:
        return user.get("lang", "en")
    return "en"


def set_lang(user_id, lang: str):
    """Persist language choice ('en' or 'bn') in bot_users.json."""
    if _user_db is None:
        return
    _user_db.update_user_field(user_id, "lang", lang)


def has_lang_set(user_id) -> bool:
    """True if the user has explicitly selected a language before."""
    if _user_db is None:
        return False
    user = _user_db.get_user(user_id)
    return user is not None and "lang" in user
