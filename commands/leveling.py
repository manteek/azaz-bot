import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import base_embed, success_embed


def xp_for_level(level: int) -> int:
    return 5 * (level ** 2) + 50 * level + 100


class Leveling(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="rank", description="Show your (or another member's) level and XP")
    @app_commands.describe(member="Member to check (defaults to you)")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        row = await self.bot.db.get_xp(interaction.guild.id, member.id)
        next_level_xp = xp_for_level(row["level"] + 1)
        embed = base_embed(f"Rank — {member}", f"Level **{row['level']}** • {row['xp']}/{next_level_xp} XP")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="level", description="Show your current level")
    @app_commands.describe(member="Member to check (defaults to you)")
    async def level(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        row = await self.bot.db.get_xp(interaction.guild.id, member.id)
        await interaction.response.send_message(embed=success_embed(f"{member} is level {row['level']}"))

    @app_commands.command(name="leaderboard", description="Show the server's XP leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        rows = await self.bot.db.get_xp_leaderboard(interaction.guild.id, limit=10)
        if not rows:
            return await interaction.response.send_message(embed=success_embed("Leaderboard", "No XP data yet."))

        lines = []
        for i, row in enumerate(rows, start=1):
            lines.append(f"**{i}.** <@{row['user_id']}> — Level {row['level']} ({row['xp']} XP)")
        await interaction.response.send_message(embed=success_embed("🏆 XP Leaderboard", "\n".join(lines)))


async def setup(bot: commands.Bot):
    await bot.add_cog(Leveling(bot))