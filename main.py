import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
intents.members = True  # Ensure the bot can fetch member information
intents.message_content = True  # Ensure the bot can read message content

# Create an instance of the bot
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")


@bot.command()
@commands.has_role("Mod")  # Ensure only Moderators can run this command
async def check_staff_activity(ctx):
    # Get the channel where we will check for messages
    hunting_runs_channel = discord.utils.get(ctx.guild.text_channels, name="hunting-runs")
    if not hunting_runs_channel:
        await ctx.send("The 'hunting-runs' channel was not found.")
        return

    # Get the channel where we will post the results
    staff_activity_channel = discord.utils.get(ctx.guild.text_channels, name="staff-activity-check")
    if not staff_activity_channel:
        await ctx.send("The 'staff-activity-check' channel was not found.")
        return

    # Get the ticket-transcripts channel
    ticket_transcripts_channel = discord.utils.get(ctx.guild.text_channels, name="staff-logs")
    if not ticket_transcripts_channel:
        await ctx.send("The 'ticket-transcripts' channel was not found.")
        return

    # Get the Staff and Security roles
    organiser_role = discord.utils.get(ctx.guild.roles, name="Org")
    security_role = discord.utils.get(ctx.guild.roles, name="Security")
    if not organiser_role:
        await ctx.send("The 'Org' role was not found.")
        return
    if not security_role:
        await ctx.send("The 'Security' role was not found.")
        return

    # Get the Tickets bot
    tickets_bot = discord.utils.get(ctx.guild.members, name="Tickets", discriminator="6981")
    if not tickets_bot:
        await ctx.send("The 'Tickets#6981' bot was not found.")
        return

    # List to store activity results
    activity_results = []
    inactive_organisers = []
    inactive_security = []

    # Calculate the date threshold (2 months ago)
    two_months_ago = datetime.now(timezone.utc) - timedelta(days=60)

    activity_results.append("**ORGANISER ACTIVITY**\n")
    # 1. Iterate through all members with the Org role
    for member in ctx.guild.members:
        if organiser_role in member.roles:
            # Get the most recent message from the user that includes @here
            async for message in hunting_runs_channel.history(limit=10000):
                if message.author == member and "@here" in message.content and "key" not in message.content:
                    # Check if the organiser was active
                    message_date = message.created_at
                    if message_date < two_months_ago:
                        inactive_organisers.append(member)
                        active = False
                    else:
                        active = True

                    # Add the result to the list
                    if active:
                        activity_results.append(f"<@{member.id}> / `{member.display_name}`\nLast run: {message.created_at.strftime('%Y-%m-%d')} - {message.jump_url}\nActive: ✅\n")
                    else:
                        activity_results.append(f"<@{member.id}> / `{member.display_name}`\nLast run: {message.created_at.strftime('%Y-%m-%d')} - {message.jump_url}\nActive: ❌\n")
                    break

    activity_results.append("\n**SECURITY ACTIVITY**\n")
    # 2. Iterate through all members with the Security role
    for member in ctx.guild.members:
        if security_role in member.roles:
            # Search for the most recent embedded message from the Tickets bot in the ticket-transcripts channel that contains the security member's ID
            async for message in ticket_transcripts_channel.history(limit=10000):  # Adjust limit as necessary
                if message.author == tickets_bot and message.embeds:  # Check if the message is from Tickets bot and contains embeds
                    for embed in message.embeds:
                        for field in embed.fields:
                            if str(member.id) in field.value:
                                message_date = message.created_at
                                if message_date < two_months_ago:
                                    inactive_security.append(member)
                                    active = False
                                else:
                                    active = True

                                # Add the result to the list
                                if active:
                                    activity_results.append(f"<@{member.id}> `{member.display_name}`\nLast ticket: {message.created_at.strftime('%Y-%m-%d')} - {message.jump_url}\nActive: ✅\n")
                                if not active:
                                    activity_results.append(f"<@{member.id}> `{member.display_name}`\nLast ticket: {message.created_at.strftime('%Y-%m-%d')} - {message.jump_url}\nActive: ❌\n")
                                break
                        break
                    break
                break

    # Send the results to the staff-activity-check channel
    if activity_results:
        await staff_activity_channel.send("\n".join(activity_results))
        await staff_activity_channel.send("---------------------------------------------------------\n")
    else:
        await staff_activity_channel.send("No recent activity found for any Staff or Security members.")

    # Send the inactive staff members to a separate channel or log them
    if inactive_organisers:
        inactive_staff_message = "\n**INACTIVE ORGS** (activity within the last 2 months):\n\n" + "\n".join([f"<@{member.id}> - `{member.display_name}`" for member in inactive_organisers])
        await staff_activity_channel.send(inactive_staff_message)
    else:
        await staff_activity_channel.send("\n**INACTIVE ORGS** (activity within the last 2 months):\n\nNo inactive organisers found.")

    if inactive_security:
        inactive_staff_message = "\n**INACTIVE SECURITY** (activity within the last 2 months):\n\n" + "\n".join([f"<@{member.id}> - `{member.display_name}`" for member in inactive_security])
        await staff_activity_channel.send(inactive_staff_message)
    else:
        await staff_activity_channel.send("\n**INACTIVE SECURITY** (activity within the last 2 months):\n\nNo inactive security found.")

# Run the bot with your token
bot.run(TOKEN)
