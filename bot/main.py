import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import sys
import logging
from datetime import datetime

# Add parent directory to path for AJS import
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from AJS import AJS

# Import bot modules
try:
    from database import Database
    from config import Config
except ImportError:
    from bot.database import Database
    from bot.config import Config

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AutoBackupBot(commands.Bot):
    """Main bot class"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        
        super().__init__(
            command_prefix=Config.PREFIX,
            intents=intents,
            help_command=None
        )
        
        self.db = Database()
        self.ajs = None
        self.start_time = datetime.now()
        
    async def setup_hook(self):
        """Setup hook - load cogs and sync commands"""
        logger.info("Setting up bot...")
        
        # Initialize AJS
        self.ajs = AJS(
            bot_token=Config.BOT_TOKEN,
            client_id=Config.CLIENT_ID,
            client_secret=Config.CLIENT_SECRET,
            redirect_uri=Config.REDIRECT_URI
        )
        
        # Load cogs
        cogs = ['bot.cogs.backup', 'bot.cogs.restore', 'bot.cogs.admin', 'bot.cogs.stats']
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")
        
        # Sync commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s)")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    async def on_ready(self):
        """Bot ready event"""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")
        
        # Set status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers | /help"
            )
        )
    
    async def on_guild_join(self, guild: discord.Guild):
        """Guild join event"""
        logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")
        
        # Send welcome message
        if guild.system_channel:
            embed = discord.Embed(
                title="🎉 Auto Backup Bot に参加していただきありがとうございます！",
                description=(
                    "サーバーメンバーのバックアップと復元を簡単に行えるBotです。\n\n"
                    "**主な機能:**\n"
                    "🔹 メンバー情報のバックアップ\n"
                    "🔹 サーバー復元機能\n"
                    "🔹 自動バックアップスケジューラー\n"
                    "🔹 詳細な統計情報\n\n"
                    "**使い方:**\n"
                    "`/help` - コマンド一覧を表示\n"
                    "`/setup` - 初期設定を開始"
                ),
                color=discord.Color.blue()
            )
            embed.set_footer(text="Powered by AJS Library")
            
            try:
                await guild.system_channel.send(embed=embed)
            except:
                pass
    
    async def close(self):
        """Close bot and cleanup"""
        logger.info("Shutting down bot...")
        
        if self.ajs:
            await self.ajs.close()
        
        await super().close()


def main():
    """Main entry point"""
    # Check if token exists
    if not Config.BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables!")
        return
    
    # Create and run bot
    bot = AutoBackupBot()
    
    try:
        bot.run(Config.BOT_TOKEN, log_handler=None)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        asyncio.run(bot.close())


if __name__ == "__main__":
    main()
