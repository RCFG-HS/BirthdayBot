
🎂 Discord Birthday Bot
=======================

A simple yet powerful Discord bot that allows users to submit their birthdays, view an organized birthday list, and receive a special role on their special day.

---

✨ Features
-----------

- 📝 Submit your birthday via a button or `/birthday` command  
- 📅 Birthdays grouped and sorted by month  
- 🧑‍🤝‍🧑 Automatically assigns and removes a birthday role on the correct day  
- 🔄 Daily checks using background tasks  
- 📦 Persistent storage using JSON  
- 💬 Slash command and button interface using Discord UI components  

---

🚀 Getting Started
------------------

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/discord-birthday-bot.git
cd discord-birthday-bot
```

### 2. Install Dependencies

Requires **Python 3.9+**

```bash
pip install -r requirements.txt
```

Or manually:

```bash
pip install discord.py python-dotenv
```

### 3. Set Up Environment Variables

Create a `.env` file in the root directory:

```
DISCORD_BOT_TOKEN=your_discord_bot_token_here
```

### 4. Configure Bot Settings

In the main Python file (e.g., `bot.py`), update these constants:

```
GUILD_ID = YOUR_GUILD_ID
CHANNEL_ID = CHANNEL_ID_FOR_BIRTHDAY_LIST
BIRTHDAY_ROLE_NAME = "Birthday"
```

You can get these values by enabling **Developer Mode** in Discord and right-clicking the server, channel, or role.

---

✅ How It Works
----------------

- Users click **Submit Birthday** or use the `/birthday` command.
- Birthdays are stored in `birthdays.json`.
- The bot posts a live-updating birthday list.
- Every 24 hours, it checks for birthdays and assigns/removes the special role accordingly.

---

📂 File Structure
------------------

```
.
├── birthdays.json        # Saved user birthday data
├── bot.py                # Main bot script
├── .env                  # Contains your bot token (not committed)
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

---

🔒 Permissions Needed
---------------------

To function correctly, the bot requires:

- Read and Send Messages
- Manage Roles
- Use Slash Commands and Buttons

OAuth2 scopes required:

```
bot applications.commands
```

Recommended permissions integer: `268435456`

---

🛠 To-Do / Improvements
-----------------------

- ✅ Sort birthdays by month  
- ⌛ Let users update or remove their birthday  
- 🔔 Optional announcements or reminders  
- 🌐 Add a web dashboard  
- 🛡️ Improve role error handling  

---

🙌 Credits
----------

Created by rtgm_ ([@1123319935360319568](https://discord.com/users/1123319935360319568))  
Join the support server: https://discord.gg/au4U6R2GBP  
Built with discord.py

---

📄 License
----------

MIT License – feel free to use, modify, and share!
