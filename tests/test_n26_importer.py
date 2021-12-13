import datetime
import os.path
from textwrap import dedent

from beancount.core.number import Decimal
import pytest

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
    return N26Importer(IBAN_NUMBER, 'Assets:N26', language)


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
    assert transactions[0].date == datetime.date(2019, 10, 10)
    assert transactions[0].payee == 'Muster GmbH'
    assert transactions[0].narration == 'Muster payment'

    assert len(transactions[0].postings) == 1
    assert transactions[0].postings[0].account == 'Assets:N26'
    assert transactions[0].postings[0].units.currency == 'EUR'
    assert transactions[0].postings[0].units.number == Decimal('-12.34')


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

    # first

    assert transactions[0].date == datetime.date(2019, 12, 28)
    assert transactions[0].payee == 'MAX MUSTERMANN'
    assert transactions[0].narration == 'Muster GmbH'

    assert len(transactions[0].postings) == 1
    assert transactions[0].postings[0].account == 'Assets:N26'
    assert transactions[0].postings[0].units.currency == 'EUR'
    assert transactions[0].postings[0].units.number == Decimal('-56.78')

    # second

    assert transactions[1].date == datetime.date(2020, 1, 5)
    assert transactions[1].payee == 'Muster SARL'
    assert transactions[1].narration == 'Muster Fr payment'

    assert len(transactions[1].postings) == 1
    assert transactions[1].postings[0].account == 'Assets:N26'
    assert transactions[1].postings[0].units.currency == 'EUR'
    assert transactions[1].postings[0].units.number == Decimal('-42.24')

    # third

    assert transactions[2].date == datetime.date(2020, 1, 3)
    assert transactions[2].payee == 'Muster GmbH'
    assert transactions[2].narration == 'Muster De payment'

    assert len(transactions[2].postings) == 1
    assert transactions[2].postings[0].account == 'Assets:N26'
    assert transactions[2].postings[0].units.currency == 'EUR'
    assert transactions[2].postings[0].units.number == Decimal('-12.34')
