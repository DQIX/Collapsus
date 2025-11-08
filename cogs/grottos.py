import io
import itertools
import json
import re

import aiohttp
import discord
from discord import Option
from discord.commands import SlashCommandGroup
from discord.ext import commands
from parsel import Selector
from titlecase import titlecase

import grotto_db
import parsers
from main import guild_id
from parsers import grotto_prefixes, grotto_environments, grotto_suffixes, translation_languages, is_special, \
    create_grotto, grotto_keys, grotto_chest_ranks, Translation, translation_languages_simple
from utils import create_embed, dev_tag, create_paginator, create_collage


def setup(bot):
    bot.add_cog(Grottos(bot))


class SaveGrottoModal(discord.ui.Modal):
    def __init__(self, grotto):
        super().__init__(title="Save Grotto")
        self.grotto = grotto

        self.add_item(
            discord.ui.InputText(style=discord.InputTextStyle.long, label="Grotto Notes", placeholder="Cool Grotto"))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.grotto.notes = self.children[0].value
        if grotto_db.confirm_unique_note(self.grotto.owner, self.grotto.notes):
            grotto_db.insert_grotto(self.grotto)
            await interaction.followup.send("Grotto saved successfully!", ephemeral=True)
        else:
            await interaction.followup.send("Grotto with the same notes already exists. Please enter a unique note.",
                                            ephemeral=True)
            return


class SaveGrottoView(discord.ui.View):
    def __init__(self, grotto):
        super().__init__()
        self.grotto = grotto

    @discord.ui.button(label="Save Grotto", style=discord.ButtonStyle.primary)
    async def button_callback(self, button, interaction):
        self.grotto.owner = interaction.user.id
        await interaction.response.send_modal(SaveGrottoModal(self.grotto))


class Grottos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.grotto_bot_channel = 845339551173050389
        self.grotto_search_url = "https://www.yabd.org/apps/dq9/grottosearch.php"
        self.grotto_details_url = "https://www.yabd.org/apps/dq9/grottodetails.php?map="
        self.admin_user = 496392770374860811
        self.contributor_role = 1241808955580219453

    grotto_translate = SlashCommandGroup("grotto_translate", "Grotto Translation Commands")

    @discord.slash_command(description="Search for a Grotto")
    async def grotto(self, ctx,
                     material: Option(str, "Material (Ex. Granite)", choices=grotto_prefixes["english"], required=True),
                     environment: Option(str, "Environment (Ex. Tunnel)", choices=grotto_environments["english"],
                                         required=True),
                     suffix: Option(str, "Suffix (Ex. of Woe)", choices=grotto_suffixes["english"], required=True),
                     level: Option(int, required=True), location: Option(str, required=False)):
        await self.grotto_command(ctx, material, environment, suffix, level, location)

    @discord.slash_command(description="Search for a Grotto (Location Required)")
    async def gg(self, ctx,
                 material: Option(str, "Material (Ex. Granite)", choices=grotto_prefixes["english"], required=True),
                 environment: Option(str, "Environment (Ex. Tunnel)", choices=grotto_environments["english"],
                                     required=True),
                 suffix: Option(str, "Suffix (Ex. of Woe)", choices=grotto_suffixes["english"], required=True),
                 level: Option(int, "Level (Ex. 1)", required=True),
                 location: Option(str, "Location (Ex. 05)", required=True)):
        await self.grotto_command(ctx, material, environment, suffix, level, location)

    @discord.slash_command(description="Search for a Grotto Using Abbreviations (Location Required)")
    async def gs(self, ctx, material: Option(str, "Material Abbreviation (Ex. G)", required=True),
                 environment: Option(str, "Environment Abbreviation (Ex. T)", required=True),
                 suffix: Option(str, "Suffix Abbreviation (Ex. of W)", required=True),
                 level: Option(int, "Level (Ex. 1)", required=True),
                 location: Option(str, "Location (Ex. 05)", required=True)):
        if not ctx.response.is_done():
            await ctx.defer()

        materials = [mat for mat in grotto_prefixes["english"] if mat.lower().startswith(material.lower())]
        environments = [env for env in grotto_environments["english"] if env.lower().startswith(environment.lower())]
        suffixes = [suff for suff in grotto_suffixes["english"] if
                    suff.lower().removeprefix('of ').startswith(suffix.lower())]

        all_embeds = []
        all_files = []
        all_grottos = []

        for mat in materials:
            for env in environments:
                for suff in suffixes:
                    embeds, files, grottos = await self.grotto_command(ctx, mat, env, suff, level, location,
                                                                       abbreviations=True)
                    if embeds is not None:
                        all_embeds.extend(embeds)
                        for file in files:
                            embed = embeds[files.index(file)]
                            file["id"] = all_embeds.index(embed)
                        all_files.extend(files)
                        all_grottos.extend(grottos)

        premium = ctx.author.get_role(self.contributor_role) is not None
        if len(all_embeds) > 1:
            if premium:
                views = [SaveGrottoView(grotto) for grotto in all_grottos]
                paginator = create_paginator(all_embeds, all_files, views)
            else:
                paginator = create_paginator(all_embeds, all_files)
            await paginator.respond(ctx.interaction)
        else:
            if len(all_embeds) == 1:
                embed = all_embeds[0]
                fs = [file["file"] for file in all_files if file["id"] == 0]
                file_name = "collages/collage0.png"
                create_collage(fs, file_name)
                with open(file_name, 'rb') as fp:
                    data = io.BytesIO(fp.read())
                file = discord.File(data, file_name.removeprefix("collages/"))
                embed.set_image(url="attachment://%s" % file_name.removeprefix("collages/"))
            else:
                embed = create_embed("No grotto found. Please check parameters and try again.")
                file = None

            if file is not None:
                if premium:
                    view = SaveGrottoView(all_grottos[0])
                    await ctx.followup.send(embed=embed, file=file, view=view)
                else:
                    await ctx.followup.send(embed=embed, file=file)
            else:
                if premium and len(all_grottos) > 0:
                    view = SaveGrottoView(all_grottos[0])
                    await ctx.followup.send(embed=embed, view=view)
                else:
                    await ctx.followup.send(embed=embed)

    @discord.slash_command(description="Browse saved personal grottos", guild_ids=[guild_id])
    async def my_grottos(self, ctx):
        if ctx.author.get_role(self.contributor_role) is None:
            embed = create_embed("You must be a contributor to use this command.")
            await ctx.respond(embed=embed)
            return
        grottos = grotto_db.get_grottos(ctx.author.id)
        if len(grottos) == 0:
            embed = create_embed("No grottos saved. Save a grotto with the /grotto command.",
                                 footer="Thank you for supporting development!")
            await ctx.respond(embed=embed, ephemeral=True)
            return

        page_count = len(grottos) // 8 + 1
        embeds = []

        for i in range(page_count):
            name = f"{ctx.author.display_name} - Personal Grotto List - Page {i + 1}"
            description = ""

            for grotto in grottos[i * 8:(i + 1) * 8]:
                grotto_numb = grottos.index(grotto) + 1
                if grotto.special:
                    grotto.name = ":star: %s :star:" % grotto.name
                description += f"**{grotto_numb}**: **[{grotto.name}]({grotto.url})**: {grotto.notes}\n\n"

            embed = create_embed(name, description=description, footer="Thank you for supporting development!")
            embeds.append(embed)

        paginator = create_paginator(embeds)
        await paginator.respond(ctx.interaction, ephemeral=True)

    @discord.slash_command(description="Get a saved personal grotto", guild_ids=[guild_id])
    async def get_grotto(self, ctx, grotto_note: Option(str, "Grotto Note", required=True),
                         private: Option(bool, "Keep Private", required=False) = False):
        if ctx.author.get_role(self.contributor_role) is None:
            embed = create_embed("You must be a contributor to use this command.")
            await ctx.respond(embed=embed)
            return
        grotto = grotto_db.get_grotto(ctx.author.id, grotto_note)
        if grotto is None:
            embed = create_embed("Grotto with that note does not exist.",
                                 footer="Thank you for supporting development!")
            await ctx.respond(embed=embed, ephemeral=True)
            return

        if grotto.special:
            grotto.name = ":star: %s :star:" % grotto.name
        title = f"{grotto.name} - {grotto.notes}"
        description = '''
**Seed:** %s | **Rank:** %s

**Type:** %s | **Floors:** %s

**Boss:** %s | **Monster Rank:** %s
        ''' % (grotto.seed, grotto.rank, grotto.type, grotto.floors, grotto.boss, grotto.monster_rank)

        files = []

        if grotto.chests != "":
            grotto.chests = grotto.chests.replace("'", "\"")
            chests = json.loads(grotto.chests)
            description += "\n**Chests**\n%s\n" % ", ".join([f"**{k}**: {v}" for k, v in chests.items()])
        if grotto.locations != "":
            description += "\n**Locations**"

            grotto.locations = grotto.locations.replace("'", "\"")
            locations_values = json.loads(grotto.locations)
            with open("data/locations.json", "r") as f:
                locations = json.load(f)["locations"]
                for location in locations_values:
                    description += "\n**%s**: ||%s||" % (location, locations[location])
                    files.append({"id": 0, "file": "grotto_images/%s.png" % location})

        embed = create_embed(title, description=description, footer="Thank you for supporting development!")

        fs = [file["file"] for file in files if file["id"] == 0]
        file_name = "collages/collage0.png"
        create_collage(fs, file_name)
        with open(file_name, 'rb') as fp:
            data = io.BytesIO(fp.read())
        file = discord.File(data, file_name.removeprefix("collages/"))
        embed.set_image(url="attachment://%s" % file_name.removeprefix("collages/"))

        if grotto.special:
            embed.color = discord.Color.gold()

        await ctx.respond(embed=embed, file=file, ephemeral=private)

    @discord.slash_command(description="Update the notes of a saved personal grotto", guild_ids=[guild_id])
    async def update_grotto(self, ctx, old_note: Option(str, "Grotto Note", required=True),
                            new_note: Option(str, "New Grotto Note", required=True)):
        if ctx.author.get_role(self.contributor_role) is None:
            embed = create_embed("You must be a contributor to use this command.")
            await ctx.respond(embed=embed)
            return
        if grotto_db.update_grotto(ctx.author.id, old_note, new_note):
            embed = create_embed("Grotto updated successfully.", footer="Thank you for supporting development!")
        else:
            embed = create_embed("Grotto with that note does not exist.",
                                 footer="Thank you for supporting development!")
        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(description="Delete a saved personal grotto", guild_ids=[guild_id])
    async def delete_grotto(self, ctx, grotto_note: Option(str, "Grotto Note", required=True)):
        if ctx.author.get_role(self.contributor_role) is None:
            embed = create_embed("You must be a contributor to use this command.")
            await ctx.respond(embed=embed)
            return
        if grotto_db.delete_grotto(ctx.author.id, grotto_note):
            embed = create_embed("Grotto deleted successfully.", footer="Thank you for supporting development!")
        else:
            embed = create_embed("Grotto with that note does not exist.",
                                 footer="Thank you for supporting development!")
        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(description="View all saved grottos", guild_ids=[guild_id])
    async def all_grottos(self, ctx, user: Option(discord.User, "User", required=False)):
        if ctx.author.id != self.admin_user:
            embed = create_embed("Invalid permissions.")
            await ctx.respond(embed=embed)
            return
        if user is None:
            user = ctx.author
        grottos = grotto_db.get_grottos(user.id, True)
        if len(grottos) == 0:
            embed = create_embed("No grottos saved.", footer="Thank you for supporting development!")
            await ctx.respond(embed=embed, ephemeral=True)
            return

        pages = []
        for owner, grottos in itertools.groupby(grottos, key=lambda x: x.owner):
            grottos = list(grottos)
            owner = self.bot.get_user(int(owner))

            page_count = len(grottos) // 14 + 1
            embeds = []

            for i in range(page_count):
                name = f"{owner.display_name} - Personal Grotto List - Page {i + 1}"
                description = ""

                for grotto in grottos[i * 14:(i + 1) * 14]:
                    grotto_numb = grottos.index(grotto) + 1
                    if grotto.special:
                        grotto.name = ":star: %s :star:" % grotto.name
                    description += f"**{grotto_numb}**: **[{grotto.name}]({grotto.url})**: {grotto.notes}\n\n"

                embed = create_embed(name, description=description, footer="Thank you for supporting development!")
                embeds.append(embed)
            pages.extend(embeds)

        paginator = create_paginator(pages)
        await paginator.respond(ctx.interaction, ephemeral=True)

    @discord.slash_command(description="Get instructions to a grotto location")
    async def grotto_location(self, ctx, location: Option(str, "Location (Ex. 05)", required=True)):
        location = location.upper()
        if not re.match(r'^[0-9a-fA-F]{2}$', location) or not 1 <= int(location, 16) <= 150:
            embed = create_embed("Invalid location. Please provide a valid location code (Ex. 05)")
            await ctx.respond(embed=embed)
            return
        with open("data/locations.json", "r") as f:
            locations = json.load(f)["locations"]
            description = "**%s**: ||%s||" % (location, locations[location])
            embed = create_embed("Location Instructions", description=description)

            file_name = "grotto_images/%s.png" % location
            with open(file_name, 'rb') as fp:
                data = io.BytesIO(fp.read())
            file = discord.File(data, file_name.removeprefix("grotto_images/"))
            embed.set_image(url="attachment://%s" % file_name.removeprefix("grotto_images/"))
            await ctx.respond(embed=embed, file=file)

    @grotto_translate.command(name="english", description="Translate a Grotto")
    async def grotto_translate_english(self, ctx, material: Option(str, "Material (Ex. Granite)",
                                                                   choices=grotto_prefixes["english"], required=True),
                                       environment: Option(str, "Environment (Ex. Tunnel)",
                                                           choices=grotto_environments["english"], required=True),
                                       suffix: Option(str, "Suffix (Ex. of Woe)", choices=grotto_suffixes["english"],
                                                      required=True),
                                       language_output: Option(str, choices=translation_languages, required=False),
                                       level: Option(int, "Level (Ex. 1)", required=False),
                                       location: Option(str, "Location (Ex. 05)", required=False)):
        await self.translate_grotto_command(ctx, material, environment, suffix, "english", language_output, level,
                                            location)

    @grotto_translate.command(name="japanese", description="宝の地図翻訳")
    async def grotto_translate_japanese(self, ctx, material: Option(str, "形容詞 (例：うす暗き)",
                                                                    choices=grotto_prefixes["japanese"], required=True),
                                        suffix: Option(str, "名詞 (例：獣の)", choices=grotto_suffixes["japanese"],
                                                       required=True), environment: Option(str, "地形 (例：地下道)",
                                                                                           choices=grotto_environments[
                                                                                               "japanese"],
                                                                                           required=False),
                                        language_output: Option(str, "翻訳言語 (例：English)",
                                                                choices=translation_languages, required=False),
                                        level: Option(int, "Ｌｖ (例：1)", required=False),
                                        location: Option(str, "場所コード (例：05)", required=False)):
        await self.translate_grotto_command(ctx, material, environment, suffix, "japanese", language_output, level,
                                            location)

    @grotto_translate.command(name="spanish", description="Traduce una Gruta")
    async def grotto_translate_spanish(self, ctx, environment: Option(str, "Entorno (Ej. Galería)",
                                                                      choices=grotto_environments["spanish"],
                                                                      required=True),
                                       material: Option(str, "Material (Ej. de Granito)",
                                                        choices=grotto_prefixes["spanish"], required=True),
                                       suffix: Option(str, "Sufijo (Ej. de la Congoja)",
                                                      choices=grotto_suffixes["spanish"], required=True),
                                       language_output: Option(str, "Salida de Idioma (Ej. English)",
                                                               choices=translation_languages, required=False),
                                       level: Option(int, "Nivel (Ej. 1)", required=False),
                                       location: Option(str, "Localización (Ej. 05)", required=False)):
        await self.translate_grotto_command(ctx, material, environment, suffix, "spanish", language_output, level,
                                            location)

    @grotto_translate.command(name="french", description="Traduire un Antre")
    async def grotto_translate_french(self, ctx, environment: Option(str, "Environnement (Ex. Tunnel)",
                                                                     choices=grotto_environments["french"],
                                                                     required=True),
                                      material: Option(str, "Matériel (Ex. de granit)",
                                                       choices=grotto_prefixes["french"], required=True),
                                      suffix: Option(str, "Affixe (Ex. de la Détresse)",
                                                     choices=grotto_suffixes["french"], required=True),
                                      language_output: Option(str, "Langue de Sortie (Ex. English)",
                                                              choices=translation_languages, required=False),
                                      level: Option(int, "Niveau (Ex. 1)", required=False),
                                      location: Option(str, "Localisation (Ex. 05)", required=False)):
        await self.translate_grotto_command(ctx, material, environment, suffix, "french", language_output, level,
                                            location)

    @grotto_translate.command(name="german", description="Übersetze eine Grotte")
    async def grotto_translate_german(self, ctx, material: Option(str, "Material (z.B. Granit-)",
                                                                  choices=grotto_prefixes["german"], required=True),
                                      environment: Option(str, "Umgebung (z.B. Tunnel)",
                                                          choices=grotto_environments["german"], required=True),
                                      suffix: Option(str, "Anhang (z.B. des Grams)", choices=grotto_suffixes["german"],
                                                     required=True),
                                      language_output: Option(str, "Sprachen Ausgabe (z.B. English)",
                                                              choices=translation_languages, required=False),
                                      level: Option(int, "Level (z.B. 1)", required=False),
                                      location: Option(str, "Standort (z.B. 05)", required=False)):
        await self.translate_grotto_command(ctx, material, environment, suffix, "german", language_output, level,
                                            location)

    @grotto_translate.command(name="italian", description="Translate a Grotto")
    async def grotto_translate_italian(self, ctx, environment: Option(str, "Environment (Ex. Galleria)",
                                                                      choices=grotto_environments["italian"],
                                                                      required=True),
                                       material: Option(str, "Material (Ex. Granito)",
                                                        choices=grotto_prefixes["italian"], required=True),
                                       suffix: Option(str, "Suffix (Ex. dell’Angoscia)",
                                                      choices=grotto_suffixes["italian"], required=True),
                                       language_output: Option(str, choices=translation_languages, required=False),
                                       level: Option(int, required=False), location: Option(str, required=False)):
        await self.translate_grotto_command(ctx, material, environment, suffix, "italian", language_output, level,
                                            location)

    async def grotto_command(self, ctx, material, environment, suffix, level, location, abbreviations=False):
        if not abbreviations:
            if not ctx.response.is_done():
                await ctx.defer()

        embeds, files, grottos = await self.grotto_func(material, environment, suffix, level, location)
        if abbreviations:
            if len(embeds) == 0:
                return None, None, None
            return embeds, files, grottos

        premium = ctx.author.get_role(self.contributor_role) is not None
        if len(embeds) > 1:
            if premium:
                views = [SaveGrottoView(grotto) for grotto in grottos]
                paginator = create_paginator(embeds, files, views)
            else:
                paginator = create_paginator(embeds, files)
            await paginator.respond(ctx.interaction)
        else:
            if len(embeds) == 1:
                embed = embeds[0]
                fs = [file["file"] for file in files if file["id"] == 0]
                file_name = "collages/collage0.png"
                create_collage(fs, file_name)
                with open(file_name, 'rb') as fp:
                    data = io.BytesIO(fp.read())
                file = discord.File(data, file_name.removeprefix("collages/"))
                embed.set_image(url="attachment://%s" % file_name.removeprefix("collages/"))
            else:
                embed = create_embed("No grotto found. Please check parameters and try again.")
                file = None

            if file is not None:
                if premium:
                    view = SaveGrottoView(grottos[0])
                    await ctx.followup.send(embed=embed, file=file, view=view)
                else:
                    await ctx.followup.send(embed=embed, file=file)
            else:
                if premium and len(grottos) > 0:
                    view = SaveGrottoView(grottos[0])
                    await ctx.followup.send(embed=embed, view=view)
                else:
                    await ctx.followup.send(embed=embed)

    async def grotto_func(self, material, environment, suffix, level, location):
        async with aiohttp.ClientSession() as session:
            environment_name = str(grotto_environments["english"].index(
                titlecase(environment)) + 1) if environment.lower() != "map" else ""
            params = {"search": "Search", "prefix": str(grotto_prefixes["english"].index(titlecase(material)) + 1),
                      "envname": environment_name, "suffix": str(grotto_suffixes["english"].index(suffix) + 1),
                      "level": str(level), }

            if location is not None:
                try:
                    params["loc"] = str(int(location, base=16))
                except ValueError:
                    pass

            try:
                async with session.get(self.grotto_search_url, params=params) as response:
                    text = await response.text()
            except ConnectionTimeoutError:
                err = create_embed(
                    "Connection timeout to host",
                    description="https://www.yabd.org/apps/dq9/grottosearch.php"
                )
                return [err], [], []
            except Exception:
                err = create_embed("Error contacting grotto database.")
                return [err], [], []

            selector = Selector(text=text)
            divs = selector.xpath('//div[@class="inner"]//text()')
            grottos_res = divs.getall()

            embeds = []
            files = []
            grottos = []

            for parsed in create_grotto(grottos_res):
                special = is_special(parsed)
                color = discord.Color.gold() if special else discord.Color.green()
                embed = create_embed(None, color=color)

                if special:
                    parsed = parsed[1:]

                zipped = zip(range(len(parsed)), grotto_keys, parsed)

                seed = ""
                rank = ""
                type = ""
                floors = ""
                boss = ""
                monster_rank = ""

                chests_value = ""
                locations_values = []

                description = '''
**Seed:** | **Rank:**

**Type:** | **Floors:**

**Boss:** | **Monster Rank:**
    '''
                for i, key, value in zipped:
                    if key == "Name":
                        if special:
                            value = ":star: %s :star:" % value
                        embed.title = "%s\n[Click For Full Info]" % value
                    else:
                        if key == "Seed":
                            value = str(value).zfill(4)
                            seed = value
                        if key == "Rank":
                            value = str(value).replace(" / ", "/")
                            rank = value
                        if key == "Type":
                            type = value
                        if key == "Floors":
                            floors = value
                        if key == "Boss":
                            boss = value
                        if key == "Monster Rank":
                            pattern = r'\((.*?)\)'
                            matches = re.findall(pattern, value)
                            value = '-'.join(matches)
                            monster_rank = value
                        if key == "Chests":
                            values = [str(x) for x in parsed[i:i + 10]]
                            chests = list(zip(grotto_chest_ranks, values))
                            value = ", ".join([': '.join(x) for x in chests if x[1] != "0"])
                            chests_value = value
                        if key == "Locations":
                            values = [str(x).zfill(2) for x in parsed[i + 9:]]
                            for v in values:
                                files.append({"id": len(embeds), "file": "grotto_images/%s.png" % v})
                            locations_values = values
                        description = description.replace("**%s:**" % key, "**%s:** %s" % (key, value))

                if chests_value != "":
                    description += "\n**Chests**\n%s\n" % chests_value
                if len(locations_values) > 0:
                    description += "\n**Locations**"

                    with open("data/locations.json", "r") as f:
                        locations = json.load(f)["locations"]
                        for location in locations_values:
                            description += "\n**%s**: ||%s||" % (location, locations[location])
                embed.description = description
                embed.url = self.grotto_details_url + parsers.grotto_ranks[int(rank.split()[0])] + seed
                embeds.append(embed)

                name = embed.title.replace(":star: ", "").replace(" :star:", "").split("\n")[0]
                locations = locations_values
                chests = chests_value.replace("*", "").split(", ")
                if len(chests) > 0 and chests[0] != "":
                    chests = {x.split(": ")[0]: x.split(": ")[1] for x in chests}
                grotto = parsers.Grotto(name=name, url=embed.url, special=int(special), seed=seed, rank=rank,
                                        type=type, floors=floors, boss=boss, monster_rank=monster_rank,
                                        chests=str(chests), locations=str(locations))
                grottos.append(grotto)

            return embeds, files, grottos
        return None

    async def translate_grotto_command(self, ctx, material, environment, suffix, language_input, language_output, level,
                                       location):
        await ctx.defer()

        embed, material, environment, suffix = await self.translate_grotto(material, environment, suffix,
                                                                           language_input, language_output)
        await ctx.followup.send(embed=embed)

        if level is not None:
            await self.grotto_command(ctx, material, environment, suffix, level, location)

    async def translate_grotto(self, material, environment, suffix, language_input, language_output):
        with open("data/translations/grottos.json", "r", encoding="utf-8") as fp:
            data = json.load(fp)

        translations = data["translations"]

        translation = Translation

        translation_english = []
        translation_japanese = []
        translation_spanish = []
        translation_french = []
        translation_german = []
        translation_italian = []

        phrases = [material, environment, suffix]
        if environment is None:
            phrases.remove(environment)

        for p in phrases:
            index = next(filter(lambda r: r[language_input].lower() == p.lower(), translations), None)

            translation = Translation.from_dict(index)

            translation_english.append(translation.english)
            translation_japanese.append(translation.japanese)
            translation_spanish.append(translation.spanish)
            translation_french.append(translation.french)
            translation_german.append(translation.german)
            translation_italian.append(translation.italian)

        if environment is None:
            translation_english.insert(1, "Map")
            translation_japanese.insert(1, "地図")
            translation_spanish.insert(1, "Map")  # TODO Get translation for "map"
            translation_french.insert(1, "Map")  # TODO Get translation for "map"
            translation_german.insert(1, "Map")  # TODO Get translation for "map"
            translation_italian.insert(1, "Map")  # TODO Get translation for "map"

        translation.english = "%s %s %s" % (translation_english[0], translation_english[1], translation_english[2])
        translation.japanese = "%s%s%s" % (translation_japanese[0], translation_japanese[2], translation_japanese[1])
        translation.spanish = "%s %s %s" % (translation_spanish[1], translation_spanish[0], translation_spanish[2])
        translation.french = "%s %s %s" % (translation_french[1], translation_french[0], translation_french[2])
        translation.german = "%s%s %s" % (translation_german[0], translation_german[1], translation_german[2])
        translation.italian = "%s %s %s" % (translation_italian[1], translation_italian[0], translation_italian[2])

        all_languages = [translation.english, translation.japanese, translation.spanish, translation.french,
                         translation.german, translation.italian]

        title = "Translation of: %s" % titlecase(all_languages[translation_languages_simple.index(language_input)])
        color = discord.Color.green()
        embed = create_embed(title, color=color,
                             error="Any errors? Want to contribute data? Please speak to %s" % dev_tag)
        if language_output is not None:
            value = all_languages[translation_languages.index(language_output)]
            if value != "":
                embed.add_field(name=language_output, value=value, inline=False)
        else:
            for language, translation in zip(translation_languages, all_languages):
                if translation != "":
                    embed.add_field(name=language, value=translation, inline=False)

        return embed, translation_english[0], translation_english[1], translation_english[2]
