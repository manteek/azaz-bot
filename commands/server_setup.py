import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed


class ServerSetup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="serverkit", description="Create the standard channel layout for this server")
    @app_commands.describe(staff_role="Optional role that should also see staff-only channels (besides admins)")
    @app_commands.default_permissions(administrator=True)
    async def serverkit(self, interaction: discord.Interaction, staff_role: discord.Role = None):
        guild = interaction.guild
        await interaction.response.defer(ephemeral=True)

        everyone = guild.default_role
        created = []

        readonly_overwrites = {everyone: discord.PermissionOverwrite(send_messages=False)}
        staff_overwrites = {
            everyone: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        if staff_role:
            staff_overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True)

        async def get_or_create_category(name, overwrites={}):
            existing = discord.utils.get(guild.categories, name=name)
            if existing:
                return existing
            cat = await guild.create_category(name, overwrites=overwrites)
            created.append(f"📁 {name}")
            return cat

        async def get_or_create_text(name, category, overwrites={}):
            existing = discord.utils.get(guild.text_channels, name=name, category=category)
            if existing:
                return existing
            ch = await guild.create_text_channel(name, category=category, overwrites=overwrites)
            created.append(f"# {name}")
            return ch

        async def get_or_create_voice(name, category):
            existing = discord.utils.get(guild.voice_channels, name=name, category=category)
            if existing:
                return existing
            ch = await guild.create_voice_channel(name, category=category)
            created.append(f"🔊 {name}")
            return ch

        # INFORMATION
        info_cat = await get_or_create_category("INFORMATION")
        welcome_ch = await get_or_create_text("welcome", info_cat, readonly_overwrites)
        await get_or_create_text("announcements", info_cat, readonly_overwrites)
        await get_or_create_text("roles", info_cat, readonly_overwrites)

        # GENERAL
        general_cat = await get_or_create_category("GENERAL")
        await get_or_create_text("general", general_cat)
        await get_or_create_text("suggestions", general_cat)
        await get_or_create_text("bot-commands", general_cat)

        # VOICE
        voice_cat = await get_or_create_category("VOICE")
        await get_or_create_voice("General", voice_cat)
        afk_vc = await get_or_create_voice("AFK", voice_cat)

        # STAFF (hidden from regular members — admins bypass overwrites automatically)
        staff_cat = await get_or_create_category("STAFF", staff_overwrites)
        mod_log = await get_or_create_text("mod-log", staff_cat)
        await get_or_create_text("mod-chat", staff_cat)
        await get_or_create_text("reports", staff_cat)

        try:
            await guild.edit(afk_channel=afk_vc, afk_timeout=300)
        except discord.Forbidden:
            pass

        await self.bot.db.update_guild_config(
            guild.id,
            log_channel_id=mod_log.id,
            welcome_channel_id=welcome_ch.id,
        )

        summary = "\n".join(created) if created else "Everything already existed — nothing new created."
        await interaction.followup.send(embed=success_embed("Server kit applied", summary), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ServerSetup(bot))