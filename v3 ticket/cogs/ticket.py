import discord
from discord.commands import SlashCommandGroup, option, Option
import ezcord
from datetime import datetime
import chat_exporter
import asyncio
import io

from discord.utils import basic_autocomplete


class TicketDB(ezcord.DBHandler):
    def __init__(self):
        super().__init__("db/ticket.db")

    async def setup(self):
        try:
            await self.execute(
                """CREATE TABLE IF NOT EXISTS ticket(
                guild_id INTEGER PRIMARY KEY,
                category_id INTEGER DEFAULT 0,
                teamrole_id INTEGER DEFAULT 0,
                logs_channel_id INTEGER DEFAULT 0,
                channel_id INTEGER DEFAULT 0,
                message_id INTEGER DEFAULT 0
                )"""
            )
            await self.execute(
                """CREATE TABLE IF NOT EXISTS ticket_options(
                guild_id INTEGER,
                option_name TEXT,
                FOREIGN KEY(guild_id) REFERENCES ticket(guild_id)
                )"""
            )
            print("Tables 'ticket' and 'names' created successfully")
        except Exception as e:
            print(f"An error occurred while creating the tables: {e}")



    async def set_category(self, guild_id, category_id):
        await self.execute(
            "INSERT OR IGNORE INTO ticket  (guild_id, category_id) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET category_id = ?",
            (guild_id, category_id, category_id)
        )

    async def get_category(self, guild_id):
        return await self.one("SELECT category_id FROM ticket WHERE guild_id = ?", (guild_id,))

    async def set_teamrole(self, guild_id, teamrole_id):
        await self.execute(
            "INSERT OR IGNORE INTO ticket (guild_id, teamrole_id) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET teamrole_id = ?",
            (guild_id, teamrole_id, teamrole_id)
        )

    async def get_teamrole(self, guild_id):
        return await self.one("SELECT teamrole_id FROM ticket WHERE guild_id = ?", (guild_id,))

    async def set_logs_channel(self, guild_id, logs_channel_id):
        await self.execute(
            "INSERT OR IGNORE INTO ticket (guild_id, logs_channel_id) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET logs_channel_id = ?",
            (guild_id, logs_channel_id, logs_channel_id)
        )

    async def get_logs_channel(self, guild_id):
        return await self.one("SELECT logs_channel_id FROM ticket WHERE guild_id = ?", (guild_id,))

    async def set_channel(self, guild_id, channel_id):
        await self.execute(
            "INSERT OR IGNORE INTO ticket (guild_id, channel_id) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET "
            "channel_id = ?",
            (guild_id, channel_id, channel_id)
        )

    async def get_channel(self, guild_id):
        return await self.one("SELECT channel_id FROM ticket WHERE guild_id = ?", (guild_id,))

    async def set_message(self, guild_id, message_id):
        await self.execute(
            "INSERT OR IGNORE INTO ticket (guild_id, message_id) VALUES (?, ?) ON CONFLICT(guild_id) DO UPDATE SET message_id = ?",
            (guild_id, message_id, message_id)
        )

    async def get_message(self, guild_id):
        return await self.one("SELECT message_id FROM ticket WHERE guild_id = ?", (guild_id,))

    async def add_option(self, guild_id, option_name):
        await self.execute(
            "INSERT INTO ticket_options (guild_id, option_name) VALUES (?, ?)",
            (guild_id, option_name)
        )

    async def get_options(self, guild_id):
        options = await self.all("SELECT option_name FROM ticket_options WHERE guild_id = ?", (guild_id,))
        print(f"Options for guild {guild_id}: {options}")
        return options


    async def remove_option(self, guild_id, option_name):
        await self.execute("DELETE FROM ticket_options WHERE guild_id = ? AND option_name = ?", (guild_id, option_name))



    async def name_exists(self, guild_id, option_name):
        return await self.one("SELECT option_name FROM ticket_options WHERE guild_id = ? AND option_name = ?",
                              (guild_id, option_name))
        return result is not None


    async def setup_exists(self, guild_id):
        return await self.one("SELECT guild_id FROM ticket WHERE guild_id = ?", (guild_id,))


db = TicketDB()

t_options = [
    discord.SelectOption(label="Ticket", emoji="🎫")
]


async def get_ticket(ctx: discord.AutocompleteContext):
    try:
        active_options = await db.get_options(ctx.interaction.guild.id)
        if active_options:
            ticket_options = [discord.OptionChoice(name=name, value=name) for name in active_options]
            return ticket_options
        else:
            print("Keine Optionen aus der Datenbank abgerufen.")
            return []
    except Exception as e:
        print(f"Fehler beim Abrufen der Ticket-Optionen: {e}")
        return []

my_option_count = 0
class Ticket(ezcord.Cog, emoji="🎫"):
    def __init__(self, bot):
        self.bot = bot
        self.ticket_owner = True
        self.channel_name = True
        self.logs_channel_name = True
        self.category_name = True

    @ezcord.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(TicketView())
        self.bot.add_view(CreateTicketSelect(t_options))
        self.bot.add_view(QuestionsButton(self.ticket_owner))
        self.bot.add_view(TicketRole(self.channel_name, self.logs_channel_name, self.category_name))

    ticket = SlashCommandGroup("ticket", default_member_permissions=discord.Permissions(administrator=True))

    @ticket.command(description="Setup the ticket system")
    @option("category", description="Select a category", type=discord.CategoryChannel)
    @option("ticket_channel", description="Select a ticket_channel", type=discord.TextChannel)
    @option("logs", description="Select a logs Channel", type=discord.TextChannel)
    async def setup(self, ctx, ticket_channel: discord.TextChannel, category: discord.CategoryChannel,
                    logs: discord.TextChannel):
        guild_id = ctx.guild.id
        if await db.setup_exists(guild_id):
            embed = discord.Embed(
                title="Ticket System Setup",
                description=f"You can only execute the command a maximum of once per server  Please {self.bot.get_cmd('ticket settings')}",
                color=discord.Color.red()
            )
            await ctx.respond(embed=embed, ephemeral=True, delete_after=10)
            return
        await ctx.defer(ephemeral=True)
        guild_id = ctx.guild.id
        category_id = category.id
        logs_channel_id = logs.id
        channel_id = ticket_channel.id
        await db.set_channel(guild_id, channel_id)
        await db.set_logs_channel(guild_id, logs_channel_id)
        await db.set_category(guild_id, category_id)
        category_name = category.name
        logs_channel_name = logs.name
        channel_name = ticket_channel.name

        embed = discord.Embed(
            title="🎫 Ticket System Setup",
            description="Welcome to the ticket system setup.",
            color=discord.Color.dark_green()
        )
        print(t_options)
        embed.add_field(name="🔘 Open Tickets",
                        value=f"``{category_name}``",
                        inline=False)
        embed.add_field(name="🎫 Ticket Channel ", value=f"``{channel_name}``", inline=False)
        embed.add_field(name="📜 Log Channel", value=f"``{logs_channel_name}``", inline=False)
        embed.add_field(name="Great! Now you can select roles that should have access to tickets.",
                        value="Click on Continue afterward.", inline=False)

        setup_message = await ctx.send(embed=embed,
                                       view=TicketRole(channel_name, logs_channel_name, category_name))
        channel_id = await db.get_channel(guild_id)
        if channel_id:
            ticket_channel = ctx.guild.get_channel(channel_id)
            if ticket_channel:
                embed = discord.Embed(
                    title="Ticket System",
                    description="Choose a category to contact support.",
                    color=discord.Color.blue()
                )
                message = await ticket_channel.send(embed=embed, view=CreateTicketSelect(t_options))
                await db.set_message(guild_id, message.id)
            else:
                print(f"Channel with ID {channel_id} not found.")
        else:
            print(f"No channel ID found for server {guild_id}.")
        await ctx.respond("The setup was completed successfully", ephemeral=True, delete_after=10)
        print(f"Setting up ticket system for guild: {guild_id}")



    @ticket.command(description="Set the ticket settings")
    async def settings(self, ctx):
        embed = discord.Embed(
            title="Ticket System Settings",
            description="You can change the settings for the ticket system.\n\n (It is in progress and will be released with a new update)",
            color=discord.Color.dark_green()
        )
        await ctx.respond(embed=embed, ephemeral=True, delete_after=10)

    @ticket.command(description="Add a ticket option")
    async def select(self, ctx, name: str, emoji: str):
        global my_option_count
        await ctx.defer(ephemeral=True)
        ticket_message = await db.get_message(ctx.guild.id)
        if ticket_message:
            try:
                if await db.name_exists(ctx.guild.id, name):
                    await ctx.respond("This name is already in use. Please choose a different name.", ephemeral=True)
                    return
                if my_option_count >= 5:
                    await ctx.respond(
                        "You have reached the maximum number of options (5). Please remove an option before adding a new one.",
                        ephemeral=True)
                    return

                message = await ctx.channel.fetch_message(ticket_message)
                t_options.append(discord.SelectOption(label=name, emoji=emoji))
                view = CreateTicketSelect(t_options)
                await message.edit(view=view)
                await ctx.respond("The option was added successfully.", ephemeral=True)
                my_option_count += 1
            except Exception as e:
                await ctx.respond(f"An error occurred: {e}", ephemeral=True)
            print(name)

            await db.add_option(ctx.guild.id, name)
        else:
            await ctx.respond(f"The ticket message was not found. Please {self.bot.get_cmd('ticket setup')} First!", ephemeral=True, delete_after=10)

    @ticket.command(description="Remove a ticket option")
    async def remove(self, ctx, name: Option(str, autocomplete=basic_autocomplete(get_ticket))):
        await ctx.defer(ephemeral=True)
        ticket_message = await db.get_message(ctx.guild.id)
        if ticket_message:
            try:
                message = await ctx.channel.fetch_message(ticket_message)
                await db.remove_option(ctx.guild.id,
                                     name)
                for option in t_options:
                    if option.label == name:
                        t_options.remove(option)
                view = CreateTicketSelect(t_options)
                await message.edit(view=view)
                await ctx.respond("The option was removed successfully.", ephemeral=True)
            except Exception as e:
                await ctx.respond(f"An error occurred: {e}", ephemeral=True)
        else:
            await ctx.respond(f"The ticket message was not found. Please {self.bot.get_cmd('ticket setup')} First!", ephemeral=True, delete_after=10)





def setup(bot):
    bot.add_cog(Ticket(bot))


class TicketRole(discord.ui.View):
    def __init__(self, channel_name, logs_channel_name, category_name):
        super().__init__(timeout=None)
        self.category_name = category_name
        self.channel_name = channel_name
        self.logs_channel_name = logs_channel_name

    @discord.ui.role_select(placeholder="Wähle Rollen aus", min_values=1, max_values=1, custom_id="role", row=1)
    async def role_callback(self, select, interaction):
        try:
            teamrole_id = select.values[0].id
            await db.set_teamrole(interaction.guild.id, teamrole_id)
            selected_role = interaction.guild.get_role(teamrole_id)
            role_mention = selected_role.mention if selected_role else "Unknown Role"
            embed = discord.Embed(
                title="🎫 Ticket System Setup",
                description="Welcome to the ticket system setup. Follow the instructions below to configure your ticket system.",
                color=discord.Color.dark_green()
            )
            embed.add_field(name="🔘Open Tickets",
                            value=f"``{self.category_name}``",
                            inline=False)
            embed.add_field(name="🎫 Ticket Channel ", value=f"``{self.channel_name}``", inline=False)
            embed.add_field(name="📜 Log Channel", value=f"``{self.logs_channel_name}``", inline=False)
            embed.add_field(name="Great! Now you can select roles that should have access to tickets.",
                            value=f"The following roles can access tickets: {role_mention}\nClick on Continue afterward.",
                            inline=False)
            await interaction.response.edit_message(embed=embed, view=None)
        except Exception as e:
            print(f"Error setting teamrole: {e}")




class CreateTicketSelect(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.options = db.get_options(self.guild_id)

    @discord.ui.select(
        custom_id="bro_i_dont_know",
        placeholder="👆 | CLICK ME!",
        options=t_options,
    )
    async def ticket_select_callback(self, select, interaction):
        category_id = await db.get_category(interaction.guild.id)
        teamrole_id = await db.get_teamrole(interaction.guild.id)

        if category_id:
            category = discord.utils.get(interaction.guild.categories, id=category_id)

            if category:
                overwrites = {
                    interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    interaction.user: discord.PermissionOverwrite(view_channel=True, read_message_history=True,
                                                                  send_messages=True),
                    interaction.guild.me: discord.PermissionOverwrite(view_channel=True, read_message_history=True,
                                                                      send_messages=True),
                }
                team_role = interaction.guild.get_role(teamrole_id)
                if team_role:
                    topic = f"Ticket for {interaction.user.name}. Contact {team_role.mention} for assistance."
                else:
                    topic = f"Ticket for {interaction.user.name}. Contact staff for assistance."

                channel = await category.create_text_channel(name=f"{select.values}",
                                                             overwrites=overwrites, topic=topic)

                msg = await channel.send(
                    f"{team_role.mention if team_role else '@staff'} {interaction.user.mention} has opened a ticket.")

                # Creating the Embed
                embed = discord.Embed(
                    title="🎫 Ticket",
                    description=f"Hey, {interaction.user.mention}!\n\nHow can we assist you? A moderator will be with you shortly.",
                    color=discord.Color.blue()
                )

                await channel.send(embed=embed, view=TicketView())
                await interaction.response.send_message(f"I've opened a ticket for you at {channel.mention}",
                                                        ephemeral=True)
                return

        await interaction.response.send_message(
            "The category ID is not set in the database or the specified category doesn't exist.", ephemeral=True)


options = [
    discord.SelectOption(label="Add User", description="Add User to ticket", emoji="👥"),
    discord.SelectOption(label="Remove User", description="Remove a user from ticket",
                         emoji="<:redcross:758380151238033419>"),
    discord.SelectOption(label="Do you still have questions?",
                         description="Ask the user if they have any further questions", emoji="❓")
]


class QuestionsButton(discord.ui.View):
    def __init__(self, ticket_owner):
        super().__init__(timeout=None)
        self.ticket_owner = ticket_owner
        self.button_clicked = False

    @discord.ui.button(label="Have questions", emoji="<:Haken:1231162694854246410>", row=1, custom_id="yes")
    async def yes_button(self, button, interaction):
        ticket_owner_name = interaction.channel.topic.split("Ticket for ")[1].split(".")[0]
        ticket_owner = discord.utils.get(interaction.guild.members, name=ticket_owner_name)

        if not ticket_owner:
            await interaction.response.send_message("❌ Ticket owner not found.", ephemeral=True)
            return

        if self.button_clicked:
            await interaction.response.send_message("You have already clicked the button.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"👋 Hi {ticket_owner.display_name}",
            description=f"🎫 Hi {ticket_owner.display_name}, the ticket will be automatically deleted in ⏰ **24 hours**. \n Thank you for trusting the ``ticket team``. If you have any questions, feel free to ask!",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

        self.button_clicked = True

    @discord.ui.button(label="No I have not", style=discord.ButtonStyle.blurple,
                       emoji="<:Loeschen:1231184154427920465>", row=1, custom_id="close_ticket")
    async def no_ticket(self, button, interaction):
        ticket_owner_name = interaction.channel.topic.split("Ticket for ")[1].split(".")[0]
        ticket_owner = discord.utils.get(interaction.guild.members, name=ticket_owner_name)

        if not ticket_owner:
            await interaction.response.send_message("❌ Ticket owner not found.", ephemeral=True)
            return

        server_id = interaction.guild.id

        embed = discord.Embed(
            title="Close Ticket",
            description="Deleting Ticket in less than `10 Seconds`... ⏳\n\n"
                        "_If not, you can do it manually!_",
            color=discord.Color.dark_red()
        )

        await interaction.response.edit_message(view=self)
        await interaction.followup.send(embed=embed, ephemeral=True)

        transcript = await chat_exporter.export(interaction.channel)

        if transcript is None:
            return

        transcript_file = discord.File(
            io.BytesIO(transcript.encode()),
            filename=f"transcript-{interaction.channel.name}.html",
        )

        if ticket_owner and not ticket_owner.dm_channel:
            log_channel_id = await db.get_logs_channel(server_id)
            log_channel = interaction.guild.get_channel(log_channel_id)

            if log_channel:
                message = await log_channel.send(file=transcript_file)
                link = await chat_exporter.link(message)
                embed = discord.Embed(
                    title="Your Ticket has been Closed",
                    description=f"Your ticket at **{interaction.guild.name}** has been closed.\n"
                                f"Ticket Channel: ```{interaction.channel.name}```\n\n"
                                f"You can find the **transcript** [here]({link}).\n\n",
                    color=discord.Color.blue()
                )
                embed.timestamp = datetime.utcnow()
                await ticket_owner.send(embed=embed)

        await asyncio.sleep(5)
        await interaction.channel.delete()


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.clicked = False

    @discord.ui.button(label="Ticket accepted", style=discord.ButtonStyle.green, emoji="🗂️", row=1,
                       custom_id="accepted_button")
    async def accept_ticket(self, button, interaction):
        # Überprüfen, ob der Button bereits geklickt wurde
        if self.clicked:
            await interaction.response.send_message("You have already accepted the ticket.", ephemeral=True)
            return

        button.disabled = True
        self.clicked = True

        team_role_id = await db.get_teamrole(interaction.guild.id)
        if team_role_id is None:
            await interaction.response.send_message(
                "The team role has not been configured. Please contact the administrator.", ephemeral=True)
            return

        team_role = interaction.guild.get_role(team_role_id)
        if team_role is None:
            await interaction.response.send_message(
                "The configured team role was not found. Please contact the administrator.", ephemeral=True)
            return

        if team_role not in interaction.user.roles:
            await interaction.response.send_message("You are not authorized to accept this ticket.", ephemeral=True)
            return

        await interaction.response.defer()
        member = interaction.user
        embed = discord.Embed(
            title="<a:Prozess:1231185270502588467> | Ticket accepted",
            description=f"<a:Prozess:1231185270502588467> | {member.mention} will now attend to your request!",
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.blurple, emoji="🔐", row=1, custom_id="close_ticket")
    async def close_ticket(self, button, interaction):
        server_id = interaction.guild.id

        embed = discord.Embed(
            title="Close Ticket",
            description="Deleting Ticket in less than `10 Seconds`... ⏳\n\n"
                        "_If not, you can do it manually!_",
            color=discord.Color.dark_red()
        )

        await interaction.response.edit_message(view=self)
        await interaction.followup.send(embed=embed)

        transcript = await chat_exporter.export(interaction.channel)

        if transcript is None:
            return

        transcript_file = discord.File(
            io.BytesIO(transcript.encode()),
            filename=f"transcript-{interaction.channel.name}.html",
        )

        ticket_owner_name = interaction.channel.topic.split("Ticket for ")[1].split(".")[0]
        ticket_owner = discord.utils.get(interaction.guild.members, name=ticket_owner_name)

        if ticket_owner and not ticket_owner.dm_channel:
            log_channel_id = await db.get_logs_channel(server_id)
            log_channel = interaction.guild.get_channel(log_channel_id)

            if log_channel:
                message = await log_channel.send(file=transcript_file)
                link = await chat_exporter.link(message)

                userembed = discord.Embed(
                    title="Your ticket has been closed",
                    description=f"Your ticket has been closed.\n"
                                f"You can find the transcript [here]({link}).",
                    color=discord.Color.blue(),
                )
                await ticket_owner.send(embed=userembed)

        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.select(
        custom_id="ticket_actions",
        min_values=1,
        max_values=2,
        placeholder="Choose an action",
        options=options,
    )
    async def handle_ticket_actions(self, select, interaction):
        server_id = interaction.guild.id
        teamrole_id = await db.get_teamrole(server_id)

        user_roles = [role.id for role in interaction.user.roles]

        if teamrole_id not in user_roles:
            await interaction.response.send_message("You don't have the required role to perform this action.",
                                                    ephemeral=True)
            return

        selected_options = interaction.data.get('values', [])
        channel = interaction.channel
        await interaction.message.edit(view=self)

        if "Add User" in selected_options:
            await interaction.response.send_modal(AddUserModal())
        elif "Remove User" in selected_options:
            await interaction.response.send_modal(RemoveUserModal())

        if "Do you still have questions?" in selected_options:
            ticket_owner_name = interaction.channel.topic.split("Ticket for ")[1].split(".")[0]
            ticket_owner = discord.utils.get(interaction.guild.members, name=ticket_owner_name)

            if ticket_owner:
                embed = discord.Embed(
                    title=f"<:Winken:1231183939910107146> Hi {ticket_owner.display_name}",
                    description=f"<:Ticket:1231183941952868382> Hi {ticket_owner.display_name}, the ticket will be automatically deleted in  ⏰ **24 hours**. \n Thank you for trusting the ``ticket team``. If you have any questions, feel free to ask!",
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed, view=QuestionsButton(ticket_owner))
            else:
                await interaction.response.send_message("❌ Ticket owner not found.", ephemeral=True)


class AddUserModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(
            discord.ui.InputText(
                label="User",
                placeholder="User ID",
                style=discord.InputTextStyle.short,
                custom_id="add_user",
            ),
            title="Add User to Ticket"
        )

    async def callback(self, interaction):
        user = interaction.guild.get_member(int(self.children[0].value))
        if user is None:
            return await interaction.response.send_message("Invalid user ID, make sure the user is in this guild!",
                                                           ephemeral=True)
        overwrite = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        await interaction.channel.set_permissions(user, overwrite=overwrite)
        await interaction.response.send_message(content=f"{user.mention} has been added to this ticket!",
                                                ephemeral=True)


class RemoveUserModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(
            discord.ui.InputText(
                label="Remove User",
                placeholder="User ID",
                style=discord.InputTextStyle.short,
                custom_id="remove_user",
            ),
            title=" Remove user to Ticket"
        )

    async def callback(self, interaction):
        user = interaction.guild.get_member(int(self.children[0].value))
        if user is None:
            return await interaction.response.send_message("Invalid user ID, make sure the user is in this guild!",
                                                           ephemeral=True)
        overwrite = discord.PermissionOverwrite(view_channel=False, send_messages=False, read_message_history=False)
        await interaction.channel.set_permissions(user, overwrite=overwrite)
        await interaction.response.send_message(content=f"{user.mention} has been Remove to this ticket!",
                                                ephemeral=True)