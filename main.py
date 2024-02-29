#coding: utf-8
# discord module
from typing import Any, Dict, List
import discord
from discord.ext import commands

#for debug log
import logging
import logging.handlers

# sqlite3 database
import sqlite3

from dotenv import dotenv_values

from sendMail import Email

from verify import *

# get global environment variable
environ = dotenv_values('.env')
DISCORD_TOKEN: str = str(environ['TOKEN'])
DATABASE_NAME: str = str(environ['DATABASE_NAME'])
COMMAND_PREFIX: str = str(environ['COMMAND_PREFIX'])
VERIFY_MAIL: str = str(environ['VERIFY_MAIL_EMAIL'])
VERIFY_MAIL_PASSWORD: str = str(environ['VERIFY_MAIL_PASSWORD'])

class GDSCCommBot( commands.Bot ):
    def __init__( self, command_prefix: str,  self_bot:bool = False ) -> None:

        # setup email object
        self.email = Email(VERIFY_MAIL, VERIFY_MAIL_PASSWORD)

        # setting up logging
        self.log = logging.getLogger('discord')
        self.log.setLevel(logging.INFO)
        logging.getLogger('discord.http').setLevel(logging.INFO)

        self.log_handler = logging.handlers.RotatingFileHandler(
            filename='bot.log', # write log to bot.log file
            encoding='utf-8',
            maxBytes=( 64 * 1024 * 1024 ),
            backupCount=5
        )
        dt_fmt = '%Y-%m-%d %H:%M:%S'
        formatter = logging.Formatter('{asctime} {levelname:<8} -> {name}: {message}', dt_fmt, style='{')
        self.log_handler.setFormatter(formatter)
        self.log.addHandler(self.log_handler)

        # setup database sqlite3
        self.db_conn = sqlite3.connect(DATABASE_NAME)
        self.sql = self.db_conn.cursor() # this cursor will effect the database

        # inheritance for discord class
        super().__init__(command_prefix = command_prefix, self_bot = self_bot, intents=discord.Intents.all())

        # current bot client
        #self.bot_client = discord.Client( intents = discord.Intents.all() )

        self.__init_dev_command()

    async def on_ready( self ) -> None:
        # when the bot ready load for cog
        await self.load_extension('verify')
        # active when bot is ready set some funny presence
        await self.change_presence(activity=discord.Game(name="Muốn Mở Mang"))

    async def on_message( self, message: discord.Message ) -> None:
        # if message sent by a bot do nothing
        if message.author.bot:
            return None
        try:
            if message.content.startswith(COMMAND_PREFIX):
                await self.process_commands(message)
                self.log.info(f'\"{message.author.global_name}\" execute \"{message.content}\"')
                self.db_conn.commit()
        except commands.errors.CommandNotFound as e:
            if not message.content.startswith(COMMAND_PREFIX):
                # perform the gdsc credit
                pass

    def __init_dev_command( self ) ->  None:
        @self.command( name='reload', aliases=['r'], description="Hot reload cho bot module", brief="Hot reload cho bot module" )
        async def reload( ctx, module: str ):
            try:
                await self.reload_extension(module)
                await ctx.message.add_reaction("✅")
                self.log.info(f'Reloaded module "{module}"')
            except Exception as e:
                await ctx.send(f'**Module \"{module}\" cannot reload because some error occurred!** :x:')
                self.log.error(f'Reload module "{module}" error')
                raise e




# run the bot
if __name__ == "__main__":
    bot = GDSCCommBot( command_prefix=COMMAND_PREFIX )
    bot.run(DISCORD_TOKEN, log_handler=None)

