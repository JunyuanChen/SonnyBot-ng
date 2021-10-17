#!/usr/bin/env python3
# coding: utf-8

import io
import os
import threading

import logger
import botutils
import storage

from concerns import (
    user_stat,
    calc_exp,
    calc_coins
)


storage.sync()  # Pull remote change


logger.LOGGERS = [
    logger.ConsoleLogger()
]


bot = botutils.setup_bot()


# Storage access must be serialized
STORAGE_LOCK = threading.lock()


@botutils.command(bot)
async def stat(ctx, user_id=None):
    if user_id is None:
        user_id = ctx.author.id

    member = ctx.guild.get_member(user_id)
    avatar = io.BytesIO(await member.avatar_url_as(size=128).read())

    with STORAGE_LOCK:
        try:
            user = storage.User.load(user_id)
            users = storage.User.all()
            rank = calc_exp.rank_users(users).index(user)
            stat_img = user_stat.draw_stat(
                avatar, member.name, user.level, rank + 1,
                user.exp, user.coins, user.msg_count
            )
            await ctx.send(file=botutils.File(stat_img))
            os.unlink(stat_img)
        except KeyError:
            await ctx.send(f"User <@{user_id}> not found!")
        except storage.StorageError as e:
            await ctx.send(str(e))


@botutils.admin_command(bot)
async def removeUser(ctx, user_id):
    with STORAGE_LOCK:
        try:
            storage.User.load(user_id).destroy()
            await ctx.send(f"User <@{user_id}> has been deleted")
        except KeyError:
            logger.debug(f"removeUser: User {user_id} not found")
            await ctx.send(f"User <@{user_id}> not found!")
        except storage.StorageError as e:
            await ctx.send(str(e))


@botutils.admin_command(bot)
async def changeEXP(ctx, user_id, amount):
    with STORAGE_LOCK:
        try:
            amount = int(amount)
            user = storage.User.load(user_id)
            logger.debug(f"changeEXP: Old level: {user.level}")
            logger.debug(f"changeEXP: Old EXP: {user.exp}")
            old_level = user.level
            user.level, user.exp = calc_exp.recalc_level_and_exp(
                user.level, user.exp, amount)
            assert user.level > -1
            logger.debug(f"changeEXP: New level: {user.level}")
            logger.debug(f"changeEXP: New EXP: {user.exp}")
            if user.level > old_level:
                coins = calc_coins.level_up_award(old_level, user.level)
                user.coins += coins
                await ctx.send(f"<@{user_id}> upgraded to Lvl. {user.level} "
                               f"and was awarded {coins} coins!")
            elif user.level < old_level:
                coins = calc_coins.level_up_award(user.level, old_level)
                coins = min(coins, user.coins)
                user.coins -= coins
                await ctx.send(f"<@{user_id}> downgraded to Lvl. "
                               f"{user.level} and lost {coins} coins!")
            user.save()
            storage.commit(f"Change EXP for user {user_id}: {amount}")
            await ctx.send(f"<@{user_id}>'s EXP has been updated by {amount}!")
        except ValueError:
            logger.debug(f"changeEXP: Bad amount: {amount}")
            await ctx.send(f"Amount {amount} must be an integer!")
        except AssertionError:
            logger.debug("changeEXP: Not enough EXP")
            await ctx.send(f"<@{user_id}> does not have enough EXP!")
        except KeyError:
            logger.debug(f"changeEXP: User {user_id} not found")
            await ctx.send(f"User <@{user_id}> not found!")
        except storage.StorageError as e:
            await ctx.send(str(e))


@botutils.admin_command(bot)
async def changeCoins(ctx, user_id, amount):
    with STORAGE_LOCK:
        try:
            amount = int(amount)
            user = storage.User.load(user_id)
            logger.debug(f"changeCoins: Old coins: {user.coins}")
            user.coins += amount
            logger.debug(f"changeCoins: New coins: {user.coins}")
            assert user.coins >= 0
            user.save()
            storage.commit(f"Change coins for user {user_id}: {amount}")
            await ctx.send(f"<@{user_id}>'s coin count has been "
                           f"updated by {amount} coin(s)!")
        except ValueError:
            logger.debug(f"changeCoins: Bad amount: {amount}")
            await ctx.send(f"Amount {amount} must be an integer!")
        except AssertionError:
            logger.debug("changeCoins: Not enough coins")
            await ctx.send(f"<@{user_id} does not have enough coins!")
        except KeyError:
            logger.debug(f"changeCoins: User {user_id} not found")
            await ctx.send(f"User <@{user_id}> not found!")
        except storage.StorageError as e:
            await ctx.send(str(e))


@botutils.command(bot)
async def transactCoins(ctx, user_id, amount):
    """ Transact amount to user_id. """
    sender_id = ctx.message.author.id
    logger.debug(f"transactCoins: {sender_id} --({amount})--> {user_id}")
    with STORAGE_LOCK:
        try:
            amount = int(amount)
            assert amount > 0
            sender = storage.User.load(sender_id)
            receiver = storage.User.load(user_id)
            logger.debug(f"transactCoins: Sender Old: {sender.coins}")
            logger.debug(f"transactCoins: Receiver Old: {receiver.coins}")
            sender.coins -= amount
            receiver.coins += amount
            assert sender.coins >= 0
            logger.debug(f"transactCoins: Sender New: {sender.coins}")
            logger.debug(f"transactCoins: Receiver New: {receiver.coins}")
            sender.save()
            receiver.save()
            storage.commit(f"Transact {amount} coins from "
                           f"user {sender.id} to {receiver.id}")
            await ctx.send(f"<@{sender.id}> successfully transacted "
                           f"{amount} to <@{receiver.id}>!")
        except ValueError:
            logger.debug(f"transactCoins: Bad amount: {amount}")
            await ctx.send(f"Amount {amount} must be an integer!")
        except AssertionError:
            if amount <= 0:
                logger.debug("transactCoins: Negative or zero count")
                await ctx.send(f"<@{sender.id}>, amount must be positive!")
            else:
                logger.debug("transactCoins: Not enough coins")
                await ctx.send(f"<@{sender.id}>, you do not have enough coins!")
        except KeyError:
            logger.debug(f"transactCoins: User {user_id} not found")
            await ctx.send(f"User <@{user_id}> not found!")
        except storage.StorageError as e:
            await ctx.send(str(e))


@botutils.admin_command(bot)
async def resetUserStat(ctx, user_id):
    with STORAGE_LOCK:
        try:
            user = storage.User.load(user_id)
            user.exp = 0
            user.level = 0
            user.coins = 0
            user.save()
            storage.commit(f"Reset stat for user {user_id}")
            await ctx.send(f"<@{user_id}>'s stats are reset! "
                           f"(CCC progress not included)")
        except KeyError:
            logger.debug(f"resetUserStat: User {user_id} not found")
            await ctx.send(f"User <@{user_id}> not found!")
        except storage.StorageError as e:
            await ctx.send(str(e))


@bot.command()
@botutils.require_admin
async def syncData(ctx):
    logger.debug("[Command] syncData")
    with STORAGE_LOCK:
        try:
            storage.sync()
            await ctx.send(f"Successfully synced to remote!")
        except storage.StorageError as e:
            await ctx.send(str(e))


bot.run(os.environ["BotToken"])
