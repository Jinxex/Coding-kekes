import discord
from discord.commands import SlashCommandGroup, option
from discord.ext import commands
from ezcord import View
import ezcord

class RegelwerkDB(ezcord.DBHandler):
    def __init__(self):
        super().__init__("db/regelwerk.db")

    async def setup(self):
        await self.execute(
            """CREATE TABLE IF NOT EXISTS regelwerk(
            server_id INTEGER PRIMARY KEY,
            role_id INTEGER DEFAULT 0,
            channel_id INTEGER DEFAULT 0
            )"""
        )

    async def set_regelwerk_channel(self, server_id, channel_id):
        await self.execute(
            "INSERT INTO regelwerk (server_id, channel_id) VALUES (?, ?) ON CONFLICT(server_id) DO UPDATE SET channel_id = ?",
            (server_id, channel_id, channel_id)
        )

    async def get_channel(self, server_id):
        return await self.one("SELECT channel_id FROM regelwerk WHERE server_id = ?", (server_id,))

    async def set_regelwerk_role(self, server_id, role_id):
        await self.execute(
            "INSERT INTO regelwerk (server_id, role_id) VALUES (?, ?) ON CONFLICT(server_id) DO UPDATE SET role_id = ?",
            (server_id, role_id, role_id)
        )

    async def get_role(self, server_id):
        return await self.one("SELECT role_id FROM regelwerk WHERE server_id = ?", (server_id,))


db = RegelwerkDB()

class Regelwerk(ezcord.Cog):

    def __init__(self, bot):
        self.bot = bot

    @ezcord.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(RulesButton(self.bot))
        self.bot.add_view(RoleRules())

    regelwerk = SlashCommandGroup("regelwerk", default_member_permissions=discord.Permissions(administrator=True))

    @regelwerk.command(name="setup", description="Create a regelwerk")
    @option("channel", description="Select a regelwerk Channel")
    @option("role", description="Select a regelwerk role")
    async def setup_command(self, ctx, channel: discord.TextChannel, role: discord.Role):
        server_id = ctx.guild.id
        channel_id = channel.id
        role_id = role.id
        await db.set_regelwerk_channel(server_id, channel_id)
        await db.set_regelwerk_role(server_id, role_id)
        embed = discord.Embed(
            title="Regelwerk Setup",
            description="Regelwerk setup complete!",
            color=discord.Color.dark_blue()
        )
        await ctx.respond(embed=embed, view=RulesButton(self.bot))


def setup(bot):
    bot.add_cog(Regelwerk(bot))

class RulesButton(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Rules setup", style=discord.ButtonStyle.green, row=1, custom_id="rules_button")
    async def rules_back(self, button, interaction):
        await interaction.response.send_modal(RulesModal(self.bot))

class RoleRules(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="I have read the rules", style=discord.ButtonStyle.primary, row=1, emoji="✔",
                       custom_id="role_button")
    async def role_back(self, button, interaction):
        role_id = await db.get_role(interaction.guild.id)
        role = discord.utils.get(interaction.guild.roles, id=role_id)
        if role:
            if role in interaction.user.roles:
                await interaction.response.send_message(f"You already have the {role.mention}.", ephemeral=True)
            else:
                try:
                    await interaction.user.add_roles(role)
                except discord.Forbidden:
                    await interaction.response.send_message("I don't have permission to assign roles.", ephemeral=True)
                else:
                    embed = discord.Embed(
                        title="Thank you for reading the rules",
                        description=f"You have now received the {role.mention}",
                        color=discord.Color.green()
                    )
                    embed.set_thumbnail(url=interaction.user.avatar.url)
                    await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("No role found in the database.", ephemeral=True)


class RulesModal(discord.ui.Modal):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(
            discord.ui.InputText(
                label="Rules Title",
                placeholder="Placeholder"
            ),
            discord.ui.InputText(
                label="Rules Description",
                placeholder="Placeholder",
                style=discord.InputTextStyle.long
            ),
            title="Set of rules setup",
            *args,
            **kwargs
        )
        self.bot = bot

    async def callback(self, interaction):
        embed = discord.Embed(
            title=self.children[0].value,
            description=self.children[1].value,
            color=discord.Color.green()
        )

        channel_id = await db.get_channel(interaction.guild.id)
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.send(embed=embed, view=RoleRules())
                await interaction.response.send_message(f"I created your rules in {channel.mention}",
                                                        ephemeral=True)
            else:
                await interaction.response.send_message("Error: Channel not found")
        else:
            await interaction.response.send_message("Error: Channel ID not found")

