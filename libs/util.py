import os
from dotenv import load_dotenv
import discord
import math

# Get bot token from environment variable
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
ADMINID = os.getenv('ADMINUSERID')
SHOPOWNER = os.getenv('SHOP_OWNER')
TOWN= os.getenv('TOWN')
CHEST_X= os.getenv('CHEST_X')
CHEST_Z= os.getenv('CHEST_Z')
LOG_CHANNEL_ID= os.getenv('LOG_CHANNEL_ID')


if not TOKEN:
    print("Error: DISCORD_BOT_TOKEN environment variable not set")
    exit(1)
if not ADMINID:
    print("Warning: ADMINUSERID environment variable not set")
if not SHOPOWNER:
    print("Warning: ShopOwner environment variable not set (Breaks auto-deposit)")

def token():
    return TOKEN

def logchannel():
    return LOG_CHANNEL_ID

def chestcords():
    return [CHEST_X, CHEST_Z]

def town():
    return TOWN 

def is_admin(user_id):
    return str(user_id) == ADMINID  # Ensure user_id is compared as a string

def shop_owner():
    o = str(SHOPOWNER)
    return o

def create_embed(title, description, color=discord.Color.blue()):
    return discord.Embed(title=title, description=description, color=color)

def coordDistance(pos1, pos2):
    x1, z1 = pos1
    x2, z2 = pos2
    return math.sqrt((x2 - x1) ** 2 + (z2 - z1) ** 2)

def isInChunk(chunk_coords, player_pos):
    chunk_x, chunk_z = chunk_coords
    player_x, player_z = player_pos

    # Calculate the chunk coordinates of the player
    player_chunk_x = player_x // 16
    player_chunk_z = player_z // 16

    # Check if the player's chunk matches the given chunk coordinates
    return player_chunk_x == chunk_x and player_chunk_z == chunk_z