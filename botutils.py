# coding: utf-8

"""
Utility for building discord chatbot.

About "User ID":
Discord will by default supply a user ID in format <@!xxx>
where xxx is a unique positive integer.  However, the string
nature makes this ID not so useful.

The `with_user_id_arg()` and `with_optional_user_id_arg()`
decorator will instead supply the integer, extracted, as
the user ID.  Thus, if a function looks like
```
@with_user_id_arg
def foo(ctx, user_id):
    # bar
```
user_id refers to the extracted integer, *NOT* the string
supplied by Discord.  However, `user_id` in this module does
refer to Discord's user ID, as the whole point is to hide
these details away from the rest of the program.
"""

import functools

import discord
import discord.ext.commands
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
        logger.warn("Returning ID -1 as fallback")
        return -1


require_admin = discord.ext.commands.has_permissions(administrator=True)


def with_user_id_arg(f):
    @functools.wraps(f)
    async def decorated(ctx, user_id, *args):
        extracted = extract_id(user_id)
        if extracted == -1:
            await ctx.send(f"Invalid User ID {user_id}!")
            return
        return await f(ctx, extracted, *args)
    return decorated


def with_optional_user_id_arg(f):
    @functools.wraps(f)
    async def decorated(ctx, user_id=None):
        if user_id is None:
            extracted = ctx.message.author.id
        else:
            extracted = extract_id(user_id)
            if extracted == -1:
                await ctx.send(f"Invalid User ID {user_id}!")
                return
        return await f(ctx, extracted)
    return decorated


File = discord.File
