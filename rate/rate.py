import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from copy import deepcopy
from .utils import checks
from __main__ import send_cmd_help
import os
import time
try:
    import emoji
    emojiAvailable = True
except:
    emojiAvailable = False


default_settings = {"RATE_DELAY" : 3, "UNLIMITED_RATINGS" : 1}

intervals = (
    ('weeks', 604800),  # 60 * 60 * 24 * 7
    ('days', 86400),    # 60 * 60 * 24
    ('hours', 3600),    # 60 * 60
    ('minutes', 60),
    ('seconds', 1),
    )

def display_time(seconds, granularity=2): # Thanks economy.py
    result = []                           # And thanks http://stackoverflow.com/a/24542445

    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append("{} {}".format(value, name))
    return ', '.join(result[:granularity])

class Rate:
    def __init__(self,bot):
        global default_settings
        self.bot = bot
        self._load_ratings()
        self.antispam = {}
        self.settings = dataIO.load_json('data/ratings/settings.json')

    def _load_ratings(self):
        self.Ratings = dataIO.load_json('data/ratings/ratings.json')


    def _apply_rating(self, ctx, user, givenemoji : str):
        server = user.server
        author = ctx.message.author
        if server.id not in self.Ratings:
            self.Ratings[server.id] = {}
        if user.id not in self.Ratings[server.id]:
            self.Ratings[server.id][user.id] = {}
        if givenemoji not in self.Ratings[server.id][user.id]:
            self.Ratings[server.id][user.id][givenemoji] = {}
        serverratings = self.Ratings[server.id][user.id][givenemoji]
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
        if ( has_rated is False ) or ( self.settings[server.id]["UNLIMITED_RATINGS"] == 1 ):
            self.Ratings[server.id][user.id][givenemoji]["count"] += 1
            self.Ratings[server.id][user.id][givenemoji]["rated_by"][str(time.time())] = author.id
            self._save_ratings()
            return 1
        else:
            if has_rated == serverratings:
                for key in has_rated["rated_by"]:
                    if has_rated["rated_by"][key] == author.id:
                        has_rated["rated_by"].pop(key)
                        has_rated["count"] -= 1
                self.self.Ratings[server.id][user.id][givenemoji]["count"] += 1
                self.Ratings[server.id][user.id][givenemoji]["rated_by"][str(time.time())] = author.id
                self._save_ratings()
                return 2
        
        

    def _save_ratings(self):
        dataIO.save_json('data/ratings/ratings.json', self.Ratings)

    def _save_settings(self):
        dataIO.save_json('data/ratings/settings.json', self.settings)

    @commands.command(pass_context=True, no_pm=True)
    async def rate(self, ctx, user : discord.Member, givenemoji : str):
        """Rate another user using A SINGLE emoji.

        Arguments:
          <user> | Mentioned discord user.
          <givenemoji> | An emoji, such as :smile: or any server emoji.

        If no arguments are provided, we display help."""


        author = ctx.message.author
        server = author.server
        serveremojis = server.emojis
        validemojis = []
        for e in serveremojis:
            validemojis.append("<:{}:{}>".format(e.name,e.id))

        if givenemoji.endswith(">"):
            emojis = givenemoji.split(">") # Do not allow emoji spam.
            givenemoji = emojis[0] + ">"
        else:
            emojis = givenemoji.split(" ")
            givenemoji = emojis[0]
            givenemoji = emoji.demojize(givenemoji)
        try:
            self.settings[server.id]
        except KeyError:
            self.settings[server.id] = deepcopy(default_settings)
            self._save_settings()
        if (givenemoji in validemojis)  or (givenemoji in emoji.EMOJI_UNICODE):
            if author != user:
                if server.id not in self.antispam:
                    self.antispam[server.id] = {} # Sanity check.
                if author.id in self.antispam[server.id]:
                    seconds = abs(self.antispam[server.id][author.id] - int(time.perf_counter()))
                    if seconds >= self.settings[server.id]["RATE_DELAY"]:
                        self.antispam[server.id][author.id] = int(time.perf_counter())
                        msg = self._apply_rating(ctx, user, givenemoji)
                    else:
                        msg = "Woah there, slow down friend! Wait {} more seconds!".format(str(self.settings[server.id]['RATE_DELAY'] - seconds))
                else:
                    self.antispam[server.id][author.id] = int(time.perf_counter())
                    msg = self._apply_rating(ctx, user, givenemoji)
            else:
                msg = "Sorry, you cannot rate yourself!"
        else:
            msg = "**Error!** `Either that wasn't an emoji, or you tried to use an unsupported unicode emoji.`\n\nYou gave me : _{}_".format(emoji.emojize(givenemoji))
            msg += "\nThis server's emoji: "
            for e in validemojis:
                msg += e + " "
        try:
            msg
        except NameError:
            pass
            # Do nothing
        else:
            if msg == 1:
                msg = "Rated {} {}".format(user.display_name, emoji.emojize(givenemoji))
            elif msg == 2:
                msg = "Updated Rating for {} to {}".format(user.display_name, emoji.emojize(givenemoji))
            await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True)
    async def ratings(self, ctx, arg=None, top : int=10):
        """Display ratings for a user. Valid arguments are below:

        - @username | Display that user's ratings
        - leaderboard | Display rankings for all recorded ratings.
            - Accepts another argument, <top> as the ammount to show.
        - :emoji: | Display rankings for that emoji.
            - Accepts another argument, <top> as the ammount to show.
        - help | This text, silly!

        If no argument is given, we will assume you want your ratings.
        """
        server = ctx.message.server
        author = ctx.message.author
        serveremojis = server.emojis
        validemojis = []
        for e in serveremojis:
            validemojis.append("<:{}:{}>".format(e.name,e.id))
        if arg:
            arg = emoji.demojize(arg)
        if arg != None: # I've received an argument! YAY!!!
            if isinstance(arg, str) and arg == "leaderboard": # Get the leaderboard son!
                try:
                    self.Ratings[server.id]
                except KeyError:
                    msg = "There are no ratings in this server!"
                else:
                    msg = "```py\n"
                    temp_ratings = []
                    if top < 1:
                        top = 10
                    for userid in self.Ratings[server.id]:
                        user = server.get_member(userid)
                        try:
                            user.display_name
                        except AttributeError:
                            pass
                        else:
                            count = 0
                            for givenemoji in self.Ratings[server.id][userid]:
                                count += self.Ratings[server.id][userid][givenemoji]['count']
                            toappend = [user.display_name, count]
                            temp_ratings.append(toappend)
                    lboard = sorted(temp_ratings, key=lambda entry: entry[1], reverse=True)
                    topten = lboard[:top]
                    highscore = ""
                    place = 1
                    for acc in topten:
                        highscore += (str(place)).ljust(len(str(top))+2)
                        highscore += ("\""+acc[0]+"\" ").ljust(35-len(str(acc[1])))
                        highscore += str(acc[1]) + "\n"
                        place += 1
                    msg += highscore + "```"
                    if msg:
                        if len(highscore) >= 1985:
                            msg = "The leaderboard is too big to be displayed. Try with a lower <top> argument."
            elif isinstance(arg, str) and (arg in validemojis or arg in emoji.EMOJI_UNICODE): # I've been given an emoji
                try:
                    self.Ratings[server.id]
                except KeyError:
                    msg = "There are no ratings in this server!"
                else:
                    msg = "```py\n"
                    temp_ratings = []
                    if top < 1:
                        top = 10
                    for userid in self.Ratings[server.id]:
                        user = server.get_member(userid)
                        try:
                            user.display_name
                        except AttributeError:
                            pass
                        else:
                            try:
                                self.Ratings[server.id][userid][arg]
                            except KeyError:
                                pass
                            else:
                                count = self.Ratings[server.id][userid][arg]['count']
                                toappend = [user.display_name, count]
                                temp_ratings.append(toappend)
                    lboard = sorted(temp_ratings, key=lambda entry: entry[1], reverse=True)
                    topten = lboard[:top]
                    highscore = ""
                    place = 1
                    for acc in topten:
                        highscore += (str(place)).ljust(len(str(top))+2)
                        highscore += ("\""+acc[0]+"\" ").ljust(35-len(str(acc[1])))
                        highscore += str(acc[1]) + "\n"
                        place += 1
                    msg += highscore + "```"
                    if msg:
                        if len(highscore) >= 1985:
                            msg = "The leaderboard is too big to be displayed. Try with a lower <top> argument."
            elif arg == "help":
                await send_cmd_help(ctx)
            else:
                try:
                    ctx.message.mentions[0]
                except AttributeError:
                    msg = "Invalid argument provided! (AttributeError)"
                except IndexError:
                    msg = "Invalid argument provided! (You didn't mention a user or a valid command!)"
                except NameError: #Virtually everything it could be, idk what it actually is.
                    msg = "Invalid argument provided! (NameError)"
                else:
                    arg = ctx.message.mentions[0]
                    try:
                        self.Ratings[arg.server.id][arg.id]
                    except KeyError:
                        msg = "We cannot find any ratings for {}, sorry!".format(user.display_name)
                    else:
                        userratings = self.Ratings[arg.server.id][arg.id]
                        msg = "**Ratings for {}**\n\n".format(arg.display_name)
                        count = 0
                        temp_ratings = []
                        for k in userratings:
                            count += userratings[k]['count'] or 0
                            toappend = [ k, userratings[k]['count'] ]
                            temp_ratings.append(toappend)
                        temp_ratings = sorted(temp_ratings, key=lambda emote: emote[1], reverse=True)
                        for k in temp_ratings:
                            msg += "{} x **_{}_**, ".format(emoji.emojize(k[0]), str(k[1]))
                        msg += "\n\n Total Ratings: *{}*".format(count)
        else:
            try:
                self.Ratings[server.id][author.id]
            except KeyError:
                msg = "We cannot find any ratings for you, sorry!"
            else:
                userratings = self.Ratings[server.id][author.id]
                msg = "**Your ratings**\n\n"
                count = 0
                temp_ratings = []
                for k in userratings:
                    count += userratings[k]['count'] or 0
                    toappend = [ k, userratings[k]['count'] ]
                    temp_ratings.append(toappend)
                temp_ratings = sorted(temp_ratings, key=lambda emote: emote[1], reverse=True)
                for k in temp_ratings:
                    msg += "{} x **_{}_**, ".format(emoji.emojize(k[0]), str(k[1]))
                msg += "\n\n Total Ratings: *{}*".format(count)
        try:
            msg
        except NameError:
            pass
        else:
            await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def wiperatings(self, ctx, user : discord.Member, emoji_to_wipe = None, amount = None):
        """Wipes a user's ratings. Useful if they are somehow broken or have been spammed.
        WARNING: This wipes a user's ratings with EXTREME prejudice.

        Arguments:
          <user> | The mentioned discord user that you would like to wipe the ratings of.
          [emoji_to_wipe] (optional) | The specific emoji you would like wiped from that user.
          [amount] (optional) | Amount of <emoji_to_wipe> that you would like removed from that user."""

        #try:
            #self.Ratings[user.server.id][user.id] = {}
            #self._save_ratings()
            #msg = "{}'s ratings have been wiped clean!".format(user.display_name)
        #except KeyError:
            #msg = "Unable to wipe ratings, we don't have any ratings saved for this server yet!"
        if amount:
            try:
                amount = int(amount)
            except:
                pass
        server = user.server
        serveremojis = server.emojis
        validemojis = []
        for e in serveremojis:
            validemojis.append("<:{}:{}>".format(e.name,e.id))
        if emoji_to_wipe:
            emoji_to_wipe = emoji.demojize(emoji_to_wipe)
            if emoji_to_wipe.endswith(">"):
                emojis = emoji_to_wipe.split(">")
                emoji_to_wipe = emojis[0] + ">"
        if emoji_to_wipe and (emoji_to_wipe in validemojis or emoji_to_wipe in emoji.EMOJI_UNICODE):
            if amount and isinstance(amount,int):
                try:
                    self.Ratings[user.server.id][user.id][emoji_to_wipe]['count'] -= amount
                    if self.Ratings[user.server.id][user.id][emoji_to_wipe]['count'] <= 0:
                        self.Ratings[user.server.id][user.id].pop(emoji_to_wipe)
                    self._save_ratings()
                    msg = "**{}** x {} ratings have been removed from **{}**.".format(amount,emoji.emojize(emoji_to_wipe),user.display_name)
                except KeyError:
                    msg = "**Error!** `We either couldn't find any ` {} ` ratings for that user, or that user has yet to receive any ratings.`".format(emoji.emojize(emoji_to_wipe))
            elif not amount:
                try:
                    self.Ratings[user.server.id][user.id].pop(emoji_to_wipe)
                    self._save_ratings()
                    msg = "All {} ratings have been removed from **{}**.".format(emoji.emojize(emoji_to_wipe),user.display_name)
                except KeyError:
                    msg = "**Error!** `We either couldn't find any ` {} ` ratings for that user, or that user has yet to receive any ratings.`".format(emoji.emojize(emoji_to_wipe))
            else:
                msg = "**Error!** `Invalid argument type for amount, expected a number.`"
        elif emoji_to_wipe and not (emoji_to_wipe in validemojis or emoji_to_wipe in emoji.EMOJI_UNICODE):
            msg = "**Error** `Invalid emoji specified, that doesn't appear to be a server emoji or a unicode emoji.`"
        else:
            try:
                self.Ratings[user.server.id].pop(user.id)
                self._save_ratings()
                msg = "**{}**'s ratings have been wiped clean!".format(user.display_name)
            except KeyError:
                msg = "**Error!** `We couldn't find any ratings for that user, perhaps he hasn't received any ratings yet?"
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
    if emojiAvailable:
        bot.add_cog(Rate(bot))
    else:
        raise RuntimeError("The emoji lib is not installed. Please run `pip3 install emoji` and then reload this cog.")