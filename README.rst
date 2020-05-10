Beancount N26 Importer
======================

.. image:: https://github.com/siddhantgoel/beancount-n26/workflows/beancount-n26/badge.svg
    :target: https://github.com/siddhantgoel/beancount-n26/workflows/beancount-n26/badge.svg

.. image:: https://img.shields.io/pypi/v/beancount-n26.svg
    :target: https://pypi.python.org/pypi/beancount-n26

.. image:: https://img.shields.io/pypi/pyversions/beancount-n26.svg
    :target: https://pypi.python.org/pypi/beancount-n26

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black

:code:`beancount-n26` provides an Importer for converting CSV exports of N26_
account summaries to the Beancount_ format.

Installation
------------

.. code-block:: bash

    $ pip install beancount-n26

In case you prefer installing from the Github repository, please note that
:code:`master` is the development branch so :code:`stable` is what you should be
installing from.

Usage
-----

.. code-block:: python

    from beancount_n26 import N26Importer

    CONFIG = [
        N26Importer(
            IBAN_NUMBER,
            'Assets:N26',
            language='en',
            file_encoding='utf-8',
        ),
    ]

Contributing
------------

Contributions are most welcome!

Please make sure you have Python 3.5+ and Poetry_ installed.

1. Git clone the repository -
   :code:`git clone https://github.com/siddhantgoel/beancount-n26`

2. Install the packages required for development -
   :code:`poetry install`

3. That's basically it. You should now be able to run the test suite -
   :code:`poetry run py.test`.

.. _Beancount: http://furius.ca/beancount/
.. _N26: https://n26.com/
.. _Poetry: https://poetry.eustace.io/
