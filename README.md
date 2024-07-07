# Beancount N26 Importer

[![image](https://github.com/siddhantgoel/beancount-n26/workflows/beancount-n26/badge.svg)](https://github.com/siddhantgoel/beancount-n26/workflows/beancount-n26/badge.svg)

[![image](https://img.shields.io/pypi/v/beancount-n26.svg)](https://pypi.python.org/pypi/beancount-n26)

[![image](https://img.shields.io/pypi/pyversions/beancount-n26.svg)](https://pypi.python.org/pypi/beancount-n26)

[![image](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

`beancount-n26` provides a [Beancount] Importer for converting CSV exports of
[N26] account summaries to the Beancount format.

## Installation

```sh
$ pip install beancount-n26
```

In case you prefer installing from the Github repository, please note that `main` is the
development branch so `stable` is what you should be installing from.

Note that v1.x will *only* work with Beancount 3.x, while v0.x will *only* work with
Beancount 2.x, due to incompatibilities between Beancount 3.x and 2.x.

## Usage

### Beancount 3.x

Beancount 3.x has replaced the `config.py` file based workflow in favor of having a
script based workflow, as per the [changes documented here]. As a result, the importer's
initialization parameters have been shifted to `pyproject.toml`.

Add the following to your `pyproject.toml` in your project root.

```toml
[tool.beancount-n26]
ibn = "IBAN_NUMBER" # required
account_name = "Assets:N26" # required
language = "en"
file_encoding = "utf-8"
```

### Beancount 2.x

Add the following to your `config.py`.

```python
from beancount_n26 import N26Importer

CONFIG = [
    N26Importer(
        IBAN_NUMBER,
        'Assets:N26',
        language='en',
        file_encoding='utf-8',
    ),
]
```

### Classification

To classify specific recurring transactions automatically, you can specify an
`account_patterns` parameter. The key should be the account name and the items in the
list are regular expressions that should match a `payee`.

A few helper functions have been provided in
`beancount_n26/utils/patterns_generation.py` to help you generate this dictionnary.

#### Beancount 3.x

```toml
[tool.beancount-n26.account_patterns]
"Expenses:Supermarket" = ["REWE", "ALDI"]
```

#### Beancount 2.x

```python
from beancount_n26 import N26Importer

CONFIG = [
    N26Importer(
        ...
        account_patterns={"Expenses:Supermarket": ["REWE", "ALDI"]}
    ),
]
```

### Multiple-currency transactions

To mark transaction fees associated with multiple-currency transactions, you can
specify the `exchange_fees_account` parameter.

#### Beancount 3.x

```toml
[tool.beancount-n26]
ibn = "IBAN_NUMBER" # required
account_name = "Assets:N26" # required
language = "en"
file_encoding = "utf-8"
exchange_fees_account = "Expenses:TransferWise"
```

#### Beancount 2.x

```python
from beancount_n26 import N26Importer

CONFIG = [
    N26Importer(
        IBAN_NUMBER,
        'Assets:N26',
        language='en',
        file_encoding='utf-8',
        exchange_fees_account='Expenses:TransferWise',
    ),
]
```

With this in place, for transactions where both the amount in EUR and amount in foreign
currency are given, the importer will calculate the transaction fee based on the
exchange rate included in the CSV export and automatically allocate the value to the
account specified in `exchange_fees_account`.

## Contributing

Please make sure you have Python 3.8+ and [Poetry] installed.

1. Git clone the repository -
   `git clone https://github.com/siddhantgoel/beancount-n26`

2. Install the packages required for development -
   `poetry install`

3. That's basically it. You should now be able to run the test suite -
   `poetry run task test`.

[Beancount]: http://furius.ca/beancount/
[N26]: https://n26.com/
[Poetry]: https://python-poetry.org/
[changes documented here]: https://docs.google.com/document/d/1O42HgYQBQEna6YpobTqszSgTGnbRX7RdjmzR2xumfjs/edit#heading=h.hjzt0c6v8pfs
