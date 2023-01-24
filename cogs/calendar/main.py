import discord
import json
import os
import sqlite3
import datetime as date
from datetime import datetime, time
from PIL import (Image,
                 ImageDraw,
                 ImageFont)
from discord.ext import commands, tasks


class Calendar(commands.Cog):
    def __init__(self, bot):
        self.send_calendar_every_day.start()
        self.bot = bot
        self.con = sqlite3.connect('database/database.db')

    @tasks.loop(minutes=1)
    async def send_calendar_every_day(self):
        await self.bot.wait_until_ready()
        hour = date.datetime.today().hour
        minute = date.datetime.today().minute

        if time(hour, minute) == time(0, 0):
            day = date.datetime.today().day
            month = date.datetime.today().month
            name_of_day = date.datetime.today().strftime('%A')

            with open(r'cogs/calendar/resources/vardi.json', 'r') as kalendars:
                data = json.load(kalendars)
                names = ''

                for x in data[month - 1][str(day - 1)]:
                    names += x + ','

            with open(r'cogs/calendar/resources/svetki.json', 'r', encoding='utf8') as svetki:
                data = json.load(svetki)
                svetki = None
                try:
                    svetki = data[0][f'{day}/{month}']
                except KeyError:
                    pass

            for server in self.bot.guilds:
                c = self.con.cursor()
                c.execute(f'SELECT calendar_channel FROM guilds WHERE guild_id=?', (server.id,))
                resp = c.fetchall()[0][0]
                c.close()
                if resp == 'None':
                    continue
                channel = await self.bot.fetch_channel(resp)
                await generate_calendar(day, month, name_of_day, names, channel, svetki)


async def generate_calendar(day, month, name_of_day, names, ctx, svetki):
    arial = 'project/resources/fonts/arial.ttf'
    arialbd = 'project/resources/fonts/arialbd.ttf'

    font = ImageFont.truetype(arialbd, 160)
    font1 = ImageFont.truetype(arial, 20)
    font2 = ImageFont.truetype(arialbd, 20)
    font3 = ImageFont.truetype(arial, 15)

    monthName = str(get_month_name(month))
    dayName = get_day_name(name_of_day)

    img = Image.open('cogs/calendar/resources/base.png')

    draw = ImageDraw.Draw(img)

    color = "black"

    if svetki is not None:
        color = "red"

    w, h = font.getsize(str(day))
    draw.text(((261 - w) / 2, 70), str(day), font=font, fill=color)

    w1, h1 = font1.getsize(names[:-1])
    if w1 >= img.size[0] - 20:
        res = names[:-1].split(',', 1)
        h = 235
        for x in res:
            draw.text(((img.size[0] - font1.getsize(x)[0]) / 2, h), x, font=font1, fill="black")
            h += 20
    else:
        draw.text(((img.size[0] - w1) / 2, 235), names[:-1], font=font1, fill="black")

    w2, h2 = font2.getsize(monthName)
    draw.text(((261 - w2) / 2, 23), monthName, font=font2, fill="white")

    w3, h3 = font2.getsize(dayName)
    draw.text(((261 - w3) / 2, 304), dayName, font=font2, fill="white")

    if svetki is not None:
        w4, h4 = font3.getsize(str(svetki))
        draw.text(((img.size[0] - w4) / 2, 282), str(svetki), font=font3, fill="black")

    img.save('cogs/calendar/resources/uga.png')
    img.close()

    file = discord.File('cogs/calendar/resources/uga.png', filename='calendar.png')
    xmas_info = days_till_christmas()
    ligo_info = days_till_ligo()
    embed = discord.Embed(
        title=f'📅 {day}/{month}/{date.datetime.today().year}', description=f'🎄 **{xmas_info[0]}** {xmas_info[1]}'
                                                                           f' līdz ziemīšiem! 🎄\n 🌳 **{ligo_info[0]}**'
                                                                           f' {ligo_info[1]}'
                                                                           ' līdz līgo! 🔥', color=0xffffff)
    embed.set_image(url='attachment://calendar.png')
    await ctx.send(file=file, embed=embed)
    os.remove('cogs/calendar/resources/uga.png')


def get_month_name(x):
    switcher = {
        1: "Janvāris",
        2: "Februāris",
        3: "Marts",
        4: "Aprīlis",
        5: "Maijs",
        6: "Jūnijs",
        7: "Jūlijs",
        8: "Augusts",
        9: "Septembris",
        10: "Oktobris",
        11: "Novembris",
        12: "Decembris"
    }

    return switcher.get(x, "ERROR")


def get_day_name(x):
    switcher = {
        'Monday': "Pirmdiena",
        'Tuesday': "Otrdiena",
        'Wednesday': "Trešdiena",
        'Thursday': "Ceturtdiena",
        'Friday': "Piektdiena",
        'Saturday': "Sestdiena",
        'Sunday': "Svētdiena",
    }

    return switcher.get(x, "ERROR")


def days_till_christmas():
    xmas = datetime(datetime.today().year, 12, 25) - datetime.now()

    if xmas.days < 0:
        xmas = datetime(datetime.today().year + 1, 12, 25) - datetime.now()

    lst = list(map(int, str(xmas.days)))
    return xmas.days, 'diena' if (lst[len(lst) - 1] == 1) else 'dienas'


def days_till_ligo():
    xmas = datetime(datetime.today().year, 6, 23) - datetime.now()

    if xmas.days < 0:
        xmas = datetime(datetime.today().year + 1, 6, 23) - datetime.now()

    lst = list(map(int, str(xmas.days)))
    return xmas.days, "diena" if (lst[len(lst) - 1] == 1) else "dienas"


def setup(bot):
    bot.add_cog(Calendar(bot))
