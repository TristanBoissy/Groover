import os
import threading, queue
import discord
from discord.ext.commands import Bot
import youtube_dl
from youtube_search import YoutubeSearch
import json
import time
import asyncio

client = Bot(command_prefix="-")

song_queue = []
bot_voice = []
thread_list = []
queue = queue.Queue()


def getChannel(ctx, channelName):
    return discord.utils.get(ctx.guild.voice_channels, name=channelName)


def getVoice(ctx):
    return discord.utils.get(client.voice_clients, guild=ctx.guild)


def updateBotVoice(ctx):
    bot_voice.append(getVoice(ctx))


def getYoutubeCodeFromSuffix(suffix):
    index = 0
    code_str = ""
    for i in range(0, len(suffix)):
        if suffix[i] == "=":
            index = i + 1
            break
    for i in range(index, len(suffix)):
        code_str += suffix[i]
    return code_str


def getSongURL(index):
    return "https://www.youtube.com/" + song_queue[index].get("url_suffix")


async def verifyPlayMessage(ctx, message):
    if len(message) < 7:
        await ctx.send("Groover needs a song to play")
        return False
    return True


async def sendPlayingSongMessage(song_url):
    await client.get_channel(song_queue[0].get("channelID")).send(
        "Groover is now playing : " + song_queue[0].get("title") + " \n" + song_url)


async def sendQueueMessage(ctx, index, song_url):
    await ctx.send(content="Queued " + song_queue[index].get("title") + " \n" +  song_url)


def verifyIfSongIsDownloaded(filename):
    for file in os.listdir("./"):
        if str(file.title()).lower() == str(filename).lower():
            return True
    return False

def verifyIfSameSongInPlaylist():
    if len(song_queue) == 1:
        return False
    for i in range(len(song_queue)-1):
        if song_queue[i+1].get("title") == song_queue[0].get("title"):
            return True
    return False

def deleteSongFile(filename):
    for file in os.listdir("./"):
        if str(file.title()).lower() == str(filename).lower():
            os.remove(file.title())

def deleteAllSongFile():
    for file in os.listdir("./"):
        if file.endswith(".mp3"):
            os.remove(file.title())

def tryToDownloadSong(url : str):
    youtube_options = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }],
    }
    try:
        if not verifyIfSongIsDownloaded(song_queue[len(song_queue) - 1].get("url_suffix")):
            with youtube_dl.YoutubeDL(youtube_options) as ydl:
                ydl.download([url])
    except:
        song_queue.pop(len(song_queue) - 1)
        return False
    return True


def playerManager():
    playVoiceSong()
    song_playing_thread = threading.Thread(target=returnWhenNotPlaying)
    song_playing_thread.start()


def playVoiceSong():
    #sendPlayingSongMessage(getSongURL(0))
    bot_voice[0].play(discord.FFmpegPCMAudio(song_queue[0].get("title") + "-" + getYoutubeCodeFromSuffix(song_queue[0].get("url_suffix")) + ".mp3"))


def returnWhenNotPlaying():
    queue.get()
    while bot_voice[0].is_playing():
        time.sleep(0.1)
    #if not verifyIfSameSongInPlaylist():
        #deleteSongFile(song_queue[0].get("title") + "-" + getYoutubeCodeFromSuffix(song_queue[0].get("url_suffix")) + ".mp3")
    queue.task_done()
    song_queue.pop(0)

    if not queue.empty():
        time.sleep(1)
        playerManager()
    else:
        deleteAllSongFile()


@client.event
async def on_ready():
    print("Groover is online")


@client.command()
async def play(ctx):
    try:
        updateBotVoice(ctx)

        if not bot_voice[0] == None and bot_voice[0].is_paused():
            await ctx.send("Please resume the music first!")
            return

        message = ctx.message.content
        if not await verifyPlayMessage(ctx, message): return
        youtube_keywords = message.replace("-play ", "")

        try:
            channel = getChannel(ctx, ctx.message.author.voice.channel.name)
        except:
            await ctx.send("You need to be in a channel")
            return

        result = json.loads(YoutubeSearch(youtube_keywords, max_results=1).to_json()).get("videos")[0]
        result.update({"channelID": ctx.message.channel.id})
        queue.put(result)
        song_queue.append(result)
        print(result.get("title") + "-" + getYoutubeCodeFromSuffix(result.get("url_suffix")) + ".mp3")

        if not verifyIfSongIsDownloaded(result.get("title") + "-" + getYoutubeCodeFromSuffix(result.get("url_suffix")) + ".mp3"):
            if not tryToDownloadSong(getSongURL(len(song_queue) - 1)):
                await ctx.send("Groover had a problem while downloading the song")
                return

        if bot_voice[0] == None:
            try:
                await channel.connect()
            except Exception as e:
                print(e)
            bot_voice.insert(0,getVoice(ctx))

        if bot_voice[0].is_playing():
            await sendQueueMessage(ctx, len(song_queue) - 1, getSongURL(len(song_queue)-1))

        else:
            playerManager()
            await sendPlayingSongMessage(getSongURL(0))

    except Exception as e:
        print(e)
        await ctx.send("Groover had a problem")
        return


@client.command()
async def quit(ctx):
    try:
        updateBotVoice(ctx)
        if bot_voice[0].is_connected:
            await ctx.send("See ya bitches")
            await bot_voice[0].disconnect()
        deleteAllSongFile()
    except:
        await ctx.send("Groover had a problem")


@client.command()
async def pause(ctx):
    try:
        updateBotVoice(ctx)
        if bot_voice[0].is_playing():
            bot_voice[0].pause()
        else:
            await ctx.send("Groover is paused already!")
    except:
        await ctx.send("Groover had a problem")

@client.command()
async def resume(ctx):
    try:
        updateBotVoice(ctx)
        if bot_voice[0].is_paused():
            bot_voice[0].resume()
        else:
            await ctx.send("Groover is already playing music!")
    except:
        await ctx.send("Groover had a problem")


@client.command()
async def skip(ctx):
    try:
        updateBotVoice(ctx)
        if bot_voice[0].is_playing():
            bot_voice[0].stop()
            await ctx.send("Groover has skipped " + song_queue[0].get("title"))
        else:
            await ctx.send("Groover is not playing music!")
    except:
        await ctx.send("Groover had a problem")


client.run('ODg3ODE4ODgxNTE3ODc5MzI2.YUJrxA.Gp2REvN3iQgxvqC4hOxd6BhqV3s')