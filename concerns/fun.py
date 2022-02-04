# coding: utf-8

import random


def gamble_curve(rand):
    """
    Reward curve for gambling.

    Desired properties of the curve:
    - Low probability of value near 0, or players will be mad and
      think the game is unfair (for whatever standard of fair).
    - Low probability of value near 1, or players will be winning
      too many coins (i.e. Mathematical expectation > 0).
    - Most likely near 0.2 ~ 0.3, because the cost of a gamble is
      30 coins.  This keeps mathematical expectation a little bit
      less than 0, so in average players are losing coins, but not
      too many at once.

    The `base` curve has a large derivative near 0.  This ensures
    a low probability of 0.  The `extra` curve is negligibly small
    for most part but have a large derivative near 1.  Together,
    the curve looks like this:

    +----------------------------------+
    |                                 ||
    |                                 ||
    |                                / |
    |                              _/  |
    | <-- 0.3            ______----    |
    |   __--------------               |
    | /                                |
    ||                                 |
    +----------------------------------+
    """
    base = 0.1 * rand ** 0.15 #Original formula:  0.3 * rand ** 0.4
    extra = 0.9 * rand ** 52  #Original formula:  0.7 * rand ** 32
    return base + extra


def gamble():
    rand = random.random()
    return round(100 * gamble_curve(rand))
