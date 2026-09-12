import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed, error_embed
from utils.permissions import has_permission, bot_has_permission
from utils.helpers import is_hierarchy_safe
from utils.logging_helper import send_log


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _log(self, interaction, action: str, target: str, reason: str | None):
        embed = success_embed(action, f"Target: {target}\nModerator: {interaction.user.mention}\nReason: {reason or 'No reason provided'}")
        await send_log(self.bot, interaction.guild, embed)

    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(member="Member to kick", reason="Reason for the kick")
    @has_permission("kick_members")
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        if not bot_has_permission(interaction, "kick_members"):
            return await interaction.response.send_message(embed=error_embed("Missing permission", "I don't have permission to kick members."), ephemeral=True)
        if not is_hierarchy_safe(interaction.user, member):
            return await interaction.response.send_message(embed=error_embed("Action blocked", "You can't kick someone with an equal or higher role."), ephemeral=True)

        await member.kick(reason=reason)
        await interaction.response.send_message(embed=success_embed("Member kicked", f"{member.mention} was kicked.\nReason: {reason or 'No reason provided'}"))
        await self._log(interaction, "👢 Member kicked", str(member), reason)

    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.describe(member="Member to ban", reason="Reason for the ban")
    @has_permission("ban_members")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        if not bot_has_permission(interaction, "ban_members"):
            return await interaction.response.send_message(embed=error_embed("Missing permission", "I don't have permission to ban members."), ephemeral=True)
        if not is_hierarchy_safe(interaction.user, member):
            return await interaction.response.send_message(embed=error_embed("Action blocked", "You can't ban someone with an equal or higher role."), ephemeral=True)

        await member.ban(reason=reason)
        await interaction.response.send_message(embed=success_embed("Member banned", f"{member.mention} was banned.\nReason: {reason or 'No reason provided'}"))
        await self._log(interaction, "🔨 Member banned", str(member), reason)

    @app_commands.command(name="unban", description="Unban a user by ID")
    @app_commands.describe(user_id="The ID of the user to unban", reason="Reason for the unban")
    @has_permission("ban_members")
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = None):
        try:
            user = discord.Object(id=int(user_id))
        except ValueError:
            return await interaction.response.send_message(embed=error_embed("Invalid ID", "That doesn't look like a valid user ID."), ephemeral=True)

        try:
            await interaction.guild.unban(user, reason=reason)
        except discord.NotFound:
            return await interaction.response.send_message(embed=error_embed("Not found", "That user isn't banned."), ephemeral=True)

        await interaction.response.send_message(embed=success_embed("User unbanned", f"<@{user_id}> was unbanned.\nReason: {reason or 'No reason provided'}"))
        await self._log(interaction, "✅ Member unbanned", f"<@{user_id}>", reason)

    @app_commands.command(name="timeout", description="Timeout a member")
    @app_commands.describe(member="Member to timeout", minutes="Duration in minutes", reason="Reason for the timeout")
    @has_permission("moderate_members")
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = None):
        if not is_hierarchy_safe(interaction.user, member):
            return await interaction.response.send_message(embed=error_embed("Action blocked", "You can't time out someone with an equal or higher role."), ephemeral=True)

        duration = discord.utils.utcnow() + discord.timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        await interaction.response.send_message(embed=success_embed("Member timed out", f"{member.mention} timed out for {minutes} minute(s).\nReason: {reason or 'No reason provided'}"))
        await self._log(interaction, "🔇 Member timed out", f"{member} ({minutes}m)", reason)

    @app_commands.command(name="untimeout", description="Remove a member's timeout")
    @app_commands.describe(member="Member to remove timeout from", reason="Reason")
    @has_permission("moderate_members")
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        await member.timeout(None, reason=reason)
        await interaction.response.send_message(embed=success_embed("Timeout removed", f"{member.mention}'s timeout was removed."))
        await self._log(interaction, "🔊 Timeout removed", str(member), reason)

    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.describe(member="Member to warn", reason="Reason for the warning")
    @has_permission("moderate_members")
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        await self.bot.db.add_warning(interaction.guild.id, member.id, interaction.user.id, reason)
        await interaction.response.send_message(embed=success_embed("Member warned", f"{member.mention} was warned.\nReason: {reason or 'No reason provided'}"))
        await self._log(interaction, "⚠️ Member warned", str(member), reason)

    @app_commands.command(name="warnings", description="View a member's warnings")
    @app_commands.describe(member="Member to check")
    @has_permission("moderate_members")
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        rows = await self.bot.db.get_warnings(interaction.guild.id, member.id)
        if not rows:
            return await interaction.response.send_message(embed=success_embed("No warnings", f"{member.mention} has no warnings."))

        embed = success_embed(f"Warnings for {member}", f"{len(rows)} total")
        for row in rows[:10]:
            embed.add_field(name=f"Warning #{row['id']}", value=f"{row['reason'] or 'No reason'}\n<@{row['moderator_id']}> • {row['created_at']}", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clear", description="Delete a number of recent messages")
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    @has_permission("manage_messages")
    async def clear(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(embed=success_embed("Messages cleared", f"Deleted {len(deleted)} message(s)."), ephemeral=True)
        await self._log(interaction, "🧹 Messages cleared", f"{len(deleted)} in {interaction.channel.mention}", None)

    @app_commands.command(name="slowmode", description="Set slowmode for this channel")
    @app_commands.describe(seconds="Delay between messages, in seconds (0 to disable)")
    @has_permission("manage_channels")
    async def slowmode(self, interaction: discord.Interaction, seconds: app_commands.Range[int, 0, 21600]):
        await interaction.channel.edit(slowmode_delay=seconds)
        await interaction.response.send_message(embed=success_embed("Slowmode updated", f"{interaction.channel.mention} set to {seconds}s"))
        await self._log(interaction, "🐢 Slowmode changed", f"{interaction.channel.mention} → {seconds}s", None)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))