# coding: utf-8

"""
Calculations for EXP and levels.

EXP vs total EXP
================
EXP refers to EXP at current level.  When EXP reaches a certain value
determined by exp_requirement(), the user will level up, and EXP will be
reset to 0.  However, total EXP takes level into consideration.  It will
NOT reset when user levels up.

Example:
exp_requirement(0) = 1000, this means users at level 0 need 1000 EXP to
level up.  Suppose current level = 0, EXP = 900.  The total EXP is 900.
If the user gained another 200 EXP, EXP = 1100 > 1000, so the user will
level up.  Now level = 1 and EXP = 1100 - 1000 = 100, but total EXP is
not reset, thus total EXP = 1100.

To calculate total EXP from EXP, just add exp_requirement for all level
below user's level.  This is the total number of EXP deducted from the
user for levelling up.  Adding them back to EXP gives total EXP.
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


def recalc_level(level, exp, exp_change):
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
