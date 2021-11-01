# coding: utf-8

""" Discord-related. """

import io

import discord

import logger


def bot_channel(server):
    if server == "Test Server":
        return 869696625017229432
    if server[:7] == "The SCU":
        return 833831903878053908
    if server == "Coding Club":
        return 893224522763878460
    logger.warn(f"Unknown Discord server: {server}")
    return -1


async def get_avatar(member):
    avatar = member.avatar_url_as(size=128)
    return io.BytesIO(await avatar.read())


def normal_help():
    """ Help for normal bot commands. """
    embed = discord.Embed(title="All Normal Commands", color=0x00ff00)
    embed.add_field(
        name=".help",
        value="Print this help message",
        inline=False
    )
    embed.add_field(
        name=".stat [<@user>]",
        value=("Print out the stat of <@user>. If <@user> "
               "is not supplied, print your own stat."),
        inline=False
    )
    embed.add_field(
        name=".leaderboard",
        value="Print the leaderboard.",
        inline=False
    )
    embed.add_field(
        name=".transactCoins <@receiver> <amount>",
        value="Transact <amount> coins to <@receiver>.",
        inline=False
    )
    embed.add_field(
        name=".connectDMOJAccount <account>",
        value=("Connect your DMOJ account to claim coins for finishing "
               "CCC problems. You must solve at least 1 problem to connect!"),
        inline=False
    )
    embed.add_field(
        name=".getDMOJAccount [<@user>]",
        value=("Get the DMOJ account of <@user>. If <@user> "
               "is not supplied, get your own DMOJ account."),
        inline=False
    )
    embed.add_field(
        name=".CCCProgressList",
        value="Send your CCC progress to you DM",
        inline=False
    )
    embed.add_field(
        name=".fetchCCCProgress",
        value="Update your CCC progress, and claim coins!",
        inline=False
    )
    return embed


def admin_help():
    """ Help for admin commands. """
    embed = discord.Embed(title="All Admin Commands", color=0x00ff00)
    embed.add_field(
        name=".adminHelp",
        value="Print this admin help message",
        inline=False
    )
    embed.add_field(
        name=".mute <@user>",
        value="Mute <@user>.",
        inline=False
    )
    embed.add_field(
        name=".unmute <@user>",
        value="Unmute <@user>.",
        inline=False
    )
    embed.add_field(
        name=".addRole <@user> <role>",
        value="Add <role> to <@user>.",
        inline=False
    )
    embed.add_field(
        name=".removeRole <@user> <role>",
        value="Remove <role> from <@user>.",
        inline=False
    )
    embed.add_field(
        name=".syncData",
        value=("Sync data from GitHub remote. Make sure you know "
               "what you are doing!! Data loss can result!!!"),
        inline=False
    )
    embed.add_field(
        name=".changeEXP <@user> <amount>",
        value="Add or remove <amount> EXP to/from <@user>.",
        inline=False
    )
    embed.add_field(
        name=".changeCoins <@user> <amount>",
        value="Add or remove <amount> coins to/from <@user>",
        inline=False
    )
    embed.add_field(
        name=".changeMsgSent <@user> <amount>",
        value=("Add or remove <amount> from the "
               "number of messages sent by <@user>"),
        inline=False
    )
    embed.add_field(
        name=".resetUserStat <@user>",
        value=("Reset <@user>'s EXP, coins and number of messages sent. "
               "Contact a maintainer in case of accidents for reversal."),
        inline=False
    )
    embed.add_field(
        name=".removeUser <@user>",
        value=("Delete <@user> from bot's database. Make sure you know "
               "what you are doing! Fortunately, this can be reverted. "
               "Contact a maintainer in case of accidents."),
        inline=False
    )
