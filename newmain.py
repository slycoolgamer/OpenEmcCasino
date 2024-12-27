import discord
from discord import app_commands
from discord.ext import commands, tasks

from libs.Bank import get_bank_balance, change_balance, transfer, bank_transfer, get_user_balance, init_db
from libs.util import is_admin, create_embed, token, shop_owner, coordDistance, isInChunk, logchannel, chestcords, town
import os
import time
import asyncio
import requests
import aiohttp

# Initialize the database
try:
    init_db()
except Exception as e:
    print(f"Error initializing database: {e}")
    exit(1)

# Create a lock
deposit_lock = asyncio.Lock()
config = {'AutoDeposits': True}

# Functions
async def Confirm(player: str, receiver: str, amount: int, channel: discord.channel):
    try:
        response = requests.post('https://api.earthmc.net/v3/aurora/players', json={"query": [player, receiver], "template": {"uuid": True}}).json()

        uuids = [x['uuid'] for x in response if response and len(response) >= 1 and 'uuid' in x]

        if len(uuids) != 2:
            await channel.send(f"❌ Failed to deposit **{amount}g** into {player}'s account.")
            return

        response = requests.post('https://api.earthmc.net/v3/aurora/discord', json={"query": [{"type": "minecraft", "target": uuids[0]}, {"type": "minecraft", "target": uuids[1]}]}).json()

        discord_ids = [int(x['id']) for x in response if response and len(response) >= 1 and 'id' in x and x['id']]

        if len(discord_ids) != 2:
            await channel.send(f"❌ Failed to deposit **{amount}g** into {player}'s account.")
            return
            
        player_obj: discord.User = bot.get_user(discord_ids[0])
        receiver_obj: discord.User = bot.get_user(discord_ids[1])

        if not receiver_obj or not player_obj:
            await channel.send(f"❌ Failed to deposit **{amount}g** into {player}'s account.")
            return

        embed = create_embed(title='Deposit', description=f'✅ Deposited **{amount}g** into your account.')
        if await player_obj.send(embed=embed):
            embed = create_embed(title='Deposit', description=f"✅ Deposited **{amount}g** into {player_obj.name}'s account.")

            await receiver_obj.send(embed=embed)
            
            current_balance = get_user_balance(player_obj.id)
            new_balance = change_balance(player_obj.id, amount)

            await channel.send(f"✅ Deposited **{amount}g** into {player_obj.name}'s account. (Received by {receiver_obj.name})")
            print(f'{player_obj.name} deposited {amount}g > {receiver_obj.name}')

    except Exception as e:
        print(f'AUTO-DEPOSIT ERROR: {e}')
        await channel.send(f"❌ Failed to deposit **{amount}g** into {player}'s account.")
        return


async def deposit(town_name, receiver, chest_pos):
    global config, logs_channel
    logs_channel = int(logchannel())

    async with deposit_lock:
        async with aiohttp.ClientSession() as session:
            async with session.post('https://api.earthmc.net/v3/aurora/towns', json={"query": [town_name], "template": {"coordinates": True}}) as resp:
                response = await resp.json()
            
            if not response:
                return
            
            channel = bot.get_channel(logs_channel)
            if not channel:
                print("CHANNEL NOT FOUND! RESTART")
            
            town_chunks = response[0]['coordinates']['townBlocks']
            seen_in_town = {}
            last_balances = {}
            while True:
                if not config['AutoDeposits']:
                    await asyncio.sleep(20)
                    continue

                async with session.get('https://map.earthmc.net/tiles/players.json') as resp:
                    if resp.status == 200 and resp.content_type == 'application/json':
                        response = await resp.json()
                    else:
                        response = {'players': []}
                
                players_in_town = [receiver]
                for item in seen_in_town:
                    if item not in players_in_town:
                        players_in_town.append(item)
                
                player_positions = {}
                try:
                    for player in response['players']:
                        if isinstance(player, dict):
                            player_pos = [player['x'], player['z']]
                            player_name = player['name']
                            if [x for x in town_chunks if isInChunk(x, player_pos)]:
                                player_positions[player_name] = player_pos
                                seen_in_town[player_name] = {'pos': player_pos, 'epoch': int(time.time())}
                                if player_name not in players_in_town:
                                    players_in_town.append(player_name)
                except Exception:
                    await asyncio.sleep(3)
                    continue
                
                players_in_town = list(set(players_in_town))

                if players_in_town:
                    differences = []
                    async with session.post('https://api.earthmc.net/v3/aurora/players', json={"query": players_in_town, "template": {"stats": True}}) as resp:
                        if resp.status == 200 and resp.content_type == 'application/json':
                            response = await resp.json()
                        else:
                            response = {'players': []}
                    
                    try:
                        for index, player in enumerate(response):
                            if isinstance(player, dict):
                                player_name = players_in_town[index]
                                player_balance = player['stats']['balance']
                                if player_name in last_balances and last_balances[player_name] != player_balance:
                                    bal_difference = player_balance - last_balances[player_name]
                                    differences.append({'player': player_name, 'value': bal_difference})
                                last_balances[player_name] = player_balance
                    except Exception:
                        await asyncio.sleep(3)
                        continue
                    
                    receiver_difference = [int(y['value']) for y in differences if y['player'] == receiver and abs(y['value']) > 0]
                    receiver_difference = receiver_difference[0] if len(receiver_difference) == 1 else None

                    if receiver_difference and receiver_difference >= 1:
                        potentials = [x for x in differences if x['value'] < 0 and x['player'] != receiver and receiver_difference == -x['value']]

                        if len(potentials) > 1:
                            closest = min(potentials, key=lambda p: coordDistance(chest_pos, player_positions[p['player']]))
                            await Confirm(player=closest['player'], receiver=receiver, amount=receiver_difference, channel=channel)
                        elif potentials:
                            await Confirm(player=potentials[0]['player'], receiver=receiver, amount=receiver_difference, channel=channel)
                
                last_balances = {k: v for k, v in last_balances.items() if k in players_in_town}
                epoch_now = int(time.time())
                seen_in_town = {k: v for k, v in seen_in_town.items() if epoch_now - v['epoch'] <= 12}
                
                await asyncio.sleep(3)

# Configure intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Create bot instance
bot = commands.Bot(command_prefix='!', intents=intents)

#funcs
async def load_extensions():
    # Load existing extensions
    await bot.load_extension(f'cogs.games')
    await bot.load_extension(f'cogs.economy_management')
    

# Ready event with improved error handling
@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}!")
    try:
        await load_extensions()
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
        asyncio.create_task(deposit(town_name=str(town()), receiver=str(shop_owner()), chest_pos=chestcords()))
    except Exception as e:
        print(f"Failed to sync commands: {e}")
        

@bot.command(name='reload_extensions')
async def reload_extensions(ctx):
    """Reload all bot extensions."""
    if not is_admin(ctx.author.id):
        await ctx.send("You do not have permission to use this command.")
        return
    
    try:
        # Unload and reload each extension
        await bot.unload_extension(f'cogs.games')
        await bot.unload_extension(f'cogs.economy_management')
        
        # Reload extensions
        await bot.load_extension(f'cogs.games')
        await bot.load_extension(f'cogs.economy_management')
        
        await ctx.send("All extensions reloaded successfully!")
    except Exception as e:
        await ctx.send(f"Error reloading extensions: {e}")

# Run the bot
if __name__ == "__main__":
    bot.run(token())
