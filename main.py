#!/usr/bin/env python3
# coding: utf-8

import os
import threading

import logging
import botutils
import storage


storage.sync()  # Pull remote change


logging.LOGGERS = [
    logging.ConsoleLogger()
]


bot = botutils.setup_bot()


# Storage access must be serialized
STORAGE_LOCK = threading.lock()


@botutils.admin_command(bot)
async def removeUser(ctx, user_id):
    with STORAGE_LOCK:
        try:
            storage.User.load(user_id).destroy()
            await ctx.send(f"User <@{user_id}> has been deleted")
        except KeyError:
            logging.debug(f"removeUser: User {user_id} not found")
            await ctx.send(f"User <@{user_id}> not found!")
        except storage.StorageError as e:
            await ctx.send(str(e))


@botutils.admin_command(bot)
async def changeCoins(ctx, user_id, amount):
    with STORAGE_LOCK:
        try:
            amount = int(amount)
            user = storage.User.load(user_id)
            logging.debug(f"changeCoins: Old coins: {user.coins}")
            user.coins += amount
            logging.debug(f"changeCoins: New coins: {user.coins}")
            assert user.coins >= 0
            user.save()
            storage.commit(f"Change coins for user {user_id}: {amount}")
            await ctx.send(f"<@{user_id}>'s coin count has been "
                           f"updated by {amount} coin(s)!")
        except ValueError:
            logging.debug(f"changeCoins: Bad amount: {amount}")
            await ctx.send("Amount {amount} must be an integer!")
        except AssertionError:
            logging.debug("changeCoins: Not enough coins")
            await ctx.send(f"<@{user_id} does not have enough coins!")
        except KeyError:
            logging.debug(f"changeCoins: User {user_id} not found")
            await ctx.send(f"User <@{user_id}> not found!")
        except storage.StorageError as e:
            await ctx.send(str(e))


@botutils.command(bot)
async def transactCoins(ctx, user_id, amount):
    """ Transact amount to user_id. """
    sender_id = ctx.message.author.id
    logging.debug(f"transactCoins: {sender_id} --({amount})--> {user_id}")
    with STORAGE_LOCK:
        try:
            amount = int(amount)
            assert amount > 0
            sender = storage.User.load(sender_id)
            receiver = storage.User.load(user_id)
            logging.debug(f"transactCoins: Sender Old: {sender.coins}")
            logging.debug(f"transactCoins: Receiver Old: {receiver.coins}")
            sender.coins -= amount
            receiver.coins += amount
            assert sender.coins >= 0
            logging.debug(f"transactCoins: Sender New: {sender.coins}")
            logging.debug(f"transactCoins: Receiver New: {receiver.coins}")
            sender.save()
            receiver.save()
            storage.commit(f"Transact {amount} coins from "
                           f"user {sender.id} to {receiver.id}")
            await ctx.send(f"<@{sender.id}> successfully transacted "
                           f"{amount} to <@{receiver.id}>!")
        except ValueError:
            logging.debug(f"transactCoins: Bad amount: {amount}")
            await ctx.send(f"Amount {amount} must be an integer!")
        except AssertionError:
            if amount <= 0:
                logging.debug("transactCoins: Negative or zero count")
                await ctx.send(f"<@{sender.id}>, amount must be positive!")
            else:
                logging.debug("transactCoins: Not enough coins")
                await ctx.send(f"<@{sender.id}>, you do not have enough coins!")
        except KeyError:
            logging.debug(f"transactCoins: User {user_id} not found")
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
        except storage.StorageError as e:
            await ctx.send(str(e))


bot.run(os.environ["BotToken"])
