import os
import json
import random
import threading
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask

# -------------------
# Load environment
# -------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

if not TOKEN:
    raise RuntimeError("❌ DISCORD_TOKEN missing in .env file!")
if not GUILD_ID:
    raise RuntimeError("❌ GUILD_ID missing in .env file!")

# -------------------
# Bot setup
# -------------------
intents = discord.Intents.default()
intents.message_content = True   # <- enable this so slash cmds + msg-based work
bot = commands.Bot(command_prefix="!", intents=intents)
GUILD_OBJ = discord.Object(id=GUILD_ID)

# -------------------
# Load GIFs JSON
# -------------------
with open("gifs.json", "r", encoding="utf-8") as f:
    GIFS = json.load(f)

# -------------------
# Command factory
# -------------------
def _make_tag_command(tag: str, data: dict):
    nsfw_only = data.get("nsfw", False)
    links = data.get("links", [])

    @app_commands.command(name=tag, description=f"Send a random {tag} gif")
    @app_commands.describe(user="Optional user to tag")
    async def handler(interaction: discord.Interaction, user: discord.Member = None):
        # NSFW check
        if nsfw_only and not interaction.channel.is_nsfw():
            await interaction.response.send_message(
                f"❌ The `{tag}` command can only be used in NSFW channels.",
                ephemeral=True
            )
            return

        if not links:
            await interaction.response.send_message("No gifs available 😔")
            return

        chosen_gif = random.choice(links)

        if user:
            text = f"{user.mention} is getting {tag} from {interaction.user.mention} 😏"
        else:
            text = f"{interaction.user.mention} is enjoying some {tag} action 😉"

        embed = discord.Embed(
            description=text,
            color=discord.Color.pink()
        )
        embed.set_image(url=chosen_gif)

        await interaction.response.send_message(embed=embed)

    return handler

# -------------------
# Bot Events
# -------------------
# -------------------
# Bot Events
# -------------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

async def setup_hook():
    # Register commands for dev guild (fast sync)
    for tag, data in GIFS.items():
        bot.tree.add_command(_make_tag_command(tag, data), guild=GUILD_OBJ)

    # Sync dev guild (instant)
    await bot.tree.sync(guild=GUILD_OBJ)
    print(f"✅ Synced {len(GIFS)} commands to dev guild {GUILD_ID}")

    # Also register commands globally (takes ~1 hour to appear everywhere else)
    for tag, data in GIFS.items():
        bot.tree.add_command(_make_tag_command(tag, data))

    await bot.tree.sync()
    print(f"🌍 Synced {len(GIFS)} commands globally (may take up to 1h)")

bot.setup_hook = setup_hook


# -------------------
# Flask keep-alive server for Render
# -------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running on Render!"

def run_web():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# -------------------
# Start everything
# -------------------
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    bot.run(TOKEN)

