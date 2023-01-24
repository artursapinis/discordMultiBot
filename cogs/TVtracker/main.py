import configparser
import datetime as date
import json
import logging
import sqlite3
from datetime import datetime, time

import aiohttp
import discord
import trakt
from discord import guild_only
from discord.commands import (
    slash_command,
)
from discord.ext import commands, tasks, pages
from trakt import tv, errors


class Tracker(commands.Cog):
    def __init__(self, bot):
        config = configparser.ConfigParser()
        config.read_file(open('settings.ini'))

        self.bot = bot
        self.con = sqlite3.connect('database/database.db')
        self.tvshows.start()
        self.tmdbKey = config['TVSHOWS']['TMDBkey']

        trakt.core.CLIENT_ID = config['TVSHOWS']['traktCLIENTID']
        trakt.core.CLIENT_SECRET = config['TVSHOWS']['traktCLIENTSECRET']

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info('cogs.TVtracker.main ON_READY')

    @tasks.loop(minutes=1)
    async def tvshows(self):
        await self.bot.wait_until_ready()
        hour = date.datetime.today().hour
        minute = date.datetime.today().minute

        if time(hour, minute) == time(12, 39):
            for server in self.bot.guilds:
                c = self.con.cursor()
                c.execute(f"SELECT * FROM guilds WHERE guild_id=?", (server.id,))
                resp = c.fetchall()[0]
                c.close()

                if resp[2] == 'None':
                    continue

                show_list = json.loads(resp[4])
                for show in show_list:
                    trakt_show = trakt.tv.TVShow(slug=show)
                    background_pic = None
                    rating = None
                    try:
                        next_episode_date_object = datetime.strptime(str(trakt_show.next_episode.first_aired_date),
                                                                     '%Y-%m-%d %H:%M:%S')
                    except Exception as ex:
                        logging.warning(ex)
                        continue

                    notification_date = next_episode_date_object.date()

                    date_now = datetime.now().replace(second=0, microsecond=0)

                    next_episode = trakt_show.next_episode.title
                    if not date_now.date() == notification_date:
                        continue

                    next_episode_date_object = datetime.strptime(str(trakt_show.next_episode.first_aired_date),
                                                                 '%Y-%m-%d %H:%M:%S')
                    next_episode_date = f'{next_episode_date_object.day}/' \
                                        f'{next_episode_date_object.month}/{next_episode_date_object.year} '

                    async with aiohttp.ClientSession() as cs:
                        async with cs.get(
                                f'https://api.themoviedb.org/3/find/{trakt_show.imdb}?api_key={self.tmdbKey}'
                                f'&external_source'
                                f'=imdb_id') as r:
                            show_response = await r.json()

                    if show_response['tv_results'][0]['backdrop_path'] != 'None':
                        background_pic = 'https://image.tmdb.org/t/p/w780' + \
                                         show_response['tv_results'][0]['backdrop_path']

                    try:
                        rating = round(float(trakt_show.ratings['rating']), 1)
                    except Exception as ex:
                        logging.exception(ex)
                        pass

                    tagRole = ''

                    if resp[5] != 'None':
                        tagRole = f'<@&{resp[5]}>\n'

                    embed = discord.Embed(title=trakt_show.title,
                                          description=f'Reitings: **{rating}**',
                                          url=f'https://www.imdb.com/title/{trakt_show.imdb}/')
                    if background_pic is not None:
                        embed.set_image(url=background_pic)

                    embed.add_field(name=f'Nākamā episode:', value=f'**{next_episode}({str(next_episode_date)})**',
                                    inline=False)
                    embed.add_field(name='Apraksts:', value=trakt_show.next_episode.overview, inline=False)

                    channel = await self.bot.fetch_channel(resp[2])
                    if tagRole != '':
                        await channel.send(f'{tagRole}')
                    await channel.send(embed=embed)

    @slash_command(description='Serveriņa seriāliņu izvēlne 📺')
    # @commands.has_permissions(administrator=True)
    @guild_only()
    async def seriali(self, ctx):
        c = self.con.cursor()
        c.execute(f'SELECT * FROM guilds WHERE guild_id=?', (ctx.guild.id,))
        resp = c.fetchall()[0]
        c.close()

        roleActive = False
        roleSetup = False
        admin = False

        if resp[2] == 'None':
            return await ctx.respond(':warning: Sākumā pievieno seriālu paziņojumu kanālu! (**/konfiguracija**)')

        if resp[5] != 'None':
            roleSetup = True

        if resp[5] in [y.id for y in ctx.author.roles]:
            roleActive = True

        if ctx.author.guild_permissions.administrator:
            admin = True

        view = ShowView(self.bot, self.tmdbKey, roleActive, admin, roleSetup)
        await ctx.respond(f'Seriāliņu iestatījumi priekš **"{ctx.guild.name}"** servera! 📺', view=view,
                          ephemeral=True)


class ShowSelect(discord.ui.Select):
    def __init__(self, bot_: discord.Bot, tmdbKey, roleActive, admin, roleSetup):
        self.pages = None
        self.bot = bot_
        self.con = sqlite3.connect('database/database.db')
        self.tmdbKey = tmdbKey
        self.roleActive = roleActive
        self.admin = admin
        self.roleSetup = roleSetup

        options = []

        if self.admin:
            options.append(discord.SelectOption(
                label='Pievienot seriālu', description='Pievieno seriālu, lai saņemtu par to paziņojumus!', emoji='➕',
                value='0'
            ))
            options.append(discord.SelectOption(
                label='Noņemt seriālu', description='Laikam sūdīgs seriāls 🤔', emoji='➖', value='1'
            ))

        options.append(discord.SelectOption(
            label='Pievienotie seriāli', description='Apskatīt pievienotos seriālus', emoji='📺', value='2'
        ))

        if self.roleSetup:
            if roleActive:
                options.append(discord.SelectOption(
                    label='Noņemt paziņojumu role', description='Vairs nesaņemsi paziņojumus par seriāliņiem 😢',
                    emoji='❌',
                    value='4'
                ))
            else:
                options.append(discord.SelectOption(
                    label='Iegūt paziņojumu role', description='Tiksi ietagots, kad iznāks jauns seriāliņš 😊',
                    emoji='📍',
                    value='3'
                ))

        super().__init__(
            placeholder='Seriāliņu uzstādījumi!',
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        c = self.con.cursor()
        c.execute(f'SELECT * FROM guilds WHERE guild_id=?', (interaction.guild.id,))
        resp = c.fetchall()[0]
        c.close()
        try:
            show_list = json.loads(resp[4])
        except IndexError:
            show_list = []

        match int(self.values[0]):
            case 0:
                if len(show_list) >= 15:
                    return await interaction.response.edit_message(
                        content=':warning: Serverim jau ir pievienoti 15 seriāli! Tu esi sasniedzis limitu!',
                        view=None, embed=None)

                modal = TVModal(bot_=self.bot, title='Ievadi seriāliņa nosaukumu 📺')
                await interaction.response.send_modal(modal)
            case 1:
                if len(show_list) <= 0:
                    return await interaction.response.edit_message(
                        content=':warning: Neesi jau pievienojis nevienu seriāliņu. Nav jau ko noņemt, dunduk!',
                        view=None, embed=None)

                await interaction.response.edit_message(content='Noņemt seriālu',
                                                        view=TVView(self.bot, None, interaction.guild.id), embed=None)
            case 2:
                if len(show_list) <= 0:
                    return await interaction.response.edit_message(
                        content=':warning: Serverim nav pievienots neviens seriāliņš!',
                        view=None, embed=None)

                self.pages = []
                await interaction.response.edit_message(content='📺 Pievienotie seriāliņi', view=None, embed=None)
                for x in show_list:
                    show = trakt.tv.TVShow(slug=x)
                    background_pic = None
                    rating = None

                    async with aiohttp.ClientSession() as cs:
                        async with cs.get(
                                f'https://api.themoviedb.org/3/find/{show.imdb}?api_key={self.tmdbKey}'
                                f'&external_source'
                                f'=imdb_id') as r:
                            show_response = await r.json()

                    if show_response['tv_results'][0]['backdrop_path'] != 'None':
                        background_pic = 'https://image.tmdb.org/t/p/w780' + \
                                         show_response['tv_results'][0]['backdrop_path']

                    try:
                        rating = round(float(show.ratings['rating']), 1)
                    except Exception as ex:
                        logging.exception(ex)
                        pass

                    embed = discord.Embed(title=show.title,
                                          description=f'Reitings: **{rating}**',
                                          url=f'https://www.imdb.com/title/{show.imdb}/')
                    if background_pic is not None:
                        embed.set_image(url=background_pic)

                    embed.add_field(name='Apraksts:', value=show.overview, inline=False)
                    embed.add_field(name='Pēdējā epizode:', value=f'{show.last_episode.title} '
                                                                  f'[{show.last_episode.first_aired_date.date()}]',
                                    inline=False)

                    self.pages.append(embed)

                paginator = pages.Paginator(pages=self.pages)
                await paginator.respond(interaction, ephemeral=True)
            case 3:
                try:
                    c = self.con.cursor()
                    c.execute(f'SELECT * FROM guilds WHERE guild_id=?', (interaction.guild.id,))
                    role_id = c.fetchall()[0][5]
                    c.close()

                    role = discord.utils.get(interaction.message.author.guild.roles, id=role_id)
                    await interaction.user.add_roles(role)
                    await interaction.response.edit_message(
                        content='Tagad tu saņemsi paziņojumus par jaunākajiem seriāliņiem 😊', view=None, embed=None)
                except Exception as e:
                    logging.exception(e)
                    await interaction.response.edit_message(content='Hmmmm, kaut kas nav tā kā vajag.'
                                                                    ' Mēģini vēlreiz,'
                                                                    ' vai arī sazinies ar administratoru! 🤔',
                                                            view=None, embed=None)
            case 4:
                try:
                    c = self.con.cursor()
                    c.execute(f'SELECT * FROM guilds WHERE guild_id=?', (interaction.guild.id,))
                    role_id = c.fetchall()[0][5]
                    c.close()

                    role = discord.utils.get(interaction.message.author.guild.roles, id=role_id)
                    await interaction.user.remove_roles(role)
                    await interaction.response.edit_message(
                        content='Tagad tu vairs nesaņemsi paziņojumus par jaunākajiem seriāliem 😢', view=None,
                        embed=None)
                except (discord.Forbidden, discord.HTTPException) as e:
                    logging.exception(e)
                    await interaction.response.edit_message(content='Hmmmm, kaut kas nav tā kā vajag.'
                                                                    ' Mēģini vēlreiz,'
                                                                    ' vai arī sazinies ar administratoru! 🤔',
                                                            view=None, embed=None)
            case _:
                await interaction.response.edit_message(content='Hmmmm, kaut kas nav tā kā vajag.'
                                                                ' Mēģini vēlreiz,'
                                                                ' vai arī sazinies ar administratoru! 🤔',
                                                        view=None, embed=None)


class ShowView(discord.ui.View):
    def __init__(self, bot_: discord.Bot, tmdbKey, roleActive, admin, roleSetup):
        self.bot = bot_
        self.tmdbKey = tmdbKey
        self.roleActive = roleActive
        self.admin = admin
        self.roleSetup = roleSetup
        super().__init__()

        self.add_item(ShowSelect(self.bot, self.tmdbKey, self.roleActive, self.admin, self.roleSetup))


class TVDropdown(discord.ui.Select):
    def __init__(self, bot_: discord.Bot, selection, guildID):
        self.bot = bot_
        self.selection = selection
        self.con = sqlite3.connect('database/database.db')

        options = []
        match selection:
            case None:
                placeholder = 'Kurus seriāliņus noņemsi?'
                c = self.con.cursor()
                c.execute(f'SELECT * FROM guilds WHERE guild_id=?', (guildID,))
                resp = c.fetchall()[0]
                c.close()
                self.addedShows = json.loads(resp[4])

                max_value = len(self.addedShows)

                for x in self.addedShows:
                    show = trakt.tv.TVShow(slug=x)
                    options.append(discord.SelectOption(
                        label=f'{show.title} [{show.year}] Sezonas: {show.seasons[-1].season}',
                        description=f'https://www.imdb.com/title/{show.imdb}/',
                        value=show.slug))
            case _:
                placeholder = 'Kādu seriāliņu pievienosi?'
                max_value = 1
                trakt_show = trakt.tv.TVShow.search(selection)
                for index, show in zip(range(10), trakt_show):
                    options.append(discord.SelectOption(
                        label=f'{show.title} [{show.year}] Sezonas: {show.seasons[-1].season}',
                        description=f'https://www.imdb.com/title/{show.imdb}/',
                        value=show.slug))

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=max_value,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        match self.selection:
            case None:
                removed_shows = ''
                for x in self.values:
                    show = trakt.tv.TVShow(slug=x)
                    self.addedShows.remove(x)
                    removed_shows = removed_shows + show.title + ', '

                update = f"UPDATE guilds SET tv_episodes = ? WHERE guild_id = ?"
                c = self.con.cursor()
                c.execute(update, (str(self.addedShows).replace("'", '"'), interaction.guild.id))
                self.con.commit()
                c.close()

                await interaction.response.edit_message(
                    content=f'📺 Tu veiksmīgi noņēmi **{removed_shows[:-2]}** seriāliņu/s',
                    view=None, embed=None)
            case _:
                c = self.con.cursor()
                c.execute(f'SELECT * FROM guilds WHERE guild_id=?', (interaction.guild.id,))
                resp = c.fetchall()[0]
                c.close()
                try:
                    show_list = json.loads(resp[4])
                except IndexError:
                    show_list = []

                show_list.append(self.values[0])

                update = f"UPDATE guilds SET tv_episodes = ? WHERE guild_id = ?"
                c = self.con.cursor()
                c.execute(update, (str(show_list).replace("'", '"'), interaction.guild.id))
                self.con.commit()
                c.close()

                show = trakt.tv.TVShow(slug=self.values[0])
                await interaction.response.edit_message(
                    content=f'📺 **{show.title}** ir veiksmīgi pievienots. Priecīgu skatīšanos!',
                    view=None, embed=None)


class TVView(discord.ui.View):
    def __init__(self, bot_: discord.Bot, selection, guildID):
        self.bot = bot_
        self.selection = selection
        self.guildID = guildID
        super().__init__()

        self.add_item(TVDropdown(self.bot, self.selection, self.guildID))


class TVModal(discord.ui.Modal):
    def __init__(self, bot_, *args, **kwargs) -> None:
        self.bot = bot_
        super().__init__(*args, **kwargs)

        self.add_item(discord.ui.InputText(label='Ievadi seriāla nosaukumu'))

    async def callback(self, interaction: discord.Interaction):
        title = self.children[0].value
        try:
            trakt_show = trakt.tv.TVShow.search(title)
        except trakt.errors.NotFoundException:
            return await interaction.response.edit_message(
                content=f':warning: Nevarēju atrast seriālu ar nosaukumu {title}!',
                view=None, embed=None)

        if len(trakt_show) <= 0:
            return await interaction.response.edit_message(
                content=f':warning: Nevarēju atrast seriālu ar nosaukumu {title}!',
                view=None, embed=None)

        await interaction.response.edit_message(content=None, embed=None,
                                                view=TVView(self.bot, title, interaction.guild.id))


def setup(bot):
    bot.add_cog(Tracker(bot))
