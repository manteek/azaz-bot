import discord
from discord import app_commands


def has_permission(permission: str):
    """
    Decorator factory for slash commands. Checks the invoking member
    has the given discord.Permissions attribute (e.g. "kick_members").
    Raises app_commands.MissingPermissions on failure, which the global
    error handler in bot.py turns into a clean user-facing message.
    """
    def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.__getattribute__(permission):
            return True
        raise app_commands.MissingPermissions([permission])

    return app_commands.check(predicate)


def bot_has_permission(interaction: discord.Interaction, permission: str) -> bool:
    """Check the bot's own permissions in the current guild before acting."""
    bot_member = interaction.guild.me
    return getattr(bot_member.guild_permissions, permission, False)