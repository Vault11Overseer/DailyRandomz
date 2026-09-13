import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from backend import app as module


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        module.DATABASE = str(Path(self.temp.name) / 'test.db')
        self.client = TestClient(module.app)
        self.client.__enter__()
        self.client.headers['X-Randomz-Request'] = '1'
        self.credentials = {'username': 'explorer', 'password': 'a long test password'}

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def register(self):
        result = self.client.post('/api/auth/register', json=self.credentials)
        self.assertEqual(result.status_code, 201)
        return result

    def test_guest_access_and_protected_routes(self):
        self.assertIsNone(self.client.get('/api/me').json())
        self.assertIsNotNone(self.client.post('/api/facts/random').json()['fact'])
        self.assertEqual(self.client.get('/api/favorites').status_code, 401)
        self.assertEqual(self.client.patch('/api/settings', json={'avoid_repeats': False}).status_code, 401)
        self.assertEqual(self.client.put('/api/favorites/1').status_code, 401)

    def test_session_login_logout_and_expiry(self):
        result = self.register()
        self.assertIn('HttpOnly', result.headers['set-cookie'])
        self.assertIn('SameSite=strict', result.headers['set-cookie'])
        token = self.client.cookies.get(module.COOKIE)
        self.assertEqual(self.client.get('/api/me').json()['username'], 'explorer')
        self.client.post('/api/auth/logout')
        self.client.cookies.set(module.COOKIE, token, path='/api')
        self.assertIsNone(self.client.get('/api/me').json())
        self.client.cookies.clear()
        self.assertEqual(self.client.post('/api/auth/login', json={**self.credentials, 'password': 'incorrect password'}).status_code, 401)
        self.assertEqual(self.client.post('/api/auth/login', json=self.credentials).status_code, 200)
        with module.db() as c:
            c.execute('UPDATE sessions SET expires=0')
        self.assertIsNone(self.client.get('/api/me').json())

    def test_no_repeats_exhaustion_reset_and_settings(self):
        self.register()
        ids = [self.client.post('/api/facts/random').json()['fact']['id'] for _ in module.FACTS]
        self.assertEqual(len(set(ids)), len(module.FACTS))
        self.assertTrue(self.client.post('/api/facts/random').json()['exhausted'])
        self.client.patch('/api/settings', json={'avoid_repeats': False})
        self.assertFalse(self.client.get('/api/me').json()['avoid_repeats'])
        self.assertIsNotNone(self.client.post('/api/facts/random').json()['fact'])
        self.client.patch('/api/settings', json={'avoid_repeats': True})
        self.client.delete('/api/history')
        self.assertIsNotNone(self.client.post('/api/facts/random').json()['fact'])

    def test_favorites_are_idempotent_and_isolated(self):
        self.register()
        for _ in range(2):
            self.assertEqual(self.client.put('/api/favorites/1').status_code, 200)
        self.assertEqual(len(self.client.get('/api/favorites').json()), 1)
        self.assertEqual(self.client.put('/api/favorites/9999').status_code, 404)
        self.client.post('/api/auth/logout')
        self.client.post('/api/auth/register', json={**self.credentials, 'username': 'someone_else'})
        self.assertEqual(self.client.get('/api/favorites').json(), [])
        self.client.delete('/api/favorites/1')
        self.client.post('/api/auth/login', json=self.credentials)
        self.assertEqual(len(self.client.get('/api/favorites').json()), 1)
        self.client.delete('/api/favorites/1')
        self.assertEqual(self.client.get('/api/favorites').json(), [])

    def test_validation_csrf_and_rate_limit(self):
        self.assertEqual(self.client.post('/api/auth/register', json={**self.credentials, 'password': 'short'}).status_code, 422)
        self.register()
        self.assertEqual(self.client.post('/api/auth/register', json=self.credentials).status_code, 409)
        self.assertEqual(self.client.post('/api/auth/logout', headers={'Origin': 'https://evil.example'}).status_code, 403)
        del self.client.headers['X-Randomz-Request']
        self.assertEqual(self.client.post('/api/auth/logout').status_code, 403)
        self.client.headers['X-Randomz-Request'] = '1'
        with module.db() as c:
            c.execute('UPDATE attempts SET count=20')
        self.assertEqual(self.client.post('/api/auth/login', json=self.credentials).status_code, 429)


if __name__ == '__main__':
    unittest.main()
