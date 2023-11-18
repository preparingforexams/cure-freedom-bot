import re
from typing import Callable

from utils import escape_markdown


def get_number_from_match(match: re.Match) -> float | str:
    value = match.group("number")
    if value is None:
        return "couldn't find a valid number"
    value = value.replace(",", ".")

    try:
        return float(value)
    except ValueError:
        return f"couldn't parse number (`{value}`) as float"


def convert_number(
    match: re.Match,
    calc_fn: Callable[[float], float],
    unit_name: str,
    escape_md: bool = False,
    format_result: bool = False,
    rounding_length: int = 2,
) -> str:
    freedom = get_number_from_match(match)
    result = freedom
    if isinstance(freedom, float):
        result = calc_fn(freedom)
        result = f"{result:.{rounding_length}f}"
        if format_result:
            result = unit_name.format(result)
        else:
            result = f"{result} {unit_name}"

    if escape_md:
        return escape_markdown(result)
    else:
        return result


def to_tahocker(match: re.Match) -> str:
    return convert_number(match, lambda n: (n * 2.54) / 159.5, "tahocker")


def to_celsius(match: re.Match) -> str:
    return convert_number(match, lambda n: (n - 32) * (5 / 9), "°C")
