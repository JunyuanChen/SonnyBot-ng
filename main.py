#!/usr/bin/env python3
# coding: utf-8

import io
import os
import threading

import discord
import discord.ext.commands

import logger
import storage

from concerns import (
    user_stat,
    calc_exp,
    calc_coins,
    dmoj,
    chat
)


storage.sync()  # Pull remote change


logger.LOGGERS = [
    logger.ConsoleLogger()
]


intents = discord.Intents.default()
intents.persences = True
intents.members = True
bot = discord.ext.commands.Bot(command_prefix=".",
                               intents=intents,
                               help_command=None)


# Storage access must be serialized
STORAGE_LOCK = threading.Lock()


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
        user.coins += coins
        await ctx.send(f"<@{user.id}> upgraded to Lvl. {user.level} "
                       f"and was rewarded {coins} coins!")
    elif user.level < old_level:
        coins = calc_coins.level_up_reward(user.level, old_level)
        coins = min(coins, user.coins)
        user.coins -= coins
        await ctx.send(f"<@{user.id}> downgraded to Lvl. "
                       f"{user.level} and lost {coins} coins!")


@bot.command()
async def stat(ctx, member: discord.Member = None):
    member = ctx.message.author if member is None else member
    avatar = io.BytesIO(await member.avatar_url_as(size=128).read())

    with STORAGE_LOCK:
        try:
            user = storage.User.load(member.id)
            users = storage.User.all()
            rank = calc_exp.rank_users(users).index(user)
            stat_img = user_stat.draw_stat(
                avatar, member.name, user.level, rank + 1,
                user.exp, user.coins, user.msg_count
            )
            await ctx.send(file=discord.File(stat_img))
            os.unlink(stat_img)
        except KeyError:
            await ctx.send(f"User <@{member.id}> not found!")


@bot.command()
async def leaderboard(ctx):
    with STORAGE_LOCK:
        users = storage.User.all()
        top_10 = calc_exp.rank_users(users)[:10]
        avatars = []
        usernames = []
        levels = []
        for user in top_10:
            member = ctx.guild.get_member(user.id)
            avatar_data = member.avatar_url_as(size=128)
            avatars.append(io.BytesIO(await avatar_data.read()))
            usernames.append(member.name)
            levels.append(user.level)
        img = user_stat.leaderboard(avatars, usernames, levels)
        await ctx.send(file=discord.File(img))
        os.unlink(leaderboard)


@bot.command()
@require_admin
async def removeUser(ctx, member: discord.Member):
    with STORAGE_LOCK:
        try:
            storage.User.load(member.id).destroy()
            reply = f"User <@{member.id}> has been deleted!"
        except KeyError:
            logger.debug(f"removeUser: User {member.id} not found")
            reply = f"User <@{member.id}> not found!"
        except storage.StorageError as e:
            reply = str(e)
    await ctx.send(reply)


@bot.command()
@require_admin
async def changeEXP(ctx, member: discord.Member, amount: int):
    with STORAGE_LOCK:
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


@bot.command()
@require_admin
async def changeCoins(ctx, member: discord.Member, amount: int):
    with STORAGE_LOCK:
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


@bot.command()
@require_admin
async def changeMessageSent(ctx, member: discord.Member, amount: int):
    with STORAGE_LOCK:
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


@bot.command()
async def transactCoins(ctx, member: discord.Member, amount: int):
    """ Transact amount to user_id. """
    author = ctx.message.author
    logger.debug(f"transactCoins: {author.id} --({amount})--> {member.id}")
    with STORAGE_LOCK:
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


@bot.command()
@require_admin
async def resetUserStat(ctx, member: discord.Member):
    with STORAGE_LOCK:
        try:
            user = storage.User.load(member.id)
            user.exp = 0
            user.level = 0
            user.coins = 0
            user.msg_count = 0
            user.save()
            storage.commit(f"Reset stat for User {member.id}")
            reply = (f"<@{member.id}>'s stats are reset! "
                     f"(CCC progress not included)")
        except KeyError:
            reply = f"User <@{member.id}> not found!"
        except storage.StorageError as e:
            reply = str(e)
    await ctx.send(reply)


@bot.command()
async def connectDMOJAccount(ctx, username: str):
    author = ctx.message.author
    with STORAGE_LOCK:
        try:
            user = storage.User.load(author.id)
            assert user.dmoj_username is None
            rewards = dmoj.connect(user, username)
            if rewards is None:
                await ctx.send(f"<@{author.id}>, cannot connect DMOJ Account "
                               f"{username}! Please ensure the account exists "
                               "and have finished at least 1 CCC problem.")
                return
            exp_reward, coin_reward = rewards
            await change_exp_subtask(ctx, user, exp_reward)
            if coin_reward:
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


@bot.command()
async def getDMOJAccount(ctx, member: discord.Member = None):
    member = ctx.message.author if member is None else member
    with STORAGE_LOCK:
        try:
            user = storage.User.load(member.id)
            if user.dmoj_username is None:
                await ctx.send(f"<@{member.id}>, you don't have "
                               "any DMOJ Account connected!")
            else:
                await ctx.send(f"<@{member.id}>, your DMOJ Account "
                               f"is {user.dmoj_username}!")
        except KeyError:
            await ctx.send(f"User <@{member.id}> not found!")


@bot.command()
async def fetchCCCProgress(ctx, member: discord.Member = None):
    member = ctx.message.author if member is None else member
    with STORAGE_LOCK:
        try:
            user = storage.User.load(member.id)
            exp_reward, coin_reward = dmoj.update(user)
            await change_exp_subtask(ctx, user, exp_reward)
            if coin_reward:
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


@bot.command()
@require_admin
async def syncData(ctx):
    logger.debug("[Command] syncData")
    with STORAGE_LOCK:
        try:
            storage.sync()
            await ctx.send("Successfully synced to remote!")
        except storage.StorageError as e:
            await ctx.send(str(e))


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")


@bot.event
async def on_member_join(member: discord.Member):
    server = member.guild.name
    channel = bot.get_channel(chat.bot_channel(server))
    storage.User.load_or_create(member.id)
    await channel.send(f"User <@{member.id}> has joined the server!")


if __name__ == '__main__':
    bot.run(os.environ["BotToken"])
