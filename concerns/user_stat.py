# coding: utf-8

""" Generate fancy user stat images. """

import tempfile

from PIL import Image, ImageDraw, ImageFont

from concerns import (
    abbrev,
    calc_exp
)


FIRA_35 = ImageFont.truetype("assets/fira_sans.ttf", 35)
FIRA_24 = ImageFont.truetype("assets/fira_sans.ttf", 24)
KARLA_22 = ImageFont.truetype("assets/karla.ttf", 22)
KARLA_28 = ImageFont.truetype("assets/karla.ttf", 28)

AVATAR_MASK = Image.open("assets/avatar_mask.png")
PROGRESS_END = Image.open("assets/progress_end.png")


def draw_stat(avatar, username, level, rank, exp_current, coins, msg_count):
    """
    Draw a stat image.  Return the path of the image.

    The path points to a temporary file with extension png.  The caller
    is responsible for removing this temporary file.

    avatar is a BytesIO or path openable by PIL.Image.open()
    level is the user's current level
    rank is the user's rank among all users
    exp_current is the user's current EXP at current level
    coins is the number of coins the user currently has
    msg_amount is the number of message the user has sent
    """
    template = Image.open("assets/stat_template.png")
    avatar_img = Image.open(avatar).resize((128, 128))
    template.paste(avatar_img, (20, 10))
    template.paste(AVATAR_MASK, (20, 10))

    canvas = ImageDraw.Draw(template)
    canvas.text((165, 30), username, font=FIRA_35)

    canvas.text((240, 100), str(level), font=FIRA_24)
    canvas.text((555, 100), str(rank), font=FIRA_24)

    exp_required = calc_exp.exp_requirement(level)
    exp_str = f"{abbrev.abbrev(exp_current)} / {abbrev.abbrev(exp_required)}"
    canvas.text((345, 100), exp_str, font=FIRA_24)

    progress = exp_current / exp_required
    progress_len = int(progress * 580)
    progress_img = Image.new("RGBA", (progress_len, 35), "#7AC078")
    template.paste(progress_img, (23, 150))
    template.paste(PROGRESS_END, (23 + progress_len, 150), PROGRESS_END)

    canvas.text((612, 14), str(coins), font=KARLA_28, fill=(10, 74, 8, 1))
    canvas.text((610, 12), str(coins), font=KARLA_28, fill=(255, 255, 255, 1))

    msg_text = abbrev.abbrev(msg_count)
    canvas.text((747, 152), msg_text, font=KARLA_22, fill=(10, 74, 8, 1))
    canvas.text((745, 150), msg_text, font=KARLA_22, fill=(255, 255, 255, 1))

    filename = tempfile.mkstemp(suffix=".png")[1]
    template.save(filename)
    return filename
