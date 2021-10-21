# coding: utf-8

""" DMOJ web scraping. """

import requests
import lxml.html


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
            # TODO Reward user some exp
    return exp_reward, coin_reward


RequestException = requests.exceptions.RequestException
