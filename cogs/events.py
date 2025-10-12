import random
from datetime import datetime, timedelta

import discord
from discord.ext import commands

import utils


def setup(bot):
    bot.add_cog(Events(bot))


def is_birthday_week():
    today = datetime.now()
    birthday = datetime(today.year, 5, 13)
    start = birthday - timedelta(days=birthday.weekday())
    end = start + timedelta(days=6)
    return start <= today <= end


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.party_role = 1240460078528725014
        self.party_popper = "https://www.woodus.com/den/gallery/graphics/dq9ds/item/party_popper.png"

    @commands.Cog.listener()
    async def on_application_command(self, context):
        role = discord.utils.get(context.guild.roles, id=self.party_role)
        if role is not None:
            if is_birthday_week():
                if context.command.qualified_name == "happy_birthday":
                    await context.author.add_roles(role)
            else:
                await context.author.remove_roles(role)

    @discord.slash_command(description="Wish the bot a happy birthday!")
    async def happy_birthday(self, ctx):
        age = datetime.now().year - self.bot.user.created_at.year
        message = random.choice(["Thank you so much! I can't believe I've been helping people for {age} years already!",
                                 "It's only been {age} years? It feels like you guys have been bothering me forever!",
                                 "Wow, {age} years already? Time flies when you're having fun!",
                                 "I can't believe I'm {age} years old already! I'm getting so old!",
                                 "I'm {age} years old now? I hope bots age like fine wine!",
                                 "{age} years. Wow. I hope Discord bots don't get rusty like other bots!"])
        embed = utils.create_embed(title="It's My Birthday!", description=message.format(age=age),
                                   color=discord.Color.gold(), image=self.party_popper)
        await ctx.respond(embed=embed)
