import os
from dotenv import load_dotenv
from typing import Optional

# .envファイルを読み込む（これが重要！）
load_dotenv()


class Config:
    """Bot configuration"""
    
    # Bot settings
    BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')
    PREFIX: str = os.getenv('PREFIX', '!')
    
    # OAuth2 settings
    CLIENT_ID: str = os.getenv('DISCORD_CLIENT_ID', '')
    CLIENT_SECRET: str = os.getenv('DISCORD_CLIENT_SECRET', '')
    REDIRECT_URI: str = os.getenv('DISCORD_REDIRECT_URI', 'https://school-rekisi.kesug.com/callback')
    
    # Database settings
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite:///backup_bot.db')
    
    # Web settings
    WEB_URL: str = os.getenv('WEB_URL', 'https://school-rekisi.kesug.com')
    WEBHOOK_SECRET: str = os.getenv('WEBHOOK_SECRET', '')
    
    # Feature flags
    AUTO_BACKUP_ENABLED: bool = os.getenv('AUTO_BACKUP_ENABLED', 'false').lower() == 'true'
    BACKUP_INTERVAL_HOURS: int = int(os.getenv('BACKUP_INTERVAL_HOURS', '24'))
    
    # Rate limiting
    MAX_MEMBERS_PER_BATCH: int = int(os.getenv('MAX_MEMBERS_PER_BATCH', '50'))
    BATCH_DELAY_SECONDS: float = float(os.getenv('BATCH_DELAY_SECONDS', '0.5'))
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    # Cloudflare Turnstile
    TURNSTILE_SITE_KEY: str = os.getenv('TURNSTILE_SITE_KEY', '')
    TURNSTILE_SECRET_KEY: str = os.getenv('TURNSTILE_SECRET_KEY', '')
    
    # Admin users (comma-separated Discord IDs)
    ADMIN_IDS: list = [
        int(id.strip()) 
        for id in os.getenv('ADMIN_IDS', '').split(',') 
        if id.strip()
    ]
    
    # Embed colors
    COLOR_SUCCESS = 0x57F287
    COLOR_ERROR = 0xED4245
    COLOR_WARNING = 0xFEE75C
    COLOR_INFO = 0x5865F2
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        required = [
            ('BOT_TOKEN', cls.BOT_TOKEN),
            ('CLIENT_ID', cls.CLIENT_ID),
            ('CLIENT_SECRET', cls.CLIENT_SECRET),
        ]
        
        missing = [name for name, value in required if not value]
        
        if missing:
            print(f"❌ Missing required configuration: {', '.join(missing)}")
            return False
        
        return True
    
    @classmethod
    def print_config(cls):
        """Print current configuration (safe - hides secrets)"""
        print("\n=== Configuration ===")
        print(f"Prefix: {cls.PREFIX}")
        print(f"Database: {cls.DATABASE_URL}")
        print(f"Web URL: {cls.WEB_URL}")
        print(f"Auto Backup: {cls.AUTO_BACKUP_ENABLED}")
        print(f"Backup Interval: {cls.BACKUP_INTERVAL_HOURS}h")
        print(f"Max Batch Size: {cls.MAX_MEMBERS_PER_BATCH}")
        print(f"Admin Count: {len(cls.ADMIN_IDS)}")
        print("====================\n")