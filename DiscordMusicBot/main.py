"""
1/2021, Discord-music bot
Author: Isoviita Antti-Jussi
Description: Simple Discord -music bot for private use,
             the bot is able to queue songs and will delete
             both user commands and status messages.
Commands:
    Play: Start playing or queue current song using url
    Skip: Skips current song
    Queue: Prints out current queue
    Clear: Clears out current queue
    Pause: Pauses music.
    Resume: Resumes music.
    Stop: Stops playing music and clears queue.
    Leave: Quits current voice channel and clears queue.
"""

import os
import discord
import youtube_dl
import asyncio

from discord import FFmpegPCMAudio
from discord.ext import commands
from dotenv import load_dotenv
from urllib.error import HTTPError

bot = commands.Bot(command_prefix="!")

# YouTube_dl options
ytdlFormat = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}
# FFmpeg options
FFmpeg_opts = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}
# Structure to keep track of queued songs
songQueue = {}


class ErrorHandler(commands.Cog, name='errors'):
    def __init__(self, client):
        self.bot = client

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # If user uses an unknown command
        if isinstance(error, commands.CommandNotFound):
            message = "Not a command."
        else:
            message = "Something went wrong."

        await ctx.send(message)


class Commands(commands.Cog, name='commands'):
    def __init__(self, client):
        self.bot = client
        self.voice = None
        self.channel = None
        self.client = discord.Client()

    def next_song(self, ctx):
        if len(songQueue) > 0:
            title = next(iter(songQueue))
            song = songQueue.pop(next(iter(songQueue)))
            try:
                self.voice.play(song, after=lambda x=None: self.next_song(ctx))
                self.client.loop.create_task(
                    self.channel.send("Now playing: " + title))
            except discord.errors.ClientException:
                return

    @staticmethod
    def search(url):
        with youtube_dl.YoutubeDL(ytdlFormat) as dl:
            try:
                info = dl.extract_info(url, download=False)
                title = info.get('title', None)
                iUrl = info['formats'][0]['url']

                source = FFmpegPCMAudio(iUrl, **FFmpeg_opts)
                songQueue[title] = source

            except HTTPError.code == 403:
                return

            except KeyError:
                return
        return title

    @commands.Cog.listener()
    async def on_message(self, ctx):

        if ctx.content.startswith('!'):
            await asyncio.sleep(10)
            await ctx.delete()

        elif ctx.author.bot:
            await asyncio.sleep(10)
            await ctx.delete()

    @commands.command()
    async def play(self, ctx, url: str):

        title = self.search(url)

        try:
            self.voice = await ctx.message.author.voice.channel.connect()
        except discord.ClientException:
            self.voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)

        channelID = ctx.channel.id
        self.channel = self.bot.get_channel(channelID)

        if ctx.voice_client.is_playing():
            message = "Song: " + title + " has been added to Queue.\nCurrent queue length: " + str(len(songQueue))
            await ctx.send(message)

        else:
            if len(songQueue) > 0:
                async with ctx.typing():
                    self.voice.play(source=songQueue[title], after=lambda e: Commands.next_song(self, ctx))
                    self.voice.is_playing()
            else:
                message = "Queue is empty."
                await ctx.send(message)

    @commands.command()
    async def skip(self, ctx):
        if not len(songQueue) > 0:
            await ctx.send("Queue is empty, can't skip")
            return

        self.voice.stop()

        try:
            title = next(iter(songQueue))
            self.voice.play(songQueue[title])
            songQueue.pop(title)

            if len(songQueue) > 0:
                message = "Current queue length: " + str(len(songQueue)) + "\nNow playing" + title
            else:
                message = "Now playing: " + title

        except IndexError:
            return

        await ctx.send(message)

    @commands.command()
    async def queue(self, ctx):
        if not len(songQueue) > 0:
            await ctx.send("There is no queue.")
            return
        else:
            await ctx.send("Current Queue: ")
            position = 1
            for i in songQueue:
                message = str(position) + ": " + i
                await ctx.send(message)

    @commands.command()
    async def clear(self, ctx):
        songQueue.clear()
        await ctx.send("The queue has been cleared.")

    @commands.command()
    async def pause(self, ctx):

        if self.voice.is_playing():
            self.voice.pause()
            message = "Music is now paused."
        else:
            message = "The bot is not currently playing music"

        await ctx.send(message)

    @commands.command()
    async def resume(self, ctx):

        if self.voice.is_paused():
            self.voice.resume()
        else:
            await ctx.send("The bot is currently playing music")

    @commands.command()
    async def stop(self, ctx):
        await self.clear(ctx)
        self.voice.stop()

    @commands.command()
    async def leave(self, ctx):
        # To determine if bot is already on a channel
        if self.voice:
            message = "Good Bye!"
            await self.clear(ctx)
            await self.voice.disconnect()
        else:
            message = "I am not currently on a voice channel"

        await ctx.send(message)


bot.add_cog(Commands(bot))
bot.add_cog(ErrorHandler(bot))

load_dotenv('BotToken.env')
bot.run(os.getenv('TOKEN'))
