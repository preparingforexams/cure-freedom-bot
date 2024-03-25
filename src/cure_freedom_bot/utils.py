import inspect
from typing import Dict, Optional

import httpx

from cure_freedom_bot.logger import create_logger


def escape_markdown(text: str) -> str:
    reserved_characters = [
        "_",
        "*",
        "[",
        "]",
        "(",
        ")",
        "~",
        "`",
        ">",
        "#",
        "+",
        "-",
        "=",
        "|",
        "{",
        "}",
        ".",
        "!",
    ]
    for reserved in reserved_characters:
        text = text.replace(reserved, rf"\{reserved}")

    return text


class RequestError(Exception):
    pass


def get_json_from_url(url: str, *, headers: Dict = None) -> Optional[Dict]:
    log = create_logger(inspect.currentframe().f_code.co_name)

    try:
        response = httpx.get(url, headers=headers)
        content = response.json()
    except httpx.HTTPError as e:
        log.exception("failed to communicate with jokes api")
        raise RequestError(e)

    if not response.is_success:
        raise RequestError(f"[{response.status_code}]{response.text}")

    return content
