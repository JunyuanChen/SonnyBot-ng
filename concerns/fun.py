# coding: utf-8

import random


def gamble_curve(rand):
    """ Reward curve for gambling. """
    return 2 ** (-10 * rand)


def gamble():
    rand = random.random()
    return 10 + round(90 * gamble_curve(rand))
