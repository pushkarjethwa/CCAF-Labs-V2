# Bookshop

A tiny Python inventory app for a small bookshop. Standard library only.

## Layout

- `bookshop/inventory.py`: the `Book` dataclass, loading `data/books.json`, stock value, author search.
- `bookshop/reports.py`: reports for the shop owner, each returns a list of text lines.
- `bookshop/cli.py`: the command line, run with `python -m bookshop <command>`.
- `tests/`: unittest tests.

## Commands

- Run the tests: `python -m unittest discover -s tests`
- Run the app: `python -m bookshop summary`

## Rules

- Run the tests after every change and show me the result.
