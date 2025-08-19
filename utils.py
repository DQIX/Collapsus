import io
import math
import os

import discord
import requests
from PIL import Image
from discord.ext.pages import Paginator, Page

dev_tag = "@CompuGeniusCode"
dev_patreon = "patreon.com/compugeniusprograms"
dev_patreon = "cash.app/$compugeniuscode"


def create_embed(title, description=None, color=discord.Color.green(),
                 footer="Consider supporting development:\n%s\n%s" % (dev_patreon, dev_cashapp),
                 error="Any errors? Please report to %s" % dev_tag, image="", *, url="", author=""):
    embed = discord.Embed(title=title, description=description, url=url, color=color)
    embed.set_footer(text="%s\n%s" % (footer, error))
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
