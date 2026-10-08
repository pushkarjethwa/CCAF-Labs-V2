"""Books and stock levels."""
import json
import pathlib
from dataclasses import dataclass

DATA_FILE = pathlib.Path(__file__).resolve().parent.parent / "data" / "books.json"


@dataclass
class Book:
    isbn: str
    title: str
    author: str
    price: float
    stock: int


def load_books(path=DATA_FILE):
    """Read the shop's books from a JSON file."""
    with open(path, encoding="utf-8") as handle:
        return [Book(**row) for row in json.load(handle)]


def total_value(books):
    """What the stock on the shelves is worth at shelf price."""
    return round(sum(book.price * book.stock for book in books), 2)


def find_by_author(books, author):
    """All books by one author, matched ignoring case."""
    return [book for book in books if book.author.lower() == author.lower()]
