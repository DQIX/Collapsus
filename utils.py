import contextvars
import io
import math
import os
import random

import discord
import requests
from PIL import Image
from discord.ext.pages import Paginator, Page

dev_tag = "@zevya"
dev_patreon = "https://patreon.com/zevya"
dev_cashapp = "https://cash.app/$zevya"

contributor_role_id = 1241808955580219453
contributor_footer = "Thank you for supporting development!"
contributor_perks_footer = "Contributor perks work in The Quester's Rest."

footer_tips = [
    "Tip: /gs searches with abbreviations, like G for Granite.",
    "Tip: /grotto_seed finds a grotto from the seed and rank on its map.",
    "Tip: /grotto_location shows directions to any grotto location code.",
    "Tip: Add a level to /grotto_translate to search for the grotto too.",
    "Tip: /recipe_cascade breaks a recipe down to its base ingredients.",
    "Tip: /monster takes a name or a monster list number.",
    "Tip: /character rolls a random look for a new run.",
    "Collapsus stays online thanks to contributors. See /support.",
    "Contributors can save grottos from search results. See /support.",
]

invoker_is_contributor = contextvars.ContextVar("invoker_is_contributor", default=False)


def is_contributor(user):
    return isinstance(user, discord.Member) and user.get_role(contributor_role_id) is not None


def default_footer():
    return contributor_footer if invoker_is_contributor.get() else random.choice(footer_tips)


def command_mention(bot, name):
    command = bot.get_application_command(name)
    if command is None or (command.parent or command).id is None:
        return f"`/{name}`"
    return command.mention


def contributor_link_view():
    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Become a Contributor", url=dev_patreon))
    return view


def contributor_pitch(bot, title, footer=contributor_perks_footer):
    description = (f"Contributors can save any grotto from search results and pull it back up anytime with "
                   f"{command_mention(bot, 'my_grottos')}. Collapsus runs on contributor support, so becoming one "
                   f"also keeps the bot online. More in {command_mention(bot, 'support')}.")
    return create_embed(title, description=description, footer=footer)


def create_embed(title, description=None, color=discord.Color.green(), footer=None,
                 error="Any errors? Please report to %s" % dev_tag, image="", *, url="", author=""):
    embed = discord.Embed(title=title, description=description, url=url, color=color)
    embed.set_footer(text="%s\n%s" % (footer or default_footer(), error))
    if image != "":
        embed.set_image(url=image)
    embed.set_author(name=author)
    return embed


def create_collage(files, file_name):
    columns = math.ceil(math.sqrt(len(files)))
    rows = math.ceil(len(files) / columns)
    collage = Image.new("RGBA", (128 * columns, 96 * rows))
    index = 0
    for row in range(rows):
        for col in range(columns):
            if index < len(files):
                image = None
                if files[index].startswith("http"):
                    response = requests.get(files[index])
                    try:
                        image = Image.open(io.BytesIO(response.content))
                    except Exception as e:
                        print(f"{e} when trying to add {files[index]} to collage")
                else:
                    image = Image.open(files[index])
                collage.paste(image, (128 * col, 96 * row))
                index += 1

    if not os.path.exists("collages"):
        os.makedirs("collages")
    collage.save(file_name)


def create_paginator(embeds, files=None, views=None):
    pages = []
    for entry in embeds:
        if files is None:
            page = Page(embeds=[entry])
        else:
            fs = [file["file"] for file in files if file["id"] == embeds.index(entry)]
            file_name = "collages/collage%s.png" % embeds.index(entry)
            create_collage(fs, file_name)
            with open(file_name, 'rb') as fp:
                data = io.BytesIO(fp.read())
            file = discord.File(data, file_name.removeprefix("collages/"))
            entry.set_image(url="attachment://%s" % file_name.removeprefix("collages/"))
            page = Page(embeds=[entry], files=[file], custom_view=views[embeds.index(entry)] if views else None)
        pages.append(page)
    return Paginator(pages=pages)


def int_from_string(string):
    integer = ''.join(filter(str.isdigit, string))
    if integer != "":
        return int(integer)
    else:
        return ""


def clean_text(text, remove_spaces=True, url=False):
    text = text.lower().replace("'", "").replace("’", "").replace("ñ", "n").replace("ó", "o").replace(".", "")
    text = text.replace("-", "_") if url else text.replace("-", "")
    if remove_spaces:
        text = text.replace(" ", "")
    else:
        text = text.replace(" ", "_")

    return text
