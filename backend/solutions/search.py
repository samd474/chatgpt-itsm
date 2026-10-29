"""Article suggestions for free-typed text, such as a ticket subject.

The list search (DRF's SearchFilter) requires every word to appear, which rarely matches a sentence
someone has just typed. Suggestions instead use PostgreSQL full-text search: any significant word
may match, words are stemmed ("dropping" finds "drop"), and results are ranked with the title
weighted highest.
"""
import operator
import re
from functools import reduce

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

from .access import visible_articles
from .models import Article

MAX_WORDS = 10


def suggest(user, text, limit=5):
    words = list(dict.fromkeys(w.lower() for w in re.findall(r"\w+", text or "") if len(w) >= 3))[:MAX_WORDS]
    if not words:
        return Article.objects.none()
    # One plain query per word, OR-ed: each word is passed as data, never parsed as query syntax.
    query = reduce(operator.or_, (SearchQuery(word, config="english") for word in words))
    vector = (SearchVector("title", weight="A", config="english")
              + SearchVector("summary", "keywords", weight="B", config="english")
              + SearchVector("body", weight="C", config="english"))
    published = visible_articles(user, Article.objects.filter(status=Article.Status.PUBLISHED))
    return (published.annotate(document=vector, rank=SearchRank(vector, query))
            .filter(document=query).order_by("-rank", "-published_at")[:limit])
