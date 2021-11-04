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
