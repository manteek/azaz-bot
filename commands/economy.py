import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta

from utils.embeds import success_embed, error_embed


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="balance", description="Check your (or another member's) balance")
    @app_commands.describe(member="Member to check (defaults to you)")
    async def balance(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        config = await self.bot.db.get_guild_config(interaction.guild.id)
        bal = await self.bot.db.get_balance(interaction.guild.id, member.id)
        await interaction.response.send_message(
            embed=success_embed(f"{member}'s balance", f"{bal} {config['economy_currency_name']}")
        )

    @app_commands.command(name="daily", description="Claim your daily currency")
    async def daily(self, interaction: discord.Interaction):
        config = await self.bot.db.get_guild_config(interaction.guild.id)
        last = await self.bot.db.get_last_daily(interaction.guild.id, interaction.user.id)

        if last:
            elapsed = datetime.now(timezone.utc) - datetime.fromisoformat(last)
            if elapsed < timedelta(hours=24):
                remaining = timedelta(hours=24) - elapsed
                hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                minutes = remainder // 60
                return await interaction.response.send_message(
                    embed=error_embed("Already claimed", f"Come back in {hours}h {minutes}m."), ephemeral=True
                )

        new_balance = await self.bot.db.update_balance(interaction.guild.id, interaction.user.id, config["daily_amount"])
        await self.bot.db.set_last_daily(interaction.guild.id, interaction.user.id)
        await interaction.response.send_message(
            embed=success_embed("Daily claimed!", f"+{config['daily_amount']} {config['economy_currency_name']} (balance: {new_balance})")
        )

    @app_commands.command(name="give", description="Give currency to another member")
    @app_commands.describe(member="Who to give currency to", amount="Amount to give")
    async def give(self, interaction: discord.Interaction, member: discord.Member, amount: app_commands.Range[int, 1]):
        if member.id == interaction.user.id:
            return await interaction.response.send_message(embed=error_embed("Nice try", "You can't give currency to yourself."), ephemeral=True)
        if member.bot:
            return await interaction.response.send_message(embed=error_embed("Invalid target", "You can't give currency to a bot."), ephemeral=True)

        sender_balance = await self.bot.db.get_balance(interaction.guild.id, interaction.user.id)
        if sender_balance < amount:
            return await interaction.response.send_message(embed=error_embed("Insufficient balance", f"You only have {sender_balance}."), ephemeral=True)

        await self.bot.db.update_balance(interaction.guild.id, interaction.user.id, -amount)
        await self.bot.db.update_balance(interaction.guild.id, member.id, amount)

        config = await self.bot.db.get_guild_config(interaction.guild.id)
        await interaction.response.send_message(
            embed=success_embed("Transfer complete", f"{interaction.user.mention} gave {amount} {config['economy_currency_name']} to {member.mention}")
        )

    @app_commands.command(name="econ-leaderboard", description="Show the server's currency leaderboard")
    async def econ_leaderboard(self, interaction: discord.Interaction):
        config = await self.bot.db.get_guild_config(interaction.guild.id)
        rows = await self.bot.db.get_economy_leaderboard(interaction.guild.id, limit=10)
        if not rows:
            return await interaction.response.send_message(embed=success_embed("Leaderboard", "No balances yet."))

        lines = [f"**{i}.** <@{row['user_id']}> — {row['balance']} {config['economy_currency_name']}" for i, row in enumerate(rows, start=1)]
        await interaction.response.send_message(embed=success_embed("💰 Economy Leaderboard", "\n".join(lines)))


async def setup(bot: commands.Bot):
    await bot.add_cog(Economy(bot))