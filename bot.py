import os
import json
import re
import calendar
import datetime
import asyncio
import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Modal, TextInput
from discord import app_commands
from dotenv import load_dotenv
from collections import defaultdict
from zoneinfo import ZoneInfo, available_timezones

# -------- CONFIG ---------
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = 895437097794666546        # Your server ID
CHANNEL_ID = 1382399105745293483     # Your birthdays channel
LOG_CHANNEL_ID = 123456789012345678  # Your log channel
BIRTHDAY_ROLE_NAME = "Birthday"
CHANGE_COOLDOWN_HOURS = 12
CREATOR_ICON_URL = "https://avatars.githubusercontent.com/u/66518248?v=4"

# -------- LOGGING ---------
def get_logfile():
    now = datetime.datetime.now()
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, f"bot-{now.year}-{now.month:02d}.log")

def log_event(msg: str, client=None):
    timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    fullmsg = f"{timestamp} {msg}"
    print(fullmsg)
    logfile = get_logfile()
    with open(logfile, "a", encoding="utf-8") as f:
        f.write(fullmsg + "\n")
    # Send to Discord log channel (async) if available
    if client:
        async def send():
            channel = client.get_channel(LOG_CHANNEL_ID)
            if channel:
                await channel.send(msg)
        try:
            if hasattr(client, "loop"):
                client.loop.create_task(send())
        except Exception:
            pass

# -------- UTILITIES ---------
def load_json(fp):
    try:
        with open(fp, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_json(fp, data):
    with open(fp, "w") as f:
        json.dump(data, f, indent=4)

def load_birthdays():
    return load_json("birthdays.json")
def save_birthdays(data):
    save_json("birthdays.json", data)
def load_embeds():
    return load_json("embeds.json")
def save_embeds(data):
    save_json("embeds.json", data)
def load_greetings():
    return load_json("greetings.json")
def save_greetings(data):
    save_json("greetings.json", data)
def load_cooldowns():
    return load_json("cooldowns.json")
def save_cooldowns(data):
    save_json("cooldowns.json", data)

def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)

def get_month_from_birthday(bday):
    return int(bday.split("-")[1])

# -------- MODALS ---------
class BirthdayModal(Modal, title="Enter or Change Your Birthday"):
    def __init__(self, prefill_bday=None, prefill_tz=None):
        super().__init__()
        self.birthday = TextInput(
            label="Birthday (DD-MM)",
            placeholder="Example: 12-06",
            default=prefill_bday or ""
        )
        self.timezone = TextInput(
            label="Timezone (optional, IANA format)",
            placeholder="Example: Europe/London or leave blank",
            required=False,
            max_length=50,
            default=prefill_tz or ""
        )

    async def on_submit(self, interaction: discord.Interaction):
        date_str = self.birthday.value.strip()
        tz_str = self.timezone.value.strip()
        user_id = str(interaction.user.id)

        # Validate birthday
        if not re.fullmatch(r"^(0[1-9]|[12][0-9]|3[01])-(0[1-9]|1[0-2])$", date_str):
            await interaction.response.send_message("❌ Invalid birthday format. Use DD-MM (e.g., 12-06).", ephemeral=True)
            return
        try:
            datetime.datetime.strptime(date_str, "%d-%m")
        except ValueError:
            await interaction.response.send_message("❌ That date doesn't exist.", ephemeral=True)
            return

        # Validate timezone if provided
        if tz_str:
            if tz_str not in available_timezones():
                await interaction.response.send_message("❌ Invalid timezone. Use a valid IANA timezone name (e.g., Europe/London).", ephemeral=True)
                return

        data = load_birthdays()
        already = user_id in data
        old_bday = data[user_id]["birthday"] if already else None
        old_tz = data[user_id]["timezone"] if already else None
        data[user_id] = {
            "birthday": date_str,
            "timezone": tz_str if tz_str else "UTC"
        }
        save_birthdays(data)

        cooldowns = load_cooldowns()
        cooldowns[user_id] = (now_utc() + datetime.timedelta(hours=CHANGE_COOLDOWN_HOURS)).isoformat()
        save_cooldowns(cooldowns)

        # Log add/change
        action = "Changed" if already else "Added"
        logmsg = (
            f"🎂 {action} birthday for <@{user_id}> (`{user_id}`):\n"
            f"**Birthday:** {date_str} | **Timezone:** {data[user_id]['timezone']}"
        )
        if already:
            logmsg += f"\nPrevious: {old_bday} ({old_tz})"
        log_event(logmsg, interaction.client)

        msg = f"✅ {'Changed' if already else 'Set'} birthday to **{date_str}** with timezone **{data[user_id]['timezone']}**!"
        await interaction.response.send_message(msg, ephemeral=True)
        await update_birthday_embeds(interaction.client)

def is_on_cooldown(user_id):
    cooldowns = load_cooldowns()
    if user_id not in cooldowns:
        return False
    until = datetime.datetime.fromisoformat(cooldowns[user_id])
    return now_utc() < until

def cooldown_time_left(user_id):
    cooldowns = load_cooldowns()
    until = datetime.datetime.fromisoformat(cooldowns[user_id])
    return until - now_utc()

class BirthdayView(View):
    def __init__(self, show_submit=False, show_change=False):
        super().__init__(timeout=None)
        if show_submit:
            self.add_item(SubmitBirthdayButton())
        if show_change:
            self.add_item(ChangeBirthdayButton())

class SubmitBirthdayButton(Button):
    def __init__(self):
        super().__init__(
            label="🎉 Submit Birthday",
            style=discord.ButtonStyle.primary,
            custom_id="birthday_submit_button"
        )
    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id in load_birthdays():
            await interaction.response.send_message(
                "❌ You've already submitted a birthday. Use 'Change Birthday' to update it.",
                ephemeral=True
            )
            return
        await interaction.response.send_modal(BirthdayModal())

class ChangeBirthdayButton(Button):
    def __init__(self):
        super().__init__(
            label="🛠️ Change Birthday",
            style=discord.ButtonStyle.secondary,
            custom_id="birthday_change_button"
        )
    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        data = load_birthdays()
        if user_id not in data:
            await interaction.response.send_message("❌ No birthday to change. Please submit first.", ephemeral=True)
            return
        if is_on_cooldown(user_id):
            delta = cooldown_time_left(user_id)
            h, m = divmod(int(delta.total_seconds())//60, 60)
            await interaction.response.send_message(
                f"⏳ You can change your birthday in {h}h {m}m.",
                ephemeral=True
            )
            return
        userinfo = data[user_id]
        await interaction.response.send_modal(
            BirthdayModal(prefill_bday=userinfo["birthday"], prefill_tz=userinfo.get("timezone", ""))
        )

# -------- DISCORD BOT ---------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.AutoShardedBot(command_prefix="!", intents=intents)
tree = bot.tree

@bot.event
async def on_ready():
    try:
        await tree.sync(guild=discord.Object(id=GUILD_ID))
        log_event(f"✅ Logged in as {bot.user} | Commands synced.", bot)
        check_birthdays.start()
        cleanup_greetings.start()
        await update_birthday_embeds(bot)
        await bot.change_presence(activity=discord.Game("🎂 with birthdays!"), status=discord.Status.online)
        print ("READY")
    except Exception as e:
        log_event(f"❌ Error during on_ready: {e}", bot)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.application_command:
        user = interaction.user
        cmd = interaction.data.get("name", "?")
        options = interaction.data.get("options", [])
        args_str = ", ".join(f"{opt['name']}={opt.get('value','')}" for opt in options)
        log_event(
            f"⏩ Slash command: /{cmd} by {user} ({user.id}) [{args_str}]",
            bot
        )
    await bot.process_app_commands(interaction)


@bot.event
async def on_member_remove(member):
    msg = f"❗ Member left: **{member}** (`{member.id}`)"
    log_event(msg, bot)

@bot.event
async def on_member_update(before, after):
    if before.display_name != after.display_name:
        msg = (
            f"✏️ Nickname changed: <@{before.id}> (`{before.id}`)\n"
            f"Old: `{before.display_name}`\nNew: `{after.display_name}`"
        )
        log_event(msg, bot)

@tree.command(name="birthday", description="Submit your birthday", guild=discord.Object(id=GUILD_ID))
async def birthday(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id in load_birthdays():
        await interaction.response.send_message(
            "❌ You've already submitted a birthday. Use 'Change Birthday' on the last month embed to update.",
            ephemeral=True
        )
        return
    await interaction.response.send_modal(BirthdayModal())

@tree.command(name="refresh", description="🔄 Force refresh the birthday list", guild=discord.Object(id=GUILD_ID))
async def refresh(interaction: discord.Interaction):
    user = interaction.user
    try:
        await update_birthday_embeds(interaction.client)
        await interaction.response.send_message("✅ Refreshed the birthday list.", ephemeral=True)
        log_event(
            f"✅ /refresh used by {user} ({user.id}) - success",
            interaction.client
        )
    except Exception as e:
        await interaction.response.send_message("❌ Failed to refresh.", ephemeral=True)
        log_event(
            f"❌ /refresh used by {user} ({user.id}) - error: {e}",
            interaction.client
        )

@tree.command(
    name="purge_greetings",
    description="(Admin) Purge all birthday greetings from the channel.",
    guild=discord.Object(id=GUILD_ID)
)
async def purge_greetings(interaction: discord.Interaction):
    if not (
        interaction.user.guild_permissions.administrator or
        interaction.user.guild_permissions.manage_guild
    ):
        await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
        return
    channel = interaction.client.get_channel(CHANNEL_ID)
    greetings = load_greetings()
    deleted = 0
    for user_id, entry in greetings.items():
        try:
            msg = await channel.fetch_message(entry["msg_id"])
            await msg.delete()
            deleted += 1
        except Exception:
            continue
    save_greetings({})
    await interaction.response.send_message(f"✅ Purged {deleted} greeting message(s).", ephemeral=True)
    log_event(f"🧹 Purged {deleted} greeting message(s) by admin <@{interaction.user.id}>", interaction.client)

# -------- EMBED/VIEW/ROLE LOGIC ---------
async def update_birthday_embeds(client: discord.Client):
    embeds_state = load_embeds()
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        log_event("❌ Channel not found.", client)
        return
    data = load_birthdays()
    grouped = defaultdict(list)
    for user_id, user_info in data.items():
        day, month = user_info["birthday"].split("-")
        grouped[int(month)].append((user_id, user_info["birthday"], user_info.get("timezone", "UTC")))
    message_ids = embeds_state.get("message_ids", [None]*12)
    for month in range(1, 13):
        lines = []
        for user_id, birthday, tz in sorted(grouped.get(month, []), key=lambda x: int(x[1].split("-")[0])):
            try:
                member = channel.guild.get_member(int(user_id)) or await channel.guild.fetch_member(int(user_id))
                name = member.display_name if member else f"User {user_id}"
            except:
                name = f"User {user_id}"
            lines.append(f"**{birthday}** ({tz}) — {name}")
        description = "\n".join(lines) if lines else "No birthdays this month."
        embed = discord.Embed(
            title=f"🎂 Birthdays in {calendar.month_name[month]}",
            description=description,
            color=discord.Color.purple(),
            timestamp=now_utc()
        )
        embed.set_footer(text="Created by rtgm_", icon_url=CREATOR_ICON_URL)
        show_view = (month == 12)
        view = BirthdayView(show_submit=True, show_change=True) if show_view else None
        msg_id = message_ids[month-1]
        msg = None
        if msg_id:
            try:
                msg = await channel.fetch_message(msg_id)
            except discord.NotFound:
                msg = None
        if msg:
            await msg.edit(embed=embed, view=view)
        else:
            msg = await channel.send(embed=embed, view=view)
            message_ids[month-1] = msg.id
    embeds_state["message_ids"] = message_ids[:12]
    save_embeds(embeds_state)

async def send_greeting(channel, member):
    msg = await channel.send(
        f"🎉 Happy Birthday, {member.mention}! Enjoy your special day. Best of wishes! 🥳"
    )
    greetings = load_greetings()
    greetings[str(member.id)] = {
        "msg_id": msg.id,
        "date": now_utc().isoformat()
    }
    save_greetings(greetings)
    return msg

async def delete_greeting(channel, member_id):
    greetings = load_greetings()
    entry = greetings.get(str(member_id))
    if not entry:
        return
    try:
        msg = await channel.fetch_message(entry["msg_id"])
        await msg.delete()
    except:
        pass
    greetings.pop(str(member_id), None)
    save_greetings(greetings)

@tasks.loop(hours=24)
async def check_birthdays():
    await bot.wait_until_ready()
    data = load_birthdays()
    guild = bot.get_guild(GUILD_ID)
    channel = bot.get_channel(CHANNEL_ID)
    if not guild or not channel:
        log_event("❌ Guild or channel not found.", bot)
        return
    role = discord.utils.get(guild.roles, name=BIRTHDAY_ROLE_NAME)
    if not role:
        log_event(f"❌ Role '{BIRTHDAY_ROLE_NAME}' not found.", bot)
        return
    now = now_utc()
    for member in guild.members:
        user_id = str(member.id)
        user_data = data.get(user_id)
        if not user_data:
            continue
        user_tz_str = user_data.get("timezone", "UTC")
        try:
            user_tz = ZoneInfo(user_tz_str)
        except Exception:
            user_tz = ZoneInfo("UTC")
        user_now = now.astimezone(user_tz)
        bday_day, bday_month = user_data["birthday"].split("-")
        is_birthday = (user_now.day == int(bday_day) and user_now.month == int(bday_month))
        try:
            if is_birthday and role not in member.roles:
                await member.add_roles(role)
                await send_greeting(channel, member)
            elif not is_birthday and role in member.roles:
                await member.remove_roles(role)
                await delete_greeting(channel, user_id)
        except Exception as e:
            log_event(f"⚠️ Role error for {member.display_name}: {e}", bot)

@tasks.loop(minutes=10)
async def cleanup_greetings():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return
    greetings = load_greetings()
    to_delete = []
    for user_id, entry in greetings.items():
        sent_time = datetime.datetime.fromisoformat(entry["date"])
        if now_utc() - sent_time > datetime.timedelta(hours=24):
            try:
                msg = await channel.fetch_message(entry["msg_id"])
                await msg.delete()
            except Exception as e:
                pass
            to_delete.append(user_id)
    for user_id in to_delete:
        greetings.pop(user_id, None)
    if to_delete:
        save_greetings(greetings)

if not TOKEN:
    log_event("❌ DISCORD_BOT_TOKEN not set. Check your .env file.")
else:
    bot.run(TOKEN)
