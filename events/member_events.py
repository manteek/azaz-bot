import discord
from discord.ext import commands

from utils.embeds import success_embed, error_embed
from utils.logging_helper import send_log


class MemberEvents(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = await self.bot.db.get_guild_config(member.guild.id)

        if config["welcome_channel_id"]:
            channel = member.guild.get_channel(config["welcome_channel_id"])
            if channel:
                try:
                    await channel.send(embed=success_embed("👋 Welcome!", f"{member.mention} just joined **{member.guild.name}**."))
                except discord.Forbidden:
                    pass

        if config["autorole_id"]:
            role = member.guild.get_role(config["autorole_id"])
            if role:
                try:
                    await member.add_roles(role, reason="Autorole on join")
                except discord.Forbidden:
                    pass

        await send_log(self.bot, member.guild, success_embed("➕ Member joined", f"{member.mention} ({member})"))

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        config = await self.bot.db.get_guild_config(member.guild.id)

        if config["goodbye_channel_id"]:
            channel = member.guild.get_channel(config["goodbye_channel_id"])
            if channel:
                try:
                    await channel.send(embed=error_embed("👋 Goodbye", f"{member} has left **{member.guild.name}**."))
                except discord.Forbidden:
                    pass

        await send_log(self.bot, member.guild, error_embed("➖ Member left", f"{member} ({member.id})"))


async def setup(bot: commands.Bot):
    await bot.add_cog(MemberEvents(bot))