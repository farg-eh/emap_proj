import datetime

# SETTINGS ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
UPLOAD_FOLDER = "images"
THUMBS_FOLDER = 'images/thumbs'
ALLOWED_EXT = {'jpg', 'jpeg', 'png'}
MAX_SIZE = 8 * 1024 * 1024  # 8MB
ADMINS = [1]


# some utility functions ~~~~~~~~~~~~~~~~~~~
def token_valid(db, token):
    if not token: return False

    cursor = db.cursor()
    # Get current time in same format as stored


    current_time = datetime.datetime.now().isoformat()

    # Use SQLite's datetime() function for proper date comparison
    cursor.execute("""
                   SELECT 1
                   FROM tokens
                   WHERE token = ?
                     AND datetime(expires_at) > datetime(?)
                   """, (token, current_time))
    result = cursor.fetchone()
    return bool(result)

def get_user_id_from_token(db, token):
    if not token_valid(db, token): raise Exception("not valid token")
    cursor = db.cursor()
    # find the user id using the provided token
    cursor.execute("SELECT users.user_id FROM users inner join tokens on users.user_id = tokens.user_id  where token = ?", (token,))
    row = cursor.fetchone()
    user_id = row[0]
    return user_id


def is_admin(db, token):
    if not token_valid(db, token): return False
    user_id = get_user_id_from_token(db, token)
    return user_id in ADMINS
