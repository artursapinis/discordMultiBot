import configparser
import logging
import sqlite3
import discord
from discord import guild_only
from discord.ext import commands
from discord.commands import slash_command


class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.con = sqlite3.connect('database/database.db')
        config = configparser.ConfigParser()
        config.read_file(open('settings.ini'))
        self.cfg = config

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info('cogs.serverConfig.main ON_READY')

    @slash_command(description='Serveriņa bota konfigurācija 🤓')
    @commands.has_permissions(administrator=True)
    @guild_only()
    async def konfiguracija(self, ctx):
        view = ConfigView(self.bot)
        await ctx.respond(f'Botiņa konfigurācija priekš **"{ctx.guild.name}"** servera! 🔧', view=view,
                          ephemeral=True)


class ConfigSelect(discord.ui.Select):
    def __init__(self, bot_: discord.Bot):
        self.bot = bot_
        self.con = sqlite3.connect('database/database.db')

        options = [
            discord.SelectOption(
                label='Kalendārs', description='Uzstādīt kalendāra kanālu.', emoji='🗓️', value='0'
            ),
            discord.SelectOption(
                label='Seriāli', description='Uzstādīt seriālu paziņojumu kanālu', emoji='📺', value='1'
            ),
            discord.SelectOption(
                label='Paziņojumu role', description='Uzstādīt paziņojumu role, lai saņemtu paziņojumus par jaunajiem '
                                                     'seriāliem', emoji='📍', value='2'
            ),
            discord.SelectOption(
                label='Uzstādījumi', description='Apskatīt uzstādītos kanālus un roles', emoji='🔧', value='3'
            ),
            discord.SelectOption(
                label='Noņemt kanālu/role', description='Noņemt esošo role/kanālu no uzstādījumiem',
                emoji='❌', value='4'
            ),
        ]

        super().__init__(
            placeholder='Uzstādījumi!',
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        chanView = ChannelView(self.bot, int(self.values[0]), interaction.guild.id)

        match int(self.values[0]):
            case 0:
                configType = '**kalendāra** kanālu'
            case 1:
                configType = '**seriāliņa** paziņojumu kanālu'
            case 2:
                configType = '**role**, lai saņemtu paziņojumus par seriāliņiem'
            case 3:
                c = self.con.cursor()
                c.execute(f'SELECT * FROM guilds WHERE guild_id=?', (interaction.guild.id,))
                resp = c.fetchall()[0]
                c.close()

                tv_channel = '**Nav uzstādīts**'
                calendar_channel = '**Nav uzstādīts**'
                tv_notification_role = '**Nav uzstādīts**'

                if resp[2] != 'None':
                    try:
                        channel = await self.bot.fetch_channel(int(resp[2]))
                        tv_channel = f'<#{channel.id}>'
                    except (discord.InvalidData, discord.HTTPException, discord.NotFound, discord.Forbidden):
                        pass

                if resp[3] != 'None':
                    try:
                        channel = await self.bot.fetch_channel(int(resp[3]))
                        calendar_channel = f'<#{channel.id}>'
                    except (discord.InvalidData, discord.HTTPException, discord.NotFound, discord.Forbidden):
                        pass

                if resp[5] != 'None':
                    try:
                        guild = await self.bot.fetch_guild(int(resp[1]))
                        role = guild.get_role(int(resp[5]))
                        tv_notification_role = f'<@&{role.id}>'
                    except (discord.InvalidData, discord.HTTPException, discord.NotFound, discord.Forbidden):
                        pass

                embed = discord.Embed(title=f'{interaction.guild.name} konfigurācija!', color=0xffff00)
                embed.add_field(name='🗓️ Kalendāra kanāliņš:', value=calendar_channel, inline=False)
                embed.add_field(name='📺 Seriālu paziņojumu kanāliņš:', value=tv_channel, inline=False)
                embed.add_field(name='📍 Seriālu paziņojumu role:', value=tv_notification_role, inline=False)
                return await interaction.response.edit_message(embed=embed, content=None, view=None)
            case 4:
                c = self.con.cursor()
                c.execute(f'SELECT * FROM guilds WHERE guild_id=?', (interaction.guild.id,))
                resp = c.fetchall()[0]
                c.close()

                if resp[2] == 'None' and resp[3] == 'None' and resp[5] == 'None':
                    return await interaction.response.edit_message(
                        content=f':warning: Neesi jau neko pievienojis, lai kaut ko noņemtu!',
                        view=None, embed=None)

                return await interaction.response.edit_message(content=f'❌ Kapēc ir jāņem nost, ja var palikt kā ir?!',
                                                               view=chanView, embed=None)
            case _:
                return await interaction.response.edit_message(content='Kaut kas nogāja greizi. Mēģini vēlreiz! :(',
                                                               view=None, embed=None)

        await interaction.response.edit_message(content=f'🔧 Uzstādi {configType}!', view=chanView, embed=None)


class ConfigView(discord.ui.View):
    def __init__(self, bot_: discord.Bot):
        self.bot = bot_
        super().__init__()

        self.add_item(ConfigSelect(self.bot))


class ChannelDropdown(discord.ui.Select):
    def __init__(self, bot_: discord.Bot, selection, guildID):
        self.bot = bot_
        self.selection = selection
        self.guildID = guildID
        self.con = sqlite3.connect('database/database.db')

        typeSelect = None
        chanType = None
        placeholder = ''
        options = None
        if selection == 0 or selection == 1:
            typeSelect = discord.ComponentType.channel_select
            chanType = [discord.ChannelType.text]
            placeholder = 'Izvēlies kanālu!'

        if selection == 2:
            typeSelect = discord.ComponentType.role_select
            placeholder = 'Izvēlies role!'
            chanType = None

        if selection == 4:
            placeholder = 'Ko vēlies noņemt?!'
            typeSelect = discord.ComponentType.string_select
            chanType = None

            c = self.con.cursor()
            c.execute(f'SELECT * FROM guilds WHERE guild_id=?', (self.guildID,))
            resp = c.fetchall()[0]
            c.close()
            options = []

            if resp[2] != 'None':
                options.append(discord.SelectOption(
                    label='Noņemt seriāliņu kanālu!',
                    description='Noņemot seriāliņu kanālu,'
                                ' serverītis nesaņems paziņojumus par pievienotajiem seriāliem 😢',
                    value='rm_show'))

            if resp[3] != 'None':
                options.append(discord.SelectOption(
                    label='Noņemt kalendāra kanālu!',
                    description='Noņemot kalendāra kanālu, serverītim nesūtīsies kalendārs 😢', value='rm_cal'))

            if resp[5] != 'None':
                options.append(discord.SelectOption(
                    label='Noņemt seriāliņu paziņojumu role!',
                    description='Noņemot seriāliņu paziņojumu role 😢',
                    value='rm_role'))

        super().__init__(
            select_type=typeSelect,
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            channel_types=chanType,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == 'rm_cal' or self.values[0] == 'rm_show' or self.values[0] == 'rm_role':
            match self.values[0]:
                case 'rm_cal':
                    configType = '🔧 Tu veiksmīgi noņēmi **kalendāra** kanālu!'
                    col = 'calendar_channel'
                case 'rm_show':
                    configType = '🔧 Tu veiksmīgi noņēmi **seriāliņu** kanālu'
                    col = 'tv_episodes_channel'
                case 'rm_role':
                    configType = '🔧 Tu veiksmīgi noņēmi **paziņojumu role**'
                    col = 'tv_notification_role'
                case _:
                    configType = ':warning: kaut kas nogāja greizi :('
                    col = 'ERROR'

            update = f"UPDATE guilds SET {col} = '{'None'}' WHERE guild_id = {self.guildID}"
            c = self.con.cursor()
            c.execute(update)
            self.con.commit()
            c.close()

            return await interaction.response.edit_message(
                content=configType, view=None, embed=None)

        idGet = self.values[0].id
        match int(self.selection):
            case 0:
                configType = '**kalendāra** kanālu'
                col = 'calendar_channel'
                mention = f'<#{idGet}>'
            case 1:
                configType = '**seriāliņu** kanālu'
                col = 'tv_episodes_channel'
                mention = f'<#{idGet}>'
            case 2:
                configType = '**paziņojumu role**'
                col = 'tv_notification_role'
                mention = f'<@&{idGet}>'
            case _:
                return await interaction.response.edit_message(content='Kaut kas nogāja greizi. Mēģini vēlreiz! :(',
                                                               view=None, embed=None)

        update = f"UPDATE guilds SET {col} = '{idGet}' WHERE guild_id = {self.guildID}"
        c = self.con.cursor()
        c.execute(update)
        self.con.commit()
        c.close()

        await interaction.response.edit_message(
            content=f'🔧 Tu veiksmīgi uzstādīji **{configType}** uz {mention} ', view=None, embed=None)


class ChannelView(discord.ui.View):
    def __init__(self, bot_: discord.Bot, selection, guildID):
        self.bot = bot_
        self.selection = selection
        self.guildID = guildID
        super().__init__()

        self.add_item(ChannelDropdown(self.bot, self.selection, self.guildID))


def setup(bot):
    bot.add_cog(Config(bot))
