import json
import os
import random

import discord
import dotenv
from discord import Option
from titlecase import titlecase

import grotto_db
import parsers
from utils import create_embed, clean_text, dev_tag

dotenv.load_dotenv()
token = os.getenv("TOKEN")

bot = discord.Bot(intents=discord.Intents.all())

dev_id = 496392770374860811

guild_id = 655390550698098700

testing_channel = 973619817317797919
grotto_bot_commands_channel = 845339551173050389

logo_url = "https://cdn.discordapp.com/emojis/856330729528361000.png"
website_url = "https://dq9.carrd.co"

server_invite_url = "https://discord.gg/"
server_invite_code = ""

character_image_url = "https://www.woodus.com/den/games/dq9ds/characreate/index.php?"


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

    with open("config.json", "r", encoding="utf-8") as fp:
        data = json.load(fp)
        global server_invite_code
        server_invite_code = data["server_invite_code"]

    for command in bot.commands:
        print(f"{command.name} | {command.id}")

    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="over The Quester's Rest. Type /help ."))


@bot.command(name="help", description="Get help for using the bot.")
async def _help(ctx):
    description = f'''
A bot created by <@{dev_id}> for The Quester's Rest (<{server_invite_url + server_invite_code}>).

</character:984820203483459635> - *Generate a random character*
</gg:1038001809660334122> - *Get grotto info (location required) - <#{grotto_bot_commands_channel}> only*
</grotto:1038001809660334121> - *Search for a grotto - <#{grotto_bot_commands_channel}> only*
</monster:980895182859935765> - *Get monster info*
</quest:977175507558875167> - *Get quest info*
</recipe:977175507558875168> - *Get an item's recipe*
</recipe_cascade:1236865730683863070> - *Get cascading info about a recipe*
</song:1132033677585563799> - *Play a song*
</songs_all:1132513511570935809>- *Play all songs*
</stop:1132497509353267275> - *Stop playing songs*
</translate:1038483499121913956> - *Translate a word or phrase*
</quote:1258579663354335302> - *Get a quote*
</grotto_location:1241043446882500681> - *Get grotto location info - <#{grotto_bot_commands_channel}> only*
/grotto_translate [language] - *Translate a grotto - <#{grotto_bot_commands_channel}> only*

</help:977004400352583690> - *Displays this message*
'''

    if ctx.guild_id != guild_id:
        description = description.replace(f" - <#{grotto_bot_commands_channel}> only", "")

    embed = create_embed("Collapsus Help [Click For Server Website]", description=description, error="", image=logo_url,
                         url=website_url)
    await ctx.respond(embed=embed)


@bot.command(name="quest", description="Sends info about a quest.")
async def _quest(ctx, quest_number: Option(int, "Quest Number (1-184)", required=True)):
    with open("data/quests.json", "r", encoding="utf-8") as fp:
        data = json.load(fp)

    quests = data["quests"]
    index = quest_number - 1
    if index >= len(quests) or index < 0:
        embed = create_embed("No quest found with the number `%s`. Please check number and try again." % quest_number)
        return await ctx.respond(embed=embed)

    quest = parsers.Quest.from_dict(quests[index])

    title = ":star: Quest #%i - %s :star:" % (quest.number, quest.name) if quest.story else "Quest #%i - %s" % (
        quest.number, quest.name)
    color = discord.Color.gold() if quest.story else discord.Color.green()
    embed = create_embed(title, color=color)
    if quest.location != "":
        embed.add_field(name="Location", value=quest.location, inline=False)
    if quest.request != "":
        embed.add_field(name="Request", value=quest.request, inline=False)
    if quest.solution != "":
        embed.add_field(name="Solution", value="||%s||" % quest.solution, inline=False)
    if quest.reward != "":
        reward = quest.reward
        if quest.story:
            reward = "||%s||" % reward
        embed.add_field(name="Reward", value=reward, inline=False)
    embed.add_field(name="Repeat", value="Yes" if quest.repeat else "No", inline=False)
    embed.add_field(name="Prerequisites", value=quest.prerequisite, inline=False)

    await ctx.respond(embed=embed)


@bot.command(name="translate", description="Translate a word or phrase to a different language.")
async def _translate(ctx, phrase: Option(str, "Word or Phrase (Ex. Copper Sword)", required=True),
                     language_input: Option(str, "Input Language (Ex. English)", choices=parsers.translation_languages,
                                            required=True),
                     language_output: Option(str, "Output Language (Ex. Japanese)",
                                             choices=parsers.translation_languages, required=False)):
    data = {"translations": []}

    for file in os.listdir("data/translations"):
        if file == "grotto.json":
            continue
        with open("data/translations/" + file, "r", encoding="utf-8") as fp:
            data["translations"] += json.load(fp)["translations"]

    translations = data["translations"]

    index = next(filter(lambda t: clean_text(
        t.get(parsers.translation_languages_simple[parsers.translation_languages.index(language_input)],
              "").lower()) == clean_text(phrase.lower()), translations), None)
    if index is None:
        index = next(
            filter(lambda t: clean_text(t.get("alias", "").lower()) == clean_text(phrase.lower()), translations), None)

    if index is None:
        embed = create_embed("No word or phrase found matching `%s`. Please check phrase and try again." % phrase,
                             error="Any errors? Want to contribute data? Please speak to %s" % dev_tag)
        return await ctx.respond(embed=embed)

    translation = parsers.Translation.from_dict(index)
    all_languages = [translation.english, translation.japanese, translation.spanish, translation.french,
                     translation.german, translation.italian]

    title = "Translation of: %s" % titlecase(all_languages[parsers.translation_languages.index(language_input)])
    color = discord.Color.green()
    embed = create_embed(title, color=color, error="Any errors? Want to contribute data? Please speak to %s" % dev_tag)
    if language_output is not None:
        value = titlecase(all_languages[parsers.translation_languages.index(language_output)])
        if value != "":
            embed.add_field(name=language_output, value=value, inline=False)
        else:
            embed = create_embed("The word or phrase `%s` has not been translated to `%s`." % (phrase, language_output),
                                 error="Any errors? Want to contribute data? Please speak to %s" % dev_tag)
            return await ctx.respond(embed=embed)
    else:
        for language, translation in zip(parsers.translation_languages, all_languages):
            if translation != "":
                embed.add_field(name=language, value=titlecase(translation), inline=False)

    await ctx.respond(embed=embed)


@bot.command(name="character", description="Sends info for a randomly-generated character.")
async def _character(ctx):
    gender = random.choice(["Male", "Female"])
    body_type = random.randint(1, 5)
    hair_style = random.randint(1, 10)
    hair_color = random.randint(1, 10)
    face_style = random.randint(1, 10)
    skin_tone = random.randint(1, 8)
    eye_color = random.randint(1, 8)

    keys = {"headcolor": skin_tone, "hairnum": hair_style, "haircolor": hair_color, "eyecolor": eye_color, }

    remapped_eyes_female = {1: 1, 2: 2, 3: 3, 4: 12, 5: 13, 6: 14, 7: 15, 8: 16, 9: 17, 10: 20, }

    remapped_eyes_male = {1: 4, 2: 5, 3: 6, 4: 7, 5: 8, 6: 9, 7: 10, 8: 11, 9: 18, 10: 19, }

    if gender == "Male":
        keys["hairnum"] += 10
        keys["eyesnum"] = remapped_eyes_male[face_style]
    else:
        keys["eyesnum"] = remapped_eyes_female[face_style]

    description = '''
**Gender:** %s
    
**Body Type:** %s
    
**Hair Style:** %s
    
**Hair Color:** %s
    
**Face Style:** %s
    
**Skin Tone:** %s
    
**Eye Color:** %s
''' % (gender, body_type, hair_style, hair_color, face_style, skin_tone, eye_color)

    params = ""
    for key, value in keys.items():
        params += "%s=%s&" % (key, value)

    embed = create_embed("Random Character Generator", description, image=character_image_url + params[:-1])

    await ctx.respond(embed=embed)


grotto_db.create_table()
cogs = [f"cogs.{f[:-3]}" for f in os.listdir("cogs") if f.endswith(".py")]
for cog in cogs:
    bot.load_extension(cog)
bot.run(token)
