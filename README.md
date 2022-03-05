# Beancount N26 Importer

[![image](https://github.com/Eazhi/beancount-n26/workflows/beancount-n26/badge.svg)](https://github.com/Eazhi/beancount-n26/workflows/beancount-n26/badge.svg)

[![image](https://img.shields.io/pypi/v/beancount-n26.svg)](https://pypi.python.org/pypi/beancount-n26)

[![image](https://img.shields.io/pypi/pyversions/beancount-n26.svg)](https://pypi.python.org/pypi/beancount-n26)

[![image](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

`beancount-n26-with-regexes` provides a [Beancount] Importer for converting CSV exports of
[N26] account summaries to the Beancount format.

## Installation

```sh
$ pip install beancount-n26
```

In case you prefer installing from the Github repository, please note that
`main` is the development branch so `stable` is what you should be installing
from.

## Usage

```python
from beancount_n26_with_regexes import N26Importer

CONFIG = [
    N26Importer(
        IBAN_NUMBER,
        'Assets:N26',
        language='en',
        file_encoding='utf-8',
        fill_default=True,
        account_to_ayees={
           "Expenses:Food:Restaurants": [
              # Regex 'style' payee name
              "amorino",
              "five guys.*",
           ]
        }
    ),
]
```

## References

This is a fork of: https://github.com/siddhantgoel/beancount-n26

[Beancount]: http://furius.ca/beancount/
[N26]: https://n26.com/
[Poetry]: https://poetry.eustace.io/
