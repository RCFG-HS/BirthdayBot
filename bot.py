import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Modal, TextInput
from discord import app_commands
from datetime import datetime, timezone
import json, os, re, calendar
from dotenv import load_dotenv
from collections import defaultdict
from zoneinfo import ZoneInfo, available_timezones

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

GUILD_ID = 895437097794666546
CHANNEL_ID = 1382399105745293483
BIRTHDAY_ROLE_NAME = "Birthday"
BIRTHDAYS_FILE = "birthdays.json"

CREATOR_ICON_URL = "https://avatars.githubusercontent.com/u/66518248?v=4"

def load_birthdays():
    try:
        with open(BIRTHDAYS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_birthdays(data):
    with open(BIRTHDAYS_FILE, "w") as f:
        json.dump(data, f, indent=4)

class BirthdayModal(Modal, title="Enter Your Birthday"):
    birthday = TextInput(label="Birthday (DD-MM)", placeholder="Example: 12-06")
    timezone = TextInput(
        label="Timezone (optional, IANA format)",
        placeholder="Example: Europe/London or leave blank",
        required=False,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        date_str = self.birthday.value.strip()
        tz_str = self.timezone.value.strip()
        user_id = str(interaction.user.id)

        # Validate birthday format
        if not re.fullmatch(r"^(0[1-9]|[12][0-9]|3[01])-(0[1-9]|1[0-2])$", date_str):
            await interaction.response.send_message("❌ Invalid birthday format. Use DD-MM (e.g., 12-06).", ephemeral=True)
            return
        try:
            datetime.strptime(date_str, "%d-%m")
        except ValueError:
            await interaction.response.send_message("❌ That date doesn't exist.", ephemeral=True)
            return

        # Validate timezone if provided
        if tz_str:
            if tz_str not in available_timezones():
                await interaction.response.send_message("❌ Invalid timezone. Use a valid IANA timezone name (e.g., Europe/London).", ephemeral=True)
                return

        data = load_birthdays()
        if user_id in data:
            await interaction.response.send_message(
                f"🎂 You already submitted: {data[user_id]['birthday']} with timezone: {data[user_id].get('timezone','UTC')}", ephemeral=True)
            return

        # Save birthday and timezone (default UTC)
        data[user_id] = {
            "birthday": date_str,
            "timezone": tz_str if tz_str else "UTC"
        }
        save_birthdays(data)
        await interaction.response.send_message(f"✅ Birthday set to **{date_str}** with timezone **{data[user_id]['timezone']}**!", ephemeral=True)
        await update_birthday_message(interaction.client)

class BirthdayView(View):
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view

    @discord.ui.button(
        label="🎉 Submit Birthday",
        style=discord.ButtonStyle.primary,
        custom_id="birthday_submit_button"
    )
    async def submit_birthday(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BirthdayModal())

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.AutoShardedBot(command_prefix="!", intents=intents)
tree = bot.tree
birthday_message = None

@bot.event
async def on_ready():
    try:
        await tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"✅ Logged in as {bot.user} | Commands synced.")
        bot.add_view(BirthdayView())
        check_birthdays.start()
        await update_birthday_message(bot)
        await bot.change_presence(activity=discord.Game("🎂 with birthdays!"), status=discord.Status.online)
    except Exception as e:
        print(f"❌ Error during on_ready: {e}\nPlease contact <@1123319935360319568>")

@tree.command(name="birthday", description="Submit your birthday", guild=discord.Object(id=GUILD_ID))
async def birthday(interaction: discord.Interaction):
    await interaction.response.send_modal(BirthdayModal())

@tree.command(name="refresh", description="🔄 Force refresh the birthday list", guild=discord.Object(id=GUILD_ID))
async def refresh(interaction: discord.Interaction):
    await update_birthday_message(interaction.client)
    await interaction.response.send_message("✅ Refreshed the birthday list.", ephemeral=True)

@tasks.loop(hours=24)
async def check_birthdays():
    await bot.wait_until_ready()
    data = load_birthdays()
    guild = bot.get_guild(GUILD_ID)
    channel = bot.get_channel(CHANNEL_ID)
    if not guild or not channel:
        print("❌ Guild or channel not found.")
        return

    role = discord.utils.get(guild.roles, name=BIRTHDAY_ROLE_NAME)
    if not role:
        print(f"❌ Role '{BIRTHDAY_ROLE_NAME}' not found.")
        return

    now_utc = datetime.now(timezone.utc)

    to_remove = []

    for user_id, user_data in data.items():
        member = guild.get_member(int(user_id))
        # If member not found, they left or were banned
        if not member:
            to_remove.append(user_id)
            continue

        user_tz_str = user_data.get("timezone", "UTC")
        try:
            user_tz = ZoneInfo(user_tz_str)
        except Exception:
            user_tz = ZoneInfo("UTC")

        user_now = now_utc.astimezone(user_tz)
        user_bday = user_data["birthday"]
        user_bday_day, user_bday_month = user_bday.split("-")

        is_birthday = (user_now.day == int(user_bday_day) and user_now.month == int(user_bday_month))

        try:
            if is_birthday and role not in member.roles:
                await member.add_roles(role)
                await channel.send(f"🎉 Happy Birthday, {member.mention}! Enjoy your special day. Best of wishes! 🥳")
                print(f"🎈 Added role to {member.display_name}")
            elif not is_birthday and role in member.roles:
                await member.remove_roles(role)
                print(f"🎂 Removed birthday role from {member.display_name}")
        except Exception as e:
            print(f"⚠️ Role error for {member.display_name}: {e}")

    # Remove birthdays of users no longer in guild
    if to_remove:
        for user_id in to_remove:
            data.pop(user_id, None)
        save_birthdays(data)
        print(f"🗑️ Removed birthdays for users no longer in guild: {to_remove}")

async def update_birthday_message(client: discord.Client):
    global birthday_message
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        print("❌ Channel not found.")
        return

    try:
        async for msg in channel.history(limit=20):
            if msg.author == client.user:
                await msg.delete()
    except Exception as e:
        print(f"⚠️ Error clearing messages: {e}")

    data = load_birthdays()
    sorted_birthdays = sorted(data.items(), key=lambda i: datetime.strptime(i[1]['birthday'], "%d-%m"))

    if not sorted_birthdays:
        embed = discord.Embed(
            title="🎂 Birthday List",
            description="No birthdays submitted yet.",
            color=discord.Color.purple(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="Created by rtgm_", icon_url=CREATOR_ICON_URL)
        birthday_message = await channel.send(embed=embed, view=BirthdayView())
        return

    grouped = defaultdict(list)
    for user_id, user_info in sorted_birthdays:
        day, month = user_info["birthday"].split("-")
        grouped[int(month)].append((user_id, user_info["birthday"], user_info.get("timezone", "UTC")))

    for month in range(1, 13):
        if month not in grouped:
            continue

        lines = []
        for user_id, birthday, tz in grouped[month]:
            try:
                member = channel.guild.get_member(int(user_id)) or await channel.guild.fetch_member(int(user_id))
                name = member.display_name if member else f"User {user_id}"
            except:
                name = f"User {user_id}"
            lines.append(f"**{birthday}** ({tz}) — {name}")

        description = "\n".join(lines)

        embed = discord.Embed(
            title=f"🎂 Birthdays in {calendar.month_name[month]}",
            description=description,
            color=discord.Color.purple(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="Created by rtgm_", icon_url=CREATOR_ICON_URL)

        await channel.send(embed=embed, view=BirthdayView())

if not TOKEN:
    print("❌ DISCORD_BOT_TOKEN not set. Check your .env file.")
else:
    bot.run(TOKEN)
