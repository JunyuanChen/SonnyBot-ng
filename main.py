#!/usr/bin/env python3
# coding: utf-8

import os
import time

import discord
import discord.ext.commands
from discord_slash import SlashCommand, SlashContext

import logger
import storage
import timer

from concerns import (
    user_stat,
    calc_exp,
    calc_coins,
    dmoj,
    chat,
    fun
)


storage.sync()  # Pull remote change
timer.sync_to_remote()


logger.LOGGERS = [
    logger.ConsoleLogger()
]


bot = discord.ext.commands.Bot(
    command_prefix=".",
    intents=discord.Intents.all(),
    help_command=None
)


slash = SlashCommand(bot, sync_commands=True)
guild_id = [762065730191228929]

require_admin = discord.ext.commands.has_permissions(administrator=True)


async def change_exp_subtask(ctx, user, amount):
    """
    Change user's EXP by amount.

    This function handles level change, associated coin changes, and
    associated chat announcements.

    When a user's EXP changes, they may upgrade to a higher level or
    downgrade to a lower level.  Correspondingly, they will receive or
    lose some coins, and a chat message will be sent, announcing the
    upgrade or downgrade.
    """
    old_level = user.level
    user.level, user.exp = calc_exp.recalc_level(user.level, user.exp, amount)
    if user.level == -1:
        # User's level and EXP is insufficient for the change.
        # Operation should be cancelled.
        #
        # Example: old level = 0, old exp = 5, amount = -100
        #
        # NOTE Do NOT assert user.level > -1 here, since it will raise
        # "hidden" AssertionError (i.e. it is not obvious that this
        # function will raise AssertionError).  Better make it explicit
        # in parent function.  Example:
        # try:
        #     await change_exp_subtask(ctx, user, -100)
        #     assert user.level > -1  # (1) Assert HERE
        # except AssertionError:
        #     # Now it is obvious this error comes from (1)
        return
    if user.level > old_level:
        coins = calc_coins.level_up_reward(old_level, user.level)
        coins = calc_coins.with_booster(user, coins)
        user.coins += coins
        await ctx.send(f"<@{user.id}> upgraded to Level {user.level} "
                       f"and was rewarded {coins} coins!")
        return True
    if user.level < old_level:
        await ctx.send(f"<@{user.id}> downgraded to Level "
                       f"{user.level}")
        return False

    if amount > 0:
        await ctx.send(f"<@{user.id}> gained {amount} exp!")
    elif amount < 0:
        await ctx.send(f"<@{user.id}> lost {amount} exp!")
    return None


@slash.slash(
    name="redeploy",
    description="Redeploy bot",
    guild_ids=guild_id
)
@require_admin
async def _redeploy(ctx: SlashContext):
    import subprocess
    try:
        subprocess.run(["git", "pull", "origin"], check=True)
        subprocess.Popen(["python3", "main.py"])
        await ctx.send("Successfully redeployed! Restarting...")
        exit()
    except subprocess.CalledProcessError as e:
        logger.error(f"Redeployment failed with {e.returncode}: {e.cmd}")
        await ctx.send("Failed to redeploy - see logs for details")


@slash.slash(
    name="stat",
    description="Shows user stat",
    guild_ids=guild_id
)
async def _stat(ctx: SlashContext, member: discord.Member = None):
    member = ctx.author if member is None else member

    with storage.LOCK:
        try:
            user = storage.User.load(member.id)
            users = calc_exp.rank_users(storage.User.all())
            rank = users.index(user)
            ahead = [
                x for x in users[:rank]
                if ctx.guild.get_member(x.id) is not None
            ]
            stat_img = user_stat.draw_stat(
                await chat.get_avatar(member), member.name, user.level,
                len(ahead) + 1, user.exp, user.coins, user.msg_count
            )
            img_file = discord.File(stat_img)
            await ctx.send(file=img_file)
            img_file.close()
            os.unlink(stat_img)
            storage.flush()  # Checkpoint
        except KeyError:
            await ctx.send(f"User <@{member.id}> not found!")


@slash.slash(
    name="leaderboard",
    description="Shows leaderboard",
    guild_ids=guild_id
)
async def _leaderboard(ctx: SlashContext):
    with storage.LOCK:
        users = storage.User.all()
        avatars = []
        names = []
        levels = []
        for user in calc_exp.rank_users(users):
            member = ctx.guild.get_member(user.id)
            if member is not None:
                avatars.append(await chat.get_avatar(member))
                names.append(member.name)
                levels.append(user.level)
                if len(names) == 10:
                    break
        leaderboard_img = user_stat.leaderboard(avatars, names, levels)
        img_file = discord.File(leaderboard_img)
        await ctx.send(file=img_file)
        img_file.close()
        os.unlink(leaderboard_img)


@slash.slash(
    name="removeUser",
    description="Removes user from database",
    guild_ids=guild_id
)
@require_admin
async def _removeUser(ctx: SlashContext, member: discord.Member):
    with storage.LOCK:
        try:
            storage.User.load(member.id).destroy()
            reply = f"User <@{member.id}> has been deleted!"
        except KeyError:
            logger.debug(f"removeUser: User {member.id} not found")
            reply = f"User <@{member.id}> not found!"
        except storage.StorageError as e:
            reply = str(e)
    await ctx.send(reply)


@slash.slash(
    name="changeEXP",
    description="Changes user xp",
    guild_ids=guild_id
)
@require_admin
async def _changeEXP(ctx: SlashContext, member: discord.Member, amount: int):
    with storage.LOCK:
        try:
            user = storage.User.load(member.id)
            await change_exp_subtask(ctx, user, amount)
            assert user.level > -1
            user.save()
            storage.commit(f"Change EXP of User {member.id} by {amount}")
            reply = f"<@{member.id}>'s EXP has been updated by {amount}!"
        except AssertionError:
            reply = f"<@{member.id}> does not have enough EXP!"
        except KeyError:
            reply = f"User <@{member.id}> not found!"
        except storage.StorageError as e:
            reply = str(e)
    await ctx.send(reply)


@slash.slash(
    name="changeCoins",
    description="Changes user coins",
    guild_ids=guild_id
)
@require_admin
async def _changeCoins(ctx: SlashContext, member: discord.Member, amount: int):
    with storage.LOCK:
        try:
            user = storage.User.load(member.id)
            user.coins += amount
            assert user.coins >= 0
            user.save()
            storage.commit(f"Change coins of User {member.id} by {amount}")
            reply = f"<@{member.id}>'s coins has been updated by {amount}!"
        except AssertionError:
            reply = f"<@{member.id}> does not have enough coins!"
        except KeyError:
            reply = f"User <@{member.id}> not found!"
        except storage.StorageError as e:
            reply = str(e)
    await ctx.send(reply)


@slash.slash(
    name="changeMsgSent",
    description="Changes value of msg sent",
    guild_ids=guild_id
)
@require_admin
async def _changeMsgSent(
        ctx: SlashContext,
        member: discord.Member,
        amount: int
):
    with storage.LOCK:
        try:
            user = storage.User.load(member.id)
            user.msg_count += amount
            assert user.msg_count >= 0
            user.save()
            storage.commit(f"Change message count of "
                           f"User {member.id} by {amount}")
            reply = (f"<@{member.id}>'s message count "
                     f"has been updated by {amount}!")
        except AssertionError:
            reply = f"<@{member.id}>'s message count can't be negative!"
        except KeyError:
            reply = f"User <@{member.id}> not found!"
        except storage.StorageError as e:
            reply = str(e)
    await ctx.send(reply)


@slash.slash(
    name="giveCoinBooster",
    description="Give the user Coin Booster (negative to remove)",
    guild_ids=guild_id
)
async def _giveCoinBooster(
        ctx: SlashContext,
        member: discord.Member,
        days: float
):
    with storage.LOCK:
        try:
            user = storage.User.load(member.id)
            if user.coin_booster < time.time():
                user.coin_booster = time.time()
            user.coin_booster += days * 24 * 3600
            user.save()
            storage.commit(f"Give {days}-day Coin Booster to User {member.id}")
            ndays = round((user.coin_booster - time.time()) / (24 * 3600), 3)
            if ndays > 0:
                reply = (f"<@{member.id}>, your coin booster is active and "
                         f"will expire after {ndays} days! "
                         "Go earn some coins!")
            else:
                reply = f"<@{member.id}>, your coin booster is now expired!"
        except KeyError:
            reply = f"User <@{member.id}> not found!"
        except storage.StorageError as e:
            reply = str(e)
    await ctx.send(reply)


@slash.slash(
    name="giveExpBooster",
    description="Give the user Exp Booster (negative to remove)",
    guild_ids=guild_id
)
async def _giveExpBooster(
        ctx: SlashContext,
        member: discord.Member,
        days: float
):
    with storage.LOCK:
        try:
            user = storage.User.load(member.id)
            if user.exp_booster < time.time():
                user.exp_booster = time.time()
            user.exp_booster += days * 24 * 3600
            user.save()
            storage.commit(f"Give {days}-day Exp Booster to User {member.id}")
            ndays = round((user.exp_booster - time.time()) / (24 * 3600), 3)
            if ndays:
                reply = (f"<@{member.id}>, your exp booster is active and "
                         f"will expire after {ndays} days! Go earn some exp!")
            else:
                reply = f"<@{member.id}>, your exp booster is now expired!"
        except KeyError:
            reply = f"User <@{member.id}> not found!"
        except storage.StorageError as e:
            reply = str(e)
    await ctx.send(reply)


@slash.slash(
    name="purchaseCoinBooster",
    description="Purchase the 2-day 2x Coin Booster (Price: $75)",
    guild_ids=guild_id
)
async def _purchaseCoinBooster(ctx: SlashContext):
    member = ctx.author
    with storage.LOCK:
        try:
            user = storage.User.load(member.id)
            user.coins -= 75
            assert user.coins >= 0
            if user.coin_booster < time.time():
                user.coin_booster = time.time()
            user.coin_booster += 2 * 24 * 3600
            user.save()
            storage.commit(f"Purchase Coin Booster for User {member.id}")
            ndays = round((user.coin_booster - time.time()) / (24 * 3600), 3)
            reply = (f"<@{member.id}>, your coin booster is active and "
                     f"will expire after {ndays} days! Go earn some coins!")
        except AssertionError:
            reply = f"<@{member.id}>, you don't have enough coins!"
        except KeyError:
            reply = f"User <@{member.id}> not found!"
        except storage.StorageError as e:
            reply = str(e)
    await ctx.send(reply)


@slash.slash(
    name="purchaseExpBooster",
    description="Purchase the 2-day 2x Exp Booster (Price: $50)",
    guild_ids=guild_id
)
async def _purchaseExpBooster(ctx: SlashContext):
    member = ctx.author
    with storage.LOCK:
        try:
            user = storage.User.load(member.id)
            user.coins -= 50
            assert user.coins >= 0
            if user.exp_booster < time.time():
                user.exp_booster = time.time()
            user.exp_booster += 2 * 24 * 3600
            user.save()
            storage.commit(f"Purchase Exp Booster for User {member.id}")
            ndays = round((user.exp_booster - time.time()) / (24 * 3600), 3)
            reply = (f"<@{member.id}>, your exp booster is active and "
                     f"will expire after {ndays} days! Go earn some exp!")
        except AssertionError:
            reply = f"<@{member.id}>, you don't have enough coins!"
        except KeyError:
            reply = f"User <@{member.id}> not found!"
        except storage.StorageError as e:
            reply = str(e)
    await ctx.send(reply)


@slash.slash(
    name="showBoosters",
    description="Show currently active boosters",
    guild_ids=guild_id
)
async def _showBoosters(ctx: SlashContext, member: discord.Member = None):
    member = ctx.author if member is None else member
    with storage.LOCK:
        try:
            user = storage.User.load(member.id)
            coin = round((user.coin_booster - time.time()) / (24 * 3600), 3)
            exp = round((user.exp_booster - time.time()) / (24 * 3600), 3)
            if coin > 0:
                coin_msg = f"your coin booster will expire in {coin} days"
            else:
                coin_msg = "you have no coin booster"
            if exp > 0:
                exp_msg = f"your exp booster will expire in {exp} days"
            else:
                exp_msg = "you have no exp booster"
            reply = f"<@{member.id}>, {coin_msg} and {exp_msg}!"
        except KeyError:
            reply = f"User <@{member.id}> not found!"
    await ctx.send(reply)


@slash.slash(
    name="transactCoins",
    description="Transacts coins from user to user",
    guild_ids=guild_id
)
async def _transactCoins(
        ctx: SlashContext,
        member: discord.Member,
        amount: int
):
    """ Transact amount to user_id. """
    author = ctx.author
    logger.debug(f"transactCoins: {author.id} --({amount})--> {member.id}")
    with storage.LOCK:
        try:
            amount = int(amount)
            assert amount > 0
            sender = storage.User.load(author.id)
            receiver = storage.User.load(member.id)
            sender.coins -= amount
            receiver.coins += amount
            assert sender.coins >= 0
            sender.save()
            receiver.save()
            storage.commit(f"Transact {amount} coins from "
                           f"User {sender.id} to User {receiver.id}")
            reply = (f"<@{sender.id}> successfully transacted "
                     f"{amount} coins to <@{receiver.id}>!")
        except AssertionError:
            if amount <= 0:
                reply = f"<@{sender.id}>, amount must be positive!"
            else:
                reply = f"<@{sender.id}>, you don't have enough coins!"
        except KeyError:
            reply = f"User <@{member.id}> not found!"
        except storage.StorageError as e:
            reply = str(e)
    await ctx.send(reply)


@slash.slash(
    name="gamble",
    description="Gamble using 30 coins (max reward: 100 coins).",
    guild_ids=guild_id
)
async def _gamble(ctx: SlashContext):
    member = ctx.author
    with storage.LOCK:
        try:
            user = storage.User.load(member.id)
            user.coins -= 30
            assert user.coins >= 0
            coins = fun.gamble()
            user.coins += coins
            user.save()
            storage.commit(f"Gamble: User {member.id}: -30 +{coins}")
            reply = f"<@{member.id}>, you received {coins} coins!"
        except AssertionError:
            reply = f"<@{member.id}>, you do not have enough coins!"
        except KeyError:
            reply = f"User <@{member.id}> not found!"
        except storage.StorageError as e:
            reply = str(e)
    await ctx.send(reply)


@slash.slash(
    name="resetUserStat",
    description="Resets user stats",
    guild_ids=guild_id
)
@require_admin
async def _resetUserStat(ctx: SlashContext, member: discord.Member):
    with storage.LOCK:
        try:
            user = storage.User.load(member.id)
            user.exp = 0
            user.level = 0
            user.coins = 0
            user.msg_count = 0
            user.save()
            storage.commit(f"Reset stat for User {member.id}", no_error=True)
            reply = (f"<@{member.id}>'s stats are reset! "
                     f"(CCC progress not included)")
        except KeyError:
            reply = f"User <@{member.id}> not found!"
        except storage.StorageError as e:
            reply = str(e)
    await ctx.send(reply)


@slash.slash(
    name="connectDMOJAccount",
    description="Connects user to DMOJ account",
    guild_ids=guild_id
)
async def _connectDMOJAccount(ctx: SlashContext, username: str):
    author = ctx.author
    with storage.LOCK:
        try:
            user = storage.User.load(author.id)
            assert user.dmoj_username is None

            rewards = dmoj.connect(user, username)
            if rewards is None:
                await ctx.send(f"<@{author.id}>, cannot connect DMOJ Account "
                               f"{username}! Please ensure the account exists "
                               f"and have finished at least 1 CCC problem.")
                return

            exp_reward, coin_reward = rewards
            exp_reward = calc_exp.with_booster(user, exp_reward)
            await change_exp_subtask(ctx, user, exp_reward)
            if coin_reward:
                coin_reward = calc_coins.with_booster(user, coin_reward)
                user.coins += coin_reward
                await ctx.send(f"<@{author.id}> earned {coin_reward} coins!")

            user.save()
            storage.commit(f"Connect User {author.id} to DMOJ {username}")
            await ctx.send(f"<@{author.id}>, you have successfully "
                           f"connected to DMOJ Account {username}!")
        except KeyError:
            await ctx.send(f"User <@{author.id}> not found!")
        except AssertionError:
            await ctx.send(f"<@{author.id}>, you have already connected "
                           f"to a DMOJ Account ({user.dmoj_username})!")
        except dmoj.RequestException as e:
            logger.error(f"{type(e).__name__}: {e}")
            await ctx.send("Network errors encountered - see logs for details")
        except storage.StorageError as e:
            await ctx.send(str(e))


@slash.slash(
    name="getDMOJAccount",
    description="Gets user DMOJ account",
    guild_ids=guild_id
)
async def _getDMOJAccount(ctx: SlashContext, member: discord.Member = None):
    member = ctx.author if member is None else member
    with storage.LOCK:
        try:
            user = storage.User.load(member.id)
            name = user.dmoj_username
            await ctx.send(f"<@{member.id}>, your DMOJ Account is: {name}!")
        except KeyError:
            await ctx.send(f"User <@{member.id}> not found!")


@slash.slash(
    name="fetchCCCProgress",
    description="Fetched user DMOJ progress",
    guild_ids=guild_id
)
async def _fetchCCCProgress(ctx: SlashContext, member: discord.Member = None):
    member = ctx.author if member is None else member
    with storage.LOCK:
        try:
            user = storage.User.load(member.id)
            exp_reward, coin_reward = dmoj.update(user)
            exp_reward = calc_exp.with_booster(user, exp_reward)
            await change_exp_subtask(ctx, user, exp_reward)
            if coin_reward:
                coin_reward = calc_coins.with_booster(user, coin_reward)
                user.coins += coin_reward
                await ctx.send(f"<@{member.id}> earned {coin_reward} coins!")
            user.save()
            storage.commit(f"Update CCC progress for User {member.id}",
                           no_error=True)
            await ctx.send(f"<@{member.id}>, your CCC progress is updated!")
        except KeyError:
            await ctx.send(f"User <@{member.id}> not found!")
        except dmoj.RequestException as e:
            logger.error(f"{type(e).__name__}: {e}")
            await ctx.send("Network errors encountered - see logs for details")
        except storage.StorageError as e:
            await ctx.send(str(e))


@slash.slash(
    name="CCCProgressList",
    description="Gets user CCC progress",
    guild_ids=guild_id
)
async def _CCCProgressList(ctx: SlashContext):
    member = ctx.author
    reply = ""
    try:
        user = storage.User.load(member.id)
        for problem in dmoj.CCC_PROBLEMS:
            if problem in user.ccc_progress:
                progress = user.ccc_progress[problem]
                problem_name = dmoj.CCC_PROBLEMS[problem]["name"]
                reply += f"User has completed {progress}% of {problem_name}\n"
                if(len(reply) >= 1500):
                    await member.send(reply)
                    reply = ""
        if reply:
            await member.send(reply)
        await ctx.send(f"<@{member.id}>, your progress list "
                       f"has been sent to your DMs!")
    except KeyError:
        await ctx.send(f"User <@{member.id}> not found!")
    except dmoj.RequestException as e:
        logger.error(f"{type(e).__name__}: {e}")
        await ctx.send("Network errors encountered - see logs for details")
    except storage.StorageError as e:
        await ctx.send(str(e))


@slash.slash(
    name="mute",
    description="Mutes user",
    guild_ids=guild_id
)
@require_admin
async def _mute(ctx: SlashContext, member: discord.Member, reason=None):
    role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not role:
        role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(
                role,
                speak=False,
                send_messages=False
            )

    await member.add_roles(role)
    await ctx.send(f"<@{member.id}> was muted by <@{ctx.author.id}>. "
                   f"Reason: {reason}")


@slash.slash(
    name="unmute",
    description="Unmutes user",
    guild_ids=guild_id
)
@require_admin
async def _unmute(ctx: SlashContext, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name="Muted")
    await member.remove_roles(role)
    await ctx.send(f"<@{member.id}> is now unmuted")


@slash.slash(
    name="addRole",
    description="Adds Role",
    guild_ids=guild_id
)
@require_admin
async def _addRole(ctx: SlashContext, member: discord.Member, role_name):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.guild.create_role(name=role_name)
    await member.add_roles(role)


@slash.slash(
    name="removeRole",
    description="Removes role",
    guild_ids=guild_id
)
@require_admin
async def _removeRole(ctx: SlashContext, member: discord.Member, role_name):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    await member.remove_roles(role)


@slash.slash(
    name="syncData",
    description="Syncs data to remote",
    guild_ids=guild_id
)
@require_admin
async def _syncData(ctx: SlashContext):
    logger.debug("[Command] syncData")
    with storage.LOCK:
        try:
            storage.sync()
            await ctx.send("Successfully synced to remote!")
        except storage.StorageError as e:
            await ctx.send(str(e))


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")


@bot.event
async def on_message(message: discord.Message):
    if message.author.id == bot.user.id:
        # This message is sent by bot itself, ignore it.
        return

    server = message.guild.name
    channel = bot.get_channel(chat.bot_channel(server))

    user = storage.User.load_or_create(message.author.id)
    user.msg_count += 1
    exp_reward = calc_exp.chat_msg_reward(message.content)
    exp_reward = calc_exp.with_booster(user, exp_reward)
    upgraded = await change_exp_subtask(channel, user, exp_reward)
    user.save()
    # NOTE No commit here, because we do NOT want commits for every
    # single message.  Instead, user.save() will save data to disk.
    # Later, they will be bundled into the next commit, or flushed as
    # part of sync().  Obviously, user._snap will be updated as well.

    # ... except if the user is upgraded.  In this case, we have made a
    # chat announcement.  This is a checkpoint that occurs not as often.
    if upgraded:
        try:
            storage.commit(f"Upgrade User {user.id} to Lvl. {user.level}")
        except storage.StorageError as e:
            await channel.send(str(e))

    ctx = await bot.get_context(message)

    if ctx.command:
        await ctx.message.delete()

    await bot.process_commands(message)


@bot.event
async def on_member_join(member: discord.Member):
    server = member.guild.name
    channel = bot.get_channel(chat.bot_channel(server))
    storage.User.load_or_create(member.id)
    await channel.send(f"User <@{member.id}> has joined the server!")


if __name__ == "__main__":
    bot.run(os.environ["BOT_TOKEN"])
