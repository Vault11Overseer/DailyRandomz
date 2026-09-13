"""DailyRandomz API. Run with uv run uvicorn backend.app:app --reload."""
from contextlib import contextmanager, asynccontextmanager
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import sqlite3
import time

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

DATABASE = os.getenv('DATABASE_PATH', str(Path(__file__).resolve().parents[2] / 'randomz.db'))
ORIGIN = os.getenv('APP_ORIGIN', 'http://localhost:5173')
SECURE = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
COOKIE = 'randomz_session'
TTL = 60 * 60 * 24 * 30
FACTS = [
    ('Space', 'Sunlight takes about eight minutes to reach Earth.'),
    ('Nature', 'Octopuses have three hearts.'),
    ('Space', 'Venus takes longer to rotate once than to orbit the Sun.'),
    ('Nature', 'Butterflies taste with their feet.'),
    ('Science', 'Sound cannot travel through a vacuum.'),
    ('Space', 'The Moon reflects sunlight; it does not produce its own light.'),
    ('Science', 'A triangle’s interior angles add up to 180 degrees on a flat plane.'),
    ('Nature', 'An adult insect has six legs.'),
    ('Science', 'Water expands when it freezes.'),
    ('Space', 'Jupiter is the largest planet in our solar system.'),
    ('Nature', 'Whales are mammals and breathe air.'),
    ('Science', 'A leap year has 366 days.'),
]

@contextmanager
def db():
    connection = sqlite3.connect(DATABASE, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    try:
        with connection:
            yield connection
    finally:
        connection.close()

@asynccontextmanager
async def lifespan(app):
    with db() as c:
        c.execute('PRAGMA journal_mode = WAL')
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL, avoid_repeats INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY, user_id INTEGER REFERENCES users(id), expires INTEGER);
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY, category TEXT NOT NULL, text TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS seen (
            user_id INTEGER REFERENCES users(id), fact_id INTEGER REFERENCES facts(id),
            PRIMARY KEY (user_id, fact_id));
        CREATE TABLE IF NOT EXISTS favorites (
            user_id INTEGER REFERENCES users(id), fact_id INTEGER REFERENCES facts(id),
            PRIMARY KEY (user_id, fact_id));
        CREATE TABLE IF NOT EXISTS attempts (key TEXT PRIMARY KEY, count INTEGER, resets INTEGER);
        ''')
        c.executemany('INSERT OR IGNORE INTO facts VALUES (?, ?, ?)',
                      [(i, *fact) for i, fact in enumerate(FACTS, 1)])
    yield

app = FastAPI(title='DailyRandomz', lifespan=lifespan)

@app.middleware('http')
async def protect(request, call_next):
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        if request.headers.get('origin') not in (None, ORIGIN) or request.headers.get('x-randomz-request') != '1':
            return JSONResponse({'detail': 'Request origin rejected.'}, status_code=403)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()

def current_user(c, request, required=False):
    user = c.execute('''SELECT users.* FROM users JOIN sessions ON users.id = sessions.user_id
                        WHERE token = ? AND expires > ?''',
                     (token_hash(request.cookies.get(COOKIE, '')), time.time())).fetchone()
    if required and not user:
        raise HTTPException(401, 'Please sign in first.')
    return user

def public_user(user):
    return {'username': user['username'], 'avoid_repeats': bool(user['avoid_repeats'])} if user else None

def password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()

class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r'^[a-zA-Z0-9_]+$')
    password: str = Field(min_length=12, max_length=128)

class Settings(BaseModel):
    avoid_repeats: bool

def authenticate(data, request, response, register=False):
    # Persist throttling across restarts. Deploy a shared edge limiter for multiple instances.
    key = request.client.host if request.client else 'unknown'
    with db() as c:
        now = int(time.time())
        c.execute('DELETE FROM attempts WHERE resets < ?', (now,))
        c.execute('INSERT INTO attempts VALUES (?, 1, ?) ON CONFLICT(key) DO UPDATE SET count=count+1', (key, now + 300))
        count = c.execute('SELECT count FROM attempts WHERE key=?', (key,)).fetchone()[0]
    if count > 20:
        raise HTTPException(429, 'Too many sign-in attempts. Try again in five minutes.')
    with db() as c:
        username = data.username.lower()
        if register:
            salt = secrets.token_hex(16)
            encoded = salt + ':' + password_hash(data.password, salt)
            try:
                c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, encoded))
            except sqlite3.IntegrityError:
                raise HTTPException(409, 'That username is already taken.') from None
        user = c.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        salt, expected = user['password'].split(':') if user else ('00' * 16, '00' * 64)
        valid = hmac.compare_digest(password_hash(data.password, salt), expected)
        if not user or not valid:
            raise HTTPException(401, 'Incorrect username or password.')
        token = secrets.token_urlsafe(32)
        c.execute('DELETE FROM sessions WHERE expires < ? OR token = ?',
                  (time.time(), token_hash(request.cookies.get(COOKIE, ''))))
        c.execute('INSERT INTO sessions VALUES (?, ?, ?)', (token_hash(token), user['id'], int(time.time()) + TTL))
        response.set_cookie(COOKIE, token, max_age=TTL, httponly=True, secure=SECURE, samesite='strict', path='/api')
        return public_user(user)

@app.post('/api/auth/register', status_code=201)
def register(data: Credentials, request: Request, response: Response):
    return authenticate(data, request, response, True)

@app.post('/api/auth/login')
def login(data: Credentials, request: Request, response: Response):
    return authenticate(data, request, response)

@app.post('/api/auth/logout')
def logout(request: Request, response: Response):
    with db() as c:
        c.execute('DELETE FROM sessions WHERE token=?', (token_hash(request.cookies.get(COOKIE, '')),))
    response.delete_cookie(COOKIE, path='/api', secure=SECURE, httponly=True, samesite='strict')
    return {'ok': True}

@app.get('/api/me')
def me(request: Request):
    with db() as c:
        return public_user(current_user(c, request))

@app.post('/api/facts/random')
def random_fact(request: Request):
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        user = current_user(c, request)
        if user and user['avoid_repeats']:
            fact = c.execute('SELECT * FROM facts WHERE id NOT IN (SELECT fact_id FROM seen WHERE user_id=?) ORDER BY RANDOM() LIMIT 1', (user['id'],)).fetchone()
        else:
            fact = c.execute('SELECT * FROM facts ORDER BY RANDOM() LIMIT 1').fetchone()
        if not fact:
            return {'fact': None, 'exhausted': True}
        saved = False
        if user:
            c.execute('INSERT OR IGNORE INTO seen VALUES (?, ?)', (user['id'], fact['id']))
            saved = bool(c.execute('SELECT 1 FROM favorites WHERE user_id=? AND fact_id=?', (user['id'], fact['id'])).fetchone())
        return {'fact': dict(fact) | {'saved': saved}, 'exhausted': False}

@app.delete('/api/history')
def reset_history(request: Request):
    with db() as c:
        user = current_user(c, request, True)
        c.execute('DELETE FROM seen WHERE user_id=?', (user['id'],))
    return {'ok': True}

@app.patch('/api/settings')
def settings(data: Settings, request: Request):
    with db() as c:
        user = current_user(c, request, True)
        c.execute('UPDATE users SET avoid_repeats=? WHERE id=?', (data.avoid_repeats, user['id']))
        return {'username': user['username'], 'avoid_repeats': data.avoid_repeats}

@app.get('/api/favorites')
def favorites(request: Request):
    with db() as c:
        user = current_user(c, request, True)
        return [dict(row) for row in c.execute('SELECT facts.* FROM facts JOIN favorites ON facts.id=fact_id WHERE user_id=? ORDER BY facts.id DESC', (user['id'],))]

@app.put('/api/favorites/{fact_id}')
def save(fact_id: int, request: Request):
    with db() as c:
        user = current_user(c, request, True)
        if not c.execute('SELECT 1 FROM facts WHERE id=?', (fact_id,)).fetchone():
            raise HTTPException(404, 'Fact not found.')
        c.execute('INSERT OR IGNORE INTO favorites VALUES (?, ?)', (user['id'], fact_id))
    return {'ok': True}

@app.delete('/api/favorites/{fact_id}')
def unsave(fact_id: int, request: Request):
    with db() as c:
        user = current_user(c, request, True)
        c.execute('DELETE FROM favorites WHERE user_id=? AND fact_id=?', (user['id'], fact_id))
    return {'ok': True}
