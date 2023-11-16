import datetime
import os.path
from textwrap import dedent

from beancount.core.number import Decimal
from beancount.core.data import Transaction
import pytest

from typing import Optional, List, Tuple

from beancount_n26 import _header_values_for, N26Importer, HEADER_FIELDS

IBAN_NUMBER = 'DE99 9999 9999 9999 9999 99'.replace(' ', '')


def _format(string, **kwargs):
    kwargs.update(
        {
            'iban_number': IBAN_NUMBER,
            'header': ','.join(_header_values_for(**kwargs)),
        }
    )

    return dedent(string).format(**kwargs).lstrip().encode('utf-8')


@pytest.fixture(params=HEADER_FIELDS.keys())
def language(request):
    return request.param


@pytest.fixture
def filename(tmp_path):
    return os.path.join(str(tmp_path), '{}.csv'.format(IBAN_NUMBER))


@pytest.fixture
def importer(language):
    return N26Importer(
        IBAN_NUMBER,
        'Assets:N26',
        language=language,
    )


@pytest.fixture
def importer_with_classification(language):
    return N26Importer(
        IBAN_NUMBER,
        "Assets:N26",
        language=language,
        account_patterns={
            "Expenses:Misc": [
                "MAX MUSTERMANN",
            ]
        },
    )


def test_identify_with_optional(importer, filename):
    with open(filename, 'wb') as fd:
        fd.write(
            _format(
                '''
                {header}
                "2019-10-10","MAX MUSTERMANN","{iban_number}","Outgoing Transfer","Muster GmbH","Miscellaneous","-12.34","","",""
                ''',  # NOQA
                language=importer.language,
            )
        )

    with open(filename) as fd:
        assert importer.identify(fd)


def test_identify_correct_no_optional(importer, filename):
    with open(filename, 'wb') as fd:
        fd.write(
            _format(
                '''
                {header}
                "2019-10-10","MAX MUSTERMANN","{iban_number}","Outgoing Transfer","Muster GmbH","-12.34","","",""
                ''',  # NOQA
                language=importer.language,
                include_optional=False,
            )
        )

    with open(filename) as fd:
        assert importer.identify(fd)


def test_extract_no_transactions(importer, filename):
    with open(filename, 'wb') as fd:
        fd.write(
            _format(
                '''
                {header}
                ''',
                language=importer.language,
            )
        )

    with open(filename) as fd:
        transactions = importer.extract(fd)

    assert len(transactions) == 0


def assert_transaction(
    transaction: Transaction,
    date: datetime,
    payee: str,
    narration: str,
    postings: List[Tuple[str, Optional[str], Optional[Decimal]]],
):
    assert transaction.date == date
    assert transaction.payee == payee
    assert transaction.narration == narration

    assert len(postings) == len(transaction.postings)
    for expected, actual in zip(postings, transaction.postings):
        assert actual.account == expected[0]
        if actual.units is None:
            assert expected[1] is None
            assert expected[2] is None
        else:
            assert actual.units.currency == expected[1]
            assert actual.units.number == expected[2]


def test_extract_single_transaction(importer, filename):
    with open(filename, 'wb') as fd:
        fd.write(
            _format(
                '''
                {header}
                "2019-10-10","Muster GmbH","{iban_number}","Outgoing Transfer","Muster payment","Miscellaneous","-12.34","","",""
                ''',  # NOQA
                language=importer.language,
            )
        )

    with open(filename) as fd:
        transactions = importer.extract(fd)
        date = importer.file_date(fd)

    assert date == datetime.date(2019, 10, 10)

    assert len(transactions) == 1
    assert_transaction(
        transaction=transactions[0],
        date=datetime.date(2019, 10, 10),
        payee='Muster GmbH',
        narration='Muster payment',
        postings=[
            ('Assets:N26', 'EUR', Decimal('-12.34')),
        ],
    )


def test_extract_multiple_transactions(importer, filename):
    with open(filename, 'wb') as fd:
        fd.write(
            _format(
                '''
                {header}
                "2019-12-28","MAX MUSTERMANN","{iban_number}","Income","Muster GmbH","Income","-56.78","","",""
                "2020-01-05","Muster SARL","{iban_number}","Outgoing Transfer","Muster Fr payment","Income","-42.24","","",""
                "2020-01-03","Muster GmbH","{iban_number}","Outgoing Transfer","Muster De payment","Income","-12.34","","",""
                ''',  # NOQA
                language=importer.language,
            )
        )

    with open(filename) as fd:
        transactions = importer.extract(fd)
        date = importer.file_date(fd)

    assert date == datetime.date(2020, 1, 5)
    assert len(transactions) == 3

    assert_transaction(
        transaction=transactions[0],
        date=datetime.date(2019, 12, 28),
        payee='MAX MUSTERMANN',
        narration='Muster GmbH',
        postings=[
            ('Assets:N26', 'EUR', Decimal('-56.78')),
        ],
    )

    assert_transaction(
        transaction=transactions[1],
        date=datetime.date(2020, 1, 5),
        payee='Muster SARL',
        narration='Muster Fr payment',
        postings=[
            ('Assets:N26', 'EUR', Decimal('-42.24')),
        ],
    )

    assert_transaction(
        transaction=transactions[2],
        date=datetime.date(2020, 1, 3),
        payee='Muster GmbH',
        narration='Muster De payment',
        postings=[
            ('Assets:N26', 'EUR', Decimal('-12.34')),
        ],
    )


def test_extract_multiple_transactions_with_classification(
    importer_with_classification, filename
):
    with open(filename, 'wb') as fd:
        fd.write(
            _format(
                '''
                {header}
                "2019-12-28","MAX MUSTERMANN","{iban_number}","Income","Muster GmbH","Income","-56.78","","",""
                "2020-01-05","Muster SARL","{iban_number}","Outgoing Transfer","Muster Fr payment","Income","-42.24","","",""
                "2020-01-03","Muster GmbH","{iban_number}","Outgoing Transfer","Muster De payment","Income","-12.34","","",""
                ''',  # NOQA
                language=importer_with_classification.language,
            )
        )

    with open(filename) as fd:
        transactions = importer_with_classification.extract(fd)
        date = importer_with_classification.file_date(fd)

    assert date == datetime.date(2020, 1, 5)
    assert len(transactions) == 3

    assert_transaction(
        transaction=transactions[0],
        date=datetime.date(2019, 12, 28),
        payee='MAX MUSTERMANN',
        narration='Muster GmbH',
        postings=[
            ('Assets:N26', 'EUR', Decimal('-56.78')),
            ('Expenses:Misc', None, None),
        ],
    )

    assert_transaction(
        transaction=transactions[1],
        date=datetime.date(2020, 1, 5),
        payee='Muster SARL',
        narration='Muster Fr payment',
        postings=[
            ('Assets:N26', 'EUR', Decimal('-42.24')),
        ],
    )

    assert_transaction(
        transaction=transactions[2],
        date=datetime.date(2020, 1, 3),
        payee='Muster GmbH',
        narration='Muster De payment',
        postings=[
            ('Assets:N26', 'EUR', Decimal('-12.34')),
        ],
    )


def test_raise_on_payee_in_multiple_accounts(language):
    with pytest.raises(AssertionError):
        N26Importer(
            IBAN_NUMBER,
            "Assets:N26",
            language=language,
            account_patterns={
                "Expenses:Misc": [
                    "MAX MUSTERMANN",
                ],
                "Expenses:NotMisc": [
                    "MAX MUSTERMANN",
                ],
            },
        )


def test_extract_conversion(importer, filename):
    with open(filename, 'wb') as fd:
        fd.write(
            _format(
                '''
                {header}
                "2022-08-01","Alice","{iban_number}","Income","Muster GmbH","Income","56.78","","",""
                "2022-08-02","Bob","{iban_number}","Outgoing Transfer","Home food","Foo","-42.0","","",""
                "2022-08-04","Mustermann GmbH","{iban_number}","-","MasterCard Payment","-","-12.21","-12.21","EUR","1.0"
                ''',  # NOQA
                language=importer.language,
            )
        )

    with open(filename) as fd:
        transactions = importer.extract(fd)
        date = importer.file_date(fd)

    assert date == datetime.date(2022, 8, 4)
    assert len(transactions) == 3

    assert_transaction(
        transaction=transactions[0],
        date=datetime.date(2022, 8, 1),
        payee='Alice',
        narration='Muster GmbH',
        postings=[
            ('Assets:N26', 'EUR', Decimal('56.78')),
        ],
    )

    assert_transaction(
        transaction=transactions[1],
        date=datetime.date(2022, 8, 2),
        payee='Bob',
        narration='Home food',
        postings=[
            ('Assets:N26', 'EUR', Decimal('-42.0')),
        ],
    )

    assert_transaction(
        transaction=transactions[2],
        date=datetime.date(2022, 8, 4),
        payee='Mustermann GmbH',
        narration='MasterCard Payment',
        postings=[
            (
                'Assets:N26',
                'EUR',
                Decimal('-12.21') / Decimal('1'),
                ('EUR', Decimal('1')),
            ),
        ],
    )
