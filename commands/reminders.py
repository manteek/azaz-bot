import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timezone

from utils.embeds import success_embed, error_embed
from utils.time_parse import parse_duration


class Reminders(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_reminders.start()

    def cog_unload(self):
        self.check_reminders.cancel()

    @app_commands.command(name="remind", description="Set a reminder")
    @app_commands.describe(duration="e.g. 2h, 30m, 1d, 1h30m", message="What to be reminded about")
    async def remind(self, interaction: discord.Interaction, duration: str, message: str):
        delta = parse_duration(duration)
        if delta is None:
            return await interaction.response.send_message(
                embed=error_embed("Invalid duration", "Use a format like `2h`, `30m`, `1d`, or `1h30m`."), ephemeral=True
            )

        remind_at = datetime.now(timezone.utc) + delta
        await self.bot.db.add_reminder(
            user_id=interaction.user.id,
            channel_id=interaction.channel.id,
            guild_id=interaction.guild.id if interaction.guild else None,
            remind_at=remind_at.isoformat(),
            message=message,
        )
        await interaction.response.send_message(
            embed=success_embed("Reminder set", f"I'll remind you {discord.utils.format_dt(remind_at, 'R')}")
        )

    @tasks.loop(seconds=30)
    async def check_reminders(self):
        now_iso = datetime.now(timezone.utc).isoformat()
        due = await self.bot.db.get_due_reminders(now_iso)
        for row in due:
            await self.bot.db.mark_reminder_fired(row["id"])
            channel = self.bot.get_channel(row["channel_id"])
            if channel is None:
                continue
            try:
                await channel.send(
                    content=f"<@{row['user_id']}>",
                    embed=success_embed("⏰ Reminder", row["message"] or "(no message)"),
                )
            except discord.Forbidden:
                pass

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()  # don't hit the DB/API before login finishes


async def setup(bot: commands.Bot):
    await bot.add_cog(Reminders(bot))