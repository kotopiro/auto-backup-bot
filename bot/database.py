import aiosqlite
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class Database:
    """Database handler for user data and backups"""
    
    def __init__(self, db_path: str = "backup_bot.db"):
        self.db_path = db_path
        self._initialized = False
    
    async def initialize(self):
        """Initialize database tables"""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            # Users table - stores OAuth2 tokens
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT,
                    discriminator TEXT,
                    avatar TEXT,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT NOT NULL,
                    expires_at INTEGER NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)
            
            # Backups table - stores backup metadata
            await db.execute("""
                CREATE TABLE IF NOT EXISTS backups (
                    backup_id TEXT PRIMARY KEY,
                    guild_id TEXT NOT NULL,
                    guild_name TEXT,
                    created_by TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    member_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'completed'
                )
            """)
            
            # Guild settings table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id TEXT PRIMARY KEY,
                    auto_backup BOOLEAN DEFAULT 0,
                    backup_channel TEXT,
                    last_backup INTEGER,
                    settings_json TEXT
                )
            """)
            
            # Statistics table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    guild_id TEXT,
                    user_id TEXT,
                    data_json TEXT,
                    timestamp INTEGER NOT NULL
                )
            """)
            
            await db.commit()
            
        self._initialized = True
        logger.info("Database initialized successfully")
    
    async def save_user(
        self,
        user_id: str,
        username: str,
        discriminator: str,
        avatar: str,
        access_token: str,
        refresh_token: str,
        expires_in: int
    ) -> bool:
        """Save or update user data"""
        try:
            await self.initialize()
            
            now = int(datetime.now().timestamp())
            expires_at = now + expires_in
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO users 
                    (user_id, username, discriminator, avatar, access_token, 
                     refresh_token, expires_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 
                           COALESCE((SELECT created_at FROM users WHERE user_id = ?), ?), 
                           ?)
                """, (
                    user_id, username, discriminator, avatar,
                    access_token, refresh_token, expires_at,
                    user_id, now, now
                ))
                await db.commit()
            
            logger.info(f"Saved user: {username} ({user_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error saving user: {e}")
            return False
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user data by ID"""
        try:
            await self.initialize()
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM users WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    
                    if row:
                        return dict(row)
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users"""
        try:
            await self.initialize()
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM users") as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
                    
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete user data"""
        try:
            await self.initialize()
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "DELETE FROM users WHERE user_id = ?",
                    (user_id,)
                )
                await db.commit()
            
            logger.info(f"Deleted user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False
    
    async def get_users_by_guild(self, guild_id: str, member_ids: List[str]) -> List[Dict[str, Any]]:
        """Get users who are in a specific guild"""
        try:
            await self.initialize()
            
            if not member_ids:
                return []
            
            placeholders = ','.join('?' * len(member_ids))
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    f"SELECT * FROM users WHERE user_id IN ({placeholders})",
                    member_ids
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
                    
        except Exception as e:
            logger.error(f"Error getting guild users: {e}")
            return []
    
    async def count_users(self) -> int:
        """Count total users in database"""
        try:
            await self.initialize()
            
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else 0
                    
        except Exception as e:
            logger.error(f"Error counting users: {e}")
            return 0
    
    async def save_backup(
        self,
        backup_id: str,
        guild_id: str,
        guild_name: str,
        created_by: str,
        member_count: int
    ) -> bool:
        """Save backup metadata"""
        try:
            await self.initialize()
            
            now = int(datetime.now().timestamp())
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO backups 
                    (backup_id, guild_id, guild_name, created_by, created_at, member_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (backup_id, guild_id, guild_name, created_by, now, member_count))
                await db.commit()
            
            logger.info(f"Saved backup: {backup_id} for guild {guild_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving backup: {e}")
            return False
    
    async def get_guild_backups(self, guild_id: str) -> List[Dict[str, Any]]:
        """Get all backups for a guild"""
        try:
            await self.initialize()
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM backups WHERE guild_id = ? ORDER BY created_at DESC",
                    (guild_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
                    
        except Exception as e:
            logger.error(f"Error getting guild backups: {e}")
            return []
    
    async def log_statistic(
        self,
        event_type: str,
        guild_id: Optional[str] = None,
        user_id: Optional[str] = None,
        data: Optional[Dict] = None
    ):
        """Log statistical event"""
        try:
            await self.initialize()
            
            now = int(datetime.now().timestamp())
            data_json = json.dumps(data) if data else None
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO statistics 
                    (event_type, guild_id, user_id, data_json, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (event_type, guild_id, user_id, data_json, now))
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error logging statistic: {e}")
    
    async def get_statistics(
        self,
        event_type: Optional[str] = None,
        guild_id: Optional[str] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get statistics"""
        try:
            await self.initialize()
            
            cutoff = int((datetime.now() - timedelta(days=days)).timestamp())
            
            query = "SELECT * FROM statistics WHERE timestamp > ?"
            params = [cutoff]
            
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)
            
            if guild_id:
                query += " AND guild_id = ?"
                params.append(guild_id)
            
            query += " ORDER BY timestamp DESC"
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
                    
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return []
