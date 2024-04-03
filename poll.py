import discord
from discord.commands import SlashCommandGroup, option
import ezcord


class PollDB(ezcord.DBHandler):
    def __init__(self):
        super().__init__("db/poll.db")

    async def setup(self):
        await self.execute(
            """CREATE TABLE IF NOT EXISTS poll (
            server_id INTEGER PRIMARY KEY,
            channel_id INTEGER DEFAULT 0,
            role_id INTEGER DEFAULT 0
            )"""
        )

    async def set_role(self, server_id, role_id):
        await self.execute(
            "INSERT INTO poll (server_id, role_id) VALUES (?, ?) ON CONFLICT(server_id) DO UPDATE SET role_id = ?",
            (server_id, role_id, role_id)
        )

    async def get_role(self, server_id):
        return await self.one("SELECT role_id FROM poll WHERE server_id = ?", (server_id,))

    async def set_channel(self, server_id, channel_id):
        await self.execute(
            "INSERT INTO poll (server_id, channel_id) VALUES (?, ?) ON CONFLICT(server_id) DO UPDATE SET channel_id = ?",
            (server_id, channel_id, channel_id)
        )

    async def get_channel(self, server_id):
        channel_id = await self.one("SELECT channel_id FROM poll WHERE server_id = ?", (server_id,))
        return channel_id

db = PollDB()

class Poll(ezcord.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.upvotes = set()
        self.downvotes = set()

    @ezcord.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(PollView(bot=self.bot, title=None, description=None, upvotes=set(), downvotes=set()))

    poll = SlashCommandGroup("poll")

    @poll.command(description="Create a Poll")
    @discord.guild_only()
    async def setup(self, ctx, role: discord.Role, poll: discord.TextChannel):
        server_id = ctx.guild.id
        role_id = role.id
        channel_id = poll.id
        await db.set_channel(server_id, channel_id)
        await db.set_role(server_id, role_id)
        role_id_from_db = await db.get_role(server_id)
        channel_id_from_db = await db.get_channel(server_id)

        role_mention = ctx.guild.get_role(role_id_from_db).mention if role_id_from_db else "No role specified"
        channel_mention = ctx.guild.get_channel(
            channel_id_from_db).mention if channel_id_from_db else "No channel specified"

        embed = discord.Embed(
            title="Poll Setup",
            description="You have successfully set up the poll. Now you can start creating polls!",
            color=discord.Color.green()
        )
        embed.add_field(name="Role", value=role_mention, inline=True)
        embed.add_field(name="Channel", value=channel_mention, inline=True)
        embed.set_footer(text="Use /poll command to create polls.")
        await ctx.respond(embed=embed,ephemeral=True)

    @poll.command(description="Create a Poll")
    @discord.guild_only()
    async def create(self, ctx):
        await ctx.send_modal(PollModal(bot=self.bot))

def setup(bot):
    bot.add_cog(Poll(bot))


class PollModal(discord.ui.Modal):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(
            discord.ui.InputText(
                label="title",
                placeholder="your title",
                style=discord.InputTextStyle.short,
                required=True,
                max_length=30,
            ),
            discord.ui.InputText(
                label="Content/ Description",
                placeholder="Your content/ description of your poll ",
                style=discord.InputTextStyle.short,
                required=True,
                max_length=200
            ),
            title="Make your Poll"
        )

    async def callback(self, interaction):
        server_id = interaction.guild.id
        channel_id = await db.get_channel(server_id)
        channel = None
        if channel_id:
            channel = interaction.guild.get_channel(channel_id)

        role_id = await db.get_role(server_id)
        role = interaction.guild.get_role(role_id) if role_id else None

        embed = discord.Embed(
            title=f"{self.children[0].value}",
            description=f"{self.children[1].value}",
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="👍 __**Up Votes**__", value="```0 Votes```")
        embed.add_field(name="👎 __**Down Votes**__", value="```0 Votes```")
        embed.set_footer(text="Want to Poll something? Simply type /poll")
        poll_view = PollView(bot=self.bot, title=self.children[0].value, description=self.children[0].value,
                             upvotes=set(), downvotes=set())

        if channel:
            if role:
                await channel.send(
                    f"{role.mention} {interaction.user.mention} has opened a poll.", embed=embed, view=poll_view)
                await interaction.response.defer()
                await interaction.followup.send(
                    f"Your poll has been started in the channel: {channel.mention}", ephemeral=True)
            else:
                await channel.send(
                    f"@staff {interaction.user.mention} has opened a poll.", embed=embed, view=poll_view)
                await interaction.response.defer()
                await interaction.followup.send(
                    f"Your poll has been started in the channel: {channel.mention}", ephemeral=True)
        else:
            await interaction.response.defer()
            await interaction.followup.send(
                "No poll channel is set for this server. Please set it up first.", ephemeral=True)




class PollView(discord.ui.View):
    def __init__(self, bot, title, description,  upvotes, downvotes):
        super().__init__(timeout=None)
        self.bot = bot
        self.title = title
        self.description = description
        self.upvotes = upvotes
        self.downvotes = downvotes

    @discord.ui.button(label="", style=discord.ButtonStyle.grey, row=1, emoji="<:Check:772401517759037441>", custom_id="check")
    async def up(self, button, interaction):
        if interaction.user.id in self.upvotes:
            await interaction.response.send_message("You have already voted for Up. You can't switch your vote.",
                                                    ephemeral=True)
        else:
            self.upvotes.add(interaction.user.id)
            self.downvotes.discard(interaction.user.id)
            embed = discord.Embed(title=f"{self.title}", description=f"> {self.description}",
                                  color=discord.Color.orange()
                                  )
            embed.set_author(name=f"{interaction.user.display_name}'s Poll",
                             icon_url=f"{interaction.user.display_avatar}")
            embed.set_thumbnail(url=f"{interaction.user.display_avatar}")
            embed.add_field(name="👍 __**Up Votes**__", value=f"```{len(self.upvotes)}``` Votes")
            embed.add_field(name="👎 __**Down Votes**__", value=f"```{len(self.downvotes)}``` Votes")
            embed.set_footer(text="Want to Poll something? Simply type /poll")
            await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="", style=discord.ButtonStyle.grey, row=1 , emoji="<:Cross:772401517667680276>", custom_id="cross")
    async def down(self, button, interaction):
        if interaction.user.id in self.downvotes:
            await interaction.response.send_message("You have already voted for Up. You can't switch your vote.",
                                                    ephemeral=True)
        else:
            self.downvotes.add(interaction.user.id)
            self.upvotes.discard(interaction.user.id)
            embed = discord.Embed(title=f"{self.title}", description=f"> {self.description}",
                                  color=discord.Color.orange()
                                  )
            embed.set_author(name=f"{interaction.user.display_name}'s Poll",
                             icon_url=f"{interaction.user.display_avatar}")
            embed.set_thumbnail(url=f"{interaction.user.display_avatar}")
            embed.add_field(name="👍 __**Up Votes**__", value=f"```{len(self.upvotes)}``` Votes")
            embed.add_field(name="👎 __**Down Votes**__", value=f"```{len(self.downvotes)}``` Votes")
            embed.set_footer(text="Want to Poll something? Simply type /poll")
            await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="Who Voted?", style=discord.ButtonStyle.blurple, row=1, emoji="❓", custom_id="question")
    async def _question(self, button, interaction):
        embed = discord.Embed(title="❓ **Who reacted with what** ❓", color=discord.Color.blue())
        embed.add_field(name="Up Votes", value="\n".join(user.mention for user in map(self.bot.get_user, self.upvotes)) if self.upvotes else "None")
        embed.add_field(name="Down Votes", value="\n".join(user.mention for user in map(self.bot.get_user, self.downvotes)) if self.downvotes else "None")
        await interaction.response.send_message(embed=embed, ephemeral=True)


