import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed
from utils.logging_helper import send_log


class Config(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    config_group = app_commands.Group(
        name="config", description="Configure the bot for this server",
        default_permissions=discord.Permissions(administrator=True),
    )

    async def _log_change(self, interaction: discord.Interaction, setting: str, value: str):
        embed = success_embed("Config updated", f"**{setting}** set to {value}")
        embed.add_field(name="Changed by", value=interaction.user.mention)
        await send_log(self.bot, interaction.guild, embed)

    @config_group.command(name="welcome-channel", description="Set the channel for welcome messages")
    async def welcome_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self.bot.db.update_guild_config(interaction.guild.id, welcome_channel_id=channel.id)
        await interaction.response.send_message(embed=success_embed("Welcome channel set", channel.mention))
        await self._log_change(interaction, "Welcome channel", channel.mention)

    @config_group.command(name="goodbye-channel", description="Set the channel for goodbye messages")
    async def goodbye_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self.bot.db.update_guild_config(interaction.guild.id, goodbye_channel_id=channel.id)
        await interaction.response.send_message(embed=success_embed("Goodbye channel set", channel.mention))
        await self._log_change(interaction, "Goodbye channel", channel.mention)

    @config_group.command(name="log-channel", description="Set the channel for moderation/audit logs")
    async def log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self.bot.db.update_guild_config(interaction.guild.id, log_channel_id=channel.id)
        await interaction.response.send_message(embed=success_embed("Log channel set", channel.mention))

    @config_group.command(name="autorole", description="Set a role automatically given to new members")
    async def autorole(self, interaction: discord.Interaction, role: discord.Role):
        await self.bot.db.update_guild_config(interaction.guild.id, autorole_id=role.id)
        await interaction.response.send_message(embed=success_embed("Autorole set", role.mention))
        await self._log_change(interaction, "Autorole", role.mention)

    @config_group.command(name="level-up-channel", description="Set the channel for level-up announcements")
    async def level_up_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self.bot.db.update_guild_config(interaction.guild.id, level_up_channel_id=channel.id)
        await interaction.response.send_message(embed=success_embed("Level-up channel set", channel.mention))

    @config_group.command(name="xp-settings", description="Configure XP gain per message and cooldown")
    async def xp_settings(self, interaction: discord.Interaction, min_xp: int, max_xp: int, cooldown_seconds: int):
        await self.bot.db.update_guild_config(
            interaction.guild.id, xp_min=min_xp, xp_max=max_xp, xp_cooldown=cooldown_seconds
        )
        await interaction.response.send_message(
            embed=success_embed("XP settings updated", f"{min_xp}-{max_xp} XP, {cooldown_seconds}s cooldown")
        )

    @config_group.command(name="level-role", description="Give a role automatically at a given level")
    async def level_role(self, interaction: discord.Interaction, level: int, role: discord.Role):
        await self.bot.db.set_level_role(interaction.guild.id, level, role.id)
        await interaction.response.send_message(
            embed=success_embed("Level role set", f"Level {level} → {role.mention}")
        )

    @config_group.command(name="currency-name", description="Set the name of the server currency")
    async def currency_name(self, interaction: discord.Interaction, name: str):
        await self.bot.db.update_guild_config(interaction.guild.id, economy_currency_name=name)
        await interaction.response.send_message(embed=success_embed("Currency name updated", name))

    @config_group.command(name="daily-amount", description="Set how much currency /daily gives")
    async def daily_amount(self, interaction: discord.Interaction, amount: int):
        await self.bot.db.update_guild_config(interaction.guild.id, daily_amount=amount)
        await interaction.response.send_message(embed=success_embed("Daily amount updated", str(amount)))

    @config_group.command(name="antispam", description="Configure anti-spam thresholds")
    async def antispam(
        self, interaction: discord.Interaction,
        enabled: bool, message_limit: int = 5, interval_seconds: int = 5, timeout_seconds: int = 60,
    ):
        await self.bot.db.update_guild_config(
            interaction.guild.id,
            antispam_enabled=int(enabled),
            antispam_msg_limit=message_limit,
            antispam_interval=interval_seconds,
            antispam_timeout_seconds=timeout_seconds,
        )
        await interaction.response.send_message(
            embed=success_embed(
                "Anti-spam updated",
                f"Enabled: {enabled} • {message_limit} msgs / {interval_seconds}s → {timeout_seconds}s timeout",
            )
        )

    @config_group.command(name="view", description="Show the current configuration for this server")
    async def view(self, interaction: discord.Interaction):
        c = await self.bot.db.get_guild_config(interaction.guild.id)
        guild = interaction.guild

        def ch(cid): return guild.get_channel(cid).mention if cid and guild.get_channel(cid) else "Not set"
        def rl(rid): return guild.get_role(rid).mention if rid and guild.get_role(rid) else "Not set"

        embed = success_embed(f"Configuration — {guild.name}")
        embed.add_field(name="Welcome channel", value=ch(c["welcome_channel_id"]))
        embed.add_field(name="Goodbye channel", value=ch(c["goodbye_channel_id"]))
        embed.add_field(name="Log channel", value=ch(c["log_channel_id"]))
        embed.add_field(name="Autorole", value=rl(c["autorole_id"]))
        embed.add_field(name="Level-up channel", value=ch(c["level_up_channel_id"]))
        embed.add_field(name="XP range / cooldown", value=f"{c['xp_min']}-{c['xp_max']} / {c['xp_cooldown']}s")
        embed.add_field(name="Currency", value=c["economy_currency_name"])
        embed.add_field(name="Daily amount", value=str(c["daily_amount"]))
        embed.add_field(
            name="Anti-spam",
            value=f"{'On' if c['antispam_enabled'] else 'Off'} • {c['antispam_msg_limit']}/{c['antispam_interval']}s",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Config(bot))