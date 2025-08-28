import os
import json
import random
import threading
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask, render_template_string

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
        # Always defer response to avoid timeouts
        if not interaction.response.is_done():
            await interaction.response.defer(thinking=False, ephemeral=False)

        # NSFW check
        if nsfw_only and interaction.guild is not None:
            if not interaction.channel.is_nsfw():
                await interaction.followup.send(
                    f"❌ The `{tag}` command can only be used in NSFW channels.",
                    ephemeral=True
                )
                return

        if not links:
            await interaction.followup.send("No media available 😔")
            return

        chosen_file = random.choice(links)

        if user:
            text = f"{user.mention} is getting {tag} from {interaction.user.mention} 😏"
        else:
            text = f"{interaction.user.mention} is enjoying some {tag} action 😉"

        try:
            if chosen_file.endswith((".mp4", ".webm", ".mov")):
                await interaction.followup.send(f"{text}\n{chosen_file}")
            else:
                embed = discord.Embed(
                    description=text,
                    color=discord.Color.pink()
                )
                embed.set_image(url=chosen_file)
                await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"⚠️ Error sending media: {e}")

    return app_commands.Command(
        name=tag,
        description=f"Send a random {tag} media",
        callback=handler,
        allowed_contexts=app_commands.AppCommandContext(
            guild=True, dm_channel=True, private_channel=True
        )
    )

# -------------------
# Help Command
# -------------------
@bot.tree.command(name="help", description="Show all available commands")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
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
        description="Here’s a list of my commands (works in servers, DMs, and group chats!):",
        color=discord.Color.blurple()
    )

    if sfw_cmds:
        embed.add_field(
            name="✨ SFW Commands",
            value="\n".join(f"`/{c}`" for c in sorted(sfw_cmds)),
            inline=False
        )

    # Show NSFW commands only if in NSFW channel
    if interaction.guild and interaction.channel.is_nsfw():
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
    # --- Guild commands (instant sync for dev server) ---
    for tag, data in GIFS.items():
        cmd = _make_tag_command(tag, data)
        bot.tree.add_command(cmd, guild=GUILD_OBJ)

    await bot.tree.sync(guild=GUILD_OBJ)
    print(f"✅ Synced {len(GIFS)+1} commands to dev guild {GUILD_ID}")

    # --- Global commands (enable when bot is ready for production) ---
    # await bot.tree.sync()
    # print(f"🌍 Synced {len(GIFS)+1} commands globally (may take up to 1h)")

bot.setup_hook = setup_hook

# -------------------
# Flask keep-alive server for Render
# -------------------
app = Flask(__name__)

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>GIF Bot Status</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f4f9; text-align: center; padding: 50px; }
        h1 { color: #5865F2; }
        .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); display: inline-block; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🤖 GIF Bot is Running!</h1>
        <p>Status: <b>Online</b></p>
        <p>Commands available in <b>Servers</b>, <b>DMs</b>, and <b>Group Chats</b>.</p>
    </div>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_PAGE)

def run_web():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# -------------------
# Start everything
# -------------------
if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(TOKEN)
