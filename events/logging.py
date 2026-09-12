import discord
from discord.ext import commands

from utils.embeds import success_embed
from utils.logging_helper import send_log


class AuditLogging(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick != after.nick:
            embed = success_embed("📝 Nickname changed", f"{after.mention}\n`{before.nick}` → `{after.nick}`")
            await send_log(self.bot, after.guild, embed)

        if before.roles != after.roles:
            added = set(after.roles) - set(before.roles)
            removed = set(before.roles) - set(after.roles)
            if added or removed:
                embed = success_embed("🎭 Roles changed", after.mention)
                if added:
                    embed.add_field(name="Added", value=", ".join(r.mention for r in added), inline=False)
                if removed:
                    embed.add_field(name="Removed", value=", ".join(r.mention for r in removed), inline=False)
                await send_log(self.bot, after.guild, embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if before.channel == after.channel:
            return
        if before.channel is None:
            desc = f"{member.mention} joined 🔊 {after.channel.name}"
        elif after.channel is None:
            desc = f"{member.mention} left 🔊 {before.channel.name}"
        else:
            desc = f"{member.mention} moved {before.channel.name} → {after.channel.name}"
        await send_log(self.bot, member.guild, success_embed("🎙️ Voice activity", desc))


async def setup(bot: commands.Bot):
    await bot.add_cog(AuditLogging(bot))