
# NemoBot - Multipurpose Discord Bot

NemoBot is a Discord bot built with py-cord and aiosqlite.
It includes leveling, giveaways, moderation commands, fishing, welcome messages, and a small debug toolkit.

## Core Features

- Level and XP system from text chat, voice activity, and reactions
- Interactive leaderboard view (Level, Messages, Voice, with Level/XP toggle)
- Giveaway system with join button, reroll, persistence, and booster weighting
- Fishing mini-game with rarity system, inventory, stats, leaderboard, and selling
- Moderation commands (ban, unban, kick, mute, unmute, warn, unwarn, history)
- Welcome message with quick buttons for rules and role channels
- Debug mode for authorized users

## Requirements

- Python 3.10+ recommended
- A Discord bot application with a valid bot token
- Intents enabled in the Discord Developer Portal:
  - Message Content Intent
  - Server Members Intent

## Installation

1. Clone the repository and open it:

```bash
git clone <your-repo-url>
cd Multipurpose-Discord-Bot-NemoBot
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a .env file in the project root:

```env
Token=YOUR_DISCORD_BOT_TOKEN
```

4. Start the bot:

```bash
python bot.py
```

## Project Structure

```text
bot.py
requirements.txt
cogs/
  debug.py
  fishing.py
  giveaway.py
  level.py
  punishment.py
  welcome.py
```

## Slash Commands

### Leveling

- /level
- /leaderboard

### Giveaways

- /giveaway_start
- /giveaway_end
- /giveaway_reroll

### Fishing

- /fish
- /meine_fische
- /fishing_leaderboard
- /fische_verkaufen

### Moderation

- /ban
- /unban
- /kick
- /mute
- /unmute
- /warn
- /unwarn
- /warns
- /punishments

### Utility

- /help
- /debug

## Configuration Points

Update these IDs to match your server setup.

- cogs/level.py
  - XP_BOOST_ROLES
  - level_roles
  - level_channel
- cogs/giveaway.py
  - bonus_role
  - mod_roles
- cogs/punishment.py
  - mute_role_id
  - mod_roles
- cogs/welcome.py
  - welcome channel ID in on_member_join
  - rules channel mention
  - roles channel mention
- cogs/debug.py
  - DEBUG_USERS

## Data Files

SQLite database files are created automatically at runtime:

- level.db
- giveaway_data.db
- fishing_data.db
- punishment_data.db

## Notes

- The bot auto-loads all .py files from the cogs folder.
- Current status/activity is set in bot.py.
- Keep your .env private and never commit your bot token.
