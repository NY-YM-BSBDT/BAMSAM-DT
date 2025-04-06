import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv

# 🔐 .env 파일에서 토큰 불러오기
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix='!', intents=intents)

queue = []
idle_timer = {}
# 🎵 유튜브 스트림 주소 가져오기
def get_stream_url(url):
    ydl_opts = {
        'format': 'bestaudio',
        'quiet': True,
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        duration = info.get("duration", 0)
        return info['url'], info.get('title', 'Unknown'), duration, info.get("webpage_url", url), info.get("thumbnail")

# ⏰ 유휴 상태 타이머 (60초)
async def start_idle_timer(vc, ctx):
    await asyncio.sleep(60)
    if vc.is_connected() and not vc.is_playing():
        await vc.disconnect()
        try:
            await ctx.send("60초간 활동이 없어 음성 채널과 연결을 해제합니다.")
        except discord.HTTPException:
            pass  # 메시지 채널이 없거나 메시지 전송 실패시 무시

# 🎧 가상 목록의 음악을 재생
async def play_music(vc, ctx):
    if queue:
        url = queue.pop(0)
        stream_url, title, duration, page_url, thumbnail = get_stream_url(url)

        minutes, seconds = divmod(duration, 60)
        duration_str = f"{minutes}:{str(seconds).zfill(2)}"

        vc.play(
            discord.FFmpegPCMAudio(stream_url),
            after=lambda e: asyncio.run_coroutine_threadsafe(play_music(vc, ctx), bot.loop)
        )

        embed = discord.Embed(
            title="[{title}]({page_url})",
            description=f"[{title}]({page_url})\n⏱️ 길이: `{duration_str}`",
            color=0x1abc9c
        )
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        await ctx.send(embed=embed)
    else:
        await start_idle_timer(vc, ctx)

# 🎧 음악 재생 명령어
@bot.command(name="p")
async def play_music(ctx, *, url):
    if not ctx.author.voice:
        return await ctx.send("❗ 먼저 음성 채널에 들어가 주세요.")

    voice_channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        vc = await voice_channel.connect()
    else:
        vc = ctx.voice_client

    queue.append(url)

    if not vc.is_playing():
        await play_music(vc, ctx)
    else:
        stream_url, title, _, page_url, _ = get_stream_url(url)
        embed = discord.Embed(
            title="Music",
            description=f"[{title}]({page_url})을(를) 재생목록에 추가했습니다.",
            color=0x1abc9c
        )
        await ctx.send(embed=embed)

# ⏭️ 스킵 명령어
@bot.command(name="skip")
async def skip_music(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send(embed=discord.Embed(
            title="Music",
            description=f"[{title}]({page_url})을(를) 건너뜁니다.",
            color=0x1abc9c
        ))
    else:
        await ctx.send("❗ 지금 재생 중인 음악이 없어요!")

# 📛 정지 명령어
@bot.command(name="leave")
async def stop_music(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    else:
        await ctx.send("❗ 이미 음성 채널에 없어요!")

# 👋 서버 입장 시 닉네임 설정 + 역할 부여
@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="step-1")
    if not channel:
        return

    embed = discord.Embed(
         title="Nickname",
        description=(
            "뱀샘크루에서 사용할 닉네임을 적어주세요. 닉네임은 아래와 같이 표시됩니다."
            "べムセムクルーで使うニックネームを書いてください。 ニックネームは以下のように表示されます。"
            "```༺ৡۣۜ͜ ৡ Nickname ৡۣۜ͜ ৡ༻```"
        ),
        color=0x3498db
    )

    await channel.send(embed=embed, delete_after=28800)

    def check(msg):
        return msg.author == member and msg.channel == channel

    try:
        msg = await bot.wait_for('message', check=check)
        raw_nickname = msg.content.strip()
        formatted_nickname = f"༺ৡۣۜ͜ ৡ {raw_nickname} ৡۣۜ͜ ৡ༻"

        await member.edit(nick=formatted_nickname)
        role = discord.utils.get(member.guild.roles, name="게스트 / GUEST")

        if role:
            await member.add_roles(role)
    except discord.Forbidden:
        await channel.send(f"{member.mention} ⚠️ 닉네임 변경 또는 역할 부여 권한이 없어요.")
    except Exception as e:
        await channel.send(f"{member.mention} ⚠️ 오류가 발생했어요: {e}")

bot.run(TOKEN)