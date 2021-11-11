# coding: utf-8

import random


def gamble_curve(rand):
    """ Reward curve for gambling. """
    return 2 ** (-10 * rand)


def gamble():
    rand = random.random()
    return 100 * gamble_curve(rand)
