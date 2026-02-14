"""
OAuth2 Handler for Discord Authentication
"""

import aiohttp
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class OAuth2Handler:
    """
    Handle Discord OAuth2 flow
    """
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        proxy: Optional[str] = None
    ):
        """
        Initialize OAuth2 Handler
        
        Args:
            client_id: Discord OAuth2 Client ID
            client_secret: Discord OAuth2 Client Secret
            redirect_uri: OAuth2 Redirect URI
            proxy: Optional proxy URL
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.proxy = proxy
        
        self.token_url = "https://discord.com/api/v10/oauth2/token"
        self.api_base = "https://discord.com/api/v10"
        
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
    
    async def close(self):
        """Close aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def exchange_code(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for tokens
        
        Args:
            code: OAuth2 authorization code
            
        Returns:
            Dict containing access_token, refresh_token, expires_in
        """
        await self._ensure_session()
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri
        }
        
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        try:
            async with self._session.post(
                self.token_url,
                data=data,
                headers=headers,
                proxy=self.proxy
            ) as response:
                result = await response.json()
                
                if 'access_token' in result:
                    logger.info("Successfully exchanged code for tokens")
                else:
                    logger.error(f"Failed to exchange code: {result}")
                
                return result
                
        except Exception as e:
            logger.error(f"Error exchanging code: {e}")
            return {"error": str(e)}
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token
        
        Args:
            refresh_token: OAuth2 refresh token
            
        Returns:
            Dict containing new access_token and refresh_token
        """
        await self._ensure_session()
        
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        try:
            async with self._session.post(
                self.token_url,
                data=data,
                headers=headers,
                proxy=self.proxy
            ) as response:
                result = await response.json()
                
                if 'access_token' in result:
                    logger.info("Successfully refreshed token")
                else:
                    logger.error(f"Failed to refresh token: {result}")
                
                return result
                
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return {"error": str(e)}
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information
        
        Args:
            access_token: OAuth2 access token
            
        Returns:
            Dict containing user information
        """
        await self._ensure_session()
        
        headers = {'Authorization': f'Bearer {access_token}'}
        url = f"{self.api_base}/users/@me"
        
        try:
            async with self._session.get(
                url,
                headers=headers,
                proxy=self.proxy
            ) as response:
                result = await response.json()
                
                if 'id' in result:
                    logger.info(f"Retrieved user info: {result.get('username', 'Unknown')}")
                else:
                    logger.error(f"Failed to get user info: {result}")
                
                return result
                
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return {"error": str(e)}
    
    def get_authorization_url(
        self,
        state: Optional[str] = None,
        scopes: list = None
    ) -> str:
        """
        Generate OAuth2 authorization URL
        
        Args:
            state: Optional state parameter for CSRF protection
            scopes: List of OAuth2 scopes
            
        Returns:
            Authorization URL
        """
        if scopes is None:
            scopes = ['identify', 'guilds.join']
        
        from urllib.parse import urlencode
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(scopes)
        }
        
        if state:
            params['state'] = state
        
        auth_url = f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"
        
        return auth_url
