import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from copy import deepcopy
import os

class Rate:
    def __init__(self,bot):
        self.bot = bot
        self._load_ratings()

    def _load_ratings(self):
        self.Ratings = dataIO.load_json('data/ratings/ratings.json')


    def _apply_rating(self, user, emoji : str):
        server = user.server
        if server.id not in self.Ratings:
            self.Ratings[server.id] = {}
        if user.id not in self.Ratings[server.id]:
            self.Ratings[server.id][user.id] = {}
        if emoji not in self.Ratings[server.id][user.id]:
            self.Ratings[server.id][user.id][emoji] = 1
        else:
            self.Ratings[server.id][user.id][emoji] += 1
        self._save_ratings()

    def _save_ratings(self):
        dataIO.save_json('data/ratings/ratings.json', self.Ratings)

    @commands.command()
    async def rate(self, user : discord.Member, emoji : str):
        """Rate another user using A SINGLE emoji."""
        emoji_isvalid = False
        if emoji.startswith("<") and emoji.endswith(">"):
            emojis = emoji.split(">") # Do not allow emoji spam.
            emoji = emojis[0] + ">"
            emoji_isvalid = True
            msg = "Rating " + user.name + " " + emoji
        else:
            msg = "**Error!** `Either that wasn't an emoji, or you tried to use a unicode emoji, which currently isn't supported.`\n\n You gave me : `" + emoji + "`"
        await self.bot.say(msg)
        if emoji_isvalid == True:
            self._apply_rating(user, emoji)

    @commands.command()
    async def ratings(self, user : discord.Member):
        """Display ratings for a user."""
        userratings = deepcopy(self.Ratings[user.server.id][user.id])
        msg = "**Ratings for " + user.name + "**\n\n"
        count = 0
        for k in userratings:
            msg += k + " x ***" + str(userratings[k]) + "***, "
            count += userratings[k] or 0
        msg += "\n\n Total Ratings: *" + str(count) + "*"
        await self.bot.say(msg)


def check_folders():
    if not os.path.exists("data/ratings"):
        print("Creating data/ratings folder...")
        os.makedirs("data/ratings")

def check_files():

    f = "data/ratings/ratings.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty ratings.json...")
        dataIO.save_json(f, {})

def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Rate(bot))
