import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional
from bot.config import Config

logger = logging.getLogger(__name__)


def is_admin():
    """Check if user is admin"""
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.id in Config.ADMIN_IDS or interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)


class AdminCog(commands.Cog):
    """Admin commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="delkey", description="ユーザーの登録情報を削除")
    @app_commands.describe(user_id="削除するユーザーのID")
    @is_admin()
    async def delkey_command(
        self,
        interaction: discord.Interaction,
        user_id: str
    ):
        """Delete user registration"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Check if user exists
        user_data = await self.bot.db.get_user(user_id)
        
        if not user_data:
            await interaction.followup.send(
                f"❌ ユーザーID `{user_id}` は登録されていません",
                ephemeral=True
            )
            return
        
        # Delete user
        success = await self.bot.db.delete_user(user_id)
        
        if success:
            embed = discord.Embed(
                title="✅ 削除完了",
                description=f"ユーザーID `{user_id}` の登録情報を削除しました",
                color=discord.Color.green()
            )
            embed.add_field(
                name="削除されたユーザー",
                value=f"{user_data['username']}#{user_data['discriminator']}",
                inline=True
            )
            
            # Log statistic
            await self.bot.db.log_statistic(
                event_type="user_deleted",
                guild_id=str(interaction.guild.id) if interaction.guild else None,
                user_id=str(interaction.user.id),
                data={"deleted_user": user_id}
            )
        else:
            embed = discord.Embed(
                title="❌ 削除失敗",
                description="削除中にエラーが発生しました",
                color=discord.Color.red()
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        logger.info(f"User {user_id} deleted by {interaction.user}")
    
    @app_commands.command(name="purge", description="期限切れトークンを一括削除")
    @is_admin()
    async def purge_command(self, interaction: discord.Interaction):
        """Purge expired tokens"""
        
        await interaction.response.defer(ephemeral=True)
        
        from datetime import datetime
        
        # Get all users
        all_users = await self.bot.db.get_all_users()
        now = int(datetime.now().timestamp())
        
        expired_users = [u for u in all_users if u['expires_at'] < now]
        
        if not expired_users:
            await interaction.followup.send(
                "✅ 期限切れトークンはありません",
                ephemeral=True
            )
            return
        
        # Delete expired users
        deleted_count = 0
        for user in expired_users:
            success = await self.bot.db.delete_user(user['user_id'])
            if success:
                deleted_count += 1
        
        embed = discord.Embed(
            title="🗑️ クリーンアップ完了",
            description=f"{deleted_count} 件の期限切れトークンを削除しました",
            color=discord.Color.green()
        )
        embed.add_field(
            name="削除前",
            value=f"```{len(all_users):,} ユーザー```",
            inline=True
        )
        embed.add_field(
            name="削除後",
            value=f"```{len(all_users) - deleted_count:,} ユーザー```",
            inline=True
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Log statistic
        await self.bot.db.log_statistic(
            event_type="tokens_purged",
            guild_id=str(interaction.guild.id) if interaction.guild else None,
            user_id=str(interaction.user.id),
            data={"count": deleted_count}
        )
        
        logger.info(f"Purged {deleted_count} expired tokens by {interaction.user}")
    
    @app_commands.command(name="refresh", description="ユーザーのトークンをリフレッシュ")
    @app_commands.describe(user_id="リフレッシュするユーザーのID")
    @is_admin()
    async def refresh_command(
        self,
        interaction: discord.Interaction,
        user_id: str
    ):
        """Refresh user token"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Get user data
        user_data = await self.bot.db.get_user(user_id)
        
        if not user_data:
            await interaction.followup.send(
                f"❌ ユーザーID `{user_id}` は登録されていません",
                ephemeral=True
            )
            return
        
        # Refresh token
        result = await self.bot.ajs.refresh_token(user_data['refresh_token'])
        
        if 'access_token' in result:
            # Update database
            await self.bot.db.save_user(
                user_id=user_id,
                username=user_data['username'],
                discriminator=user_data['discriminator'],
                avatar=user_data['avatar'],
                access_token=result['access_token'],
                refresh_token=result['refresh_token'],
                expires_in=result['expires_in']
            )
            
            embed = discord.Embed(
                title="✅ リフレッシュ成功",
                description=f"ユーザーID `{user_id}` のトークンをリフレッシュしました",
                color=discord.Color.green()
            )
            embed.add_field(
                name="有効期限",
                value=f"```{result['expires_in']} 秒```",
                inline=True
            )
            
            # Log statistic
            await self.bot.db.log_statistic(
                event_type="token_refreshed",
                guild_id=str(interaction.guild.id) if interaction.guild else None,
                user_id=str(interaction.user.id),
                data={"target_user": user_id}
            )
        else:
            embed = discord.Embed(
                title="❌ リフレッシュ失敗",
                description=f"トークンのリフレッシュに失敗しました\n\n**エラー:** {result.get('error', '不明')}",
                color=discord.Color.red()
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        logger.info(f"Token refresh for {user_id} by {interaction.user}")
    
    @app_commands.command(name="listbackups", description="サーバーのバックアップ一覧")
    @app_commands.describe(limit="表示件数（最大20）")
    async def listbackups_command(
        self,
        interaction: discord.Interaction,
        limit: Optional[int] = 10
    ):
        """List server backups"""
        
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ このコマンドはサーバー内でのみ使用できます",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        limit = min(limit, 20)
        
        backups = await self.bot.db.get_guild_backups(str(interaction.guild.id))
        
        if not backups:
            await interaction.followup.send(
                "❌ このサーバーにはバックアップがありません"
            )
            return
        
        # Create embed
        embed = discord.Embed(
            title=f"📦 バックアップ一覧 ({len(backups)} 件)",
            color=discord.Color.blue()
        )
        
        for backup in backups[:limit]:
            from datetime import datetime
            created_at = datetime.fromtimestamp(backup['created_at'])
            
            embed.add_field(
                name=f"ID: {backup['backup_id'][:8]}...",
                value=(
                    f"**メンバー:** {backup['member_count']:,} 人\n"
                    f"**作成者:** <@{backup['created_by']}>\n"
                    f"**日時:** <t:{backup['created_at']}:R>"
                ),
                inline=False
            )
        
        if len(backups) > limit:
            embed.set_footer(text=f"他 {len(backups) - limit} 件のバックアップがあります")
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="setup", description="サーバーの初期設定")
    async def setup_command(self, interaction: discord.Interaction):
        """Server setup wizard"""
        
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ このコマンドはサーバー内でのみ使用できます",
                ephemeral=True
            )
            return
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ このコマンドは管理者のみ使用できます",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="⚙️ Auto Backup Bot - セットアップ",
            description=(
                "セットアップへようこそ！以下の手順で設定を完了してください。\n\n"
                "**ステップ 1: 認証ボタンの設置**\n"
                "`/button` コマンドでメンバー認証用のボタンを表示できます。\n\n"
                "**ステップ 2: メンバーに認証を促す**\n"
                "メンバーにボタンをクリックして認証してもらいます。\n\n"
                "**ステップ 3: バックアップの作成**\n"
                "`/backup` コマンドでメンバー情報をバックアップできます。\n\n"
                "**ステップ 4: 復元**\n"
                "必要に応じて `/restore` や `/call` で復元できます。"
            ),
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📌 主要コマンド",
            value=(
                "`/button` - 認証ボタン表示\n"
                "`/backup` - バックアップ作成\n"
                "`/restore` - バックアップから復元\n"
                "`/call` - 全ユーザー追加\n"
                "`/request` - 特定ユーザー追加\n"
                "`/stats` - 統計情報\n"
                "`/help` - ヘルプ"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔗 認証URL",
            value=Config.WEB_URL,
            inline=False
        )
        
        embed.set_footer(text="質問があればサポートサーバーへ！")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="help", description="ヘルプを表示")
    async def help_command(self, interaction: discord.Interaction):
        """Show help"""
        
        embed = discord.Embed(
            title="📚 Auto Backup Bot - ヘルプ",
            description="サーバーメンバーのバックアップと復元を簡単に行えるBotです",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🔐 認証コマンド",
            value=(
                "`/button` - 認証用ボタンを表示\n"
                "`/check [user]` - 登録状況確認\n"
                "`/datacheck` - 登録ユーザー数確認"
            ),
            inline=False
        )
        
        embed.add_field(
            name="💾 バックアップコマンド",
            value=(
                "`/backup` - サーバーをバックアップ\n"
                "`/listbackups` - バックアップ一覧"
            ),
            inline=False
        )
        
        embed.add_field(
            name="♻️ 復元コマンド",
            value=(
                "`/restore [backup_id]` - バックアップから復元\n"
                "`/call` - 全登録ユーザーを追加\n"
                "`/request <user_id>` - 特定ユーザーを追加"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📊 統計コマンド",
            value=(
                "`/stats` - 統計情報表示\n"
                "`/leaderboard` - サーバーランキング"
            ),
            inline=False
        )
        
        embed.add_field(
            name="⚙️ 管理コマンド（管理者限定）",
            value=(
                "`/delkey <user_id>` - ユーザー削除\n"
                "`/purge` - 期限切れトークン削除\n"
                "`/refresh <user_id>` - トークンリフレッシュ\n"
                "`/setup` - 初期設定"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔗 リンク",
            value=f"[認証ページ]({Config.WEB_URL})",
            inline=False
        )
        
        embed.set_footer(text="Powered by AJS Library | 詳細は各コマンドで確認できます")
        
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
