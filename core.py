# Import all the required libraries
import discord.ext.commands as discord
import discord.utils as discordutils
import random
import asyncio
import sqlite3
import os
import time
import threading

# Initialise database
database = sqlite3.connect("player_data.db")
database.execute("CREATE TABLE IF NOT EXISTS users (discordID integer, balance integer)")

# Initialise key information
def user_from_mention(mention):
    try:
        user_id = int(mention[2:-1])
    except:
        return None
    return bot.get_user(user_id)

roulette_in_progress = False
# Get bot token
with open("bot-token.txt", mode="r") as f:
    token = f.readlines()[0]

# Create bot object
bot = discord.Bot(command_prefix="..")

# Initialise Roulette Game class
class rouletteGame(object):
    async def init(self, ctx):
        self.ctx = ctx
        self.betting_zones = list(map(str, range(37))) + ["1-12","13-24","25-36","1-18","19-36"] + ["red","black","even","odd"] + ["1st","2nd","3rd"]
        self.roll = random.randint(0,37) # Fair, I promise!
        self.bets = []
        self.timer = 5
    async def add_bet(self, user, bet, betting_zone):
        try:
            bet = int(bet)
        except:
            return False
        user_balance = list(database.execute("SELECT balance FROM users WHERE discordID=(?)", (user.id,)))
        if len(user_balance) == 0:
            return False
        else:
            if betting_zone in self.betting_zones and bet <= user_balance[0][0]:
                self.bets.append([user.id, bet, betting_zone])
                user_balance = user_balance[0][0] - bet
                database.execute("UPDATE users SET balance=(?) WHERE discordID=(?)", (user_balance, user.id))
                database.commit()
                return True
            else:
                return False
    async def decrement_timer(self):
        await self.ctx.send("5")
        while self.timer > 0:
            self.timer -= 1
            if self.timer == 0:
                await self.payout(self.ctx)
                time.sleep(1)
            else:
                await self.ctx.send(self.timer)


    async def payout(self, ctx):
        winners = []
        for bet in self.bets:
            if bet[2] == "1-12":
                if self.roll >= 1 and self.roll <= 12:
                    winners.append([bet[0], bet[1]*3])
            elif bet[2] == "13-24":
                if self.roll >= 13 and self.roll <= 24:
                    winners.append([bet[0], bet[1]*3])
            elif bet[2] == "25-36":
                if self.roll >= 25 and self.roll <= 36:
                    winners.append([bet[0], bet[1]*3])
            elif bet[2] == "1-18":
                if self.roll >= 1 and self.roll <= 18:
                    winners.append([bet[0], bet[1]*2])
            elif bet[2] == "19-36":
                if self.roll >= 19 and self.roll <= 36:
                    winners.append([bet[0], bet[1]*2])
            elif bet[2] == "red":
                if self.roll % 2 == 0:
                    winners.append([bet[0], bet[1]*2])
            elif bet[2] == "black":
                if self.roll % 2 == 1:
                    winners.append([bet[0], bet[1]*2])
            elif bet[2] == "1st":
                if self.roll % 3 == 0:
                    winners.append([bet[0], bet[1]*3])
            elif bet[2] == "2nd":
                if self.roll % 3 == 1:
                    winners.append([bet[0], bet[1]*3])
            elif bet[2] == "3rd":
                if self.roll % 3 == 2:
                    winners.append([bet[0], bet[1]*3])
            elif bet[2] == str(self.roll):
                winners.append([bet[0], bet[1]*36])

        out = f"The ball stopped on **{'black' if self.roll%2 else 'red'} {self.roll}!**"
        if len(winners) == 0:
            out += "\n**No winners :(**"
        for winner in winners:
            out += f"\n{bot.get_user(winner[0]).mention} won £{winner[1]}!"
            user_balance = list(database.execute("SELECT balance FROM users WHERE discordID=(?)", (winner[0],)))
            user_balance = user_balance[0][0]
            user_balance += winner[1]
            database.execute("UPDATE users SET balance=(?) WHERE discordID=(?)", (user_balance, winner[0]))
            database.commit()
        await ctx.send(out)
        


# Initialise Commands
@bot.command()
async def roulette(ctx, bet, betting_zone):
    global roulette_in_progress
    if (not roulette_in_progress):
        global game
        game = rouletteGame()
        await game.init(ctx)
        await ctx.send("A game of roulette has begun! 30 secodns!")
        bet_success = await game.add_bet(ctx.author, bet, betting_zone)
        if bet_success:
            await ctx.send("Bet added successfully!")
            await game.decrement_timer()
        else:
            await ctx.send("There was a problem with your bet! Can you afford it or is the betting zone wrong?")
    else:
        bet_success = await game.add_bet(ctx.author, bet, betting_zone)
        if bet_success:
            await ctx.send("Bet added successfully!")
        else:
            await ctx.send("There was a problem with your bet! Can you afford it or is the betting zone wrong?")

@bot.command()
async def give_100(ctx):
    user_balance = list(database.execute("SELECT balance FROM users WHERE discordID=(?)", (ctx.author.id,)))
    if len(user_balance) == 0:
        await ctx.send("I don't know you! Use ..init first!")
    else:
        user_balance = user_balance[0][0]
        user_balance += 100
        database.execute("UPDATE users SET balance=(?) WHERE discordID=(?)", (user_balance, ctx.author.id))
        await ctx.send("Added £100 successfully!")
        database.commit()

@bot.command()
async def bal(ctx, *user):
    if len(user) == 1:
        user = user_from_mention(user[0])
        if user == None:
            await ctx.send("That person doesn't exist!")
        else:
            user_balance = list(database.execute("SELECT balance FROM users WHERE discordID=(?)", (user.id,)))
            if len(user_balance) == 0:
                await ctx.send("I don't know them!")
            else:
                await ctx.send(f"{user.mention}'s balance: £{user_balance[0][0]}")
    elif len(user) == 0:
        user_balance = list(database.execute("SELECT balance FROM users WHERE discordID=(?)", (ctx.author.id,)))
        if len(user_balance) == 0:
            await ctx.send("I don't know them!")
        else:
            await ctx.send(f"{ctx.author.mention}'s balance: £{user_balance[0][0]}")
    else:
        await ctx.send("Too many arguments!")

@bot.command()
async def init(ctx):
    if tuple([ctx.author.id]) not in database.execute("SELECT discordID FROM users"):
        database.execute("INSERT INTO users VALUES (?,?)", (ctx.author.id, 500))
        database.commit()
        await ctx.send(f"{ctx.author.mention}, you are now ready!")
    else:
        await ctx.send(f"{ctx.author.mention}, you are already initialised!")

# Initialise Events
@bot.event
async def on_ready():
    print("Logged in!")
    print(f"Name: {bot.user.name}")
    print(f"ID: {bot.user.id}")
    print("~"*25)

# Start her up!
bot.run(token)
