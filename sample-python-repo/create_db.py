"""Initialize the database and add demo users for local development."""

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from database.db_handler import get_connection, initialize_database


def main():
    load_dotenv()
    initialize_database()
    conn = get_connection()
    try:
        for username, password in [('admin', 'admin123'), ('user1', 'pass123')]:
            conn.execute(
                '''INSERT INTO users (username, password_hash)
                   SELECT ?, ? WHERE NOT EXISTS (
                       SELECT 1 FROM users WHERE username = ?
                   )''',
                (username, generate_password_hash(password), username),
            )
        conn.commit()
    finally:
        conn.close()
    print('Database initialized with local demo users.')


if __name__ == '__main__':
    main()
