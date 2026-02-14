"""
Discord API Wrapper
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class DiscordAPI:
    """
    Discord API wrapper for guild and member management
    """
    
    def __init__(
        self,
        bot_token: str,
        proxy: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: int = 2
    ):
        """
        Initialize Discord API
        
        Args:
            bot_token: Discord Bot Token
            proxy: Optional proxy URL
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries (seconds)
        """
        self.bot_token = bot_token
        self.proxy = proxy
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self.api_base = "https://discord.com/api/v10"
        
        self._session: Optional[aiohttp.ClientSession] = None
        self._rate_limits: Dict[str, Dict[str, Any]] = {}
    
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
        endpoint: str,
        headers: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            headers: Request headers
            json_data: JSON data
            retry_count: Current retry count
            
        Returns:
            Response data or status code
        """
        await self._ensure_session()
        
        url = f"{self.api_base}{endpoint}"
        
        if headers is None:
            headers = {}
        
        headers['Authorization'] = f'Bot {self.bot_token}'
        
        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
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
                            method, endpoint, headers, json_data, retry_count + 1
                        )
                
                # Update rate limit info
                if 'X-RateLimit-Reset' in response.headers:
                    reset_timestamp = float(response.headers['X-RateLimit-Reset'])
                    self._rate_limits[endpoint] = {
                        'reset_time': datetime.fromtimestamp(reset_timestamp)
                    }
                
                # Return JSON for successful responses
                if response.status in [200, 201, 204]:
                    if response.status == 204:
                        return {"status": 204, "success": True}
                    try:
                        return await response.json()
                    except:
                        return {"status": response.status, "success": True}
                
                # Return status code for errors
                try:
                    error_data = await response.json()
                except:
                    error_data = await response.text()
                
                return {"status": response.status, "error": error_data}
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            
            if retry_count < self.max_retries:
                await asyncio.sleep(self.retry_delay)
                return await self._request(
                    method, endpoint, headers, json_data, retry_count + 1
                )
            
            return {"status": 0, "error": str(e)}
    
    async def add_guild_member(
        self,
        guild_id: str,
        user_id: str,
        access_token: str,
        nick: Optional[str] = None,
        roles: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Add member to guild
        
        Args:
            guild_id: Target guild ID
            user_id: User ID to add
            access_token: User's OAuth2 access token
            nick: Optional nickname
            roles: Optional list of role IDs
            
        Returns:
            Dict with status and result
        """
        endpoint = f"/guilds/{guild_id}/members/{user_id}"
        
        json_data = {'access_token': access_token}
        
        if nick:
            json_data['nick'] = nick
        if roles:
            json_data['roles'] = roles
        
        result = await self._request('PUT', endpoint, json_data=json_data)
        
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
        endpoint = f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}"
        
        result = await self._request('PUT', endpoint)
        
        if result.get('status') == 204:
            logger.info(f"Added role {role_id} to user {user_id}")
        else:
            logger.error(f"Failed to add role: {result}")
        
        return result
    
    async def remove_guild_member_role(
        self,
        guild_id: str,
        user_id: str,
        role_id: str
    ) -> Dict[str, Any]:
        """
        Remove role from guild member
        
        Args:
            guild_id: Guild ID
            user_id: User ID
            role_id: Role ID to remove
            
        Returns:
            Dict with status
        """
        endpoint = f"/guilds/{guild_id}/members/{user_id}/roles/{role_id}"
        
        result = await self._request('DELETE', endpoint)
        
        if result.get('status') == 204:
            logger.info(f"Removed role {role_id} from user {user_id}")
        else:
            logger.error(f"Failed to remove role: {result}")
        
        return result
    
    async def get_guild_member(
        self,
        guild_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get guild member
        
        Args:
            guild_id: Guild ID
            user_id: User ID
            
        Returns:
            Member data
        """
        endpoint = f"/guilds/{guild_id}/members/{user_id}"
        
        result = await self._request('GET', endpoint)
        
        return result
    
    async def get_guild(self, guild_id: str) -> Dict[str, Any]:
        """
        Get guild information
        
        Args:
            guild_id: Guild ID
            
        Returns:
            Guild data
        """
        endpoint = f"/guilds/{guild_id}"
        
        result = await self._request('GET', endpoint)
        
        return result
