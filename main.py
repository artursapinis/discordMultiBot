import configparser

from discord.ext import commands
import discord
import logging

config = configparser.ConfigParser()
config.read_file(open('settings.ini'))

client = commands.Bot(command_prefix=config['DEFAULT']['BotPrefix'])

logging.basicConfig(level=logging.INFO)

cog_extensions = (
    'cogs.eventsDatabase.main',
    'cogs.calendar.main',
    'cogs.commands.main',
    'cogs.TVtracker.main',
    'cogs.serverConfig.main',
)

cog_extensions_loaded = 0

logging.info('|-------------------- LOADING EXTENSIONS --------------------|')

started_extensions = []
failed_extensions = []

for extension in cog_extensions:
    try:
        client.load_extension(extension)
        logging.info(f'\t\t\tExtension [{extension}] status - STARTED')
        started_extensions.append(extension)
        cog_extensions_loaded += 1
    except Exception as e:
        logging.exception(e)
        logging.exception(f'\t\t\tExtension [{extension}] status - FAILED\n')
        failed_extensions.append(extension)

logging.info(
    f'|----------------- DONE [started {cog_extensions_loaded} out of {len(cog_extensions)}] -----------------|')


@client.event
async def on_ready():
    logging.info('on_ready event called successfully')
    await change_status()

    @client.event
    async def on_application_command_error(inter, error):
        if isinstance(error, commands.CommandOnCooldown):
            await inter.respond(f'Večuk, nevar tik bieži! Mēģini vēlreiz pēc {error.retry_after:.0f} sekundēm',
                                ephemeral=True)

        if isinstance(error, commands.MissingPermissions):
            await inter.respond(f'Izskatās, ka Tev šī komanda nav pieejama 🤫',
                                ephemeral=True)

    @client.event
    async def on_user_command_error(inter, error):
        if isinstance(error, commands.CommandOnCooldown):
            await inter.respond(f'Večuk, nevar tik bieži! Mēģini vēlreiz pēc {error.retry_after:.0f} sekundēm',
                                ephemeral=True)


async def change_status():
    try:
        await client.change_presence(status=discord.Status.online,
                                     activity=discord.Game(name='Datortārps 🤓'))
    except Exception as ex:
        logging.info(ex)

client.run(config['DEFAULT']['BotToken'])
