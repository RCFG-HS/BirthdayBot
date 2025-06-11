import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Modal, TextInput
from discord import app_commands
from datetime import datetime, timezone
import json, os, re, calendar
from dotenv import load_dotenv
from collections import defaultdict

# Load token
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Config
GUILD_ID = 895437097794666546
CHANNEL_ID = 1382399105745293483
BIRTHDAY_ROLE_NAME = "Birthday"
BIRTHDAYS_FILE = "birthdays.json"

# Utils
def load_birthdays():
    try:
        with open(BIRTHDAYS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_birthdays(data):
    with open(BIRTHDAYS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Modal for birthday input
class BirthdayModal(Modal, title="Enter Your Birthday"):
    birthday = TextInput(label="Birthday (MM-DD)", placeholder="Example: 06-10")

    async def on_submit(self, interaction: discord.Interaction):
        date_str = self.birthday.value.strip()
        user_id = str(interaction.user.id)

        if not re.fullmatch(r"^(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$", date_str):
            await interaction.response.send_message("Invalid format. Use MM-DD (e.g., 06-10).", ephemeral=True)
            return

        try:
            datetime.strptime(date_str, "%m-%d")
        except ValueError:
            await interaction.response.send_message("Invalid date.", ephemeral=True)
            return

        data = load_birthdays()
        if user_id in data:
            await interaction.response.send_message(f"You've already submitted: {data[user_id]}.", ephemeral=True)
            return

        data[user_id] = date_str
        save_birthdays(data)

        await interaction.response.send_message(f"🎉 Birthday set to {date_str}", ephemeral=True)
        await update_birthday_message(interaction.client)

# View with button
class BirthdayView(View):
    @discord.ui.button(label="Submit Birthday", style=discord.ButtonStyle.primary)
    async def submit_birthday(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BirthdayModal())

# Set up bot
intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
birthday_message = None

# Sync and ready
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"🔄 Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    check_birthdays.start()
    await update_birthday_message(bot)

# Slash command
@tree.command(name="birthday", description="Submit your birthday", guild=discord.Object(id=GUILD_ID))
async def birthday(interaction: discord.Interaction):
    await interaction.response.send_modal(BirthdayModal())

# Birthday checker
@tasks.loop(hours=24)
async def check_birthdays():
    await bot.wait_until_ready()
    today = datetime.now(timezone.utc).strftime("%m-%d")
    data = load_birthdays()
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print("❌ Guild not found.")
        return

    role = discord.utils.get(guild.roles, name=BIRTHDAY_ROLE_NAME)
    if not role:
        print(f"❌ Role '{BIRTHDAY_ROLE_NAME}' not found.")
        return

    for member in guild.members:
        user_id = str(member.id)
        has_birthday = data.get(user_id) == today
        if has_birthday and role not in member.roles:
            try:
                await member.add_roles(role)
                print(f"🎈 Gave {role.name} to {member.display_name}")
            except Exception as e:
                print(f"Error adding role: {e}")
        elif not has_birthday and role in member.roles:
            try:
                await member.remove_roles(role)
                print(f"❌ Removed {role.name} from {member.display_name}")
            except Exception as e:
                print(f"Error removing role: {e}")

# Update birthday embed
async def update_birthday_message(client: discord.Client):
    global birthday_message
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        print("❌ Channel not found.")
        return

    try:
        async for msg in channel.history(limit=10):
            if msg.author == client.user:
                await msg.delete()
    except Exception as e:
        print(f"Error clearing messages: {e}")

    data = load_birthdays()
    sorted_birthdays = sorted(data.items(), key=lambda i: datetime.strptime(i[1], "%m-%d"))

    if not sorted_birthdays:
        description = "No birthdays submitted yet."
    else:
        grouped = defaultdict(list)
        for user_id, date in sorted_birthdays:
            month = int(date.split("-")[0])
            grouped[month].append((user_id, date))

        lines = []
        for month in range(1, 13):
            if month in grouped:
                lines.append(f"__**{calendar.month_name[month]}**__")
                for user_id, date in grouped[month]:
                    try:
                        member = channel.guild.get_member(int(user_id)) or await channel.guild.fetch_member(int(user_id))
                        name = member.display_name if member else f"User {user_id}"
                    except:
                        name = f"User {user_id}"
                    lines.append(f"**{date}** — {name}")
                lines.append("")

        description = "\n".join(lines).strip()

    embed = discord.Embed(
        title="🎂 Birthday List",
        description=description,
        color=discord.Color.purple(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text="Created by rtgm_")

    birthday_message = await channel.send(embed=embed, view=BirthdayView())

# Run the bot
if not TOKEN:
    print("❌ DISCORD_BOT_TOKEN not set. Check .env file.")
else:
    bot.run(TOKEN)
