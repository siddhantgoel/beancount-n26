from collections import OrderedDict
import csv
from datetime import datetime
from typing import Tuple

from beancount.core import data
from beancount.core.amount import Amount
from beancount.core.number import Decimal
from beancount.ingest import importer

HEADER_FIELDS = {
    'en': OrderedDict(
        (
            ('date', 'Date'),
            ('payee', 'Payee'),
            ('account_number', 'Account number'),
            ('transaction_type', 'Transaction type'),
            ('payment_reference', 'Payment reference'),
            ('category', 'Category'),
            ('amount_eur', 'Amount (EUR)'),
            ('amount_foreign_currency', 'Amount (Foreign Currency)'),
            ('type_foreign_currency', 'Type Foreign Currency'),
            ('exchange_rate', 'Exchange Rate'),
        )
    )
}


def _is_language_supported(lang: str) -> bool:
    return lang in HEADER_FIELDS


def _header_for(lang: str) -> Tuple[str, ...]:
    return tuple(HEADER_FIELDS[lang].values())


class InvalidFormatError(Exception):
    pass


class N26Importer(importer.ImporterProtocol):
    def __init__(
        self,
        iban: str,
        account: str,
        language: str = 'en',
        file_encoding: str = 'utf-8',
    ):
        self.iban = iban
        self.account = account
        self.language = language
        self.file_encoding = file_encoding

        if not _is_language_supported(language):
            raise InvalidFormatError(
                f'Language {language} is not supported (yet)'
            )

    @property
    def _expected_header(self):
        return _header_for(self.language)

    def name(self):
        return 'N26 {}'.format(self.__class__.__name__)

    def file_account(self, _):
        return self.account

    def is_valid_header(self, line: str) -> bool:
        fields = tuple([column.strip('"') for column in line.split(',')])

        return fields == self._expected_header

    def identify(self, file_) -> bool:
        with open(file_.name, encoding=self.file_encoding) as fd:
            line = fd.readline().strip()

        return self.is_valid_header(line)

    def extract(self, file_):
        entries = []

        if not self.identify(file_):
            return []

        with open(file_.name, encoding=self.file_encoding) as fd:
            reader = csv.DictReader(
                fd, delimiter=',', quoting=csv.QUOTE_MINIMAL, quotechar='"'
            )

            for index, line in enumerate(reader):
                meta = data.new_metadata(file_.name, index)

                if line['Amount (EUR)']:
                    amount = Decimal(line['Amount (EUR)'])
                    currency = 'EUR'
                else:
                    amount = Decimal(line['Amount (Foreign Currency)'])
                    currency = line['Type Foreign Currency']

                postings = [
                    data.Posting(
                        self.account,
                        Amount(amount, currency),
                        None,
                        None,
                        None,
                        None,
                    )
                ]

                entries.append(
                    data.Transaction(
                        meta,
                        datetime.strptime(line['Date'], '%Y-%m-%d').date(),
                        self.FLAG,
                        line['Payee'],
                        line['Payment reference'],
                        data.EMPTY_SET,
                        data.EMPTY_SET,
                        postings,
                    )
                )

        return entries
