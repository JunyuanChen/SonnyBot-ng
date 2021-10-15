#!/usr/bin/env python3
# coding: utf-8

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
            user = storage.User.load(user_id)
            logging.debug(f"changeCoins: Old coins: {user.coins}")
            user.coins += amount
            logging.debug(f"changeCoins: New coins: {user.coins}")
            assert user.coins > 0
            user.save()
            storage.commit(f"Change coins for user {user_id}: {amount}")
            await ctx.send(f"<@{user_id}>'s coin count has been "
                           f"updated by {amount} coin(s)!")
        except AssertionError:
            logging.debug("changeCoins: Not enough coins")
            await ctx.send("<@{user_id} does not have enough coins!")
        except KeyError:
            logging.debug(f"changeCoins: User {user_id} not found")
            await ctx.send(f"User <@{user_id}> not found!")
        except storage.StorageError as e:
            await ctx.send(str(e))
