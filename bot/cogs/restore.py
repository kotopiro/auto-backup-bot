import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)


class RestoreCog(commands.Cog):
    """Restore/Add member commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="restore", description="バックアップからメンバーを復元")
    @app_commands.describe(
        backup_id="バックアップID（省略すると最新）"
    )
    async def restore_command(
        self,
        interaction: discord.Interaction,
        backup_id: Optional[str] = None
    ):
        """Restore members from backup"""
        
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
        
        # Get backup
        if backup_id:
            backups = await self.bot.db.get_guild_backups(str(interaction.guild.id))
            backup = next((b for b in backups if b['backup_id'] == backup_id), None)
            
            if not backup:
                await interaction.followup.send(
                    f"❌ バックアップID `{backup_id}` が見つかりません",
                    ephemeral=True
                )
                return
        else:
            # Get latest backup
            backups = await self.bot.db.get_guild_backups(str(interaction.guild.id))
            
            if not backups:
                await interaction.followup.send(
                    "❌ このサーバーにはバックアップがありません\n"
                    "`/backup` コマンドでバックアップを作成してください",
                    ephemeral=True
                )
                return
            
            backup = backups[0]
        
        # Get current members
        current_member_ids = {str(m.id) for m in interaction.guild.members}
        
        # Get registered members (excluding current members)
        all_member_ids = [str(m.id) for m in interaction.guild.members if not m.bot]
        registered_members = await self.bot.db.get_users_by_guild(
            str(interaction.guild.id),
            all_member_ids
        )
        
        # Get all registered users who aren't in the server
        all_users = await self.bot.db.get_all_users()
        users_to_add = [u for u in all_users if u['user_id'] not in current_member_ids]
        
        if not users_to_add:
            await interaction.followup.send(
                "✅ 追加可能な新しいメンバーはいません\n"
                "すべての登録ユーザーは既にサーバーに参加しています"
            )
            return
        
        # Send initial message
        progress_embed = discord.Embed(
            title="⏳ 復元を開始しています...",
            description=f"約 {len(users_to_add)} 人のメンバーを追加します",
            color=discord.Color.blue()
        )
        progress_message = await interaction.followup.send(embed=progress_embed)
        
        # Prepare member data for batch add
        members_data = []
        for user in users_to_add:
            members_data.append({
                'access_token': user['access_token'],
                'user_id': user['user_id'],
                'nick': None,
                'roles': None
            })
        
        # Add members in batches
        results = await self.bot.ajs.batch_add_members(
            members_data=members_data,
            guild_id=str(interaction.guild.id),
            delay=0.5
        )
        
        # Log statistic
        await self.bot.db.log_statistic(
            event_type="restore_completed",
            guild_id=str(interaction.guild.id),
            user_id=str(interaction.user.id),
            data=results
        )
        
        # Create result embed
        result_embed = discord.Embed(
            title="✅ 復元完了",
            description="メンバーの復元が完了しました",
            color=discord.Color.green()
        )
        result_embed.add_field(
            name="✅ 成功",
            value=f"```{results['success']:,} 人```",
            inline=True
        )
        result_embed.add_field(
            name="📝 既に参加済み",
            value=f"```{results['already_member']:,} 人```",
            inline=True
        )
        result_embed.add_field(
            name="❌ 失敗",
            value=f"```{results['failed']:,} 人```",
            inline=True
        )
        
        # Add error details if any
        if results['errors']:
            error_text = "\n".join([
                f"<@{err['user_id']}>: {err['error'][:50]}"
                for err in results['errors'][:5]
            ])
            if len(results['errors']) > 5:
                error_text += f"\n... 他 {len(results['errors']) - 5} 件"
            
            result_embed.add_field(
                name="エラー詳細",
                value=error_text,
                inline=False
            )
        
        result_embed.set_footer(text=f"バックアップID: {backup['backup_id']}")
        
        await progress_message.edit(embed=result_embed)
        
        logger.info(
            f"Restore completed in {interaction.guild}: "
            f"{results['success']} success, {results['failed']} failed"
        )
    
    @app_commands.command(name="call", description="登録済みメンバー全員をサーバーに追加")
    async def call_command(self, interaction: discord.Interaction):
        """Add all registered members to server"""
        
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
        
        # Confirmation
        confirm_embed = discord.Embed(
            title="⚠️ 確認",
            description=(
                "データベースに登録されている**全ユーザー**をこのサーバーに追加しようとしています。\n\n"
                "この操作は取り消せません。本当に実行しますか？"
            ),
            color=discord.Color.orange()
        )
        
        view = ConfirmView()
        await interaction.response.send_message(embed=confirm_embed, view=view, ephemeral=True)
        
        await view.wait()
        
        if not view.value:
            await interaction.followup.send("❌ キャンセルされました", ephemeral=True)
            return
        
        # Get current members
        current_member_ids = {str(m.id) for m in interaction.guild.members}
        
        # Get all users
        all_users = await self.bot.db.get_all_users()
        users_to_add = [u for u in all_users if u['user_id'] not in current_member_ids]
        
        if not users_to_add:
            await interaction.followup.send(
                "✅ 追加可能な新しいメンバーはいません",
                ephemeral=True
            )
            return
        
        # Send progress message
        progress_embed = discord.Embed(
            title="⏳ メンバーを追加しています...",
            description=f"約 {len(users_to_add)} 人を追加します",
            color=discord.Color.blue()
        )
        progress_message = await interaction.followup.send(embed=progress_embed)
        
        # Prepare member data
        members_data = []
        for user in users_to_add:
            members_data.append({
                'access_token': user['access_token'],
                'user_id': user['user_id'],
                'nick': None,
                'roles': None
            })
        
        # Add members
        results = await self.bot.ajs.batch_add_members(
            members_data=members_data,
            guild_id=str(interaction.guild.id),
            delay=0.5
        )
        
        # Log statistic
        await self.bot.db.log_statistic(
            event_type="call_completed",
            guild_id=str(interaction.guild.id),
            user_id=str(interaction.user.id),
            data=results
        )
        
        # Result embed
        result_embed = discord.Embed(
            title="✅ 追加完了",
            color=discord.Color.green()
        )
        result_embed.add_field(
            name="✅ 成功",
            value=f"```{results['success']:,} 人```",
            inline=True
        )
        result_embed.add_field(
            name="📝 既に参加済み",
            value=f"```{results['already_member']:,} 人```",
            inline=True
        )
        result_embed.add_field(
            name="❌ 失敗",
            value=f"```{results['failed']:,} 人```",
            inline=True
        )
        
        await progress_message.edit(embed=result_embed)
        
        logger.info(
            f"Call completed in {interaction.guild} by {interaction.user}: "
            f"{results['success']} added"
        )
    
    @app_commands.command(name="request", description="特定のユーザーをサーバーに追加")
    @app_commands.describe(user="追加するユーザーのID")
    async def request_command(
        self,
        interaction: discord.Interaction,
        user: str
    ):
        """Add specific user to server"""
        
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ このコマンドはサーバー内でのみ使用できます",
                ephemeral=True
            )
            return
        
        # Check permissions
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ このコマンドは「サーバー管理」権限が必要です",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        # Get user data
        user_data = await self.bot.db.get_user(user)
        
        if not user_data:
            await interaction.followup.send(
                f"❌ ユーザーID `{user}` は登録されていません",
                ephemeral=True
            )
            return
        
        # Check if already member
        try:
            member = await interaction.guild.fetch_member(int(user))
            await interaction.followup.send(
                f"✅ {member.mention} は既にこのサーバーに参加しています",
                ephemeral=True
            )
            return
        except discord.NotFound:
            pass
        
        # Add member
        result = await self.bot.ajs.add_guild_member(
            access_token=user_data['access_token'],
            guild_id=str(interaction.guild.id),
            user_id=user
        )
        
        status = result.get('status', 0)
        
        if status == 201:
            embed = discord.Embed(
                title="✅ メンバー追加成功",
                description=f"<@{user}> をサーバーに追加しました",
                color=discord.Color.green()
            )
        elif status == 204:
            embed = discord.Embed(
                title="📝 既に参加済み",
                description=f"<@{user}> は既にサーバーに参加しています",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="❌ 追加失敗",
                description=f"<@{user}> の追加に失敗しました\n\n**エラー:** {result.get('error', '不明')}",
                color=discord.Color.red()
            )
        
        await interaction.followup.send(embed=embed)
        
        # Log statistic
        await self.bot.db.log_statistic(
            event_type="member_added",
            guild_id=str(interaction.guild.id),
            user_id=str(interaction.user.id),
            data={"target_user": user, "status": status}
        )
        
        logger.info(f"Request by {interaction.user} to add {user}: status {status}")


class ConfirmView(discord.ui.View):
    """Confirmation view for dangerous operations"""
    
    def __init__(self):
        super().__init__(timeout=60)
        self.value = None
    
    @discord.ui.button(label="実行する", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        await interaction.response.defer()
    
    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        await interaction.response.defer()


async def setup(bot):
    await bot.add_cog(RestoreCog(bot))
