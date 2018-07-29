from discord.ext import commands
import discord
import logging
import random
import ujson
import datetime
import math
from .utils.chat_formatting import pagify
from colorthief import ColorThief

from urllib.parse import quote_plus
import aiohttp
from io import BytesIO

log = logging.getLogger()

def millify(n):
    millnames = ['', 'k', 'M', ' Billion', ' Trillion']
    n = float(n)
    millidx = max(0, min(len(millnames) - 1,
                         int(math.floor(0 if n == 0 else math.log10(abs(n)) / 3))))

    return '{:.0f}{}'.format(n / 10 ** (3 * millidx), millnames[millidx])

def triplet(rgb):
    return format(rgb[0]<<16 | rgb[1]<<8 | rgb[2], '06'+'X')

languages = ["english", "weeb", "tsundere", "polish", "spanish", "french"]
lang = {}

for l in languages:
    with open("lang/%s.json" % l, encoding="utf-8") as f:
        lang[l] = ujson.load(f)

def getlang(la:str):
    return lang.get(la, None)

class General:

    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    async def shutdown(self, ctx):
        await ctx.send("Bai bai")
        await self.bot.close()

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def setlang(self, ctx, lang: str = None):
        """Change the bot language for you."""
        if lang is None:
            em = discord.Embed(color=0xDEADBF, title="Change Language.",
                               description="Usage: `n!setlang <language>`\n"
                                           "Example: `n!setlank english`\n"
                                           "\n"
                                           "List of current languages:\n"
                                           "`english`,\n"
                                           "`weeb`,\n"
                                           "`tsundere` - computerfreaker#4054\n"
                                           "`polish` - YebakazLLE#7118\n"
                                           "`spanish` - ΛTLΛS Dinoseto & Luketten\n"
                                           "`french` - ShiroNeko#7379 & Anderson")
            return await ctx.send(embed=em)
        if lang.lower() in languages:
            await self.bot.redis.set(f"{ctx.author.id}-lang", lang.lower())
            await ctx.send(f"Set language to {lang.title()}!")
        else:
            await ctx.send("Invalid language.")

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def cookie(self, ctx, user: discord.Member):
        """Give somebody a cookie :3"""
        lang = await self.bot.redis.get(f"{ctx.author.id}-lang")
        if lang:
            lang = lang.decode("utf8")
        else:
            lang = "english"
        await ctx.send(getlang(lang)["general"]["cookie"].format(ctx.message.author.name, user.mention))

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def choose(self, ctx, *items):
        """Choose from a random amount of items."""
        em = discord.Embed(color=0xDEADBF)
        em.description = random.choice(items)
        await ctx.send(embed=em)

    def get_bot_uptime(self, *, brief=False):
        now = datetime.datetime.utcnow()
        delta = now - self.bot.uptime
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        if not brief:
            if days:
                fmt = '{d} days, {h} hours, {m} minutes, and {s} seconds'
            else:
                fmt = '{h} hours, {m} minutes, and {s} seconds'
        else:
            fmt = '{h}h {m}m {s}s'
            if days:
                fmt = '{d}d ' + fmt

        return fmt.format(d=days, h=hours, m=minutes, s=seconds)

    @commands.command(aliases=['version'])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def info(self, ctx):
        """Get Bot's Info"""
        await ctx.trigger_typing()

        servers = 0
        members = 0
        messages = 0
        commands = 0
        channels = 0

        for x in range(0, 3):
            y = (await self.bot.redis.get("instance%s-guilds" % x)).decode("utf8")
            servers += int(y)
            y = (await self.bot.redis.get("instance%s-users" % x)).decode("utf8")
            members += int(y)
            y = (await self.bot.redis.get("instance%s-messages" % x)).decode("utf8")
            messages += int(y)
            y = (await self.bot.redis.get("instance%s-commands" % x)).decode("utf8")
            commands += int(y)
            y = (await self.bot.redis.get("instance%s-channels" % x)).decode("utf8")
            channels += int(y)

        lang = await self.bot.redis.get(f"{ctx.author.id}-lang")
        if lang:
            lang = lang.decode('utf8')
        else:
            lang = "english"

        em = discord.Embed(color=0xDEADBF)
        em.title = getlang(lang)["general"]["info"]["info"]
        em.description = getlang(lang)["general"]["info"]["stats"].format(millify(servers), servers,
                                                                          millify(members),
                                                                          len(self.bot.commands),
                                                                          millify(channels),
                                                                          self.bot.shard_count, 0,
                                                                          self.get_bot_uptime(),
                                                                          millify(messages),
                                                                          self.bot.command_usage.most_common(1)[0][0],
                                                                          commands)
        em.set_thumbnail(url=self.bot.user.avatar_url_as(format="png"))
        em.add_field(name=getlang(lang)["general"]["info"]["links"]["name"],
                     value=getlang(lang)["general"]["info"]["links"]["links"])
        await ctx.send(embed=em)

    @commands.command(aliases=["emojiinfo", "emote", "emoji"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def emoteinfo(self, ctx, emote: discord.Emoji):
        """Get Emote Info"""
        em = discord.Embed(color=0xDEADBF)
        em.add_field(name="Name", value=emote.name, inline=False)
        em.add_field(name="ID", value=emote.id, inline=False)
        em.add_field(name="Animated?", value=str(emote.animated), inline=False)
        guild = emote.guild
        em.add_field(name="Server", value=f"{guild.name} ({guild.id})", inline=False)
        em.set_thumbnail(url=emote.url)
        await ctx.send(embed=em)

    @commands.command(aliases=["user"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def userinfo(self, ctx, user: discord.Member = None):
        """Get a users info."""
        lang = await self.bot.redis.get(f"{ctx.author.id}-lang")
        if lang:
            lang = lang.decode('utf8')
        else:
            lang = "english"

        if user == None:
            user = ctx.author

        server = ctx.guild
        embed = discord.Embed(color=0xDEADBF)
        embed.set_author(name=user.name,
                         icon_url=user.avatar_url)
        embed.add_field(name=getlang(lang)["general"]["userinfo"]["id"], value=user.id)
        embed.add_field(name=getlang(lang)["general"]["userinfo"]["discrim"], value=user.discriminator)
        embed.add_field(name=getlang(lang)["general"]["userinfo"]["bot"], value=str(user.bot))
        embed.add_field(name=getlang(lang)["general"]["userinfo"]["created"],
                        value=user.created_at.strftime("%d %b %Y %H:%M"))
        embed.add_field(name=getlang(lang)["general"]["userinfo"]["joined"],
                        value=user.joined_at.strftime("%d %b %Y %H:%M"))
        embed.add_field(name=getlang(lang)["general"]["userinfo"]["animated_avatar"],
                        value=str(user.is_avatar_animated()))
        embed.add_field(name=getlang(lang)["general"]["userinfo"]["status"], value=user.status)
        embed.add_field(name=getlang(lang)["general"]["userinfo"]["color"], value=str(user.color))

        try:
            roles = [x.name for x in user.roles if x.name != "@everyone"]

            if roles:
                roles = sorted(roles, key=[x.name for x in server.role_hierarchy
                                           if x.name != "@everyone"].index)
                roles = ", ".join(roles)
            else:
                roles = "None"
            embed.add_field(name="Roles", value=roles)
        except:
            pass

        await ctx.send(embed=embed)

    @commands.command(aliases=["server"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def serverinfo(self, ctx):
        """Display Server Info"""
        lang = await self.bot.redis.get(f"{ctx.author.id}-lang")
        if lang:
            lang = lang.decode('utf8')
        else:
            lang = "english"

        server = ctx.guild

        verif = server.verification_level

        online = len([m.status for m in server.members
                      if m.status == discord.Status.online or
                      m.status == discord.Status.idle])

        embed = discord.Embed(color=0xDEADBF)
        embed.add_field(name=getlang(lang)["general"]["serverinfo"]["name"], value=f"**{server.name}**\n({server.id})")
        embed.add_field(name=getlang(lang)["general"]["serverinfo"]["owner"], value=server.owner)
        embed.add_field(name=getlang(lang)["general"]["serverinfo"]["online"], value=f"**{online}**")
        embed.add_field(name=getlang(lang)["general"]["serverinfo"]["created_at"],
                        value=server.created_at.strftime("%d %b %Y %H:%M"))
        embed.add_field(name=getlang(lang)["general"]["serverinfo"]["channels"],
                        value=f"Text Channels: **{len(server.text_channels)}**\n"
                              f"Voice Channels: **{len(server.voice_channels)}**\n"
                              f"Categories: **{len(server.categories)}**\n"
                              f"AFK Channel: **{server.afk_channel}**")
        embed.add_field(name=getlang(lang)["general"]["serverinfo"]["roles"], value=str(len(server.roles)))
        embed.add_field(name=getlang(lang)["general"]["serverinfo"]["emojis"], value=f"{len(server.emojis)}/100")
        embed.add_field(name=getlang(lang)["general"]["serverinfo"]["region"], value=str(server.region).title())
        embed.add_field(name=getlang(lang)["general"]["serverinfo"]["security"],
                        value=f"Verification Level: **{verif}**\n"
                              f"Content Filter: **{server.explicit_content_filter}**")

        try:
            embed.set_thumbnail(url=server.icon_url)
        except:
            pass

        await ctx.send(embed=embed)

    @commands.command(aliases=["channel"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def channelinfo(self, ctx, channel: discord.TextChannel = None):
        """Get Channel Info"""
        lang = await self.bot.redis.get(f"{ctx.author.id}-lang")
        if lang:
            lang = lang.decode('utf8')
        else:
            lang = "english"

        if channel is None:
            channel = ctx.channel

        embed = discord.Embed(color=0xDEADBF,
                              description=channel.mention)
        embed.add_field(name=getlang(lang)["general"]["channelinfo"]["name"], value=channel.name)
        embed.add_field(name=getlang(lang)["general"]["channelinfo"]["guild"], value=channel.guild)
        embed.add_field(name=getlang(lang)["general"]["channelinfo"]["id"], value=channel.id)
        embed.add_field(name=getlang(lang)["general"]["channelinfo"]["category_id"], value=channel.category_id)
        embed.add_field(name=getlang(lang)["general"]["channelinfo"]["position"], value=channel.position)
        embed.add_field(name=getlang(lang)["general"]["channelinfo"]["nsfw"], value=str(channel.is_nsfw()))
        embed.add_field(name=getlang(lang)["general"]["channelinfo"]["members"], value=str(len(channel.members)))
        embed.add_field(name=getlang(lang)["general"]["channelinfo"]["category"], value=channel.category)
        embed.add_field(name=getlang(lang)["general"]["channelinfo"]["created_at"],
                        value=channel.created_at.strftime("%d %b %Y %H:%M"))

        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def urban(self, ctx, search_terms:str, definition_number: int = 1):
        """Search urban dictionary"""

        if not ctx.channel.is_nsfw():
            return await ctx.send("Please use this in an NSFW channel.", delete_after=5)

        def encode(s):
            return quote_plus(s, encoding='utf-8', errors='replace')

        search_terms = search_terms.split(" ")
        try:
            if len(search_terms) > 1:
                pos = int(search_terms[-1]) - 1
                search_terms = search_terms[:-1]
            else:
                pos = 0
            if pos not in range(0, 11):
                pos = 0
        except ValueError:
            pos = 0

        search_terms = "+".join([encode(s) for s in search_terms])
        url = "http://api.urbandictionary.com/v0/define?term=" + search_terms
        try:
            async with aiohttp.ClientSession() as cs:
                async with cs.get(url) as r:
                    result = await r.json()
            if result["list"]:
                definition = result['list'][pos]['definition']
                example = result['list'][pos]['example']
                defs = len(result['list'])
                msg = ("**Definition #{} out of {}:\n**{}\n\n"
                       "**Example:\n**{}".format(pos + 1, defs, definition,
                                                 example))
                msg = pagify(msg, ["\n"])
                for page in msg:
                    await ctx.send(page)
            else:
                await ctx.send("Your search terms gave no results.")
        except IndexError:
            await ctx.send("There is no definition #{}".format(pos + 1))
        except Exception as e:
            await ctx.send(f"Error. {e}")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def avatar(self, ctx, user: discord.Member = None, type: str = None):
        """Get a user's avatar"""
        await ctx.channel.trigger_typing()
        if user is None:
            user = ctx.message.author
        async with aiohttp.ClientSession() as cs:
            async with cs.get(user.avatar_url_as(format='png')) as r:
                res = await r.read()
        color_thief = ColorThief(BytesIO(res))
        em = discord.Embed(color=int(triplet(color_thief.get_color()), 16), title=f"{user.name}'s Avatar")
        if type is None or type not in ['jpeg', 'jpg', 'png']:
            await ctx.send(embed=em.set_image(url=user.avatar_url))
        else:
            await ctx.send(embed=em.set_image(url=user.avatar_url_as(format=type)))

def setup(bot):
    bot.add_cog(General(bot))