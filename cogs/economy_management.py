import discord
from discord import app_commands
from discord.ext import commands

from libs.Bank import get_bank_balance, change_balance, transfer, bank_transfer, get_user_balance, init_db
from libs.util import is_admin, create_embed
import random

class EconomyManagement(commands.Cog):  # Corrected class name to 'EconomyManagement' and 'Cog'
    def __init__(self, bot):
        self.bot = bot

    # Adjust command (Admin only, ephemeral)
    @discord.app_commands.command(name="adjust", description="Adjust a user's balance (Admin only).")
    @app_commands.describe(user="User to adjust", amount="Amount to adjust (can be negative).")
    async def adjust(self, interaction: discord.Interaction, user: discord.Member, amount: float):
        # Comprehensive permission checks
        if not interaction.guild:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)

        if not is_admin(interaction.user.id):
            return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

        # Adjust the balance
        try:
            new_balance = change_balance(str(user.id), amount)
            embed = create_embed("Balance Adjusted", f"{user.mention}'s balance has been updated to **{new_balance:.2f}**.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

    # Check balance command with improved permission handling
    @discord.app_commands.command(name="balance", description="Check your balance or another user's balance.")
    @app_commands.describe(user="User to check balance for (optional).")
    async def balance(self, interaction: discord.Interaction, user: discord.Member = None):
        # If no user specified, check own balance
        target = user or interaction.user

        # Only admins can check others' balances
        if user and not is_admin(interaction.user.id):
            return await interaction.response.send_message("You do not have permission to check others' balances.", ephemeral=True)

        try:
            balance = get_user_balance(str(target.id))
            embed = create_embed("Balance", f"{target.mention}'s balance is **{balance:.2f}**.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

    # Reward command (Admin only, ephemeral)
    @discord.app_commands.command(name="reward", description="Reward a user from the bank (Admin only).")
    @app_commands.describe(user="User to reward", amount="Amount to reward.")
    async def reward(self, interaction: discord.Interaction, user: discord.Member, amount: float):
        # Comprehensive admin check
        if not is_admin(interaction.user.id):
            return await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)

        try:
            _, bank_balance = bank_transfer(str(user.id), amount)
            embed = create_embed(
                "Reward Given",
                f"Rewarded {user.mention} **{amount:.2f} gold** from the bank.\n"
                f"Bank's remaining balance: **{bank_balance:.2f}**."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except ValueError as e:
            embed = create_embed("Reward Failed", str(e), color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An unexpected error occurred: {str(e)}", ephemeral=True)
    
    @discord.app_commands.command(name="pay", description="Send money to another user.")
    @app_commands.describe(receiver="User to send money to", amount="Amount to send.")
    async def pay(self, interaction: discord.Interaction, receiver: discord.Member, amount: int):
        if not interaction.guild:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)

        sender_id = str(interaction.user.id)
        receiver_id = str(receiver.id)

        if sender_id == receiver_id:
            return await interaction.response.send_message("You cannot send money to yourself.", ephemeral=True)

        if amount <= 0:
            return await interaction.response.send_message("You must send a positive amount.", ephemeral=True)

        try:
            sender_new_balance, receiver_new_balance = transfer(sender_id, receiver_id, amount)
            embed = create_embed(
                "Transaction Successful",
                f"{interaction.user.mention} sent **{amount:.2f} gold** to {receiver.mention}.\n"
                f"Your new balance: **{sender_new_balance:.2f}**.\n"
                f"{receiver.mention}'s new balance: **{receiver_new_balance:.2f}**."
            )
            await interaction.response.send_message(embed=embed)
        except ValueError as e:
            embed = create_embed("Transaction Failed", str(e), color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
async def setup(bot):
    await bot.add_cog(EconomyManagement(bot))  # Corrected to 'EconomyManagement'
