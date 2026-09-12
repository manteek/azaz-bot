import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import base_embed


class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        latency_ms = round(self.bot.latency * 1000)
        await interaction.response.send_message(
            embed=base_embed("🏓 Pong!", f"Latency: {latency_ms}ms")
        )

    @app_commands.command(name="help", description="List available commands")
    async def help(self, interaction: discord.Interaction):
        embed = base_embed("📖 Commands", "Available slash commands:")
        embed.add_field(
            name="Utility",
            value="`/ping` `/help` `/userinfo` `/serverinfo` `/avatar`",
            inline=False,
        )
        embed.add_field(
            name="Moderation",
            value="`/kick` `/ban` `/unban` `/timeout` `/untimeout` `/warn` `/warnings` `/clear` `/slowmode`",
            inline=False,
        )
        embed.add_field(
            name="Config (admin)",
            value="`/config welcome-channel` `/config goodbye-channel` `/config log-channel` `/config autorole` "
                  "`/config level-up-channel` `/config xp-settings` `/config level-role` `/config currency-name` "
                  "`/config daily-amount` `/config antispam` `/config view`",
            inline=False,
        )
        embed.add_field(
            name="Roles (admin)",
            value="`/roles add` `/roles remove` `/roles setup`",
            inline=False,
        )
        embed.add_field(
            name="Leveling",
            value="`/rank` `/level` `/leaderboard`",
            inline=False,
        )
        embed.add_field(
            name="Economy",
            value="`/balance` `/daily` `/give` `/econ-leaderboard`",
            inline=False,
        )
        embed.add_field(
            name="Polls & Reminders",
            value="`/poll` `/remind`",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="userinfo", description="Show information about a user")
    @app_commands.describe(member="The user to look up (defaults to you)")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        embed = base_embed(f"User Info — {member}")
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=member.id)
        embed.add_field(name="Joined server", value=discord.utils.format_dt(member.joined_at, "R"))
        embed.add_field(name="Account created", value=discord.utils.format_dt(member.created_at, "R"))
        roles = [r.mention for r in member.roles if r.name != "@everyone"]
        embed.add_field(name=f"Roles ({len(roles)})", value=", ".join(roles) or "None", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="Show information about this server")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = base_embed(f"Server Info — {guild.name}")
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown")
        embed.add_field(name="Members", value=guild.member_count)
        embed.add_field(name="Created", value=discord.utils.format_dt(guild.created_at, "R"))
        embed.add_field(name="Roles", value=len(guild.roles))
        embed.add_field(name="Text channels", value=len(guild.text_channels))
        embed.add_field(name="Voice channels", value=len(guild.voice_channels))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="Show a user's avatar")
    @app_commands.describe(member="The user to look up (defaults to you)")
    async def avatar(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        embed = base_embed(f"{member}'s avatar")
        embed.set_image(url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))