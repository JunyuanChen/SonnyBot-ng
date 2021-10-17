# coding: utf-8

"""
Utility for building discord chatbot.

About "User ID":
Discord will by default supply a user ID in format <@!xxx>
where xxx is a unique positive integer.  However, the string
nature makes this ID not so useful.

The `command()` and `admin_command()` wrapper decorator will
instead supply the integer, extracted, as the user ID.  Thus,
if a function looks like
```
@command(client)
def foo(ctx, user_id):
    # bar
```
user_id refers to the extracted integer, *NOT* the string
supplied by Discord.  However, `user_id` in this module does
refer to Discord's user ID, as the whole point is to hide
these details away from the rest of the program.
"""

import discord
import logger


def setup_bot():
    intents = discord.Intents.default()
    intents.presences = True
    intents.members = True

    return discord.ext.commands.Bot(
        command_prefix='.',
        intents=intents,
        help_command=None
    )


def extract_id(user_id):
    try:
        # "<@!...>" where "..." is what we want
        return int(user_id[3:-1])
    except ValueError:
        logger.warn(f"Malformed UserID string: {user_id}")
        logger.warn(f"Returning ID -1 as fallback")
        return -1


require_admin = discord.ext.commands.has_permissions(administrator=True)


def command(client):
    def decorator(f):
        @client.command()
        async def decorated(ctx, user_id, *args):
            args_str = " ".join(map(str, args))
            logger.debug(f"[Command] {f.__name__} {user_id} {args_str}")
            extracted = extract_id(user_id)
            if extracted == -1:
                await ctx.send(f"Invalid User ID {user_id}!")
            else:
                return await f(ctx, extracted, *args)

        return decorated
    return decorator


def admin_command(client):
    def decorator(f):
        @client.command()
        @require_admin
        async def decorated(ctx, user_id, *args):
            args_str = " ".join(map(str, args))
            logger.debug(f"[Command] {f.__name__} {user_id} {args_str}")
            extracted = extract_id(user_id)
            if extracted == -1:
                await ctx.send(f"Invalid User ID {user_id}!")
            else:
                return await f(ctx, extracted, *args)

        return decorated
    return decorator


File = discord.File
