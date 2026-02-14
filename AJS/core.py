import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AJS:
    """
    Advanced Join System - Main Class
    
    Async Discord OAuth2 and Member Management
    """
    
    def __init__(
        self,
        bot_token: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        proxy: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: int = 2
    ):
        """
        Initialize AJS
        
        Args:
            bot_token: Discord Bot Token
            client_id: OAuth2 Client ID
            client_secret: OAuth2 Client Secret
            redirect_uri: OAuth2 Redirect URI
            proxy: Optional proxy URL
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries (seconds)
        """
        self.bot_token = bot_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.proxy = proxy
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # API endpoints
        self.api_base = "https://discord.com/api/v10"
        self.token_url = f"{self.api_base}/oauth2/token"
        
        # Session management
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Rate limit tracking
        self._rate_limits: Dict[str, Dict[str, Any]] = {}
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
        
    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            
    async def close(self):
        """Close aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
            
    async def _handle_rate_limit(self, endpoint: str):
        """Handle rate limiting"""
        if endpoint in self._rate_limits:
            rate_info = self._rate_limits[endpoint]
            reset_time = rate_info.get('reset_time')
            
            if reset_time and datetime.now() < reset_time:
                wait_time = (reset_time - datetime.now()).total_seconds()
                logger.warning(f"Rate limited on {endpoint}, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                
    async def _request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            data: Form data
            json_data: JSON data
            retry_count: Current retry count
            
        Returns:
            Response data or status code
        """
        await self._ensure_session()
        
        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                data=data,
                json=json_data,
                proxy=self.proxy
            ) as response:
                
                # Handle rate limiting
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', self.retry_delay))
                    logger.warning(f"Rate limited, retrying after {retry_after}s")
                    await asyncio.sleep(retry_after)
                    
                    if retry_count < self.max_retries:
                        return await self._request(
                            method, url, headers, data, json_data, retry_count + 1
                        )
                    
                # Update rate limit info
                if 'X-RateLimit-Reset' in response.headers:
                    reset_timestamp = float(response.headers['X-RateLimit-Reset'])
                    self._rate_limits[url] = {
                        'reset_time': datetime.fromtimestamp(reset_timestamp)
                    }
                
                # Return JSON for successful responses
                if response.status in [200, 201, 204]:
                    if response.status == 204:
                        return {"status": 204, "success": True}
                    return await response.json()
                    
                # Return status code for errors
                return {"status": response.status, "error": await response.text()}
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            
            if retry_count < self.max_retries:
                await asyncio.sleep(self.retry_delay)
                return await self._request(
                    method, url, headers, data, json_data, retry_count + 1
                )
            
            return {"status": 0, "error": str(e)}
    
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for tokens
        
        Args:
            code: OAuth2 authorization code
            
        Returns:
            Dict containing access_token, refresh_token, expires_in
        """
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri
        }
        
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        result = await self._request('POST', self.token_url, headers=headers, data=data)
        
        if 'access_token' in result:
            logger.info("Successfully exchanged code for tokens")
        else:
            logger.error(f"Failed to exchange code: {result}")
            
        return result
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token
        
        Args:
            refresh_token: OAuth2 refresh token
            
        Returns:
            Dict containing new access_token and refresh_token
        """
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        result = await self._request('POST', self.token_url, headers=headers, data=data)
        
        if 'access_token' in result:
            logger.info("Successfully refreshed token")
        else:
            logger.error(f"Failed to refresh token: {result}")
            
        return result
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information
        
        Args:
            access_token: OAuth2 access token
            
        Returns:
            Dict containing user information
        """
        headers = {'Authorization': f'Bearer {access_token}'}
        url = f"{self.api_base}/users/@me"
        
        result = await self._request('GET', url, headers=headers)
        
        if 'id' in result:
            logger.info(f"Retrieved user info: {result.get('username', 'Unknown')}")
        else:
            logger.error(f"Failed to get user info: {result}")
            
        return result
    
    async def add_guild_member(
        self,
        access_token: str,
        guild_id: str,
        user_id: str,
        nick: Optional[str] = None,
        roles: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Add member to guild
        
        Args:
            access_token: User's OAuth2 access token
            guild_id: Target guild ID
            user_id: User ID to add
            nick: Optional nickname
            roles: Optional list of role IDs
            
        Returns:
            Dict with status and result
        """
        headers = {
            'Authorization': f'Bot {self.bot_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.api_base}/guilds/{guild_id}/members/{user_id}"
        
        json_data = {'access_token': access_token}
        
        if nick:
            json_data['nick'] = nick
        if roles:
            json_data['roles'] = roles
            
        result = await self._request('PUT', url, headers=headers, json_data=json_data)
        
        status = result.get('status', 0)
        
        if status == 201:
            logger.info(f"Successfully added user {user_id} to guild {guild_id}")
        elif status == 204:
            logger.info(f"User {user_id} already in guild {guild_id}")
        else:
            logger.error(f"Failed to add member: {result}")
            
        return result
    
    async def add_guild_member_role(
        self,
        guild_id: str,
        user_id: str,
        role_id: str
    ) -> Dict[str, Any]:
        """
        Add role to guild member
        
        Args:
            guild_id: Guild ID
            user_id: User ID
            role_id: Role ID to add
            
        Returns:
            Dict with status
        """
        headers = {'Authorization': f'Bot {self.bot_token}'}
        url = f"{self.api_base}/guilds/{guild_id}/members/{user_id}/roles/{role_id}"
        
        result = await self._request('PUT', url, headers=headers)
        
        if result.get('status') == 204:
            logger.info(f"Added role {role_id} to user {user_id}")
        else:
            logger.error(f"Failed to add role: {result}")
            
        return result
    
    async def batch_add_members(
        self,
        members_data: List[Dict[str, Any]],
        guild_id: str,
        delay: float = 0.5
    ) -> Dict[str, Any]:
        """
        Add multiple members with rate limiting
        
        Args:
            members_data: List of member data dicts
            guild_id: Target guild ID
            delay: Delay between requests
            
        Returns:
            Dict with success/failure counts
        """
        results = {
            'success': 0,
            'failed': 0,
            'already_member': 0,
            'errors': []
        }
        
        for member in members_data:
            try:
                result = await self.add_guild_member(
                    access_token=member['access_token'],
                    guild_id=guild_id,
                    user_id=member['user_id'],
                    nick=member.get('nick'),
                    roles=member.get('roles')
                )
                
                status = result.get('status', 0)
                
                if status == 201:
                    results['success'] += 1
                elif status == 204:
                    results['already_member'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'user_id': member['user_id'],
                        'error': result.get('error', 'Unknown error')
                    })
                    
                await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error adding member {member.get('user_id')}: {e}")
                results['failed'] += 1
                results['errors'].append({
                    'user_id': member.get('user_id'),
                    'error': str(e)
                })
        
        logger.info(
            f"Batch add complete: {results['success']} success, "
            f"{results['already_member']} already members, "
            f"{results['failed']} failed"
        )
        
        return results
