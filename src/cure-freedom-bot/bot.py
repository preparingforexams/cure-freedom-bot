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
        result = f"{result:.2f}"
        if "{}" in unit_name:
            return unit_name.format(result)
        else:
            return f"{result} {unit_name}"
    except ValueError:
        return f"couldn't parse number (`{value}`) as float"


def multiply_by_helper(factor: float) -> Callable[[float], float]:
    return lambda n: n * factor


def convert_cups(match: re.Match) -> str:
    results = []
    number_result = convert_number(match, lambda n: n, "")
    try:
        number = float(number_result)
    except ValueError:
        return number_result

    for factor, unit_name in [
        (227, "gram (butter)"),
        (125, "gram (all purpose flour)"),
        (136, "gram (bread flour)"),
        (85, "gram (cocoa powder)"),
        (120, "gram (powdered sugar)"),
        (95, "gram (rolled oats)"),
        (200, "gram (granulated sugar)"),
        (220, "gram (packed brown sugar)"),
        (185, "gram (uncooked long grain rice)"),
        (200, "gram (uncooked short grain rice)"),
        (340, "gram (honey, molasse, syrup)"),
        (237, "gram (water)"),
        (249, "gram (whole milk)"),
    ]:
        results.append(f"{number * factor:.2f}{unit_name}")

    return "\n".join(results)


def convert_tablespoon(match: re.Match) -> str:
    return "\n".join(
        [
            convert_number(match, multiply_by_helper(15), "gram"),
            convert_number(match, multiply_by_helper(14.7867648), "ml"),
        ]
    )


def convert_teaspoon(match: re.Match) -> str:
    return "\n".join(
        [
            convert_number(match, multiply_by_helper(4.18), "gram"),
            convert_number(match, multiply_by_helper(5), "ml"),
        ]
    )


def convert_ounces(match: re.Match) -> str:
    fluid = convert_number(match, multiply_by_helper(29.57353), "ml")
    mass = convert_number(match, multiply_by_helper(28.34952), "gram")

    return f"{fluid}\n{mass}"


def convert_aldi_beer(match: re.Match) -> str:
    multiplier = 1

    if match.group("unit_name").strip().lower() in ("euro", "€"):
        multiplier = 100

    return convert_number(
        match, lambda n: (n * multiplier) / 29, "Boah Bruder, das sind ja {} Aldi Bier"
    )


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
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>(:?\"|in(:?ch(:?es)?)?))",
            re.IGNORECASE,
        ),
        "process": lambda m: convert_number(m, multiply_by_helper(2.54), "cm"),
    },
    "pound": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>(:?pound|lb)(:?s)?)", re.IGNORECASE
        ),
        "process": lambda m: convert_number(m, multiply_by_helper(453.59237), "gram"),
    },
    "ounces": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>(:?fl\.)?oz|ounces)", re.IGNORECASE
        ),
        "process": convert_ounces,
    },
    "feet": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>ft|feet)", re.IGNORECASE
        ),
        "process": lambda m: convert_number(m, multiply_by_helper(0.3048), "m"),
    },
    "cups": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>cup|endgegner)", re.IGNORECASE
        ),
        "process": convert_cups,
    },
    "tablespoon": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>tablespoon|tbsp)", re.IGNORECASE
        ),
        "process": convert_tablespoon,
    },
    "teaspoon": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>teaspoon|tsp)", re.IGNORECASE
        ),
        "process": convert_teaspoon,
    },
    "mile": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>mi(?:le)?)", re.IGNORECASE
        ),
        "process": lambda m: convert_number(m, multiply_by_helper(1.609344), "km"),
    },
    "yard": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>yd|yard)", re.IGNORECASE
        ),
        "process": lambda m: convert_number(m, multiply_by_helper(0.9144), "m"),
    },
    "aldi beer": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}(?P<unit_name>\s*(€|euro|ct|cent))", re.IGNORECASE
        ),
        "process": convert_aldi_beer,
    },
}


def match_unit(unit: dict, args: str) -> re.Match | None:
    regex: re.Pattern = unit["regex"]
    if match := regex.match(args):
        return match

    return None


def find_matching_unit(args: str) -> Tuple[re.Match, dict] | Tuple[None, None]:
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
    match, unit = find_matching_unit(args)
    if match is None or unit is None:
        await update.effective_message.reply_text("couldn't find a valid unit to convert")
    else:
        message = unit["process"](match)
        await update.effective_message.reply_text(message)


async def supported_units(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("\n".join(str(key) for key in units.keys()))
