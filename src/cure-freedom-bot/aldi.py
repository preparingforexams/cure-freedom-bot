import json

import requests
from bs4 import BeautifulSoup


def get_karlskrone_price() -> float:
    url = "https://www.aldi-nord.de/sortiment/getraenke/bier/pilsener-0313-1-1.article.html"
    response = requests.get(url)
    bs4 = BeautifulSoup(response.content, "html.parser")
    element = bs4.find("div", attrs={"data-t-name": "ArticleIntro"})
    data_article = element.attrs["data-article"]
    data_article = json.loads(data_article)
    price = data_article["productInfo"]["priceWithTax"]

    return float(price)
