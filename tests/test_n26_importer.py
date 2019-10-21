from textwrap import dedent

import pytest

from beancount_n26 import _header_for, N26Importer

IBAN_NUMBER = 'DE99 9999 9999 9999 9999 99'.replace(' ', '')


def _format(string, **kwargs):
    kwargs.update({
        'iban_number': IBAN_NUMBER,
        'header': ','.join(_header_for('en'))
    })

    return dedent(string).format(**kwargs).lstrip().encode('utf-8')


@pytest.fixture
def importer():
    return N26Importer(IBAN_NUMBER, 'Assets:N26', 'en')


@pytest.fixture
def filename(tmp_path):
    return tmp_path / f'{IBAN_NUMBER}.csv'


def test_en_identify_correct(importer, filename):
    with open(filename, 'wb') as fd:
        fd.write(
            _format(
                '''
                {header}
                "2019-10-10","MAX MUSTERMANN","{iban_number}","Outgoing Transfer","Muster GmbH","Miscellaneous","-10.0","","",""
                '''
            )
        )

    with open(filename) as fd:
        assert importer.identify(fd)
