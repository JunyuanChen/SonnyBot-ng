# coding: utf-8

"""
Calculations for coins.
"""


def level_up_award(level, new_level):
    """ Coins rewarded when upgrading to new_level. """
    coins = 0
    while level < new_level:
        coins += 5 + level // 15
        level += 1
    return coins
