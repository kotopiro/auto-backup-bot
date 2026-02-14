from flask import Flask, render_template, request, redirect, session, jsonify
import aiohttp
import asyncio
import os
import secrets
from urllib.parse import urlencode

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))

# Configuration
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
DISCORD_REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI', 'https://school-rekisi.kesug.com/callback')
TURNSTILE_SITE_KEY = os.getenv('TURNSTILE_SITE_KEY')
TURNSTILE_SECRET_KEY = os.getenv('TURNSTILE_SECRET_KEY')
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', '')

# Discord OAuth2 URLs
DISCORD_API_BASE = 'https://discord.com/api/v10'
DISCORD_AUTH_URL = 'https://discord.com/api/oauth2/authorize'
DISCORD_TOKEN_URL = f'{DISCORD_API_BASE}/oauth2/token'

# Bot webhook for data storage
BOT_WEBHOOK_URL = os.getenv('BOT_WEBHOOK_URL')


async def verify_turnstile(token: str, ip: str) -> bool:
    """
    Verify Cloudflare Turnstile token
    
    Args:
        token: Turnstile response token
        ip: User IP address
        
    Returns:
        True if verification successful
    """
    async with aiohttp.ClientSession() as session:
        data = {
            'secret': TURNSTILE_SECRET_KEY,
            'response': token,
            'remoteip': ip
        }
        
        async with session.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data=data
        ) as resp:
            result = await resp.json()
            return result.get('success', False)


@app.route('/')
def index():
    """Landing page with Turnstile challenge"""
    return render_template('index.html', site_key=TURNSTILE_SITE_KEY)


@app.route('/verify', methods=['POST'])
def verify():
    """Verify Turnstile and redirect to Discord OAuth2"""
    turnstile_token = request.form.get('cf-turnstile-response')
    
    if not turnstile_token:
        return jsonify({'error': 'Missing Turnstile token'}), 400
    
    # Verify Turnstile
    ip = request.headers.get('CF-Connecting-IP', request.remote_addr)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    is_valid = loop.run_until_complete(verify_turnstile(turnstile_token, ip))
    loop.close()
    
    if not is_valid:
        return jsonify({'error': 'Turnstile verification failed'}), 403
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    
    # Build Discord OAuth2 URL
    params = {
        'client_id': DISCORD_CLIENT_ID,
        'redirect_uri': DISCORD_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'identify guilds.join',
        'state': state
    }
    
    auth_url = f"{DISCORD_AUTH_URL}?{urlencode(params)}"
    
    return jsonify({'redirect': auth_url})


@app.route('/callback')
def callback():
    """OAuth2 callback - exchange code for tokens"""
    code = request.args.get('code')
    state = request.args.get('state')
    
    # Verify state
    if not state or state != session.get('oauth_state'):
        return render_template('error.html', message='Invalid state'), 403
    
    if not code:
        return render_template('error.html', message='Missing authorization code'), 400
    
    # Exchange code for tokens
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(exchange_code(code))
    loop.close()
    
    if 'error' in result:
        return render_template('error.html', message=result['error']), 400
    
    # Get user info
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    user_info = loop.run_until_complete(get_user_info(result['access_token']))
    loop.close()
    
    if 'error' in user_info:
        return render_template('error.html', message='Failed to get user info'), 400
    
    # Send data to bot for storage
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(send_to_bot({
        'user_id': user_info['id'],
        'username': user_info['username'],
        'discriminator': user_info.get('discriminator', '0'),
        'avatar': user_info.get('avatar'),
        'access_token': result['access_token'],
        'refresh_token': result['refresh_token'],
        'expires_at': result['expires_in']
    }))
    loop.close()
    
    return render_template('success.html', username=user_info['username'])


async def exchange_code(code: str) -> dict:
    """Exchange authorization code for tokens"""
    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': DISCORD_REDIRECT_URI
    }
    
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(DISCORD_TOKEN_URL, data=data, headers=headers) as resp:
            return await resp.json()


async def get_user_info(access_token: str) -> dict:
    """Get user information from Discord"""
    headers = {'Authorization': f'Bearer {access_token}'}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{DISCORD_API_BASE}/users/@me', headers=headers) as resp:
            return await resp.json()


async def send_to_bot(data: dict):
    """Send user data to bot via webhook"""
    if not BOT_WEBHOOK_URL:
        return
    
    async with aiohttp.ClientSession() as session:
        async with session.post(BOT_WEBHOOK_URL, json=data) as resp:
            return await resp.json()


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})


@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Receive user data from bot"""
    data = request.json
    
    # Verify webhook secret
    auth_header = request.headers.get('Authorization')
    if WEBHOOK_SECRET and auth_header != f"Bearer {WEBHOOK_SECRET}":
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Store data (you can send this to a database or message queue)
    # For now, we'll just log it
    print(f"Received user data: {data.get('user_id')}")
    
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    import os
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8000)))

