import discord
from discord import Interaction
from discord.commands import SlashCommandGroup, option
import ezcord
from datetime import datetime
import chat_exporter
import asyncio
import io
from discord.ext import commands

class TicketDB(ezcord.DBHandler):
    def __init__(self):
        super().__init__("db/ticket.db")

    async def setup(self):
        try:
            await self.execute(
                """CREATE TABLE IF NOT EXISTS ticket(
                server_id INTEGER PRIMARY KEY,
                category_id INTEGER DEFAULT 0,
                teamrole_id INTEGER DEFAULT 0,
                logs_channel_id INTEGER DEFAULT 0
                )"""
            )
        except Exception as e:
            print(f"Error setting up database: {e}")



    async def set_category(self, server_id, category_id):
        await self.execute(
            "INSERT OR IGNORE INTO ticket  (server_id, category_id) VALUES (?, ?) ON CONFLICT(server_id) DO UPDATE SET category_id = ?",
            (server_id, category_id, category_id)
        )

    async def get_category(self, server_id):
        return await self.one("SELECT category_id FROM ticket WHERE server_id = ?", (server_id,))

    async def set_teamrole(self, server_id, teamrole_id):
        await self.execute(
            "INSERT OR IGNORE INTO ticket (server_id, teamrole_id) VALUES (?, ?) ON CONFLICT(server_id) DO UPDATE SET teamrole_id = ?",
            (server_id, teamrole_id, teamrole_id)
        )

    async def get_teamrole(self, server_id):
        return await self.one("SELECT teamrole_id FROM ticket WHERE server_id = ?", (server_id,))

    async def set_logs_channel(self, server_id, logs_channel_id):
        await self.execute(
            "INSERT OR IGNORE INTO ticket (server_id, logs_channel_id) VALUES (?, ?) ON CONFLICT(server_id) DO UPDATE SET logs_channel_id = ?",
            (server_id, logs_channel_id, logs_channel_id)
        )

    async def get_logs_channel(self, server_id):
        return await self.one("SELECT logs_channel_id FROM ticket WHERE server_id = ?", (server_id,))

db = TicketDB()

options = [
    discord.SelectOption(label="Report user", emoji="<:Neues_Mitglied:1228519246838104075>"),
    discord.SelectOption(label="Ticket", emoji="<:Inhaber:1231162706149638185>"),
]

class Ticket(ezcord.Cog, emoji="🎫"):
    def __init__(self, bot):
        self.bot = bot

    @ezcord.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(CreateTicket())
        self.bot.add_view(TicketView())
        self.bot.add_view(CreateTicketSelect())

    ticket = SlashCommandGroup("ticket", default_member_permissions=discord.Permissions(administrator=True))

    @ticket.command(name="setup", description="Create a ticket")
    @discord.guild_only()
    @option("category", description="Select a category", type=discord.CategoryChannel)
    @option("role", description="Select a role", type=discord.Role)
    @option("logs", description="Select a logs Channel", type=discord.TextChannel)
    async def setup_command(self, ctx, category: discord.CategoryChannel, logs: discord.TextChannel,
                            role: discord.Role):
        server_id = ctx.guild.id
        category_id = category.id
        teamrole_id = role.id
        logs_channel_id = logs.id

        # Save settings to the database
        await db.set_logs_channel(server_id, logs_channel_id)
        await db.set_category(server_id, category_id)
        await db.set_teamrole(server_id, teamrole_id)

        # Create and send the embed
        embed = discord.Embed(
            title="Create a ticket",
            description="**If you need support, click `📨 Create ticket` button below and create a ticket!**",
            color=discord.Color.dark_green()
        )
        embed.timestamp = datetime.utcnow()
        await ctx.send(embed=embed, view=CreateTicket())
        await ctx.respond("The setup was completed successfully", ephemeral=True)

def setup(bot):
    bot.add_cog(Ticket(bot))

class CreateTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, emoji="📨", custom_id="create_ticket")
    async def button_callback1(self, button, interaction):
        server_id = interaction.guild.id

        embed = discord.Embed(
            title="Create Ticket",
            description="Choose your ticket",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, view=CreateTicketSelect(), ephemeral=True)

class CreateTicketSelect(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        custom_id="bro_i_dont_know",
        min_values=1,
        max_values=2,
        placeholder="👆 | CLICK ME!",
        options=options,
    )
    async def ticket_select_callback(self, select, interaction):
        category_id = await db.get_category(interaction.guild.id)
        teamrole_id = await db.get_teamrole(interaction.guild.id)

        selected_options = select.values

        if "Report user" in selected_options:
            await interaction.response.send_modal(user(category_id, teamrole_id, select))
        elif "Ticket" in selected_options:
            await interaction.response.send_modal(Support(category_id, teamrole_id, select))

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
        if self.button_clicked:
            await interaction.response.send_message("You have already clicked the button.", ephemeral=True)
            return

        ticket_owner_name = interaction.channel.topic.split("Ticket for ")[1].split(".")[0]
        ticket_owner = discord.utils.get(interaction.guild.members, name=ticket_owner_name)

        if not ticket_owner:
            await interaction.response.send_message("❌ Ticket owner not found.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"👋 Hi {ticket_owner.display_name}",
            description=f"🎫 Hi {ticket_owner.display_name}, the ticket will be automatically deleted in ⏰ **24 hours**. \n Thank you for trusting the ``ticket team``. If you have any questions, feel free to ask!",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

        self.button_clicked = True


    @discord.ui.button(label="No I have not", style=discord.ButtonStyle.blurple, emoji="<:Loeschen:1231184154427920465>", row=1, custom_id="close_ticket")
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
        await interaction.followup.send(embed=embed, ephemeral=True )

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

        # Deaktivieren des Buttons, nachdem er geklickt wurde
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




class user(discord.ui.Modal):
    def __init__(self, category_id, teamrole_id, select, *args, **kwargs):
        super().__init__(
            discord.ui.InputText(
                label="User name",
                placeholder="e.g nico_kawi",
                style=discord.InputTextStyle.short,
                custom_id="username",
            ),
            discord.ui.InputText(
                label="User ID",
                placeholder="e.g 817435791079768105",
                style=discord.InputTextStyle.long,
                custom_id="user_id",
            ),
            title="Report User"
        )
        self.category_id = category_id
        self.teamrole_id = teamrole_id
        self.select = select

    async def callback(self, interaction: Interaction):

        if self.category_id:
            category = discord.utils.get(interaction.guild.categories, id=self.category_id)

            if category:
                overwrites = {
                    interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    interaction.user: discord.PermissionOverwrite(view_channel=True, read_message_history=True,
                                                                  send_messages=True),
                    interaction.guild.me: discord.PermissionOverwrite(view_channel=True, read_message_history=True,
                                                                      send_messages=True),
                }
                team_role = interaction.guild.get_role(self.teamrole_id)
                if team_role:
                    overwrites[team_role] = discord.PermissionOverwrite(view_channel=True,
                                                                        read_message_history=True,
                                                                        send_messages=True)
                    topic = f"Ticket for {interaction.user.name}. Contact {team_role.mention} for assistance."
                else:
                    topic = f"Ticket for {interaction.user.name}. Contact the team for assistance."

                selected_option = self.select.values[0] if self.select.values else "Unknown"


                channel = await category.create_text_channel(name=f"🎫-{selected_option}",
                                                             overwrites=overwrites, topic=topic)

                msg = await channel.send(
                    f"{interaction.user.mention} - Has created a ticket | {team_role.mention if team_role else '@staff'} ")
                embed = discord.Embed(
                    title="User Report",
                    description=f"Hey, {interaction.user.mention}!\n\nHow can we assist you? A moderator will be with you shortly.\n\n**Which user do you want to report?**\n{self.children[0].value}\n\n**User ID**\n{self.children[1].value}",
                    color=discord.Color.blue()
                )

                await channel.send(embed=embed, view=TicketView())
                await interaction.response.send_message(
                    f"You have successfully created a ticket! › {channel.mention}",ephemeral=True)
                return

        await interaction.response.send_message(
            "The category ID is not set in the database or the specified category doesn't exist.", ephemeral=True)




class Support(discord.ui.Modal):
    def __init__(self, category_id, teamrole_id, select, *args, **kwargs):
        super().__init__(
            discord.ui.InputText(
                label="title Ticket",
                placeholder="Describe your title Ticket ",
                style=discord.InputTextStyle.short,
                custom_id="titleTicket",
            ),
            discord.ui.InputText(
                label="Ticket",
                placeholder="Describe your problem",
                style=discord.InputTextStyle.short,
                custom_id="Ticket",
            ),
            title="Ticket"
        )
        self.category_id = category_id
        self.teamrole_id = teamrole_id
        self.select = select

    async def callback(self, interaction: Interaction):

        if self.category_id:
            category = discord.utils.get(interaction.guild.categories, id=self.category_id)

            if category:
                overwrites = {
                    interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    interaction.user: discord.PermissionOverwrite(view_channel=True, read_message_history=True,
                                                                  send_messages=True),
                    interaction.guild.me: discord.PermissionOverwrite(view_channel=True, read_message_history=True,
                                                                      send_messages=True),
                }
                team_role = interaction.guild.get_role(self.teamrole_id)
                if team_role:
                    overwrites[team_role] = discord.PermissionOverwrite(view_channel=True,
                                                                        read_message_history=True,
                                                                        send_messages=True)
                    topic = f"Ticket for {interaction.user.name}. Contact {team_role.mention} for assistance."
                else:
                    topic = f"Ticket for {interaction.user.name}. Contact the team for assistance."

                selected_option = self.select.values[0] if self.select.values else "Unknown"


                channel = await category.create_text_channel(name=f"🎫-{selected_option}",
                                                             overwrites=overwrites, topic=topic)

                msg = await channel.send(
                    f"{interaction.user.mention} - Has created a ticket | {team_role.mention if team_role else '@staff'} ")
                embed = discord.Embed(
                    title="Ticket Report",
                    description=f"Hey, {interaction.user.mention}!\n\nHow can we assist you? A moderator will be with you shortly.\n\n**Which  do you want to report?**\n{self.children[0].value}\n\n**Ticket **\n{self.children[1].value}",
                    color=discord.Color.blue()
                )

                await channel.send(embed=embed, view=TicketView())
                await interaction.response.send_message(
                    f"You have successfully created a ticket! › {channel.mention}",ephemeral=True)
                return

        await interaction.response.send_message(
            "The category ID is not set in the database or the specified category doesn't exist.", ephemeral=True)