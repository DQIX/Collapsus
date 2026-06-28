import io
import json
import os
import random

import discord
import emoji
from discord import Option
from discord.ext import commands
from titlecase import titlecase

import main
import parsers
from main import guild_id
from utils import create_embed, create_collage, clean_text


def setup(bot):
    bot.add_cog(Admin(bot))


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.quests_channel = 766039065849495574
        self.welcome_channel = 965688638295924766
        self.rules_channel_en = 688480621856686196
        self.rules_channel_fr = 965694046049800222
        self.rules_channel_de = 965693961907875850
        self.rules_channel_jp = 965693827568529448
        self.rules_channel_es = 1221871725663223818
        self.role_en = 879436700256964700
        self.role_fr = 965696709290262588
        self.role_de = 965696853951795221
        self.role_jp = 859563030220374057
        self.role_es = 1221871392451203113
        self.role_celestrian = 655438935278878720

    @staticmethod
    def _extract_snowflake(value):
        if value is None:
            return None

        candidate = str(value).split(" - ", 1)[0].strip()
        return int(candidate) if candidate.isdecimal() else None

    async def get_tourney_amounts(self, ctx: discord.AutocompleteContext):
        query = (ctx.value or "").strip()
        data_type = ((ctx.options or {}).get("data") or "").lower()

        suggestions = ["2", "4", "8", "16", "32", "64"]
        if data_type:
            try:
                with open(f"data/{data_type}.json", "r", encoding="utf-8") as fp:
                    data_list = json.load(fp)[data_type]
                max_amount = len(data_list)
                suggestions = [amount for amount in suggestions if int(amount) <= max_amount]
                if str(max_amount) not in suggestions:
                    suggestions.append(str(max_amount))
            except (FileNotFoundError, KeyError):
                pass

        results = []
        for amount in suggestions:
            if query in amount:
                results.append(amount)
            if len(results) == 25:
                break

        return results

    @discord.slash_command(name="change_invite", guild_ids=[guild_id])
    async def _change_server_invite(self, ctx, invite_code: Option(str, "Server Invite Code", required=True)):
        main.server_invite_code = invite_code

        with open("config.json", "w", encoding="utf-8") as fp:
            json.dump({"server_invite_code": main.server_invite_code}, fp, indent=2)

        embed = create_embed("Server Invite Code Changed", main.server_invite_url + main.server_invite_code)
        await ctx.respond(embed=embed)

    @discord.slash_command(name="edit_forum_message", guild_ids=[guild_id])
    async def _edit_forum_message(self, ctx,
                                  channel: Option(discord.SlashCommandOptionType.channel, "Channel", required=True),
                                  thread_id: Option(str, "Thread ID", required=True),
                                  message_id: Option(str, "Message ID", required=True),
                                  content: Option(str, "Content", required=True)):
        thread_id_value = self._extract_snowflake(thread_id)
        message_id_value = self._extract_snowflake(message_id)
        if thread_id_value is None or message_id_value is None:
            embed = create_embed("Invalid thread or message ID.")
            await ctx.respond(embed=embed, ephemeral=True)
            return

        threads = list(getattr(channel, "threads", [])) + await channel.archived_threads().flatten()
        thread = discord.utils.get(threads, id=thread_id_value)
        if thread is None:
            embed = create_embed("Thread not found.")
            await ctx.respond(embed=embed, ephemeral=True)
            return

        rearchive = getattr(thread, "archived", False)
        if rearchive:
            await thread.unarchive()
        message = await thread.fetch_message(message_id_value)
        await message.edit(content=content)
        if rearchive:
            await thread.archive()

        embed = create_embed("Message Edited", message.jump_url)
        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(name="edit_message", guild_ids=[guild_id])
    async def _edit_message(self, ctx, message_url: Option(str, "Message URL", required=True), content: Option(str, "Content", required=True)):
        message = await commands.MessageConverter().convert(ctx, message_url)
        await message.edit(content=content)

        embed = create_embed("Message Edited", message.jump_url)
        await ctx.respond(embed=embed, ephemeral=True)

    @discord.slash_command(name="migrate_resources", guild_ids=[guild_id])
    async def _migrate_resources(self, ctx):
        await ctx.defer()

        test_mode = os.getenv("TEST_MODE", "FALSE").lower() == "true"

        test_resources_channel = 1142886986949087272
        resources_channel = 1143509536783736965

        if test_mode:
            resources_channel = test_resources_channel

        migrations = [{"test_channel": 1142195240833388655, "channel": 891711067976249375, "thread": True,
                       "title": "Grotto Info"},
                      {"test_channel": 1142195242494337034, "channel": 788454671684468771, "thread": True,
                       "title": "Vocation Info"}, {"test_channel": 1142195244264345670, "channel": 655463607030644747,
                                                   "title": "EXP Manipulation", },
                      {"test_channel": 1142195245661032479, "channel": 706892011718049802, "title": "Seed Farming", },
                      {"test_channel": 1142195247158411274, "channel": 691066485279424582, "title": "Alchemy", },
                      {"test_channel": 1142195248429269022, "channel": 766039065849495574, "thread": True,
                       "title": "Quests List"},
                      {"test_channel": 1142195249721118780, "channel": 688861170236391626, "title": "Hoimi Table", },
                      {"test_channel": 1142195251159765044, "channel": 695401106305712228, "title": "Accolades", },
                      {"test_channel": 1142195255446356030, "channel": 655392079819833354, "title": "Other Info"}]

        large_messages = []

        for migration in reversed(migrations):
            if test_mode:
                migration["channel"] = migration["test_channel"]

            if migration.get("thread", False):
                all_messages = []

                archived_threads = await self.bot.get_channel(migration["channel"]).archived_threads().flatten()
                for thread in archived_threads:
                    messages = await thread.history().flatten()
                    messages.sort(key=lambda message: message.created_at)
                    all_messages.append(messages)

                all_messages.sort(key=lambda messages: messages[0].created_at)

                first_message_too_long = True
                while first_message_too_long:
                    try:
                        post = await self.bot.get_channel(resources_channel).create_thread(migration["title"],
                                                                                           all_messages[0][0].content)
                        message = await post.fetch_message(post.id)
                        await message.edit(files=[await f.to_file() for f in all_messages[0][0].attachments])
                        first_message_too_long = False
                    except discord.errors.HTTPException as ex:
                        if "Must be 2000 or fewer in length." in str(ex):
                            large_messages.append(all_messages[0][0])
                            all_messages[0] = all_messages[0][1:]

                all_messages[0] = all_messages[0][1:]

                for t, messages in enumerate(all_messages):
                    for i, message in enumerate(messages):
                        try:
                            await post.send(content=message.content,
                                            files=[await f.to_file() for f in message.attachments])
                        except discord.errors.HTTPException as ex:
                            if "Must be 2000 or fewer in length." in str(ex):
                                large_messages.append(message)

                await post.edit(locked=True)

                embed = create_embed("Migrated messages from <#%s> to <#%s>." % (migration["channel"], post.id))
                await ctx.send(embed=embed)

            else:
                messages = await self.bot.get_channel(migration["channel"]).history().flatten()
                messages.sort(key=lambda message: message.created_at)

                first_message_too_long = True
                while first_message_too_long:
                    try:
                        if migration["title"] == "Accolades":
                            first_part = """**Game Completion Accolades In order of Priority**:
```yml
Light-Speed Champion - clear time under 12 hours
Jot to Trot - clear time 12-19 hours
Sleeper on the Job - clear time 228+ hours
Easy Rider - clear time 152-227:59 hours
Exterminator - win 1500 battles
Shopaholic - wardrobe collection at 50%
Pacifist - 250 or fewer battles
Socialite - multiplayer time is 50%+ of total time played
Philanthropist - 60 quests cleared
Cartographer - 30 grottos cleared
Mighty Inviter - 50 tags (or maybe it's multiplayer sessions)
Entitled Adventurer - 60 accolades
Completely Potty - alchemy 120 times
Zoologist - defeated monster list 75%+
Punchbag - party wiped out 24+ times
Snappy Dresser - wardrobe collection at 38-49%
Recipe Researcher - recipes at 30%+
Moneybags - 90000+ gold (carried money + bank)
Grievous Angel - party wiped out 16-23 times
Monster Masher - 1000-1499 battles
Fleet Completer - clear time 19-26:59 hours
Steady Eddie/Edwina - clear time 76-151:59 hours
Party Hopper - multiplayer is 30% but less than 50% total time played
Immaculate Completion - party wiped out 0 times
Guardian Angel/Lionheart/Sent from Above/Watched-over One/Storied Saviour: Default titles. They depend on your class/level when completing.```"""
                            second_part = """**Grotto Accolades**:
```yml
1: Celestial Sentinel -- Awarded to xxx on the occasion of his/her victory over various renowned denizens of the depths.
[Defeat all Legacy Bosses.]

2: Heralded Hero/Heralded Heroine -- Awarded to xxx to commemorate his/her victory over a grotto boss of level 25 or above.

3: Superhero/Superheroine -- Awarded to xxx to commemorate his/her victory over a grotto boss of level 50 or above.

4: Heavenly Hero/Heavenly Heroine -- Awarded to xxx to commemorate his/her victory over a grotto boss of level 75 or above.

5: Legendary Hero/Legendary Heroine -- Awarded to xxx to commemorate his/her victory over a grotto boss of level 99.

6: Spelunker -- Presented to xxx for clearance of a grotto of level 25 or above.

7: Spunky Spelunker -- Presented to xxx for clearance of a grotto of level 50 or above.

8: Spelunking Specialist -- Presented to xxx for clearance of a grotto of level 75 or above.

9: Supreme Spelunker -- Presented to xxx for clearance of a grotto of level 99.

10: Cave Dweller -- Awarded to xxx on the occasion of his/her 10th grotto clearance.

11: Cave Craver -- Awarded to xxx on the occasion of his/her 50th grotto clearance.

12: From Cradle to Cave -- Awarded to xxx on the occasion of his/her 100th grotto clearance.

13: Stalag Mighty -- Awarded to xxx on the occasion of his/her 500th grotto clearance.

14: Caving Lunatic -- The Cavers' Cooperative would like to congratulate xxx for the outstanding achievement of completing 1000 grottoes.```"""

                            post = await self.bot.get_channel(resources_channel).create_thread(migration["title"],
                                                                                               first_part)
                            await post.send(content=second_part)
                        else:
                            post = await self.bot.get_channel(resources_channel).create_thread(migration["title"],
                                                                                               messages[0].content)
                            message = await post.fetch_message(post.id)
                            await message.edit(files=[await f.to_file() for f in messages[0].attachments])
                        first_message_too_long = False
                    except discord.errors.HTTPException as ex:
                        if "Must be 2000 or fewer in length." in str(ex):
                            large_messages.append(messages[0])
                            messages = messages[1:]

                for message in messages[1:]:
                    try:
                        await post.send(content=message.content, files=[await f.to_file() for f in message.attachments])
                    except discord.errors.HTTPException as ex:
                        if "Must be 2000 or fewer in length." in str(ex):
                            large_messages.append(message)

                await post.edit(locked=True)

                embed = create_embed("Migrated messages from <#%s> to <#%s>." % (migration["channel"], post.id))
                await ctx.send(embed=embed)

        if large_messages:
            desc = ""
            for message in large_messages:
                desc += "%s\n" % message.jump_url

            embed = create_embed("The following messages were too large to migrate.", desc)
            await ctx.send(embed=embed)

        embed = create_embed("Finished migration.")
        await ctx.followup.send(embed=embed)

    @discord.slash_command(name="migrate_challenges", guild_ids=[guild_id])
    async def _migrate_challenges(self, ctx):
        await ctx.defer()

        test_mode = os.getenv("TEST_MODE", "FALSE").lower() == "true"

        test_challenges_channel = 1143641065560227910
        challenges_channel = 1143670710443716680

        if test_mode:
            challenges_channel = test_challenges_channel

        migrations = [{"test_channel": 1142195226312704061, "channel": 1020384998567706694, "title": "Challenges"},
                      {"test_channel": 1142195227742969877, "channel": 724610856565997599, "title": "Challenge Runs"}]

        large_messages = []

        for migration in reversed(migrations):
            if test_mode:
                migration["channel"] = migration["test_channel"]

            archived_threads = await self.bot.get_channel(migration["channel"]).archived_threads().flatten()
            for thread in archived_threads:
                messages = await thread.history().flatten()
                messages.sort(key=lambda message: message.created_at)

                first_message_too_long = True
                while first_message_too_long:
                    try:
                        post = await self.bot.get_channel(challenges_channel).create_thread(
                            migration["title"] + " - " + thread.name.replace(" " + migration["title"], ""),
                            messages[0].content)
                        message = await post.fetch_message(post.id)
                        await message.edit(files=[await f.to_file() for f in messages[0].attachments])
                        first_message_too_long = False
                    except discord.errors.HTTPException as ex:
                        if "Must be 2000 or fewer in length." in str(ex):
                            large_messages.append(messages[0])
                            messages = messages[1:]

                messages = messages[1:]

                for i, message in enumerate(messages):
                    try:
                        await post.send(content=message.content, files=[await f.to_file() for f in message.attachments])
                    except discord.errors.HTTPException as ex:
                        if "Must be 2000 or fewer in length." in str(ex):
                            large_messages.append(message)

                await post.edit(locked=True)

                embed = create_embed("Migrated messages from <#%s> to <#%s>." % (thread.id, post.id))
                await ctx.send(embed=embed)

        if large_messages:
            desc = ""
            for message in large_messages:
                desc += "%s\n" % message.jump_url

            embed = create_embed("The following messages were too large to migrate.", desc)
            await ctx.send(embed=embed)

        embed = create_embed("Finished migration.")
        await ctx.followup.send(embed=embed)

    @discord.slash_command(name="parse_quests", description="Parses the quests.", guild_ids=[guild_id])
    async def _parse_quests(self, ctx):
        await ctx.defer()

        quests = []
        channel = self.bot.get_channel(self.quests_channel)
        archived_threads = await channel.archived_threads().flatten()
        for thread in archived_threads:
            messages = await thread.history().flatten()
            for message in messages:
                quests.append(parsers.parse_regex(parsers.Quest, message.content))

        data = {"quests": sorted(quests, key=lambda quest: quest["number"])}
        with open("data/quests.json", "w+", encoding="utf-8") as fp:
            json.dump(data, fp, indent=2)

        embed = create_embed("%i Quests Parsed Successfully" % len(quests))
        await ctx.followup.send(embed=embed)

    class TourneySelection(discord.ui.Select):
        def __init__(self, data):
            self.data = data
            super().__init__(placeholder="Vote for Your Choice!", min_values=1, max_values=1,
                             options=[discord.SelectOption(label=choice) for choice in self.data])

        async def callback(self, interaction: discord.Interaction):
            await interaction.response.send_message("You voted for %s!" % interaction.data["values"][0], ephemeral=True)

    @discord.slash_command(name="tourney", description="Generates a tournament.", guild_ids=[guild_id])
    async def _tourney(self, ctx, name: Option(str, "Name (Ex. Cutest Monster)", required=True),
                       amount: Option(str, "Amount (Ex. 8)", autocomplete=get_tourney_amounts, required=True),
                       data: Option(str, "Data (Ex. Monster)", choices=parsers.tourney_data_types, required=True)):
        await ctx.defer()

        data_type = data.lower()
        with open("data/%s.json" % data_type, "r", encoding="utf-8") as fp:
            json_data = json.load(fp)

        data_list = json_data[data_type]
        if not amount.isdecimal():
            embed = create_embed("Invalid amount. Please provide a numeric tournament size.")
            await ctx.followup.send(embed=embed, ephemeral=True)
            return

        amount_value = int(amount)
        if amount_value <= 0 or amount_value > len(data_list):
            embed = create_embed("Invalid amount. Please choose a value between 1 and %s." % len(data_list))
            await ctx.followup.send(embed=embed, ephemeral=True)
            return

        parser = getattr(parsers, data_type[:-1].capitalize())
        data_picked = [parser.from_dict(data) for data in random.sample(data_list, amount_value)]
        for item in data_picked:
            if item.image == "":
                image_url = getattr(__import__(__name__), data_type[:-1] + "_images_url")
                item.image = image_url % clean_text(item.name, False, True)

        data_images = [item.image for item in data_picked]

        embed = create_embed(name, ", ".join(
            [f"**{index + 1}:** {titlecase(item.name)}" for index, item in enumerate(data_picked)]))

        file_name = "tourney.png"
        create_collage(data_images, file_name)
        with open(file_name, 'rb') as fp:
            data = io.BytesIO(fp.read())
        file = discord.File(data, file_name)
        embed.set_image(url="attachment://%s" % file_name)

        view = discord.ui.View(timeout=None)
        view.add_item(self.TourneySelection(data=[titlecase(item.name) for item in data_picked]))
        await ctx.followup.send(embed=embed, file=file, view=view)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        emoji_name = emoji.demojize(payload.emoji.name)
        channel = self.bot.get_channel(payload.channel_id)
        guild = self.bot.get_guild(payload.guild_id)
        user = guild.get_member(payload.user_id)

        rules_channels = [self.bot.get_channel(self.rules_channel_en), self.bot.get_channel(self.rules_channel_fr),
                          self.bot.get_channel(self.rules_channel_de), self.bot.get_channel(self.rules_channel_jp),
                          self.bot.get_channel(self.rules_channel_es)]

        message = await channel.fetch_message(payload.message_id)
        if message.channel == self.bot.get_channel(self.welcome_channel):
            role_id = 0
            if emoji_name == ":United_Kingdom:":
                role_id = self.role_en
            if emoji_name == ":France:":
                role_id = self.role_fr
            if emoji_name == ":Germany:":
                role_id = self.role_de
            if emoji_name == ":Japan:":
                role_id = self.role_jp
            if emoji_name == ":Spain:":
                role_id = self.role_es

            await user.add_roles(discord.utils.get(guild.roles, id=role_id), reason="User assigned role to themselves.")

        elif message.channel in rules_channels:
            if emoji_name == ":thumbs_up:":
                await user.add_roles(discord.utils.get(guild.roles, id=self.role_celestrian),
                                     reason="User accepted rules.")
                await message.remove_reaction(payload.emoji, user)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        emoji_name = emoji.demojize(payload.emoji.name)
        channel = self.bot.get_channel(payload.channel_id)
        guild = self.bot.get_guild(payload.guild_id)
        user = guild.get_member(payload.user_id)

        message = await channel.fetch_message(payload.message_id)
        if message.channel == self.bot.get_channel(self.welcome_channel):
            role_id = 0
            if emoji_name == ":United_Kingdom:":
                role_id = self.role_en
            if emoji_name == ":France:":
                role_id = self.role_fr
            if emoji_name == ":Germany:":
                role_id = self.role_de
            if emoji_name == ":Japan:":
                role_id = self.role_jp
            if emoji_name == ":Spain:":
                role_id = self.role_es

            await user.remove_roles(discord.utils.get(guild.roles, id=role_id),
                                    reason="User removed role from themselves.")
