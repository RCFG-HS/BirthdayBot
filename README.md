# 🎂 Birthday Bot

A Discord bot that lets users submit their birthdays (DD-MM format), keeps a monthly-sorted list, assigns a birthday role on their special day, and sends a birthday greeting message in the channel. Includes a `/refresh` command to update the birthday list embed manually.

---

## Features

- Users submit birthdays via `/birthday` slash command (modal input)
- Birthdays stored persistently in a JSON file (`birthdays.json`)
- Birthday list embed sorted by month, updated daily and on demand
- Automatically assigns a "Birthday" role on the user’s birthday
- Sends a public birthday greeting message in the designated channel on the user’s birthday
- Removes birthday role and deletes birthday message the next day
- `/refresh` command to manually refresh the birthday list embed

---

## Setup

1. Clone this repo or copy the script.
2. Create a Discord bot, invite it to your server with members intent enabled.
3. Create a `.env` file with your bot token:
```
DISCORD_BOT_TOKEN=your_bot_token_here
```
4. Update the following in the script:
- `GUILD_ID` — your server’s ID
- `CHANNEL_ID` — the channel ID where the bot posts birthday list and greetings
- `BIRTHDAY_ROLE_NAME` — role to assign on birthdays (default `"Birthday"`)
5. Run `pip install discord.py python-dotenv` if needed.
6. Run the bot with `python your_script.py`.

---

## Commands

| Command    | Description                         |
|------------|-----------------------------------|
| `/birthday` | Submit your birthday (DD-MM format) |
| `/refresh`  | Refresh the birthday list embed manually |

---

## Birthday Format

- Use the format **DD-MM** when submitting your birthday, e.g., `25-12` for 25th December.
- The bot validates the date format and disallows duplicates.

---

## Example

![image](https://github.com/user-attachments/assets/c49d2bee-ea71-4f86-9b13-bc7fcfa770a4)

---

## Support & Contact

If you need help or want to contribute, join the server:

https://discord.gg/au4U6R2GBP

Or contact Created by rtgm_ ([Discord Profile](https://discord.com/users/1123319935360319568))  

---

## License

MIT License
