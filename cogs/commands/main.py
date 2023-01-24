import asyncio
import configparser
import json
import logging
import random
import sqlite3
from datetime import datetime
from urllib.request import Request, urlopen

import discord
import requests
from discord.ext import commands
from discord.commands import Option, UserCommand
from discord.commands import (
    slash_command,
    user_command,
)


class Commands(commands.Cog):
    def __init__(self, bot):
        # logging.info('\t\t\tRadio [RADIO] started!')
        self.bot = bot
        self.con = sqlite3.connect('database/database.db')
        config = configparser.ConfigParser()
        config.read_file(open('settings.ini'))
        self.cfg = config
        # self.last_message = None

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info('cogs.commands.main ON_READY')

    @user_command()
    @commands.cooldown(1, 30, commands.BucketType.member)
    async def pabakstit(self, ctx, user):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        if not overwrite.send_messages:
            return

        await ctx.respond(f'{ctx.author.mention} pabakstīja 👉 {user.mention}')
    #
    @commands.Cog.listener()
    async def on_message(self, message):
        for x in message.mentions:
            if x == self.bot.user:
                if message.content[-1] == '?':
                    response = ['PROTAMS!', 'Tikai tā!', 'Nu bet kā tad savādāk!', 'Jā!', 'Nē!',
                                'Noraidīts, večuk!', 'Aivars saka, ka jā!', 'Apstiprinu!', 'Diemžēl man jāsaka nē!',
                                'Vakar būtu teicis JĀ, bet šodien izskatās, ka tomēr teikšu NĒ!',
                                'A kapēc tāds jautājums?', 'Nesapratu tavu ideju, pajautā vēlreiz',
                                'BEIDZ MURMINĀT! Runā skaļāk!', ':regional_indicator_j: :regional_indicator_a: ',
                                ':regional_indicator_n: :regional_indicator_e: ']
                    await message.reply(response[random.randint(0, len(response))])

    @slash_command(description="Met kauliņu!")
    async def kaulini(self, ctx):
        dice = ['https://i.imgur.com/BSAhtaC.png',
                'https://i.imgur.com/Jgfe6Xd.png',
                'https://i.imgur.com/uKwMeLQ.png',
                'https://i.imgur.com/f7p8Kro.png',
                'https://i.imgur.com/8Gvlz1m.png',
                'https://i.imgur.com/1KRNZhp.png']

        rng = random.randint(0, 5)
        embed = discord.Embed(color=0xffff00)
        embed.set_author(name=f'Cipariņš {rng+1}', icon_url=dice[rng])
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(Commands(bot))
