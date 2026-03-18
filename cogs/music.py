import asyncio
import json

import discord
from discord import Option
from discord.ext import commands

import parsers
from utils import create_embed


def setup(bot):
    bot.add_cog(Music(bot))


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stream_channel = 655390551138631704
        self.playlist_active = False
        self.stop_playlist_requested = False

    async def get_songs(self, ctx: discord.AutocompleteContext):
        return [song for song in parsers.songs if ctx.value.lower() in song.lower()]

    async def ensure_voice(self, ctx, *, deferred=False):
        voice_state = ctx.author.voice
        if voice_state is None:
            embed = create_embed("You need to be in a voice channel to use this command.")
            if deferred:
                await ctx.followup.send(embed=embed, ephemeral=True)
            else:
                await ctx.respond(embed=embed, ephemeral=True)
            return None, None

        channel = voice_state.channel
        if channel.id == self.stream_channel:
            embed = create_embed("You can't use this command in the stream channel.")
            if deferred:
                await ctx.followup.send(embed=embed, ephemeral=True)
            else:
                await ctx.respond(embed=embed, ephemeral=True)
            return None, None

        voice_client = ctx.guild.voice_client

        if voice_client is not None and voice_client.is_connected():
            if voice_client.channel and voice_client.channel.id != channel.id:
                await voice_client.move_to(channel)

            return voice_client, channel

        voice_client = await channel.connect(timeout=20.0, reconnect=False)

        if voice_client is None or not voice_client.is_connected():
            try:
                await voice_client.disconnect(force=True)
            except Exception:
                pass

            embed = create_embed("Failed to connect to the voice channel.")
            if deferred:
                await ctx.followup.send(embed=embed, ephemeral=True)
            else:
                await ctx.respond(embed=embed, ephemeral=True)
            return None, None

        return voice_client, channel

    async def play_song(self, voice_client: discord.VoiceClient, song: parsers.Song):
        done = asyncio.Event()

        def after_playback(error):
            self.bot.loop.call_soon_threadsafe(done.set)

        source = discord.FFmpegPCMAudio(
            song.url,
            executable="/usr/bin/ffmpeg",
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        )

        voice_client.play(source, after=after_playback)
        await done.wait()

    @discord.slash_command(name="song", description="Plays a song.")
    async def _song(self, ctx, song_name: Option(str, "Song Name", autocomplete=get_songs, required=True)):
        voice_client = ctx.guild.voice_client
        if voice_client is not None and voice_client.is_playing():
            embed = create_embed("I'm already playing a song. Please wait until it's finished.")
            await ctx.respond(embed=embed, ephemeral=True)
            return

        await ctx.defer()

        with open("data/songs.json", "r", encoding="utf-8") as fp:
            data = json.load(fp)

        song_data = next(
            (s for s in data["songs"] if s["title"].lower() == song_name.lower()),
            None,
        )

        if song_data is None:
            embed = create_embed("Song not found.")
            await ctx.followup.send(embed=embed, ephemeral=True)
            return

        song = parsers.Song.from_dict(song_data)

        voice_client, channel = await self.ensure_voice(ctx, deferred=True)
        if voice_client is None:
            return

        await ctx.followup.send(embed=create_embed(f"Starting `{song.title}` in <#{channel.id}>"))

        try:
            await self.play_song(voice_client, song)
            await ctx.channel.send(embed=create_embed(f"Finished playing `{song.title}` in <#{channel.id}>"))
        finally:
            if voice_client.is_connected():
                await voice_client.disconnect(force=True)

    @discord.slash_command(name="songs_all", description="Plays all songs.")
    async def _all_songs(self, ctx):
        voice_client = ctx.guild.voice_client
        if voice_client is not None and voice_client.is_playing():
            embed = create_embed("I'm already playing a song. Please wait until it's finished.")
            await ctx.respond(embed=embed, ephemeral=True)
            return

        await ctx.defer()

        with open("data/songs.json", "r", encoding="utf-8") as fp:
            data = json.load(fp)

        songs = data["songs"]

        voice_client, channel = await self.ensure_voice(ctx, deferred=True)
        if voice_client is None:
            return

        await ctx.followup.send(embed=create_embed("Starting all songs."))

        status_message = await ctx.channel.send(
            embed=create_embed("Playing all songs. Please wait...")
        )

        self.playlist_active = True
        self.stop_playlist_requested = False

        try:
            for song_data in songs:
                current_vc = ctx.guild.voice_client
                if current_vc is None or not current_vc.is_connected():
                    break

                if self.stop_playlist_requested:
                    break

                song = parsers.Song.from_dict(song_data)

                embed = create_embed("Playing all songs. Currently playing `%s` in <#%s>" % (song.title, channel.id))
                await status_message.edit(embed=embed)

                await self.play_song(current_vc, song)

            if self.stop_playlist_requested:
                await status_message.edit(embed=create_embed("Playlist stopped."))
            else:
                await status_message.edit(embed=create_embed("Finished playing all songs."))
        finally:
            self.playlist_active = False
            self.stop_playlist_requested = False

            current_vc = ctx.guild.voice_client
            if current_vc is not None and current_vc.is_connected():
                await current_vc.disconnect(force=True)

    @discord.slash_command(name="skip", description="Skips to the next song during songs_all.")
    async def _skip_song(self, ctx):
        voice_client = ctx.guild.voice_client
        if voice_client is None or not voice_client.is_connected() or not voice_client.is_playing():
            await ctx.respond(embed=create_embed("I'm not currently playing a song."), ephemeral=True)
            return

        if not self.playlist_active:
            await ctx.respond(embed=create_embed("Skip can only be used during `/songs_all`.") , ephemeral=True)
            return

        voice_client.stop()
        await ctx.respond(embed=create_embed("Skipped to the next song."))

    @discord.slash_command(name="stop", description="Stops playing a song.")
    async def _stop_song(self, ctx):
        voice_client = ctx.guild.voice_client
        if voice_client is None or not voice_client.is_connected():
            embed = create_embed("I'm not playing a song.")
            await ctx.respond(embed=embed, ephemeral=True)
            return

        if self.playlist_active:
            self.stop_playlist_requested = True

        if voice_client.is_playing():
            voice_client.stop()

        await voice_client.disconnect(force=True)

        embed = create_embed("Stopped playing.")
        await ctx.respond(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        voice_client = member.guild.voice_client
        if voice_client is None or not voice_client.is_connected() or voice_client.channel is None:
            return

        if member.id == self.bot.user.id:
            return

        non_bot_members = [m for m in voice_client.channel.members if not m.bot]
        if not non_bot_members:
            if self.playlist_active:
                self.stop_playlist_requested = True

            if voice_client.is_playing():
                voice_client.stop()

            await voice_client.disconnect(force=True)