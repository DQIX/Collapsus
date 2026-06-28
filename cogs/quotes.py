import json

import discord
from discord.ext import commands
from titlecase import titlecase

import parsers
from main import guild_id
from utils import create_embed, create_paginator


def setup(bot):
    bot.add_cog(Quotes(bot))


class Quotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_quotes(self, ctx: discord.AutocompleteContext):
        with open("data/quotes.json", "r", encoding="utf-8") as fp:
            data = json.load(fp)
        quotes = data["quotes"]
        results = []
        for q in quotes:
            quote = parsers.Quote.from_dict(q)
            if ctx.value.lower() in quote.name.lower() or any(
                    ctx.value.lower() in alias.lower() for alias in quote.aliases):
                results.append(titlecase(quote.name))
            if len(results) == 25:
                break
        return results

    @discord.slash_command(name="quote", description="Sends a quote.")
    async def _quote(self, ctx, quote_name: discord.Option(str, "Quote Name", required=True, autocomplete=get_quotes),
                     member: discord.Option(discord.Member, "Member to Mention", required=False),
                     message_id: discord.Option(str, "Message ID to Reply To", required=False)):
        with open("data/quotes.json", "r", encoding="utf-8") as fp:
            data = json.load(fp)

        quotes = data["quotes"]
        index = next((q for q in quotes if q["name"].lower() == quote_name.lower() or any(
            alias.lower() == quote_name.lower() for alias in q["aliases"])), None)
        quote = parsers.Quote.from_dict(index)

        author = ctx.guild.get_member(quote.author).display_name

        embed = create_embed(quote.name, description=quote.content, author=author, color=discord.Color.green(),
                             image=quote.image)
        if member is not None:
            await ctx.respond(member.mention, embed=embed)
        elif message_id is not None:
            message = await ctx.channel.fetch_message(message_id)
            await message.reply(embed=embed)
            await ctx.respond("Quote sent.", ephemeral=True)
        else:
            await ctx.respond(embed=embed)

    @discord.slash_command(name="add_quote", description="Adds a quote.", guild_ids=[guild_id])
    async def _add_quote(self, ctx, quote_name: discord.Option(str, "Quote Name", required=True),
                         quote_content: discord.Option(str, "Quote Content", required=True),
                         quote_image: discord.Option(discord.Attachment, "Quote Image", required=False),
                         quote_aliases: discord.Option(str, "Quote Aliases", required=False)):
        with open("data/quotes.json", "r", encoding="utf-8") as fp:
            data = json.load(fp)

        quotes = data["quotes"]
        index = next((q for q in quotes if q["name"].lower() == quote_name.lower() or any(
            alias.lower() == quote_name.lower() for alias in q["aliases"])), None)
        if index is not None:
            embed = create_embed("Quote already exists.")
            return await ctx.respond(embed=embed)

        aliases = quote_aliases.split(", ") if quote_aliases is not None else []

        if quote_image is not None:
            file = await quote_image.to_file()
            embed = create_embed("Image quote created.", "**Do not delete this message.**")
            message = await ctx.send(embed=embed, file=file)
            quote_image_url = message.attachments[0].url
        else:
            quote_image_url = ""

        quote = parsers.Quote(quote_name, ctx.author.id, quote_content, quote_image_url, aliases)
        quotes.append(quote.to_dict())

        with open("data/quotes.json", "w", encoding="utf-8") as fp:
            json.dump(data, fp, indent=4)

        embed = create_embed("Quote added.")
        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(name="remove_quote", description="Removes a quote.", guild_ids=[guild_id])
    async def _remove_quote(self, ctx,
                            quote_name: discord.Option(str, "Quote Name", required=True, autocomplete=get_quotes)):
        with open("data/quotes.json", "r", encoding="utf-8") as fp:
            data = json.load(fp)

        quotes = data["quotes"]
        index = next((q for q in quotes if q["name"].lower() == quote_name.lower() or any(
            alias.lower() == quote_name.lower() for alias in q["aliases"])), None)
        if index is None:
            embed = create_embed("Quote does not exist.")
            return await ctx.respond(embed=embed)

        quotes.remove(index)

        with open("data/quotes.json", "w", encoding="utf-8") as fp:
            json.dump(data, fp, indent=4)

        embed = create_embed("Quote removed.")
        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(name="all_quotes", description="Lists all quotes.", guild_ids=[guild_id])
    async def _all_quotes(self, ctx):
        with open("data/quotes.json", "r", encoding="utf-8") as fp:
            data = json.load(fp)

        quotes = data["quotes"]
        embeds = []
        for i in range(0, len(quotes)):
            quote = parsers.Quote.from_dict(quotes[i])
            author = ctx.guild.get_member(quote.author).display_name
            embed = create_embed(quote.name, description=quote.content, author=author,
                                 color=discord.Color.green(), image=quote.image)
            embeds.append(embed)

        paginator = create_paginator(embeds)
        await paginator.respond(ctx.interaction, ephemeral=True)
