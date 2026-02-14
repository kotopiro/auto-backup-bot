import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class BackupCog(commands.Cog):
    """Backup commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="button", description="認証用ボタンを表示")
    @app_commands.describe(
        title="タイトル（省略可）",
        description="説明文（省略可）"
    )
    async def button_command(
        self,
        interaction: discord.Interaction,
        title: str = None,
        description: str = None
    ):
        """Display authentication button"""
        
        # Default values
        if not title:
            title = "🔐 メンバー登録"
        if not description:
            description = (
                "下のボタンをクリックして認証を完了してください。\n"
                "認証により、サーバーへの参加とバックアップ機能が利用可能になります。"
            )
        
        # Create embed
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📋 認証手順",
            value=(
                "1️⃣ ボタンをクリック\n"
                "2️⃣ Cloudflare認証を完了\n"
                "3️⃣ Discord OAuth2認証\n"
                "4️⃣ 完了！"
            ),
            inline=False
        )
        embed.set_footer(text="認証は安全に暗号化されています | Powered by AJS")
        
        # Create button
        button = discord.ui.Button(
            label="認証を開始",
            style=discord.ButtonStyle.link,
            url=self.bot.get_cog('BackupCog').bot.config.WEB_URL if hasattr(self.bot, 'config') else "https://school-rekisi.kesug.com",
            emoji="🔐"
        )
        
        view = discord.ui.View()
        view.add_item(button)
        
        await interaction.response.send_message(embed=embed, view=view)
        logger.info(f"Button displayed by {interaction.user} in {interaction.guild}")
    
    @app_commands.command(name="check", description="ユーザーの登録状況を確認")
    @app_commands.describe(user="確認するユーザー（省略すると自分）")
    async def check_command(
        self,
        interaction: discord.Interaction,
        user: discord.User = None
    ):
        """Check user registration status"""
        
        target_user = user or interaction.user
        
        await interaction.response.defer(ephemeral=True)
        
        # Get user from database
        user_data = await self.bot.db.get_user(str(target_user.id))
        
        if user_data:
            # User is registered
            expires_at = datetime.fromtimestamp(user_data['expires_at'])
            registered_at = datetime.fromtimestamp(user_data['created_at'])
            
            embed = discord.Embed(
                title="✅ 登録済み",
                description=f"{target_user.mention} は登録されています",
                color=discord.Color.green()
            )
            embed.add_field(
                name="ユーザー名",
                value=f"{user_data['username']}#{user_data['discriminator']}",
                inline=True
            )
            embed.add_field(
                name="登録日時",
                value=f"<t:{int(registered_at.timestamp())}:R>",
                inline=True
            )
            embed.add_field(
                name="トークン有効期限",
                value=f"<t:{int(expires_at.timestamp())}:R>",
                inline=True
            )
            
        else:
            # User not registered
            embed = discord.Embed(
                title="❌ 未登録",
                description=f"{target_user.mention} はまだ登録されていません",
                color=discord.Color.red()
            )
            embed.add_field(
                name="登録方法",
                value="`/button` コマンドで認証ボタンを表示できます",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="datacheck", description="登録ユーザー数を確認")
    async def datacheck_command(self, interaction: discord.Interaction):
        """Check total registered users"""
        
        await interaction.response.defer()
        
        total_users = await self.bot.db.count_users()
        
        # Get guild members who are registered
        if interaction.guild:
            member_ids = [str(m.id) for m in interaction.guild.members]
            registered_members = await self.bot.db.get_users_by_guild(
                str(interaction.guild.id),
                member_ids
            )
            guild_registered = len(registered_members)
        else:
            guild_registered = 0
        
        embed = discord.Embed(
            title="📊 登録データ統計",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="総登録ユーザー数",
            value=f"```{total_users:,} 人```",
            inline=False
        )
        
        if interaction.guild:
            embed.add_field(
                name=f"このサーバーの登録済みメンバー",
                value=f"```{guild_registered:,} 人 / {interaction.guild.member_count:,} 人```",
                inline=False
            )
            
            percentage = (guild_registered / interaction.guild.member_count * 100) if interaction.guild.member_count > 0 else 0
            embed.add_field(
                name="登録率",
                value=f"```{percentage:.1f}%```",
                inline=False
            )
        
        embed.set_footer(text=f"データベース: {self.bot.db.db_path}")
        
        await interaction.followup.send(embed=embed)
        logger.info(f"Data check performed by {interaction.user}")
    
    @app_commands.command(name="backup", description="現在のサーバーメンバーをバックアップ")
    async def backup_command(self, interaction: discord.Interaction):
        """Create server backup"""
        
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ このコマンドはサーバー内でのみ使用できます",
                ephemeral=True
            )
            return
        
        # Check permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ このコマンドは管理者のみ使用できます",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        # Get all members
        member_ids = [str(m.id) for m in interaction.guild.members if not m.bot]
        registered_members = await self.bot.db.get_users_by_guild(
            str(interaction.guild.id),
            member_ids
        )
        
        # Create backup ID
        backup_id = str(uuid.uuid4())
        
        # Save backup metadata
        await self.bot.db.save_backup(
            backup_id=backup_id,
            guild_id=str(interaction.guild.id),
            guild_name=interaction.guild.name,
            created_by=str(interaction.user.id),
            member_count=len(registered_members)
        )
        
        # Log statistic
        await self.bot.db.log_statistic(
            event_type="backup_created",
            guild_id=str(interaction.guild.id),
            user_id=str(interaction.user.id),
            data={"member_count": len(registered_members)}
        )
        
        embed = discord.Embed(
            title="✅ バックアップ完了",
            description=f"サーバーメンバーのバックアップが完了しました",
            color=discord.Color.green()
        )
        embed.add_field(
            name="バックアップID",
            value=f"```{backup_id}```",
            inline=False
        )
        embed.add_field(
            name="登録済みメンバー",
            value=f"```{len(registered_members):,} 人 / {len(member_ids):,} 人```",
            inline=True
        )
        embed.add_field(
            name="作成者",
            value=interaction.user.mention,
            inline=True
        )
        embed.add_field(
            name="作成日時",
            value=f"<t:{int(datetime.now().timestamp())}:F>",
            inline=False
        )
        embed.set_footer(text=f"復元は /restore コマンドで実行できます")
        
        await interaction.followup.send(embed=embed)
        logger.info(
            f"Backup created by {interaction.user} in {interaction.guild}: "
            f"{len(registered_members)} members"
        )


async def setup(bot):
    await bot.add_cog(BackupCog(bot))
