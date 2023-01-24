import logging
import sqlite3

from discord.ext import commands


class Events(commands.Cog):
    def __init__(self, bot):
        # logging.info('\t\t\tRadio [EVENTS] started!')
        self.bot = bot
        self.con = sqlite3.connect('database/database.db')
        c = self.con.cursor()
        c.execute(
            '''CREATE TABLE IF NOT EXISTS guilds (id INTEGER PRIMARY KEY AUTOINCREMENT, 
            guild_id INTEGER, tv_episodes_channel STRING, calendar_channel STRING,
             tv_episodes STRING, tv_notification_role STRING)''')
        c.close()

    @commands.Cog.listener()
    async def on_ready(self):
        for x in self.bot.guilds:
            c = self.con.cursor()
            r = c.execute(f'SELECT EXISTS(SELECT 1 FROM guilds WHERE guild_id=?)', (x.id,))
            f = r.fetchone()[0]
            c.close()
            if f == 1:
                continue

            c = self.con.cursor()
            params = (x.id, 'None', 'None', '[]', 'None')
            c.execute(f'INSERT INTO guilds (guild_id, tv_episodes_channel, calendar_channel,'
                      f' tv_episodes, tv_notification_role) '
                      f'VALUES(?, ?, ?, ?, ?)', params)
            self.con.commit()
            c.close()

        logging.info('cogs.eventsDatabase.main load_servers [VISI SERVERI IELADETI]')

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        c = self.con.cursor()
        r = c.execute(f'SELECT EXISTS(SELECT 1 FROM guilds WHERE guild_id=?)', (guild.id,))
        f = r.fetchone()[0]
        c.close()
        if f == 1:
            return

        c = self.con.cursor()
        params = (guild.id, 'None', 'None', '[]', 'None')
        c.execute(
            f'INSERT INTO guilds (guild_id, tv_episodes_channel, calendar_channel, tv_episodes, tv_notification_role) '
            f'VALUES(?, ?, ?, ?, ?)', params)
        self.con.commit()
        c.close()


def setup(bot):
    bot.add_cog(Events(bot))
