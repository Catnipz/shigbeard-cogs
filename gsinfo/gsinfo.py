import discord
from discord.ext import commands
from .utils import checks
from __main__ import send_cmd_help
try:
    import valve.source.a2s
    import valve.source.messages
    sourcequery_isinstalled = True
except:
    sourcequery_isinstalled = False
import socket
import json
try:
    from bs4 import BeautifulSoup
    soupAvailable = True
except:
    soupAvailable = False
import aiohttp

def validate_ip(s):
    try:
        a = s.split('.')
        if len(a) != 4:
            return False
        for x in a:
            if not x.isdigit():
                return False
            i = int(x)
            if i < 0 or i > 255:
                return False
        return True
    except IndexError:
        return False

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
            result.append("{} {}".format(int(value), name))
    return ', '.join(result[:granularity])


class GSInfo:
    def __init__(self,bot):
        self.bot = bot;

    async def _query_players(self,ip,port,msgtoedit):
        """Internal function for querying playerlists, keeps it from being piled into one function."""
        try:
            server = valve.source.a2s.ServerQuerier([ip,port])
            info = server.info()
            do_players = True
            try:
                players = server.players()
            except valve.source.messages.BrokenMessageError:
                do_players = False

            if info["player_count"] > 0 and (do_players or not muteplayers):
                playerlist = discord.Embed(title="Players", description="Playerlist for {}".format(info["server_name"]), colour=0x6666ff)
                count = 0
                charlength = 0
                for player in sorted(players['players'], key=lambda p: p['score'], reverse=True):
                    if (count == 16) or (charlength > 1300):
                        playerlist.set_footer(text="Non-ascii characters are replaced with '?'")
                        await self.bot.say(embed=playerlist)
                        count = 0
                        charlength = 0
                        playerlist = discord.Embed(title="Players (continued)", description="Playerlist for {}".format(info["server_name"]), colour=0x6666ff)
                    name =  ''.join([i if ord(i) < 128 else '?' for i in player["name"]])
                    if player['name'] == "":
                        name = "_CONNECTING_"
                    value = "**Score**: {}\nConnected for {}".format(str(player['score']), display_time(player['duration']))
                    playerlist.add_field(name=name,value=value)
                    charlength += len(name) + len(value)
                    count += 1
                playerlist.set_footer(text="Non-ascii characters are replaced with '?'")
                await self.bot.say(embed=playerlist)
            elif do_players == False:
                await self.bot.say(":warning: **Warning!** `This gameserver is not reporting it's playerlist.`\nThis is a feature in CS:GO and some other games. We cannot display the playerlist for this server.")
            elif info["player_count"] == 0:
                await self.bot.say(":no_entry: **Error!** Playercount is 0, there is nothing for me to list.")
            await self.bot.delete_message(msgtoedit)
            msg_return = "Join this server by clicking here --> steam://connect/"+ip+":"+str(port)
            await self.bot.say(msg_return)
            return None
        except valve.source.a2s.NoResponseError:
            return ":no_entry: **Error!** `Request timed out, is there a server at that address?`"


    async def _query_server(self,ip,port,msgtoedit):
        """Internal function for querying servers, keeps it from being piled into one function."""
        try:
            server = valve.source.a2s.ServerQuerier([ip,port])
            info = server.info()
            do_players = True
            try:
                players = server.players()
            except valve.source.messages.BrokenMessageError:
                do_players = False


            vac_enabled = "No"
            if info["vac_enabled"] == 1:
                vac_enabled = "Yes"

            msg_server = "**{}**".format(info["server_name"])
            msg_server += "\n:video_game: **Game:** {}\n:map: **Map:** {}\n:shield: **VAC Secured:** {}\n:robot: **Bot Count:** {}\n:basketball_player: **Player Count:** {}/{}".format(info["game"],info["map"],vac_enabled,info["bot_count"],info["player_count"],info["max_players"])
            
            someurl = "http://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/?key=079D7A41C1ECEF33960716B75A7B39D4&appid={}".format(info["app_id"])
            async with aiohttp.get(someurl) as response:
                soupObject = BeautifulSoup(await response.text(), "html.parser")
            try:
                gameschema = json.loads(soupObject.get_text())
            #gameschema = json.loads(response.read())
                if gameschema["game"]["gameName"] == info["game"]:
                    game = "Running **{}**".format(info["game"])
                else:
                    game = "Running _{}_ on **{}**".format(info["game"],gameschema["game"]["gameName"])
            except:
                game = "Running **{}**".format(info["game"])

            connection_url = "steam://connect/{}:{}".format(ip,str(port))
            playercount = "{}/{}".format(info["player_count"],info["max_players"])
            data = discord.Embed(description=game,color=0x00ff00)
            data.add_field(name="Current Map", value=info['map'])
            data.add_field(name="VAC Secured", value=vac_enabled)
            data.add_field(name="Player Count", value=playercount)
            data.add_field(name="Bot Count", value=str(info['bot_count']))
            data.add_field(name="Connect", value="steam://connect/{}:{}".format(ip,str(port)))
            #data.set_footer(text="Click here to connect to this server!")
            data.set_author(name=info["server_name"])

            playermsgs = []
            try:
                #await self.bot.edit_message(msgtoedit,"",embed=data)
                await self.bot.say(embed=data)
                await self.bot.delete_message(msgtoedit)
            except discord.HTTPException:
                await self.bot.edit_message(msgtoedit,msg_server)

            if do_players == False:
                await self.bot.say(":warning: **Warning!** `This gameserver is not reporting it's playerlist.`\nThis is a feature in CS:GO and some other games. We cannot display the playerlist for this server.")
            return None

        except valve.source.a2s.NoResponseError:
            return ":no_entry: **Error!** `Request timed out, is there a server at that address?`"

    @commands.command(pass_context=True, no_pm=True)
    async def gsinfo(self, ctx, ip : str, port : int=27015):
        """Queries a source engine server for information.

        Arguments:
          <ip> | An IP address or URL that points to a source-engine server.

          This one uses a test for embedding playercount."""
        msgtoedit = await self.bot.say("_Working, please wait..._")
        ipport = ip.split(":")
        try:
            port = int(ipport[1])
        except IndexError:
            pass
        except ValueError:
            await self.bot.say(":warning: **Warning!** `Detected port looked funny and couldn't be turned into an integer, defaulting to 27015`")
            port = int(27015)
        else:
            ip = ipport[0]
        if port > 65535 or port < 1:
            msg = ":no_entry: **Error!** `Port out of range, expected a value between 1 and 65535 inclusive, got {}`".format(str(port))
        else:
            try:
                valid_ip = validate_ip(ip)
            except IndexError:
                valid_ip = False
            if valid_ip:
                msg = await self._query_server(ip,port,msgtoedit)
            else:
                try:
                    ip = socket.gethostbyname(ip)
                except socket.error:
                    msg = ":no_entry: **Error!** `Invalid IP address, invalid URL, or no IP address resolved from that URL. I'm not sure which.`"
                else:          
                    msg = await self._query_server(ip,port,msgtoedit)
        if msg:
            await self.bot.edit_message(msgtoedit,msg)

    @commands.command(pass_context=True, no_pm=True)
    async def gsplayers(self, ctx, ip : str, port : int=27015):
        """Queries a source engine server for players.

        Arguments:
          <ip> | An IP address or URL that points to a source-engine server.

          This one uses a test for embedding playercount."""
        msgtoedit = await self.bot.say("_Working, please wait..._")
        ipport = ip.split(":")
        try:
            port = int(ipport[1])
        except IndexError:
            pass
        except ValueError:
            await self.bot.say(":warning: **Warning!** `Detected port looked funny and couldn't be turned into an integer, defaulting to 27015`")
            port = int(27015)
        else:
            ip = ipport[0]
        if port > 65535 or port < 1:
            msg = ":no_entry: **Error!** `Port out of range, expected a value between 1 and 65535 inclusive, got {}`".format(str(port))
        else:
            try:
                valid_ip = validate_ip(ip)
            except IndexError:
                valid_ip = False
            if valid_ip:
                msg = await self._query_players(ip,port,msgtoedit)
            else:
                try:
                    ip = socket.gethostbyname(ip)
                except socket.error:
                    msg = ":no_entry: **Error!** `Invalid IP address, invalid URL, or no IP address resolved from that URL. I'm not sure which.`"
                else:          
                    msg = await self._query_players(ip,port,msgtoedit)
        if msg:
            await self.bot.edit_message(msgtoedit,msg)


def setup(bot):
    if sourcequery_isinstalled and soupAvailable:
        bot.add_cog(GSInfo(bot))
    else:
        if soupAvailable and not sourcequery_isinstalled:
        	raise RuntimeError("There's a dependancy missing, please install python-valve. Do this by running `pip3 install -U https://github.com/Holiverh/python-valve/archive/master.zip`. If on linux, you need to run that as root or sudo.")
        elif sourcequery_isinstalled and not soupAvailable:
            raise RuntimeError("There's a dependancy missing, please install beautifulsoup4. Do this by running `pip3 install beautifulsoup4`. If on linux, you need to run that as root or sudo.")
        elif not soupAvailable and not sourcequery_isinstalled:
            raise RuntimeError("We are missing two dependancies. Run the following commands: \n```pip3 install -U https://github.com/Holiverh/python-valve/archive/master.zip\npip3 install beautifulsoup4```\nYou may need to run these as root or sudo.")