import re
from typing import Callable, Tuple, Union

from telegram import Update
from telegram.ext import ContextTypes


def convert_number(match: re.Match, calc_fn: Callable[[float], float], unit_name: str) -> str:
    value = match.group("number")
    if value is None:
        return "couldn't find a valid number"
    value = value.replace(",", ".")
    try:
        freedom = float(value)
        result = calc_fn(freedom)
        return f"{result:.2f}{unit_name}"
    except ValueError:
        return f"couldn't parse number (`{value}`) as float"


def convert_cups(match: re.Match) -> str:
    cups = [
        convert_number(match, lambda n: n * 227, " gram (butter)"),
        convert_number(match, lambda n: n * 125, " gram (all purpose flour)"),
        convert_number(match, lambda n: n * 136, " gram (bread flour)"),
        convert_number(match, lambda n: n * 85, " gram (cocoa powder)"),
        convert_number(match, lambda n: n * 120, " gram (powdered sugar)"),
        convert_number(match, lambda n: n * 95, " gram (rolled oats)"),
        convert_number(match, lambda n: n * 200, " gram (granulated sugar)"),
        convert_number(match, lambda n: n * 220, " gram (packed brown sugar)"),
        convert_number(match, lambda n: n * 185, " gram (uncooked long grain rice)"),
        convert_number(match, lambda n: n * 200, " gram (uncooked short grain rice)"),
        convert_number(match, lambda n: n * 340, " gram (honey, molasse, syrup)"),
        convert_number(match, lambda n: n * 237, " gram (water)"),
        convert_number(match, lambda n: n * 249, " gram (whole milk)"),
    ]

    return "\n".join(cups)


def convert_tablespoon(match: re.Match) -> str:
    return "\n".join(
        [
            convert_number(match, lambda n: n * 15, "gram"),
            convert_number(match, lambda n: n * 14.7867648, "ml"),
        ]
    )


def convert_teaspoon(match: re.Match) -> str:
    return "\n".join(
        [
            convert_number(match, lambda n: n * 4.18, "gram"),
            convert_number(match, lambda n: n * 5, "ml"),
        ]
    )


def convert_ounces(match: re.Match) -> str:
    fluid = convert_number(match, lambda n: n * 29.57353, "ml")
    mass = convert_number(match, lambda n: n * 28.34952, "gram")

    return f"{fluid}\n{mass}"


regex_match_number_with_prefix = r"(?P<number>[-+]?\d+(:?(:?,|\.)\d+)?)"
units: dict[str, dict[str, Union[re.Pattern, Callable[[re.Match], str]]]] = {
    "fahrenheit": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>°?F)", re.IGNORECASE
        ),
        "process": lambda m: convert_number(m, lambda n: (n - 32) * (5 / 9), "°C"),
    },
    "inches": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>(:?\"|in(:?ch(:?es)?)?))"
        ),
        "process": lambda m: convert_number(m, lambda n: n * 2.54, "cm"),
    },
    "pound": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>(:?pound|lb)(:?s)?)"
        ),
        "process": lambda m: convert_number(m, lambda n: n * 453.59237, "gram"),
    },
    "ounces": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>(:?fl\.)?oz|ounces)"
        ),
        "process": convert_ounces,
    },
    "feet": {
        "regex": re.compile(rf"{regex_match_number_with_prefix}\s*(?P<unit_name>ft|feet)"),
        "process": lambda m: convert_number(m, lambda n: n * 0.3048, "m"),
    },
    "cups": {
        "regex": re.compile(rf"{regex_match_number_with_prefix}\s*(?P<unit_name>cup|endgegner)"),
        "process": convert_cups,
    },
    "tablespoon": {
        "regex": re.compile(rf"{regex_match_number_with_prefix}\s*(?P<unit_name>tablespoon|tbsp)"),
        "process": convert_tablespoon,
    },
    "teaspoon": {
        "regex": re.compile(rf"{regex_match_number_with_prefix}\s*(?P<unit_name>teaspoon|tsp)"),
        "process": convert_teaspoon,
    },
    "mile": {
        "regex": re.compile(rf"{regex_match_number_with_prefix}\s*(?P<unit_name>mi(?:le)?)"),
        "process": lambda m: convert_number(m, lambda n: n * 1.609344, "km"),
    },
    "yard": {
        "regex": re.compile(rf"{regex_match_number_with_prefix}\s*(?P<unit_name>yd|yard)"),
        "process": lambda m: convert_number(m, lambda n: n * 0.9144, "m"),
    },
}


def match_unit(unit: dict, args: str) -> re.Match | None:
    regex: re.Pattern = unit["regex"]
    if match := regex.match(args):
        return match

    return None


def find_matching_unit(args: str) -> Tuple[re.Match, dict] | None:
    fmatch, funit = None, None
    longest_unitname_match = 0

    for unit in units.values():
        if match := match_unit(unit, args):
            unitname_length = len(match.group("unit_name"))
            if unitname_length > longest_unitname_match:
                longest_unitname_match = unitname_length
                fmatch, funit = match, unit

    return fmatch, funit


async def cure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = " ".join(context.args)
    unit = find_matching_unit(args)
    if unit is None:
        await update.effective_message.reply_text("couldn't find a valid unit to convert")
    else:
        match, unit = unit
        message = unit["process"](match)
        await update.effective_message.reply_text(message)


async def supported_units(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("\n".join(str(key) for key in units.keys()))
