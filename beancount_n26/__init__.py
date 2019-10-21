from collections import OrderedDict
import csv
from datetime import datetime
from typing import Tuple

from beancount.core import data
from beancount.core.amount import Amount
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

    def name(self):
        return 'N26 {}'.format(self.__class__.__name__)

    def file_account(self, _):
        return self.account

    def is_valid_header(self, line):
        fields = tuple([column.strip('"') for column in line.split(',')])

        try:
            return fields == _header_for(self.language)
        except InvalidFormatError:
            return False

    def identify(self, file_):
        with open(file_.name, encoding=self.file_encoding) as fd:
            line = fd.readline().strip()

        return self.is_valid_header(line)

    def extract(self, file_):
        entries = []
        line_index = 0

        with open(file_.name, encoding=self.file_encoding) as fd:
            # Header
            line = fd.readline().strip()
            line_index += 1

            if not self.is_valid_header(line):
                raise InvalidFormatError()

            # Data entries
            reader = csv.DictReader(
                fd, delimiter=',', quoting=csv.QUOTE_MINIMAL, quotechar='"'
            )

            for index, line in enumerate(reader):
                meta = data.new_metadata(file_.name, index)

                if line['Amount (EUR)']:
                    amount = line['Amount (EUR)']
                    currency = 'EUR'
                else:
                    amount = line['Amount (Foreign Currency)']
                    currency = line['Type Foreign Currency']

                amount = Amount(amount, currency)

                date = datetime.strptime(line['Date'], '%Y-%m-%d').date()

                description = line['Payment reference']

                postings = [
                    data.Posting(self.account, amount, None, None, None, None)
                ]

                entries.append(
                    data.Transaction(
                        meta,
                        date,
                        self.FLAG,
                        None,
                        description,
                        data.EMPTY_SET,
                        data.EMPTY_SET,
                        postings,
                    )
                )

        return entries
