import os
import random
import asyncio
import discord
from discord.ext import commands
from discord import app_commands

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_CONFIGS = {
    100100100100100100: {
        "wait_vc_id": 110110110110110110,
        "category_id": 120120120120120120,
        "admin_ids": [111111111111111111, 222222222222222222],
        "notify_role_id": 130130130130130130,
        "move_target_role_id": 130130130130130130,
    },
    200200200200200200: {
        "wait_vc_id": 210210210210210210,
        "category_id": 220220220220220220,
        "admin_ids": [111111111111111111, 222222222222222222, 333333333333333333],
        "notify_role_id": 230230230230230230,
        "move_target_role_id": 230230230230230230,
        "profile_chat_ids": [211111111111111111, 222222222222222222],
        "profile_vc_exclude": [210210210210210210],
    },
}

VC_ROOM_SIZE = 4
TIMER_MINUTES = 10

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

def is_admin(user, guild_id):
    return user.id in GUILD_CONFIGS[guild_id]["admin_ids"]

async def simple_vc_shuffle(inter, guild_id):
    cfg = GUILD_CONFIGS[guild_id]
    guild = inter.guild
    wait_vc = guild.get_channel(cfg["wait_vc_id"])
    category = guild.get_channel(cfg["category_id"])
    rooms = [ch for ch in category.voice_channels if ch.name.startswith("会議VC")]
    targets = [m for m in wait_vc.members if not m.bot]
    random.shuffle(targets)
    chunks = [targets[i:i+VC_ROOM_SIZE] for i in range(0, len(targets), VC_ROOM_SIZE)]
    for i, grp in enumerate(chunks):
        if i >= len(rooms):
            ch = await category.create_voice_channel(name=f"会議VC {i+1}", user_limit=VC_ROOM_SIZE)
            rooms.append(ch)
        for m in grp:
            try:
                await m.move_to(rooms[i])
            except: pass
    msg = "\n\n".join(f"{room.name}:\n" + "\n".join(m.display_name for m in grp) for grp, room in zip(chunks, rooms))
    await inter.channel.send(f"振り分け:\n{msg}")

async def simple_return(inter, guild_id):
    cfg = GUILD_CONFIGS[guild_id]
    guild = inter.guild
    wait_vc = guild.get_channel(cfg["wait_vc_id"])
    category = guild.get_channel(cfg["category_id"])
    rooms = [ch for ch in category.voice_channels if ch.name.startswith("会議VC")]
    for ch in rooms:
        for m in ch.members:
            try:
                await m.move_to(wait_vc)
            except: pass
    names = "\n".join([m.display_name for m in wait_vc.members if not m.bot])
    await inter.channel.send(f"集合VCメンバー:\n{names}")

async def simple_timer(inter, guild_id):
    cfg = GUILD_CONFIGS[guild_id]
    role = cfg["notify_role_id"]
    await inter.channel.send(f"⏰ タイマー開始（{TIMER_MINUTES}分）")
    await asyncio.sleep((TIMER_MINUTES-1)*60)
    await inter.channel.send(f"<@&{role}> 残り1分")
    await asyncio.sleep(60)
    await inter.channel.send(f"<@&{role}> タイムアップ")

@bot.tree.command(name="ランダム", description="会議VCランダム分け")
@app_commands.guilds(*GUILD_CONFIGS.keys())
async def randomeeting(inter: discord.Interaction):
    gid = inter.guild.id
    if not is_admin(inter.user, gid):
        await inter.response.send_message("管理者だけ", ephemeral=True)
        return
    await inter.response.defer()
    await simple_vc_shuffle(inter, gid)

@bot.tree.command(name="戻す", description="全員集合VCに戻す")
@app_commands.guilds(*GUILD_CONFIGS.keys())
async def returnall(inter: discord.Interaction):
    gid = inter.guild.id
    if not is_admin(inter.user, gid):
        await inter.response.send_message("管理者だけ", ephemeral=True)
        return
    await inter.response.defer()
    await simple_return(inter, gid)

@bot.tree.command(name="タイマー", description="タイマー通知")
@app_commands.guilds(*GUILD_CONFIGS.keys())
async def timer(inter: discord.Interaction):
    gid = inter.guild.id
    if not is_admin(inter.user, gid):
        await inter.response.send_message("管理者だけ", ephemeral=True)
        return
    await inter.response.defer()
    await simple_timer(inter, gid)

@bot.tree.command(name="人数", description="集合VC人数")
@app_commands.guilds(*GUILD_CONFIGS.keys())
async def member_count(inter: discord.Interaction):
    cfg = GUILD_CONFIGS[inter.guild.id]
    wait_vc = inter.guild.get_channel(cfg["wait_vc_id"])
    members = [m.display_name for m in wait_vc.members if not m.bot]
    await inter.response.send_message(f"{len(members)}人: " + ", ".join(members), ephemeral=True)

@bot.event
async def on_voice_state_update(member, before, after):
    try:
        if member.bot: return
        cfg = GUILD_CONFIGS.get(after.channel.guild.id) if after and after.channel else None
        if not cfg: return
        if after.channel and "profile_vc_exclude" in cfg and after.channel.id in cfg["profile_vc_exclude"]:
            return
        chat_ids = cfg.get("profile_chat_ids")
        if not chat_ids: return
        for cid in chat_ids:
            ch = member.guild.get_channel(cid)
            async for msg in ch.history(limit=50):
                if msg.author.id == member.id:
                    await after.channel.send(f"プロフィール: https://discord.com/channels/{member.guild.id}/{cid}/{msg.id}")
                    break
    except: pass

@bot.event
async def on_ready():
    print(f"Bot ready: {bot.user}")
    await bot.tree.sync()

if __name__ == "__main__":
    bot.run(TOKEN)
