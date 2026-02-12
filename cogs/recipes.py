import json
from collections import OrderedDict

import discord
from discord import Option
from discord.ext import commands
from titlecase import titlecase

import cascade_recipes
import parsers
from utils import create_embed, clean_text


def setup(bot):
    bot.add_cog(Recipes(bot))


class Recipes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.krak_pot_image_url = "https://cdn.discordapp.com/emojis/866763396108386304.png"
        self.item_images_url = "https://www.woodus.com/den/gallery/graphics/dq9ds/item/%s.png"
        self.weapon_images_url = "https://www.woodus.com/den/gallery/graphics/dq9ds/weapon/%s.png"
        self.armor_images_url = "https://www.woodus.com/den/gallery/graphics/dq9ds/armor/%s.png"
        self.shield_images_url = "https://www.woodus.com/den/gallery/graphics/dq9ds/shield/%s.png"
        self.accessory_images_url = "https://www.woodus.com/den/gallery/graphics/dq9ds/accessory/%s.png"

    async def get_recipes(self, ctx: discord.AutocompleteContext):
        with open("data/recipes.json", "r", encoding="utf-8") as fp:
            data = json.load(fp)
        recipes = data["recipes"]
        results = []
        for r in recipes:
            recipe = parsers.Recipe.from_dict(r)
            if ctx.value.lower() in recipe.result.lower():
                results.append(titlecase(recipe.result))
        return results

    def _recipe_image_url(self, name: str, recipe_type: str) -> str | None:
        recipe_images_url = ""
        t = (recipe_type or "").lower()
        if t in parsers.item_types:
            recipe_images_url = self.item_images_url
        elif t in parsers.weapon_types:
            recipe_images_url = self.weapon_images_url
        elif t in parsers.armor_types:
            recipe_images_url = self.armor_images_url
        elif t in parsers.accessory_types:
            recipe_images_url = self.accessory_images_url
        elif t == "shields":
            recipe_images_url = self.shield_images_url

        if recipe_images_url:
            return recipe_images_url % clean_text(name, False, True)
        return None

    def _chunk_lines(self, lines: list[str], limit: int = 1024) -> list[str]:
        chunks, buf, size = [], [], 0
        for line in lines:
            add = len(line) + (1 if buf else 0)
            if buf and size + add > limit:
                chunks.append("\n".join(buf))
                buf, size = [], 0
                add = len(line)
            buf.append(line)
            size += add
        if buf:
            chunks.append("\n".join(buf))
        return chunks

    def _direct_ingredients_with_locations_block(self, direct: list[tuple[str, int]]) -> list[str]:
        """
        Returns lines to render inside the Direct Ingredients field.
        Locations are indented under each direct ingredient (only if that ingredient has locations).
        """
        lines: list[str] = []
        for name, qty in direct:
            craftable = cascade_recipes.has_recipe(name)
            tag = " (craftable)" if craftable else ""
            lines.append(f"- {titlecase(name)} x{qty}{tag}")

            loc = cascade_recipes.get_location(name)
            if loc:
                locs = [titlecase(x) for x in loc if x]
                if locs:
                    # Indent under the ingredient, not a separate field.
                    # Use a compact single line; split only if it gets too long later by chunker.
                    lines.append(f"  - {', '.join(locs)}")
        return lines

    def _make_cascade_embed_and_view(self, item_name: str):
        root = cascade_recipes.get_recipe(item_name)
        if not root:
            embed = create_embed(
                "Ahem! Oh dear. I'm afraid I don't seem to be\nable to make anything with that particular"
                "\ncreation name of `%s`." % item_name,
                image=self.krak_pot_image_url,
                )
            return embed, None

        title = titlecase(root.name)
        if getattr(root, "alchemiracle", False):
            title = f":star: {title} :star:"
            color = discord.Color.gold()
        else:
            color = discord.Color.green()

        image = root.image or self._recipe_image_url(root.name, root.type)
        embed = create_embed(title, color=color, image=image)

        if root.type:
            embed.add_field(name="Type", value=root.type, inline=False)
        if root.notes:
            embed.add_field(name="Notes", value=str(root.notes), inline=False)

        direct = cascade_recipes.get_direct_ingredients(root.name)
        direct_lines = self._direct_ingredients_with_locations_block(direct)

        children_for_buttons = [name for name, _ in direct if cascade_recipes.has_recipe(name)]

        if direct_lines:
            for i, chunk in enumerate(self._chunk_lines(direct_lines), start=1):
                embed.add_field(
                    name="Direct Ingredients" if i == 1 else "Direct Ingredients (cont.)",
                    value=chunk,
                    inline=False,
                )

        tiers = cascade_recipes.get_equivalence_tiers(root.name, max_depth=8)

        for idx, tier in enumerate(tiers):
            lines = []
            for name, total in cascade_recipes.sorted_counter_items(tier):
                lines.append(f"- {titlecase(name)} x{total}")

            if not lines:
                continue

            field_name = (
                "Equivalent Totals — Tier 0 (direct)"
                if idx == 0
                else f"Equivalent Totals — Tier {idx} (expanded {idx} step{'s' if idx != 1 else ''})"
            )

            chunks = self._chunk_lines(lines, limit=1024)
            for ci, chunk in enumerate(chunks, start=1):
                embed.add_field(
                    name=field_name if ci == 1 else f"{field_name} (cont.)",
                    value=chunk,
                    inline=False,
                )

        view = RecipeCascadeView(self, children_for_buttons) if children_for_buttons else None
        return embed, view

    @discord.slash_command(name="recipe", description="Sends info about a recipe.")
    async def _recipe(
            self,
            ctx,
            creation_name: Option(
                str,
                "Creation (Ex. Special Medicine)",
                autocomplete=get_recipes,
                required=True,
            ),
    ):
        with open("data/recipes.json", "r", encoding="utf-8") as fp:
            data = json.load(fp)

        recipes = data["recipes"]
        index = next(filter(lambda r: clean_text(r["result"]) == clean_text(creation_name.lower()), recipes), None)

        if index is None:
            embed = create_embed(
                "Ahem! Oh dear. I'm afraid I don't seem to be\nable to make anything with that particular"
                "\ncreation name of `%s`." % creation_name,
                image=self.krak_pot_image_url,
                )
            return await ctx.respond(embed=embed)

        recipe = parsers.Recipe.from_dict(index)

        title = ":star: %s :star:" % titlecase(recipe.result) if recipe.alchemiracle else titlecase(recipe.result)
        color = discord.Color.gold() if recipe.alchemiracle else discord.Color.green()

        if recipe.image == "":
            recipe_images_url = ""
            if recipe.type.lower() in parsers.item_types:
                recipe_images_url = self.item_images_url
            elif recipe.type.lower() in parsers.weapon_types:
                recipe_images_url = self.weapon_images_url
            elif recipe.type.lower() in parsers.armor_types:
                recipe_images_url = self.armor_images_url
            elif recipe.type.lower() in parsers.accessory_types:
                recipe_images_url = self.accessory_images_url
            elif recipe.type.lower() == "shields":
                recipe_images_url = self.shield_images_url

            if recipe_images_url != "":
                recipe.image = recipe_images_url % clean_text(recipe.result, False, True)

        embed = create_embed(title, color=color, image=recipe.image)

        embed.add_field(name="Type", value=recipe.type, inline=False)
        if recipe.item1 != "":
            embed.add_field(name="Item 1", value="%ix %s" % (recipe.qty1, titlecase(recipe.item1)), inline=False)
        if recipe.item2 != "":
            embed.add_field(name="Item 2", value="%ix %s" % (recipe.qty2, titlecase(recipe.item2)), inline=False)
        if recipe.item3 != "":
            embed.add_field(name="Item 3", value="%ix %s" % (recipe.qty3, titlecase(recipe.item3)), inline=False)
        if recipe.notes != "":
            embed.add_field(name="Notes", value="%s" % recipe.notes, inline=False)

        await ctx.respond(embed=embed)

    @discord.slash_command(name="recipe_cascade", description="Sends cascading info about a recipe.")
    async def _recipe_cascade(
            self,
            ctx,
            creation_name: Option(
                str,
                "Creation (Ex. Special Medicine)",
                autocomplete=get_recipes,
                required=True,
            ),
    ):
        embed, view = self._make_cascade_embed_and_view(creation_name)
        if view:
            await ctx.respond(embed=embed, view=view)
        else:
            await ctx.respond(embed=embed)


class RecipeCascadeView(discord.ui.View):
    def __init__(self, cog: Recipes, child_names: list[str]):
        super().__init__(timeout=180)
        self.cog = cog

        uniq = list(OrderedDict.fromkeys(child_names))
        for name in uniq[:25]:
            self.add_item(RecipeCascadeButton(cog, name))


class RecipeCascadeButton(discord.ui.Button):
    def __init__(self, cog: Recipes, child_name: str):
        label = titlecase(child_name)
        if len(label) > 80:
            label = label[:77] + "..."
        super().__init__(style=discord.ButtonStyle.secondary, label=label)
        self.cog = cog
        self.child_name = child_name

    async def callback(self, interaction: discord.Interaction):
        embed, view = self.cog._make_cascade_embed_and_view(self.child_name)
        await interaction.response.send_message(embed=embed, view=view)
