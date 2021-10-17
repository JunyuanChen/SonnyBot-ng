# coding: utf-8

"""
Calculations for EXP and levels.
"""


def exp_requirement(level):
    """ EXP required to level up from level. """
    return 1000 * (level + 1)


def level_to_exp(level):
    """
    Convert level to equivalent total EXP.

    Formula: EXP := Sigma(1000 * i, 1, n)
    Using Gauss's formula, this is 1000 * n(1+n)/2.
    """
    return 500 * level * (1 + level)


def total_exp(user):
    """ Calculate user's total EXP. """
    return user.exp + level_to_exp(user.level)


def rank_users(users):
    """ Rank users by total EXP, in desc order. """
    return sorted(users, key=lambda u: -total_exp(u))


def recalc_level_and_exp(level, exp, exp_change):
    """ Recalculate level and EXP after exp_change. """
    exp += exp_change

    if exp >= 0:
        required = 1000 * (level + 1)
        while exp >= required:
            level += 1
            exp -= required
            required += 1000
        return level, exp

    while exp < 0 and level > -1:
        exp += 1000 * level
        level -= 1
    return level, exp
