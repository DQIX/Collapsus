import json

import discord
from discord import Option
from discord.ext import commands
from titlecase import titlecase

import parsers
from utils import create_embed, clean_text, int_from_string, create_paginator


def setup(bot):
    bot.add_cog(Monsters(bot))


class Monsters(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.monster_images_url = "https://www.woodus.com/den/gallery/graphics/dq9ds/monster/%s.webp"

    async def get_monsters(self, ctx: discord.AutocompleteContext):
        with open("data/monsters.json", "r", encoding="utf-8") as fp:
            data = json.load(fp)
        monsters = data["monsters"]
        results = []
        for m in monsters:
            monster = parsers.Monster.from_dict(m)
            altname = m.get("altname", "")
            if (ctx.value.lower() in monster.name.lower() or ctx.value.lower() in monster.number.lower()
                    or ctx.value.lower() in altname.lower()):
                results.append(monster.number + " - " + titlecase(monster.name))
            if len(results) == 25:
                break
        return results

    @discord.slash_command(name="monster", description="Sends info about a monster.")
    async def _monster(self, ctx,
                       monster_identifier: Option(str, "Monster Identifier (Ex. Slime or 1)", autocomplete=get_monsters,
                                                  required=True)):
        with open("data/monsters.json", "r", encoding="utf-8") as fp:
            data = json.load(fp)

        monsters = data["monsters"]

        monster_number = 0

        if " - " in monster_identifier:
            monster_number = monster_identifier.split(" - ")[0]
            indexes = list(filter(lambda r: clean_text(r["name"].lower()) == clean_text(
                monster_identifier.split(" - ")[1].lower()) or clean_text(r.get("altname", "").lower()) == clean_text(
                monster_identifier.split(" - ")[1].lower()), monsters))
        else:
            indexes = list(filter(
                lambda r: clean_text(r["name"].lower()) == clean_text(monster_identifier.lower()) or clean_text(
                    r.get("altname", "").lower()) == clean_text(monster_identifier.lower()), monsters))
            if not indexes:
                monster_number = "#" + "%03d" % int_from_string(monster_identifier) + monster_identifier[-1] if \
                    monster_identifier[-1].isalpha() else ""
                indexes = list(
                    filter(lambda r: int_from_string(r["number"]) == int_from_string(monster_identifier), monsters))

        if len(indexes) == 0:
            embed = create_embed(
                "No monster found with the identifier `%s`. Please check spelling and try again." % monster_identifier)
            return await ctx.respond(embed=embed)

        proper_page = 0
        embeds = []
        for index in indexes:
            monster = parsers.Monster.from_dict(index)

            title = "%s - %s (Level: %s)" % (monster.number, titlecase(monster.name), monster.level)
            description = '''
**Family:** %s | **EXP:** %s | **Gold:** %s


**HP:** %s | **MP:** %s | **ATK:** %s | **DEF:** %s | **AGI:** %s

__**%% Damage Multipliers:**__
**Fire:** %s | **Ice:** %s | **Wind:** %s
**Blast:** %s | **Earth:** %s | **Dark:** %s | **Light:** %s

**Haunts:** %s
    ''' % (monster.family, monster.exp, monster.gold, monster.hp, monster.mp, monster.atk, monster.defn, monster.agi,
           monster.fire, monster.ice, monster.wind, monster.blast, monster.earth, monster.dark, monster.light,
           titlecase(monster.haunts))
            if monster.drop1 != "":
                description += "\n**Drop 1 | Common Drop**\n%s\n" % titlecase(monster.drop1)
            if monster.drop2 != "":
                description += "\n**Drop 2 | Rare Drop**\n%s\n" % titlecase(monster.drop2)
            if monster.drop3 != "":
                description += "\n**Drop 3**\n%s\n" % titlecase(monster.drop3)

            if monster.image == "":
                monster.image = self.monster_images_url % clean_text(monster.name, False, True)

            embed = create_embed(title, description, image=monster.image)
            embeds.append(embed)

            if monster_number != 0 and monster_number == monster.number:
                proper_page = len(embeds) - 1

        if len(embeds) > 1:
            paginator = create_paginator(embeds, None)
            await paginator.respond(ctx.interaction)
            await paginator.goto_page(proper_page)
        else:
            await ctx.respond(embed=embeds[0])
