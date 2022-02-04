# coding: utf-8

"""
Calculations for coins.
"""

import time


def level_up_reward(level, new_level):
    """ Coins rewarded when upgrading to new_level. """
    coins = 0
    while level < new_level:
        coins += 5 + level // 15
        level += 1
    return coins


def ccc_reward(difficulty):
    """ Coins rewarded when finishing CCC problems. """
    base = (difficulty ** 2) - (difficulty ** 1.85)
    extra = 13 ** (difficulty // 10)
    return round(base + extra)


def with_booster(user, coins):
    """ Apply booster (if active) to coins. """
    if user.coin_booster > time.time():
        coins *= 2
    return coins
