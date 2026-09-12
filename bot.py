import logging
import discord
from discord.ext import commands

from config.settings import DISCORD_TOKEN
from database.database import Database
from utils.embeds import error_embed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bot")

INITIAL_EXTENSIONS = [
    "commands.utility",
    "commands.moderation",
    "commands.config",
    "commands.roles",
    "commands.leveling",
    "commands.economy",
    "commands.polls",
    "commands.reminders",
    "commands.server_setup",
    "events.member_events",
    "events.message_events",
    "events.logging",
]


class DiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.db = Database()

    async def setup_hook(self):
        await self.db.connect()
        for extension in INITIAL_EXTENSIONS:
            await self.load_extension(extension)
            logger.info(f"Loaded extension: {extension}")

        await self._restore_self_role_views()

        synced = await self.tree.sync()
        logger.info(f"Synced {len(synced)} slash command(s)")

    async def _restore_self_role_views(self):
        from commands.roles import SelfRoleView
        guild_rows = await self.db.get_guilds_with_self_roles()
        for guild_row in guild_rows:
            role_rows = await self.db.get_self_roles(guild_row["guild_id"])
            self.add_view(SelfRoleView(role_rows))

    async def close(self):
        await self.db.close()
        await super().close()


bot = DiscordBot()


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """
    Central error handler for all slash commands. Individual commands
    don't need their own try/except for these common cases.
    """
    if isinstance(error, discord.app_commands.MissingPermissions):
        message = "You don't have permission to use this command."
    elif isinstance(error, discord.app_commands.CommandOnCooldown):
        message = f"This command is on cooldown. Try again in {error.retry_after:.1f}s."
    elif isinstance(error, discord.app_commands.CheckFailure):
        message = "You can't use this command here."
    elif isinstance(error, discord.Forbidden):
        message = "I don't have the required Discord permissions to do that."
    else:
        logger.exception("Unhandled app command error", exc_info=error)
        message = "Something went wrong running that command."

    embed = error_embed("Error", message)
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=True)


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN, log_handler=None)