import discord


async def send_log(bot, guild: discord.Guild, embed: discord.Embed):
    """Sends an embed to the guild's configured log channel, if one is set and reachable."""
    config = await bot.db.get_guild_config(guild.id)
    channel_id = config["log_channel_id"]
    if not channel_id:
        return

    channel = guild.get_channel(channel_id)
    if channel is None:
        return  # channel was deleted; config still points at a dead ID, silently skip

    try:
        await channel.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        pass  # bot lost send perms or the request failed — don't crash the caller over a log line