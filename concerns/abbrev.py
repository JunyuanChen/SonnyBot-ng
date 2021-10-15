# coding: utf-8

"""
Abbreviate numerical values.

Example:
abbrev(12345)     # "12.3k"
abbrev(87654321)  # "87.65M"
"""

def abbrev(number):
    if number / 1000000000 > 1:
        return f"{round(number / 1000000000, 3)}G"
    if number / 1000000 > 1:
        return f"{round(number / 1000000, 2)}M"
    if number / 1000 > 1:
        return f"{round(number / 1000, 1)}k"
    return str(number)
