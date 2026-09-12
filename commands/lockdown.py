import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed
from utils.permissions import has_permission
from utils.logging_helper import send_log


class Lockdown(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="lock", description="Lock a channel so only admins (and anyone you allow) can send messages")
    @app_commands.describe(
        channel="Channel to lock (defaults to the current channel)",
        member="Optional member to still allow to talk",
        role="Optional role to still allow to talk",
        reason="Reason for locking",
    )
    @has_permission("manage_channels")
    async def lock(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel = None,
        member: discord.Member = None,
        role: discord.Role = None,
        reason: str = None,
    ):
        channel = channel or interaction.channel
        everyone = interaction.guild.default_role

        overwrite = channel.overwrites_for(everyone)
        overwrite.send_messages = False
        await channel.set_permissions(everyone, overwrite=overwrite, reason=reason)

        extra = []
        if member:
            member_overwrite = channel.overwrites_for(member)
            member_overwrite.send_messages = True
            await channel.set_permissions(member, overwrite=member_overwrite, reason=reason)
            extra.append(member.mention)

        if role:
            role_overwrite = channel.overwrites_for(role)
            role_overwrite.send_messages = True
            await channel.set_permissions(role, overwrite=role_overwrite, reason=reason)
            extra.append(role.mention)

        extra_text = f"\nAlso allowed: {', '.join(extra)}" if extra else ""

        await interaction.response.send_message(
            embed=success_embed("🔒 Channel locked", f"{channel.mention} is now locked.\nReason: {reason or 'No reason provided'}{extra_text}")
        )
        await send_log(
            self.bot, interaction.guild,
            success_embed("🔒 Channel locked", f"Channel: {channel.mention}\nBy: {interaction.user.mention}\nReason: {reason or 'No reason provided'}{extra_text}"),
        )

    @app_commands.command(name="unlock", description="Unlock a previously locked channel")
    @app_commands.describe(channel="Channel to unlock (defaults to the current channel)", reason="Reason for unlocking")
    @has_permission("manage_channels")
    async def unlock(self, interaction: discord.Interaction, channel: discord.TextChannel = None, reason: str = None):
        channel = channel or interaction.channel
        everyone = interaction.guild.default_role

        overwrite = channel.overwrites_for(everyone)
        overwrite.send_messages = None  # clears the deny, reverting to category/server default
        await channel.set_permissions(everyone, overwrite=overwrite, reason=reason)

        await interaction.response.send_message(
            embed=success_embed("🔓 Channel unlocked", f"{channel.mention} is now unlocked.\nReason: {reason or 'No reason provided'}")
        )
        await send_log(
            self.bot, interaction.guild,
            success_embed("🔓 Channel unlocked", f"Channel: {channel.mention}\nBy: {interaction.user.mention}\nReason: {reason or 'No reason provided'}"),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Lockdown(bot))