# coding: utf-8

import random


def gamble_reward(rand):
    """ Reward curve for gambling. """
    return 100 * (2 ** rand - 1)


def gamble():
    rand = random.random()
    return gamble_reward(rand)
