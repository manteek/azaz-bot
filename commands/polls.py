import discord
from discord import app_commands
from discord.ext import commands


class Polls(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="poll", description="Create a poll")
    @app_commands.describe(
        question="The poll question",
        option1="First option", option2="Second option",
        option3="Third option (optional)", option4="Fourth option (optional)",
        duration_hours="How long the poll runs, in hours (default 24)",
    )
    async def poll(
        self, interaction: discord.Interaction, question: str, option1: str, option2: str,
        option3: str = None, option4: str = None, duration_hours: app_commands.Range[int, 1, 168] = 24,
    ):
        poll = discord.Poll(question=question, duration=discord.timedelta(hours=duration_hours))
        for option in filter(None, [option1, option2, option3, option4]):
            poll.add_answer(text=option)

        await interaction.response.send_message(poll=poll)


async def setup(bot: commands.Bot):
    await bot.add_cog(Polls(bot))