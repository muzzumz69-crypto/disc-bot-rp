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
intents.message_content = True
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

    async def handler(interaction: discord.Interaction, user: discord.User = None):
        # NSFW check → only runs inside servers
        if nsfw_only and interaction.guild is not None:
            if not interaction.channel.is_nsfw():
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

    return app_commands.Command(
        name=tag,
        description=f"Send a random {tag} gif",
        callback=handler
    )

# -------------------
# Help Command
# -------------------
@bot.tree.command(name="help", description="Show all available commands")
async def help_command(interaction: discord.Interaction):
    sfw_cmds = []
    nsfw_cmds = []

    for tag, data in GIFS.items():
        if data.get("nsfw", False):
            nsfw_cmds.append(tag)
        else:
            sfw_cmds.append(tag)

    embed = discord.Embed(
        title="📖 Available Commands",
        description="Here’s a list of my commands:",
        color=discord.Color.blurple()
    )

    if sfw_cmds:
        embed.add_field(
            name="✨ SFW Commands",
            value="\n".join(f"`/{c}`" for c in sorted(sfw_cmds)),
            inline=False
        )
    if nsfw_cmds:
        embed.add_field(
            name="🔞 NSFW Commands",
            value="\n".join(f"`/{c}`" for c in sorted(nsfw_cmds)),
            inline=False
        )

    embed.set_footer(text="Use /commandname to run a command!")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# -------------------
# Bot Events
# -------------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

async def setup_hook():
    # Register commands for dev guild (instant sync)
    for tag, data in GIFS.items():
        bot.tree.add_command(_make_tag_command(tag, data), guild=GUILD_OBJ)

    # Also add help command to dev guild
    bot.tree.add_command(help_command, guild=GUILD_OBJ)

    await bot.tree.sync(guild=GUILD_OBJ)
    print(f"✅ Synced {len(GIFS)+1} commands to dev guild {GUILD_ID}")

    # Register commands globally
    for tag, data in GIFS.items():
        bot.tree.add_command(_make_tag_command(tag, data))

    bot.tree.add_command(help_command)  # add globally too
    await bot.tree.sync()
    print(f"🌍 Synced {len(GIFS)+1} commands globally (may take up to 1h)")

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
