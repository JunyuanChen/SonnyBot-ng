# coding: utf-8

""" DMOJ web scraping. """

import requests
import lxml.html

from concerns import (
    calc_exp,
    calc_coins
)


def api_for(username):
    quoted = requests.utils.quote(username)
    return f"https://dmoj.ca/user/{quoted}/solved"


def extract_ccc(content):
    result = {}
    rows = lxml.html.document_fromstring(content).xpath(
        '//div[@class="user-problem-group"][contains(., "CCC")]'
        '/table/tbody/tr'
    )
    for row in rows:
        problem_url = row.xpath('td[@class="problem-name"]/a/@href')[0]
        score_str = row.xpath('td[@class="problem-score"]/a/text()')[0]
        score, total = map(float, score_str.split("/"))
        percentage = round(score / total * 100)
        result[problem_url] = percentage
    return result


def fetch_ccc(username):
    with requests.get(api_for(username)) as resp:
        return extract_ccc(resp.content)


def connect(user, username):
    ccc = fetch_ccc(username)
    if ccc:
        user.dmoj_username = username
        return update_ccc(user, ccc)
    return None


def update(user):
    if user.dmoj_username is None:
        raise ValueError("DMOJ Account not connected")
    ccc = fetch_ccc(user.dmoj_username)
    return update_ccc(user, ccc)


def reward(total_reward, percentage):
    """
    Reward for a problem with total_reward done to percentage.

    Since the first a few test cases are generally very easy, a linear
    approach will be unfair.  Thus, the reward is given in 20:80 ratio.
    The first 50% gives 20% of the reward, and the last 50% gives 80%
    of the reward.

    Thus, if percentage <= 0.5, then the percentage of reward given is:
    0.2 * (percentage / 0.5) = 0.4 * percentage
    And if percentage >= 0.5, then the weighed percentage is:
    0.2 + 0.8 * ((percentage - 0.5) / 0.5)) = 1.6 * percentage - 0.6
    """
    if percentage <= 0.5:
        weighed_percentage = 0.4 * percentage
    else:
        weighed_percentage = 1.6 * percentage - 0.6
    return round(total_reward * weighed_percentage)


def new_reward(total_reward, old_percentage, new_percentage):
    """
    New reward eligible after completing the problem to new_percentage.

    The user have already received some rewards.  Now they finished the
    problem to a higher percentage, thus they will be eligible for some
    new rewards.
    """
    old = reward(total_reward, old_percentage)
    new = reward(total_reward, new_percentage)
    return new - old


def update_ccc(user, ccc):
    exp_reward = 0
    coin_reward = 0
    for problem, percentage in ccc.items():
        if problem in user.ccc_progress:
            old_percentage = user.ccc_progress[problem]
        else:
            old_percentage = 0
        if old_percentage < percentage:
            user.ccc_progress[problem] = percentage
            total_exp = calc_exp.ccc_reward(problem.difficulty)
            total_coins = calc_coins.ccc_reward(problem.difficulty)
            exp_reward += new_reward(total_exp, old_percentage, percentage)
            coin_reward += new_reward(total_coins, old_percentage, percentage)
    return exp_reward, coin_reward


RequestException = requests.exceptions.RequestException
