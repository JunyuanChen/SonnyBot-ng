# coding: utf-8

"""
Calculations for EXP and levels.
"""


def level_to_exp(level):
    """
    Convert level to equivalent total EXP.

    Formula: EXP := Sigma(1000 * i, 1, n)
    Using Gauss's formula, this is 1000 * n(1+n)/2.
    """
    return 500 * level * (1 + level)


def recalc_level_and_exp(level, exp, exp_change):
    """ Recalculate level and EXP after exp_change. """
    exp += exp_change

    if exp >= 0:
        required = 1000 * (level + 1)
        if exp < required:
            return level, exp
        return level + 1, exp - required

    while exp < 0 and level > -1:
        exp += 1000 * level
        level -= 1
    return level, exp
