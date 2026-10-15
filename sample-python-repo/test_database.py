import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from werkzeug.security import check_password_hash

from database.db_handler import execute_query, initialize_database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.path = str(Path(self.temp_dir.name) / 'users.db')
        env = patch.dict(os.environ, {'DATABASE_PATH': self.path, 'SECRET_KEY': 'test-only'})
        env.start()
        self.addCleanup(env.stop)

    def test_startup_creates_table_and_user_endpoint_works(self):
        from app import app

        initialize_database()
        execute_query('INSERT INTO users (username) VALUES (?)', ('admin',))
        response = app.test_client().get('/user/admin')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [1, 'admin'])

    def test_demo_setup_can_repeat_and_delete_uses_same_database(self):
        from app import app
        from create_db import main

        main()
        main()
        self.assertEqual(execute_query('SELECT COUNT(*) FROM users')[0][0], 2)
        client = app.test_client()
        password_hash = execute_query('SELECT password_hash FROM users WHERE username = ?', ('admin',))[0][0]
        self.assertTrue(check_password_hash(password_hash, 'admin123'))
        response = client.get('/admin/delete?id=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(execute_query('SELECT id FROM users WHERE username = ?', ('admin',)), [])

    def test_legacy_passwords_are_migrated_without_losing_users(self):
        with closing(sqlite3.connect(self.path)) as conn:
            conn.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)')
            conn.execute("INSERT INTO users VALUES (7, 'existing', 'original-password')")
            conn.commit()
        initialize_database()
        initialize_database()
        user = execute_query('SELECT id, username, password_hash FROM users')[0]
        self.assertEqual(user[:2], (7, 'existing'))
        self.assertTrue(check_password_hash(user[2], 'original-password'))
        self.assertNotIn('password', [row[1] for row in execute_query('PRAGMA table_info(users)')])

    def test_login_returns_signed_token_and_rejects_wrong_password(self):
        import jwt
        from app import app, SECRET_KEY
        from create_db import main

        main()
        client = app.test_client()
        response = client.post('/login', json={'username': 'admin', 'password': 'admin123'})
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body['status'], 'success')
        payload = jwt.decode(body['token'], SECRET_KEY, algorithms=['HS256'])
        self.assertEqual(payload['user_id'], 1)
        self.assertIn('exp', payload)
        response = client.post('/login', json={'username': 'admin', 'password': 'incorrect'})
        self.assertEqual(response.status_code, 401)


if __name__ == '__main__':
    unittest.main()
