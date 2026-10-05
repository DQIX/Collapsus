import json
import os
import random
import unicodedata

import discord
import dotenv
from discord import Option
from titlecase import titlecase

import grotto_db
import parsers
from utils import create_embed, dev_tag, dev_patreon

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

translation_data_dir = "data/translations"


def _load_general_translations():
    translations = []

    for file in os.listdir(translation_data_dir):
        if not file.endswith(".json"):
            continue

        with open(os.path.join(translation_data_dir, file), "r", encoding="utf-8") as fp:
            translations.extend(json.load(fp)["translations"])

    return translations


def _build_translation_autocomplete_values(translations):
    values_by_language = {language: [] for language in parsers.translation_languages_simple}
    seen_by_language = {language: set() for language in parsers.translation_languages_simple}
    all_values = []
    all_seen = set()

    for translation in translations:
        for language in parsers.translation_languages_simple:
            value = translation.get(language, "")
            if value == "":
                continue

            if value not in seen_by_language[language]:
                values_by_language[language].append(value)
                seen_by_language[language].add(value)

            if value not in all_seen:
                all_values.append(value)
                all_seen.add(value)

        alias = translation.get("alias", "")
        if alias != "":
            if alias not in seen_by_language["english"]:
                values_by_language["english"].append(alias)
                seen_by_language["english"].add(alias)

            if alias not in all_seen:
                all_values.append(alias)
                all_seen.add(alias)

    return values_by_language, all_values


def _normalize_translation_language(language):
    if language is None:
        return None

    if language in parsers.translation_languages_simple:
        return language

    try:
        return parsers.translation_languages_simple[parsers.translation_languages.index(language)]
    except ValueError:
        return None


def _normalize_translation_text(text):
    if text is None:
        return ""

    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(
        char for char in normalized
        if not unicodedata.combining(char) and char not in {" ", "'", "’", ".", "-"}
    )


def _extract_leading_number(value):
    if value is None:
        return None

    candidate = str(value).split(" - ", 1)[0].strip().removeprefix("#")
    return int(candidate) if candidate.isdecimal() else None


async def get_translations(ctx: discord.AutocompleteContext):
    language_input = _normalize_translation_language((ctx.options or {}).get("language_input"))
    values = all_translation_values if language_input is None else translation_values_by_language[language_input]
    query = _normalize_translation_text(ctx.value or "")

    results = []
    for value in values:
        if query in _normalize_translation_text(value):
            results.append(value)
        if len(results) == 25:
            break

    return results


async def get_quests(ctx: discord.AutocompleteContext):
    with open("data/quests.json", "r", encoding="utf-8") as fp:
        quests = json.load(fp)["quests"]

    query = _normalize_translation_text(ctx.value or "")
    results = []

    for quest in quests:
        quest_number = str(quest["number"])
        quest_name = quest["name"]
        label = f"{quest_number} - {quest_name}"
        if query in _normalize_translation_text(quest_number) or query in _normalize_translation_text(quest_name):
            results.append(label)
        if len(results) == 25:
            break

    return results


general_translations = _load_general_translations()
translation_values_by_language, all_translation_values = _build_translation_autocomplete_values(general_translations)


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

    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="over The Quester's Rest. Type /help ."))


grotto_commands = {
    "grotto": "Search for a grotto",
    "gg": "Search for a grotto at a known location",
    "grotto_seed": "Look up a grotto by seed and rank",
    "grotto_location": "Directions to a grotto location",
}

help_sections = {
    "Game Info": {
        "monster": "Monster stats, drops and haunts",
        "quest": "Quest request, solution and reward",
        "recipe": "Alchemy recipe for an item",
        "recipe_cascade": "Every ingredient a recipe needs, all the way down",
        "translate": "Translate a word or phrase",
    },
    "Music": {
        "song": "Play a song in your voice channel",
        "songs_all": "Play every song",
        "skip": "Skip to the next song during `/songs_all`",
        "stop": "Stop playing",
    },
    "Utilities": {
        "character": "Roll a character for a random run",
        "quote": "Send a saved answer to a frequently asked question",
    },
}

contributor_commands = {
    "my_grottos": "Browse your saved grottos",
    "get_grotto": "Show a saved grotto",
    "update_grotto": "Change a saved grotto's notes",
    "delete_grotto": "Delete a saved grotto",
}


def _command_mention(name):
    command = bot.get_application_command(name)
    if command is None or (command.parent or command).id is None:
        return f"`/{name}`"
    return command.mention


def _command_lines(commands):
    return "\n".join(f"{_command_mention(name)} — {summary}" for name, summary in commands.items())


@bot.command(name="help", description="Get help for using the bot.")
async def _help(ctx):
    description = f"Dragon Quest IX helper for The Quester's Rest, made by <@{dev_id}>."
    if ctx.guild_id == guild_id:
        description += f"\nGrotto commands only work in <#{grotto_bot_commands_channel}>."

    embed = create_embed("Collapsus Help", description=description)
    embed.set_thumbnail(url=logo_url)

    translate_mentions = " ".join(
        _command_mention(f"grotto_translate {language}") for language in parsers.translation_languages_simple
    )
    embed.add_field(name="Grottos", value=_command_lines(grotto_commands), inline=False)
    embed.add_field(name="Grotto Translation",
                    value=f"Translate a grotto name. Add a level to search for it too.\n{translate_mentions}",
                    inline=False)
    for title, commands in help_sections.items():
        embed.add_field(name=title, value=_command_lines(commands), inline=False)
    embed.add_field(name="Contributors",
                    value=f"Become a contributor on [Patreon]({dev_patreon}) to save grottos with the "
                          f"**Save Grotto** button on search results.\n{_command_lines(contributor_commands)}",
                    inline=False)

    links = discord.ui.View(timeout=None)
    links.add_item(discord.ui.Button(label="Website", url=website_url))
    links.add_item(discord.ui.Button(label="Join The Quester's Rest", url=server_invite_url + server_invite_code))
    links.add_item(discord.ui.Button(label="Support on Patreon", url=dev_patreon))

    await ctx.respond(embed=embed, view=links)


@bot.command(name="quest", description="Sends info about a quest.")
async def _quest(ctx, quest_number: Option(str, "Quest Number (1-184)", autocomplete=get_quests, required=True)):
    with open("data/quests.json", "r", encoding="utf-8") as fp:
        data = json.load(fp)

    quests = data["quests"]
    quest_number_value = _extract_leading_number(quest_number)
    if quest_number_value is None:
        embed = create_embed("No quest found with the number `%s`. Please check number and try again." % quest_number)
        return await ctx.respond(embed=embed)

    index = quest_number_value - 1
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
async def _translate(ctx,
                     language_input: Option(str, "Input Language (Ex. English)", choices=parsers.translation_languages,
                                            required=True),
                     phrase: Option(str, "Word or Phrase (Ex. Copper Sword)", autocomplete=get_translations,
                                    required=True),
                     language_output: Option(str, "Output Language (Ex. Japanese)",
                                             choices=parsers.translation_languages, required=False)):
    language_input_simple = _normalize_translation_language(language_input)
    language_output_simple = _normalize_translation_language(language_output)
    normalized_phrase = _normalize_translation_text(phrase)

    index = next(
        filter(lambda t: _normalize_translation_text(t.get(language_input_simple, "")) == normalized_phrase,
               general_translations),
        None
    )
    if index is None and language_input_simple == "english":
        index = next(
            filter(lambda t: _normalize_translation_text(t.get("alias", "")) == normalized_phrase, general_translations),
            None
        )

    if index is None:
        embed = create_embed("No word or phrase found matching `%s`. Please check phrase and try again." % phrase,
                             error="Any errors? Want to contribute data? Please speak to %s" % dev_tag)
        return await ctx.respond(embed=embed)

    translation = parsers.Translation.from_dict(index)
    all_languages = [translation.english, translation.japanese, translation.spanish, translation.french,
                     translation.german, translation.italian]

    title = "Translation of: %s" % titlecase(
        all_languages[parsers.translation_languages_simple.index(language_input_simple)]
    )
    color = discord.Color.green()
    embed = create_embed(title, color=color, error="Any errors? Want to contribute data? Please speak to %s" % dev_tag)
    if language_output is not None:
        value = titlecase(all_languages[parsers.translation_languages_simple.index(language_output_simple)])
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
