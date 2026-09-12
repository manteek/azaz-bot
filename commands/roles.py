import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import success_embed, error_embed


class RoleButton(discord.ui.Button):
    def __init__(self, role_id: int, label: str):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, custom_id=f"selfrole:{role_id}")
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(self.role_id)
        if role is None:
            return await interaction.response.send_message(embed=error_embed("Role missing", "That role no longer exists."), ephemeral=True)

        member = interaction.user
        if role in member.roles:
            await member.remove_roles(role, reason="Self-role toggle")
            await interaction.response.send_message(embed=success_embed("Role removed", role.mention), ephemeral=True)
        else:
            await member.add_roles(role, reason="Self-role toggle")
            await interaction.response.send_message(embed=success_embed("Role added", role.mention), ephemeral=True)


class SelfRoleView(discord.ui.View):
    def __init__(self, role_rows):
        super().__init__(timeout=None)  # persistent — buttons never expire
        for row in role_rows:
            self.add_item(RoleButton(row["role_id"], row["label"]))


class Roles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    roles_group = app_commands.Group(
        name="roles", description="Configure self-assignable roles",
        default_permissions=discord.Permissions(administrator=True),
    )

    @roles_group.command(name="add", description="Add a role to the self-assign menu")
    @app_commands.describe(role="The role to make self-assignable", label="Button label shown to members")
    async def add(self, interaction: discord.Interaction, role: discord.Role, label: str):
        if role >= interaction.guild.me.top_role:
            return await interaction.response.send_message(
                embed=error_embed("Role too high", "I can't manage a role positioned above or equal to my own top role."),
                ephemeral=True,
            )
        await self.bot.db.add_self_role(interaction.guild.id, role.id, label)
        await interaction.response.send_message(embed=success_embed("Self-role added", f"{role.mention} as \"{label}\""))

    @roles_group.command(name="remove", description="Remove a role from the self-assign menu")
    async def remove(self, interaction: discord.Interaction, role: discord.Role):
        await self.bot.db.remove_self_role(interaction.guild.id, role.id)
        await interaction.response.send_message(embed=success_embed("Self-role removed", role.mention))

    @roles_group.command(name="setup", description="Post the self-assign role menu in this channel")
    async def setup_menu(self, interaction: discord.Interaction):
        rows = await self.bot.db.get_self_roles(interaction.guild.id)
        if not rows:
            return await interaction.response.send_message(
                embed=error_embed("No roles configured", "Add some with `/roles add` first."), ephemeral=True
            )
        view = SelfRoleView(rows)
        await interaction.response.send_message(embed=success_embed("Pick your roles", "Click a button to toggle a role."), view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Roles(bot))