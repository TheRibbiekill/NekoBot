from discord.ext import commands
from collections import Counter
import discord
import aioredis, aiomysql, aiohttp

import config
import os, traceback
import datetime
import logging

log = logging.getLogger()

async def _prefix_callable(bot, msg):

    if config.debug:
        prefix = ["n."]

    else:
        prefix = await bot.redis.get(f"{msg.author.id}-prefix")
        if not prefix:
            prefix = ['n!', 'N!']
        else:
            prefix = [prefix.decode("utf8"), "n!", "N!"]

    return commands.when_mentioned_or(*prefix)(bot, msg)

class NekoBot(commands.AutoShardedBot):

    def __init__(self, shards, shard_ids, instance):

        super().__init__(command_prefix=_prefix_callable,
                         description="NekoBot",
                         pm_help=None,
                         shard_ids=shard_ids,
                         shard_count=shards,
                         # status=discord.Status.dnd,
                         # activity=discord.Game(name="Restarting..."),
                         fetch_offline_members=False,
                         max_messages=105,
                         help_attrs={"hidden": True})

        self.instance = instance
        self.usage = Counter()
        self.command_usage = Counter()

        async def _init_redis():
            self.redis = await aioredis.create_redis(address=("localhost", 6379), loop=self.loop)

        async def _init_sql():
            self.sql_conn = await aiomysql.create_pool(host="localhost", port=3306,
                                                       user="root", password=config.dbpass,
                                                       db="nekobot", loop=self.loop, autocommit=True)

        if not config.debug:
            self.loop.create_task(_init_sql())
            self.loop.create_task(_init_redis())

        for file in os.listdir("modules"):
            if file.endswith(".py"):
                name = file[:-3]
                try:
                    self.load_extension(f"modules.{name}")
                    log.info("Loaded %s" % name)
                except:
                    log.error(f"Failed to load {name}")
                    traceback.print_exc()

    async def on_command_error(self, ctx, e):
        if isinstance(e, commands.NoPrivateMessage):
            return
        elif isinstance(e, commands.DisabledCommand):
            return
        elif isinstance(e, discord.Forbidden):
            return
        elif isinstance(e, discord.NotFound):
            return
        elif isinstance(e, commands.CommandInvokeError):
            em = discord.Embed(color=0xDEADBF)
            em.title = "Error"
            em.description = f"Error in command {ctx.command.qualified_name}, " \
                             f"[Support Server](https://discord.gg/q98qeYN).\n`{e}`"
            await ctx.send(embed=em)
            webhook_url = f"https://discordapp.com/api/webhooks/{config.webhook_id}/{config.webhook_token}"
            payload = {
                "embeds": [
                    {
                        "title": f"Command: {ctx.command.qualified_name}, Instance: {self.instance}",
                        "description": f"```py\n{e}\n```\n By `{ctx.author}` (`{ctx.author.id}`)",
                        "color": 16740159
                    }
                ]
            }
            async with aiohttp.ClientSession() as cs:
                await cs.post(webhook_url, json=payload)
            log.error("Exception in %s, %s" % (ctx.commands.qualified_name, e,))
        elif isinstance(e, commands.BadArgument):
            await self.send_cmd_help(ctx)
        elif isinstance(e, commands.MissingRequiredArgument):
            await self.send_cmd_help(ctx)
        elif isinstance(e, commands.CheckFailure):
            await ctx.send("You are not allowed to use that command.", delete_after=5)
        elif isinstance(e, commands.CommandOnCooldown):
            await ctx.send("`{:.2f}s` left until you can use this command again.".format(e.retry_after), delete_after=5)
        elif isinstance(e, commands.CommandNotFound):
            return
        else:
            return

    async def on_command(self, ctx):
        self.usage["commands_used"] += 1
        self.command_usage[str(ctx.command)] += 1

    async def send_cmd_help(self, ctx):
        if ctx.invoked_subcommand:
            pages = await self.formatter.format_help_for(ctx, ctx.invoked_subcommand)
            for page in pages:
                await ctx.send(page)
        else:
            pages = await self.formatter.format_help_for(ctx, ctx.command)
            for page in pages:
                await ctx.send(page)

    async def on_message(self, message):
        self.usage["messages_read"] += 1
        if message.author.bot:
            return
        await self.process_commands(message)

    async def close(self):
        self.redis.close()
        self.sql_conn.close()
        await super().close()

    async def on_ready(self):
        if not hasattr(self, 'uptime'):
            self.uptime = datetime.datetime.utcnow()

        print("             _         _           _   \n"
              "            | |       | |         | |  \n"
              "  _ __   ___| | _____ | |__   ___ | |_ \n"
              " | '_ \ / _ \ |/ / _ \| '_ \ / _ \| __|\n"
              " | | | |  __/   < (_) | |_) | (_) | |_ \n"
              " |_| |_|\___|_|\_\___/|_.__/ \___/ \__|\n"
              "                                       \n"
              "                                       ")
        log.info("Ready!")
        log.info("Instance %s" % self.instance)
        log.info("%s Shards" % self.shard_count)
        log.info("%s Guilds" % len(self.guilds))
        log.info("%s Members" % len(set(self.get_all_members())))
        await self.change_presence(status=discord.Status.idle)

    def run(self):
        if config.debug:
            token = config.beta_token
        else:
            token = config.token
        super().run(token)
