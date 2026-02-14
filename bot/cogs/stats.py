import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class StatsCog(commands.Cog):
    """Statistics commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="stats", description="統計情報を表示")
    @app_commands.describe(days="集計期間（日数）")
    async def stats_command(
        self,
        interaction: discord.Interaction,
        days: Optional[int] = 30
    ):
        """Show statistics"""
        
        await interaction.response.defer()
        
        # Get statistics
        stats = await self.bot.db.get_statistics(days=days)
        
        # Calculate totals
        total_users = await self.bot.db.count_users()
        
        backups_created = len([s for s in stats if s['event_type'] == 'backup_created'])
        restores_completed = len([s for s in stats if s['event_type'] == 'restore_completed'])
        members_added = len([s for s in stats if s['event_type'] == 'member_added'])
        users_deleted = len([s for s in stats if s['event_type'] == 'user_deleted'])
        
        # Create embed
        embed = discord.Embed(
            title="📊 統計情報",
            description=f"過去 {days} 日間のデータ",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="👥 総登録ユーザー",
            value=f"```{total_users:,} 人```",
            inline=True
        )
        
        embed.add_field(
            name="💾 バックアップ作成",
            value=f"```{backups_created:,} 回```",
            inline=True
        )
        
        embed.add_field(
            name="♻️ 復元実行",
            value=f"```{restores_completed:,} 回```",
            inline=True
        )
        
        embed.add_field(
            name="➕ メンバー追加",
            value=f"```{members_added:,} 人```",
            inline=True
        )
        
        embed.add_field(
            name="🗑️ ユーザー削除",
            value=f"```{users_deleted:,} 人```",
            inline=True
        )
        
        embed.add_field(
            name="📅 集計期間",
            value=f"```{days} 日間```",
            inline=True
        )
        
        # Bot stats
        if interaction.guild:
            guild_members = len([m for m in interaction.guild.members if not m.bot])
            member_ids = [str(m.id) for m in interaction.guild.members if not m.bot]
            registered = await self.bot.db.get_users_by_guild(
                str(interaction.guild.id),
                member_ids
            )
            
            embed.add_field(
                name=f"📍 このサーバー",
                value=(
                    f"**総メンバー:** {guild_members:,} 人\n"
                    f"**登録済み:** {len(registered):,} 人\n"
                    f"**登録率:** {len(registered) / guild_members * 100:.1f}%"
                ),
                inline=False
            )
        
        # Bot uptime
        uptime = datetime.now() - self.bot.start_time
        days_up = uptime.days
        hours_up = uptime.seconds // 3600
        minutes_up = (uptime.seconds % 3600) // 60
        
        embed.add_field(
            name="⏱️ Bot稼働時間",
            value=f"```{days_up}日 {hours_up}時間 {minutes_up}分```",
            inline=False
        )
        
        embed.set_footer(text=f"Bot接続サーバー数: {len(self.bot.guilds):,}")
        
        await interaction.followup.send(embed=embed)
        
        logger.info(f"Stats displayed by {interaction.user}")
    
    @app_commands.command(name="leaderboard", description="サーバーランキング")
    @app_commands.describe(
        metric="ランキング基準",
        limit="表示件数"
    )
    @app_commands.choices(metric=[
        app_commands.Choice(name="メンバー数", value="members"),
        app_commands.Choice(name="登録率", value="registration"),
        app_commands.Choice(name="バックアップ数", value="backups")
    ])
    async def leaderboard_command(
        self,
        interaction: discord.Interaction,
        metric: str = "members",
        limit: Optional[int] = 10
    ):
        """Show server leaderboard"""
        
        await interaction.response.defer()
        
        limit = min(limit, 20)
        
        # Get guild data
        guild_stats = []
        
        for guild in self.bot.guilds:
            guild_members = len([m for m in guild.members if not m.bot])
            member_ids = [str(m.id) for m in guild.members if not m.bot]
            registered = await self.bot.db.get_users_by_guild(
                str(guild.id),
                member_ids
            )
            backups = await self.bot.db.get_guild_backups(str(guild.id))
            
            registration_rate = (len(registered) / guild_members * 100) if guild_members > 0 else 0
            
            guild_stats.append({
                'guild': guild,
                'members': guild_members,
                'registered': len(registered),
                'registration_rate': registration_rate,
                'backups': len(backups)
            })
        
        # Sort by metric
        if metric == "members":
            guild_stats.sort(key=lambda x: x['members'], reverse=True)
            title = "👥 メンバー数ランキング"
            value_format = lambda x: f"{x['members']:,} 人"
        elif metric == "registration":
            guild_stats.sort(key=lambda x: x['registration_rate'], reverse=True)
            title = "📊 登録率ランキング"
            value_format = lambda x: f"{x['registration_rate']:.1f}% ({x['registered']}/{x['members']})"
        else:  # backups
            guild_stats.sort(key=lambda x: x['backups'], reverse=True)
            title = "💾 バックアップ数ランキング"
            value_format = lambda x: f"{x['backups']:,} 個"
        
        # Create embed
        embed = discord.Embed(
            title=title,
            description=f"Top {min(limit, len(guild_stats))} サーバー",
            color=discord.Color.gold()
        )
        
        medals = ["🥇", "🥈", "🥉"]
        
        for i, stat in enumerate(guild_stats[:limit], 1):
            medal = medals[i-1] if i <= 3 else f"`{i}.`"
            
            embed.add_field(
                name=f"{medal} {stat['guild'].name}",
                value=value_format(stat),
                inline=False
            )
        
        # Show current server rank if not in top
        if interaction.guild:
            current_rank = next(
                (i+1 for i, s in enumerate(guild_stats) if s['guild'].id == interaction.guild.id),
                None
            )
            
            if current_rank and current_rank > limit:
                current_stat = guild_stats[current_rank - 1]
                embed.add_field(
                    name=f"📍 このサーバー ({current_rank}位)",
                    value=value_format(current_stat),
                    inline=False
                )
        
        embed.set_footer(text=f"総サーバー数: {len(guild_stats):,}")
        
        await interaction.followup.send(embed=embed)
        
        logger.info(f"Leaderboard ({metric}) displayed by {interaction.user}")
    
    @app_commands.command(name="activity", description="最近のアクティビティ")
    @app_commands.describe(limit="表示件数")
    async def activity_command(
        self,
        interaction: discord.Interaction,
        limit: Optional[int] = 10
    ):
        """Show recent activity"""
        
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ このコマンドはサーバー内でのみ使用できます",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        limit = min(limit, 20)
        
        # Get guild statistics
        stats = await self.bot.db.get_statistics(
            guild_id=str(interaction.guild.id),
            days=30
        )
        
        if not stats:
            await interaction.followup.send(
                "📭 最近のアクティビティはありません"
            )
            return
        
        # Create embed
        embed = discord.Embed(
            title="📜 最近のアクティビティ",
            description=f"過去30日間の活動 ({len(stats)} 件)",
            color=discord.Color.blue()
        )
        
        # Event type icons
        event_icons = {
            'backup_created': '💾',
            'restore_completed': '♻️',
            'member_added': '➕',
            'user_deleted': '🗑️',
            'token_refreshed': '🔄',
            'tokens_purged': '🧹',
            'call_completed': '📞'
        }
        
        # Event type labels
        event_labels = {
            'backup_created': 'バックアップ作成',
            'restore_completed': '復元完了',
            'member_added': 'メンバー追加',
            'user_deleted': 'ユーザー削除',
            'token_refreshed': 'トークンリフレッシュ',
            'tokens_purged': 'トークン一括削除',
            'call_completed': '全ユーザー追加'
        }
        
        for stat in stats[:limit]:
            event_type = stat['event_type']
            icon = event_icons.get(event_type, '📌')
            label = event_labels.get(event_type, event_type)
            
            timestamp = stat['timestamp']
            user_id = stat.get('user_id')
            
            value_parts = [f"<t:{timestamp}:R>"]
            
            if user_id:
                value_parts.append(f"by <@{user_id}>")
            
            embed.add_field(
                name=f"{icon} {label}",
                value=" ".join(value_parts),
                inline=False
            )
        
        if len(stats) > limit:
            embed.set_footer(text=f"他 {len(stats) - limit} 件のアクティビティがあります")
        
        await interaction.followup.send(embed=embed)
        
        logger.info(f"Activity displayed by {interaction.user}")
    
    @app_commands.command(name="userinfo", description="ユーザーの詳細情報")
    @app_commands.describe(user="情報を表示するユーザー")
    async def userinfo_command(
        self,
        interaction: discord.Interaction,
        user: discord.User
    ):
        """Show detailed user information"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Get user data from database
        user_data = await self.bot.db.get_user(str(user.id))
        
        embed = discord.Embed(
            title=f"👤 {user.name} の情報",
            color=discord.Color.blue()
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        
        embed.add_field(
            name="ユーザーID",
            value=f"```{user.id}```",
            inline=False
        )
        
        embed.add_field(
            name="アカウント作成日",
            value=f"<t:{int(user.created_at.timestamp())}:F>",
            inline=False
        )
        
        if user_data:
            registered_at = datetime.fromtimestamp(user_data['created_at'])
            expires_at = datetime.fromtimestamp(user_data['expires_at'])
            
            embed.add_field(
                name="✅ 登録状態",
                value="登録済み",
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
            
            # Check token validity
            now = datetime.now().timestamp()
            if user_data['expires_at'] < now:
                embed.add_field(
                    name="⚠️ 警告",
                    value="トークンが期限切れです",
                    inline=False
                )
        else:
            embed.add_field(
                name="❌ 登録状態",
                value="未登録",
                inline=False
            )
        
        # Guild membership
        if interaction.guild:
            try:
                member = await interaction.guild.fetch_member(user.id)
                
                embed.add_field(
                    name="サーバー参加日",
                    value=f"<t:{int(member.joined_at.timestamp())}:R>",
                    inline=True
                )
                
                roles = [r.mention for r in member.roles if r.name != "@everyone"]
                if roles:
                    embed.add_field(
                        name=f"ロール ({len(roles)})",
                        value=", ".join(roles[:5]) + ("..." if len(roles) > 5 else ""),
                        inline=False
                    )
            except discord.NotFound:
                embed.add_field(
                    name="サーバー参加",
                    value="このサーバーのメンバーではありません",
                    inline=False
                )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        logger.info(f"User info for {user} displayed by {interaction.user}")


async def setup(bot):
    await bot.add_cog(StatsCog(bot))
