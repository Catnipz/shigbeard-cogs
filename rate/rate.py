import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from copy import deepcopy
from .utils import checks
from __main__ import send_cmd_help
import os
import time

default_settings = {"RATE_DELAY" : 3, "UNLIMITED_RATINGS" : 1}

class Rate:
    def __init__(self,bot):
        global default_settings
        self.bot = bot
        self._load_ratings()
        self.antispam = {}
        self.settings = dataIO.load_json('data/ratings/settings.json')

    def _load_ratings(self):
        self.Ratings = dataIO.load_json('data/ratings/ratings.json')


    def _apply_rating(self, ctx, user, emoji : str):
        server = user.server
        author = ctx.message.author
        if server.id not in self.Ratings:
            self.Ratings[server.id] = {}
        if user.id not in self.Ratings[server.id]:
            self.Ratings[server.id][user.id] = {}
        if emoji not in self.Ratings[server.id][user.id]:
            self.Ratings[server.id][user.id][emoji] = {}
        serverratings = self.Ratings[server.id][user.id][emoji]
        if serverratings == {}:
            serverratings["count"] = 0
            serverratings["rated_by"] = {}
        elif isinstance(serverratings, int):
            serverratings["count"] = 0
            serverratings["rated_by"] = {}

        has_rated = False

        for k in self.Ratings[server.id][user.id]:

            if author.id in self.Ratings[server.id][user.id][k]["rated_by"]:
                has_rated = self.Ratings[server.id][user.id][k]
        if has_rated == False or self.settings[server.id]["UNLIMITED_RATINGS"] == 1:
            self.Ratings[server.id][user.id][emoji]["count"] += 1
            self.Ratings[server.id][user.id][emoji]["rated_by"][str(time.perf_counter())] = author.id
            self._save_ratings()
            return 1
        else:
            if has_rated == serverratings:
                for key in has_rated["rated_by"]:
                    if has_rated["rated_by"][key] == author.id:
                        has_rated["rated_by"].pop(key)
                        has_rated["count"] -= 1
                self.self.Ratings[server.id][user.id][emoji]["count"] += 1
                self.Ratings[server.id][user.id][emoji]["rated_by"][str(time.perf_counter())] = author.id
                self._save_ratings()
                return 2
        
        

    def _save_ratings(self):
        dataIO.save_json('data/ratings/ratings.json', self.Ratings)

    def _save_settings(self):
        dataIO.save_json('data/ratings/settings.json', self.settings)

    @commands.command(pass_context=True, no_pm=True)
    async def rate(self, ctx, user : discord.Member, emoji : str):
        """Rate another user using A SINGLE emoji.

        Takes @mention for <user> and a custom emoji for <emoji>."""


        author = ctx.message.author
        server = author.server
        emojis = emoji.split(">") # Do not allow emoji spam.
        emoji = emojis[0] + ">"
        try:
            self.settings[server.id]
        except KeyError:
            self.settings[server.id] = deepcopy(default_settings)
            self._save_settings()
        if emoji.startswith("<") and emoji.endswith(">"):
            if author != user:
                if server.id not in self.antispam:
                    self.antispam[server.id] = {} # Sanity check.
                if author.id in self.antispam[server.id]:
                    seconds = abs(self.antispam[server.id][author.id] - int(time.perf_counter()))
                    if seconds >= self.settings[server.id]["RATE_DELAY"]:
                        self.antispam[server.id][author.id] = int(time.perf_counter())
                        #msg = "Rated {} {}".format(user.name, emoji)
                        msg = self._apply_rating(ctx, user, emoji)
                    else:
                        msg = "Woah there, slow down friend! Wait {} more seconds!".format(str(3 - seconds))
                else:
                    self.antispam[server.id][author.id] = int(time.perf_counter())
                    #msg = "Rated {} {}".format(user.name, emoji)
                    msg = self._apply_rating(ctx, user, emoji)
            else:
                msg = "Sorry, you cannot rate yourself!"
        else:
            msg = "**Error!** `Either that wasn't an emoji, or you tried to use a unicode emoji, which currently isn't supported.`\nI currently only support custom emoji.\n\n You gave me : `{}`".format(emoji)
        try:
            msg
        except NameError:
            pass
            # Do nothing
        else:
            if msg == 1:
                msg = "Rated {} {}".format(user.name, emoji)
            elif msg == 2:
                msg = "Updated Rating for {} to {}".format(user.name, emoji)
            await self.bot.say(msg)

    @commands.command(no_pm=True)
    async def ratings(self, user : discord.Member):
        """Display ratings for a user.

        Takes  @mention for <user>."""
        userratings = self.Ratings[user.server.id][user.id]
        msg = "**Ratings for {}**\n\n".format(user.name)
        count = 0
        for k in userratings:
            msg += "{} x **_ {} _**, ".format(k, str(userratings[k]['count']))
            count += userratings[k]['count'] or 0
        msg += "\n\n Total Ratings: *{}*".format(str(count))
        await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def wiperatings(self, ctx, user : discord.Member):
        """Wipes a user's ratings. Useful if they are somehow broken or have been spammed.
        WARNING: This wipes a user's ratings with EXTREME prejudice.

        Takes @mention for <user>."""

        try:
            self.Ratings[user.server.id][user.id] = {}
            self._save_ratings()
            msg = "{}'s ratings have been wiped clean!".format(user.name)
        except KeyError:
            msg = "Unable to wipe ratings, we don't have any ratings saved for this server yet!"
        await self.bot.say(msg)

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def ratingset(self, ctx):
        """Changes rating settings"""
        server = ctx.message.server
        try:
            self.settings[server.id]
        except KeyError:
            self.settings[server.id] = deepcopy(default_settings)
            self._save_settings()
        if ctx.invoked_subcommand is None:
            msg = "```"
            for k, v in self.settings[server.id].items():
                msg += "{}: {}\n".format(k, v)
            msg += "```"
            await send_cmd_help(ctx)
            await self.bot.say(msg)

    @ratingset.command(pass_context=True)
    async def rate_delay(self, ctx, delay : int):
        """Enforced delay between consecutive ratings."""
        server = ctx.message.server
        try:
            self.settings[server.id]
        except KeyError:
            self.settings[server.id] = deepcopy(default_settings)
            self.settings[server.id]
            self._save_settings()
        self.settings[server.id]["RATE_DELAY"] = delay
        await self.bot.say("Enforced delay between consecutive ratings is now {} seconds".format(str(delay)))
        self._save_settings()

    @ratingset.command(pass_context=True)
    async def unlimited_ratings(self, ctx, unlimited : int):
        """Determines if the user can rate another user as many times as they like. Set to 0 if you want to limit people to 1 rating per person, like on Facepunch."""
        server = ctx.message.server
        try:
            self.settings[server.id]
        except KeyError:
            self.settings[server.id] = deepcopy(default_settings)
            self.settings[server.id]
            self._save_settings()
        if unlimited < 0 or unlimited > 1:
            await self.bot.say("Value is out of range! Please enter 0 for limited ratings, or 1 for unlimited.")
        else:
            self.settings[server.id]["UNLIMITED_RATINGS"] = unlimited
            if unlimited == 1:
                msg = "Users can now rate other users with no limitation."
            else:
                msg = "Users are now limited to 1 rating for each target. Existing ratings made by a user may be removed when they next rate."
            await self.bot.say(msg)
            self._save_settings()



def check_folders():
    if not os.path.exists("data/ratings"):
        print("Creating data/ratings folder...")
        os.makedirs("data/ratings")

def check_files():

    f = "data/ratings/ratings.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty ratings.json...")
        dataIO.save_json(f, {})
    f = "data/ratings/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty settings.json...")
        dataIO.save_json(f, {})


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Rate(bot))
