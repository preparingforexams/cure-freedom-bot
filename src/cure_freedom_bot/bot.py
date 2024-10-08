import re
from collections.abc import Callable
from typing import cast

import currency_converter
from telegram import Message, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from cure_freedom_bot import aldi
from cure_freedom_bot.constants import *
from cure_freedom_bot.convutils import (
    convert_number,
    get_number_from_match,
    to_celsius,
    to_tahocker,
)
from cure_freedom_bot.utils import escape_markdown


def is_non_freedom_length_unit(s: str) -> bool:
    return s.lower() in [
        "cm",
        "centimeter",
        "zentimeter",
        "m",
        "meter",
        "km",
        "kilometer",
    ]


def multiply_by_helper(factor: float) -> Callable[[float], float]:
    return lambda n: n * factor


def convert_cups(match: re.Match) -> str:
    results = []
    number = get_number_from_match(match)
    if isinstance(number, str):
        return number

    for factor, unit_name in [
        (CUPS_TO_GRAM_BUTTER, "gram (butter)"),
        (CUPS_TO_GRAM_ALL_PURPOSE_FLOUR, "gram (all purpose flour)"),
        (CUPS_TO_GRAM_BREAD_FLOUR, "gram (bread flour)"),
        (CUPS_TO_GRAM_COCOA_POWDER, "gram (cocoa powder)"),
        (CUPS_TO_GRAM_POWDERED_SUGAR, "gram (powdered sugar)"),
        (CUPS_TO_GRAM_ROLLED_OATS, "gram (rolled oats)"),
        (CUPS_TO_GRAM_GRANULATED_SUGAR, "gram (granulated sugar)"),
        (CUPS_TO_GRAM_PACKED_BROWN_SUGAR, "gram (packed brown sugar)"),
        (CUPS_TO_GRAM_UNCOOKED_LONG_GRAIN_RICE, "gram (uncooked long grain rice)"),
        (CUPS_TO_GRAM_UNCOOKED_SHORT_GRAIN_RICE, "gram (uncooked short grain rice)"),
        (CUPS_TO_GRAM_HONEY_MOLASSE_SYRUP, "gram (honey, molasse, syrup)"),
        (CUPS_TO_GRAM_WATER, "gram (water)"),
        (CUPS_TO_GRAM_WHOLE_MILK, "gram (whole milk)"),
    ]:
        results.append(f"{number * factor:.2f}{unit_name}")

    return "\n".join(results)


def convert_tablespoon(match: re.Match) -> str:
    return "\n".join(
        [
            convert_number(match, multiply_by_helper(TABLESPOON_TO_GRAM), "gram"),
            convert_number(match, multiply_by_helper(TABLESPOON_TO_MILLILITER), "ml"),
        ]
    )


def convert_teaspoon(match: re.Match) -> str:
    return "\n".join(
        [
            convert_number(match, multiply_by_helper(TEASPOON_TO_GRAM), "gram"),
            convert_number(match, multiply_by_helper(TEASPOON_TO_MILLILITER), "ml"),
        ]
    )


def convert_ounces(match: re.Match) -> str:
    fluid = convert_number(match, multiply_by_helper(OUNCES_TO_MILLILITER), "ml")
    mass = convert_number(match, multiply_by_helper(OUNCES_TO_GRAM), "gram")

    return f"{fluid}\n{mass}"


def convert_inches(match: re.Match) -> str:
    cm = convert_number(match, multiply_by_helper(INCHES_TO_CENTIMETER), "cm")
    tahocker = to_tahocker(match)

    return f"{cm}\n{tahocker}"


def convert_aldi_beer(match: re.Match) -> str:
    multiplier = 1

    if match.group("unit_name").strip().lower() in ("euro", "€"):
        multiplier = 100

    result = escape_markdown(
        convert_number(
            match,
            lambda n: (n * multiplier) / 29,
            "Boah Bruder, das sind ja {}",
            format_result=True,
            rounding_length=3,
        )
    )
    # noinspection PyBroadException
    try:
        current_price = aldi.get_karlskrone_price()
        result += escape_markdown(
            convert_number(
                match,
                lambda n: (n * multiplier) / (current_price * 100),
                " ({})",
                format_result=True,
                rounding_length=3,
            )
        )
    except Exception:
        pass
    return result + " [Aldi Bier](https://song.link/t/120323761)"


def convert_non_freedom(match: re.Match) -> str:
    value = get_number_from_match(match)
    unit_name = match.group("unit_name")

    if isinstance(value, str):
        return value

    # this obviously needs a unit check (convert to cm for everything)
    # if is_non_freedom_length_unit(unit_name):
    #     return to_tahocker(match)

    return f"{value}{unit_name}"


def convert_dollar(match: re.Match) -> str:
    currency_url = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip"

    cc = currency_converter.CurrencyConverter(currency_file=currency_url)
    value = get_number_from_match(match)
    if isinstance(value, str):
        return value
    euro = cc.convert(value, "USD", "EUR")

    return f"{euro:.2f}€"


def convert_quart(match: re.Match) -> str:
    us_liquid = convert_number(match, multiply_by_helper(US_LIQUID_QUART_TO_LITER), "l")
    us_dry = convert_number(match, multiply_by_helper(US_DRY_QUART_TO_LITER), "l")
    imperial = convert_number(match, multiply_by_helper(IMPERIAL_QUART_TO_LITER), "l")

    return f"""US liquid: {us_liquid}
US dry: {us_dry}
Imperial: {imperial}
    """


regex_match_number_with_prefix = r"(?P<number>[-+]?\d+(:?(:?,|\.)\d+)?)"

units: dict[str, dict[str, re.Pattern | Callable[[re.Match], str]]] = {
    "fahrenheit": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>°?F)", re.IGNORECASE
        ),
        "process": to_celsius,
    },
    "inches": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>(:?\"|in(:?ch(:?es)?)?))",
            re.IGNORECASE,
        ),
        "process": convert_inches,
    },
    "pound": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>(:?pound|lb)(:?s)?)",
            re.IGNORECASE,
        ),
        "process": lambda m: convert_number(
            m, multiply_by_helper(POUND_TO_GRAM), "gram"
        ),
    },
    "ounces": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>(:?fl\.)?oz|ounces)",
            re.IGNORECASE,
        ),
        "process": convert_ounces,
    },
    "feet": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>ft|feet)", re.IGNORECASE
        ),
        "process": lambda m: convert_number(m, multiply_by_helper(FEET_TO_METER), "m"),
    },
    "cups": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>cup|endgegner)",
            re.IGNORECASE,
        ),
        "process": convert_cups,
    },
    "tablespoon": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>tablespoon|tbsp)",
            re.IGNORECASE,
        ),
        "process": convert_tablespoon,
    },
    "teaspoon": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>teaspoon|tsp)",
            re.IGNORECASE,
        ),
        "process": convert_teaspoon,
    },
    "mile": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>mi(?:le)?)",
            re.IGNORECASE,
        ),
        "process": lambda m: convert_number(
            m, multiply_by_helper(MILE_TO_KILOMETER), "km"
        ),
    },
    "yard": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>yd|yard)", re.IGNORECASE
        ),
        "process": lambda m: convert_number(m, multiply_by_helper(YARD_TO_METER), "m"),
    },
    "aldi beer": {
        "regex": re.compile(
            rf".*?{regex_match_number_with_prefix}\s*(?P<unit_name>(€|euro|ct|cent))",
            re.IGNORECASE,
        ),
        "process": convert_aldi_beer,
        "parse_mode": ParseMode.MARKDOWN_V2,  # type: ignore[dict-item]
    },
    "USD": {
        "regex": re.compile(
            rf".*?{regex_match_number_with_prefix}\s*(?P<unit_name>(\$|usd|dollar))",
            re.IGNORECASE,
        ),
        "process": convert_dollar,
    },
    "feet squared": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>(ft|feet)(\^?2|\u00b2))",
            re.IGNORECASE,
        ),
        "process": lambda m: convert_number(
            m, multiply_by_helper(FEET_SQUARED_TO_METER_SQUARED), "m\u00b2"
        ),
    },
    "miles squared": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>(mi|mile)(\^?2|\u00b2))",
            re.IGNORECASE,
        ),
        "process": lambda m: convert_number(
            m, multiply_by_helper(MILE_SQUARED_TO_KILOMETER_SQUARED), "km\u00b2"
        ),
    },
    "non freedom units": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>cm|([cz])entimeter|ml|milliliterkm|kilometer|g(ram)?|m(eter)?|c(elsius)?|°C)"
        ),
        "process": convert_non_freedom,
    },
    "quart": {
        "regex": re.compile(
            rf"{regex_match_number_with_prefix}\s*(?P<unit_name>qt|quart)"
        ),
        "process": convert_quart,
    },
}


def match_unit(unit: dict, args: str) -> re.Match | None:
    regex: re.Pattern = unit["regex"]
    if match := regex.match(args):
        return match

    return None


def find_matching_unit(args: str) -> tuple[re.Match, dict] | tuple[None, None]:
    fmatch, funit = None, None
    longest_unitname_match = 0

    for unit in units.values():
        if match := match_unit(unit, args):
            unitname_length = len(match.group("unit_name"))
            if unitname_length > longest_unitname_match:
                longest_unitname_match = unitname_length
                fmatch, funit = match, unit

    return fmatch, funit  # type: ignore[return-value]


async def cure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = " ".join(context.args)  # type: ignore[arg-type]
    match, unit = find_matching_unit(args)
    effective_message = update.effective_message

    if effective_message is None:
        raise ValueError("Can't use non-message update")

    if match is None or unit is None:
        await effective_message.reply_text("couldn't find a valid unit to convert")
    else:
        message = unit["process"](match)
        if "parse_mode" in unit and unit["parse_mode"] is not None:
            await effective_message.reply_text(
                message, parse_mode=unit["parse_mode"], disable_web_page_preview=True
            )
        else:
            await effective_message.reply_text(message, disable_web_page_preview=True)


async def supported_units(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await cast(Message, update.effective_message).reply_text(
        "\n".join(str(key) for key in units.keys())
    )
