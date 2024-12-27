import discord
from discord import app_commands
from discord.ext import commands
import random

from libs.Bank import get_bank_balance, change_balance, transfer, bank_transfer, get_user_balance, init_db
from libs.util import is_admin, create_embed

# Utility to create styled embeds
def create_embed(title, description, color=discord.Color.blue()):
    return discord.Embed(title=title, description=description, color=color)

class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Coinflip command
    @discord.app_commands.command(name="coinflip", description="Challenge another player to a coinflip game.")
    @app_commands.describe(bet="Amount of gold to bet.", opponent="The player you want to challenge.")
    async def coinflip(self, interaction: discord.Interaction, bet: float, opponent: discord.Member):
        if bet <= 0:
            return await interaction.response.send_message("Bet amount must be positive.", ephemeral=True)

        user_id = str(interaction.user.id)
        opponent_id = str(opponent.id)

        user_balance = get_user_balance(user_id)
        opponent_balance = get_user_balance(opponent_id)

        if user_balance < bet:
            return await interaction.response.send_message(f"You do not have enough balance. Your current balance is **{user_balance:.2f}**.", ephemeral=True)

        if opponent_balance < bet:
            return await interaction.response.send_message(f"{opponent.display_name} does not have enough balance to accept the bet.", ephemeral=True)

        # Create the challenge message
        embed = create_embed(
            "Coinflip Challenge!",
            f"{interaction.user.mention} has challenged {opponent.mention} to a coinflip for {bet} gold!\nClick 'Accept' to play!",
            color=discord.Color.gold()
        )

        # Create the button
        class AcceptButton(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=30)  # Button times out after 30 seconds
                self.accepted = False

            @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
            async def accept(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                if button_interaction.user != opponent:
                    await button_interaction.response.send_message("You are not the challenged player!", ephemeral=True)
                    return

                self.accepted = True
                await button_interaction.response.defer()
                self.stop()

        view = AcceptButton()
        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()

        # Wait for button interaction or timeout
        await view.wait()

        if not view.accepted:
            if message:
                await message.delete()
            return await interaction.followup.send("The coinflip challenge was not accepted in time.")

        # Coinflip logic
        winner = random.choice([interaction.user, opponent])
        loser = opponent if winner == interaction.user else interaction.user

        try:
            change_balance(str(winner.id), bet)
            change_balance(str(loser.id), -bet)

            result_embed = create_embed(
                "Coinflip Result",
                f"The coin landed! {winner.mention} wins {bet:.2f} gold!\n\nBalances:\n{interaction.user.mention}: **{get_user_balance(user_id):.2f}**\n{opponent.mention}: **{get_user_balance(opponent_id):.2f}**",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=result_embed)

        except Exception as e:
            await interaction.followup.send(f"An error occurred while processing the coinflip: {str(e)}")

    @discord.app_commands.command(name="blackjack", description="Challenge another player to a game of blackjack.")
    @app_commands.describe(bet="Amount of gold to bet.", opponent="The player you want to challenge.")
    async def blackjack(self, interaction: discord.Interaction, bet: float, opponent: discord.Member):
        if bet <= 0:
            return await interaction.response.send_message("Bet amount must be positive.", ephemeral=True)

        if interaction.user == opponent:
            return await interaction.response.send_message("You can't challenge yourself!", ephemeral=True)

        user_id = str(interaction.user.id)
        opponent_id = str(opponent.id)

        user_balance = get_user_balance(user_id)
        opponent_balance = get_user_balance(opponent_id)

        if user_balance < bet:
            return await interaction.response.send_message(f"You do not have enough balance. Your current balance is **{user_balance:.2f}**.", ephemeral=True)

        if opponent_balance < bet:
            return await interaction.response.send_message(f"{opponent.display_name} does not have enough balance to accept the bet.", ephemeral=True)

        embed = create_embed(
            "Blackjack Challenge!",
            f"{interaction.user.mention} has challenged {opponent.mention} to a game of blackjack for {bet} gold!\nClick 'Accept' to play!\n\n**Challenge expires in 30 seconds**",
            color=discord.Color.gold()
        )

        class AcceptButton(discord.ui.View):
            def __init__(self, challenger, challenged, bet):
                super().__init__(timeout=30)
                self.accepted = False
                self.challenger = challenger
                self.challenged = challenged
                self.bet = bet

            @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
            async def accept(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                if button_interaction.user != self.challenged:
                    await button_interaction.response.send_message("You are not the challenged player!", ephemeral=True)
                    return

                self.accepted = True
                await button_interaction.response.defer()
                self.stop()

            async def on_timeout(self):
                try:
                    await self.message.edit(
                        embed=create_embed(
                            "Challenge Expired",
                            f"{self.challenger.mention}'s blackjack challenge to {self.challenged.mention} has expired.",
                            color=discord.Color.red()
                        ),
                        view=None
                    )
                except:
                    pass

        view = AcceptButton(interaction.user, opponent, bet)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

        await view.wait()

        if not view.accepted:
            return

        deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
        random.shuffle(deck)

        player1_hand = [deck.pop(), deck.pop()]
        player2_hand = [deck.pop(), deck.pop()]

        def hand_value(hand):
            value = sum(hand)
            aces = hand.count(11)
            while value > 21 and aces:
                value -= 10
                aces -= 1
            return value

        def hand_to_string(hand):
            return ", ".join(map(str, hand))

        class BlackjackView(discord.ui.View):
            def __init__(self, interaction, bet, player1, player2, player1_hand, player2_hand):
                super().__init__(timeout=60)
                self.interaction = interaction
                self.bet = bet
                self.player1 = player1
                self.player2 = player2
                self.player1_hand = player1_hand
                self.player2_hand = player2_hand
                self.current_player = player1
                self.current_hand = player1_hand
                self.other_player = player2
                self.other_hand = player2_hand
                self.game_over = False

            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                if interaction.user != self.current_player:
                    await interaction.response.send_message(f"It's {self.current_player.mention}'s turn!", ephemeral=True)
                    return False
                return True

            @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
            async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.current_hand.append(deck.pop())
                current_value = hand_value(self.current_hand)

                if current_value > 21:
                    self.game_over = True
                    await self.end_game(interaction)
                    return

                await interaction.response.edit_message(embed=create_embed(
                    "Blackjack",
                    f"{self.current_player.mention}'s turn\n\n" +
                    f"{self.current_player.mention}'s hand: {hand_to_string(self.current_hand)} (Value: {current_value})\n" +
                    f"{self.other_player.mention}'s hand: {self.other_hand[0]}, ?",
                    color=discord.Color.blue()
                ), view=self)

            @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
            async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
                if self.current_player == self.player1:
                    self.current_player = self.player2
                    self.current_hand = self.player2_hand
                    self.other_player = self.player1
                    self.other_hand = self.player1_hand

                    await interaction.response.edit_message(embed=create_embed(
                        "Blackjack",
                        f"{self.current_player.mention}'s turn\n\n" +
                        f"{self.current_player.mention}'s hand: {hand_to_string(self.current_hand)} (Value: {hand_value(self.current_hand)})\n" +
                        f"{self.other_player.mention}'s hand: {hand_value(self.other_hand)}",
                        color=discord.Color.blue()
                    ), view=self)
                else:
                    self.game_over = True
                    await self.end_game(interaction)

            async def end_game(self, interaction: discord.Interaction):
                player1_value = hand_value(self.player1_hand)
                player2_value = hand_value(self.player2_hand)

                if player1_value > 21:
                    winner = self.player2
                    loser = self.player1
                elif player2_value > 21:
                    winner = self.player1
                    loser = self.player2
                elif player1_value > player2_value:
                    winner = self.player1
                    loser = self.player2
                elif player2_value > player1_value:
                    winner = self.player2
                    loser = self.player1
                else:
                    try:
                        result_embed = create_embed(
                            "Blackjack Result",
                            f"It's a tie! 🤝\nThe {self.bet:.2f} gold bet is split equally.\n\n" +
                            f"Final hands:\n" +
                            f"{self.player1.mention}: {hand_to_string(self.player1_hand)} (Value: {player1_value})\n" +
                            f"{self.player2.mention}: {hand_to_string(self.player2_hand)} (Value: {player2_value})\n\n" +
                            f"Balances:\n" +
                            f"{self.player1.mention}: **{get_user_balance(str(self.player1.id)):.2f}**\n" +
                            f"{self.player2.mention}: **{get_user_balance(str(self.player2.id)):.2f}**",
                            color=discord.Color.gold()
                        )
                        await interaction.edit_original_response(embed=result_embed, view=None)
                        return
                    except Exception as e:
                        await interaction.followup.send(f"An error occurred: {str(e)}")
                        return

                try:
                    change_balance(str(winner.id), self.bet)
                    change_balance(str(loser.id), -self.bet)

                    result_embed = create_embed(
                        "Blackjack Result",
                        f"{winner.mention} wins {self.bet:.2f} gold! 🎉\n\n" +
                        f"Final hands:\n" +
                        f"{self.player1.mention}: {hand_to_string(self.player1_hand)} (Value: {player1_value})\n" +
                        f"{self.player2.mention}: {hand_to_string(self.player2_hand)} (Value: {player2_value})\n\n" +
                        f"Balances:\n" +
                        f"{self.player1.mention}: **{get_user_balance(str(self.player1.id)):.2f}**\n" +
                        f"{self.player2.mention}: **{get_user_balance(str(self.player2.id)):.2f}**",
                        color=discord.Color.green()
                    )
                    await interaction.edit_original_response(embed=result_embed, view=None)
                except Exception as e:
                    await interaction.followup.send(f"An error occurred: {str(e)}")

        # Initial game view
        view = BlackjackView(interaction, bet, interaction.user, opponent, player1_hand, player2_hand)
        initial_embed = create_embed(
            "Blackjack",
            f"{interaction.user.mention}'s turn\n\n" +
            f"{interaction.user.mention}'s hand: {hand_to_string(player1_hand)} (Value: {hand_value(player1_hand)})\n" +
            f"{opponent.mention}'s hand: {player2_hand[0]}, ?",
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=initial_embed, view=view)

async def setup(bot):
    await bot.add_cog(Games(bot))