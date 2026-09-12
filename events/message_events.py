import time
import discord
from discord.ext import commands

from utils.embeds import error_embed, success_embed
from utils.logging_helper import send_log
from datetime import timedelta

# guild_id -> user_id -> list[timestamps] (in-memory, resets on restart — fine for a rolling few-second window)
_spam_tracker: dict[int, dict[int, list[float]]] = {}


class MessageEvents(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        config = await self.bot.db.get_guild_config(message.guild.id)

        if config["antispam_enabled"]:
            await self._check_spam(message, config)

        if config["xp_enabled"]:
            await self._handle_xp(message, config)

    async def _check_spam(self, message: discord.Message, config):
        now = time.monotonic()
        guild_bucket = _spam_tracker.setdefault(message.guild.id, {})
        timestamps = guild_bucket.setdefault(message.author.id, [])
        timestamps.append(now)

        interval = config["antispam_interval"]
        timestamps[:] = [t for t in timestamps if now - t <= interval]

        if len(timestamps) > config["antispam_msg_limit"]:
            timestamps.clear()
            member = message.author
            if not isinstance(member, discord.Member):
                return
            try:
                duration = discord.utils.utcnow() + timedelta(seconds=config["antispam_timeout_seconds"])
                await member.timeout(duration, reason="Automatic anti-spam timeout")
                await message.channel.send(
                    embed=error_embed("Slow down", f"{member.mention} was timed out for spamming."),
                    delete_after=10,
                )
                await send_log(
                    self.bot, message.guild,
                    error_embed("🚫 Anti-spam triggered", f"{member.mention} timed out {config['antispam_timeout_seconds']}s for spam"),
                )
            except discord.Forbidden:
                pass  # bot's role isn't high enough to timeout this member

    async def _handle_xp(self, message: discord.Message, config):
        row = await self.bot.db.get_xp(message.guild.id, message.author.id)
        cooldown = config["xp_cooldown"]

        if row["last_xp_at"]:
            import datetime
            last = datetime.datetime.fromisoformat(row["last_xp_at"])
            elapsed = (datetime.datetime.now(datetime.timezone.utc) - last).total_seconds()
            if elapsed < cooldown:
                return  # still on cooldown, no XP this message — this is what stops spam-leveling

        import random
        amount = random.randint(config["xp_min"], config["xp_max"])
        new_xp, new_level, leveled_up = await self.bot.db.add_xp(message.guild.id, message.author.id, amount)

        if leveled_up:
            announcement = success_embed("🎉 Level up!", f"{message.author.mention} reached level **{new_level}**!")
            target_channel = message.channel
            if config["level_up_channel_id"]:
                channel = message.guild.get_channel(config["level_up_channel_id"])
                if channel:
                    target_channel = channel
            try:
                await target_channel.send(embed=announcement)
            except discord.Forbidden:
                pass

            level_roles = await self.bot.db.get_level_roles(message.guild.id)
            role_to_give = next((r for r in level_roles if r["level"] == new_level), None)
            if role_to_give:
                role = message.guild.get_role(role_to_give["role_id"])
                if role:
                    try:
                        await message.author.add_roles(role, reason=f"Reached level {new_level}")
                    except discord.Forbidden:
                        pass

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        embed = error_embed("🗑️ Message deleted", f"Author: {message.author.mention}\nChannel: {message.channel.mention}")
        if message.content:
            embed.add_field(name="Content", value=message.content[:1000], inline=False)
        await send_log(self.bot, message.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        embed = success_embed("✏️ Message edited", f"Author: {before.author.mention}\nChannel: {before.channel.mention}")
        embed.add_field(name="Before", value=(before.content or "*(empty)*")[:500], inline=False)
        embed.add_field(name="After", value=(after.content or "*(empty)*")[:500], inline=False)
        await send_log(self.bot, before.guild, embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(MessageEvents(bot))