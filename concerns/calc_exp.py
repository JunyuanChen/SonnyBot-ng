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


def new_level_and_exp(old_level, old_exp, added_exp):
    """
    Recalculate level and EXP after adding added_exp.
    """
    exp_at_level = old_exp + added_exp
    exp_required = 1000 * (old_level + 1)
    if exp_at_level < exp_required:
        return old_level, exp_at_level
    return old_level + 1, exp_at_level - exp_required
