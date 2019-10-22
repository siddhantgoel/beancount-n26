from collections import OrderedDict
import csv
from datetime import datetime
from typing import Mapping, Tuple

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
    ),
    'de': OrderedDict(
        (
            ('date', 'Datum'),
            ('payee', 'Empfänger'),
            ('account_number', 'Kontonummer'),
            ('transaction_type', 'Transaktionstyp'),
            ('payment_reference', 'Verwendungszweck'),
            ('category', 'Kategorie'),
            ('amount_eur', 'Betrag (EUR)'),
            ('amount_foreign_currency', 'Betrag (Fremdwährung)'),
            ('type_foreign_currency', 'Fremdwährung'),
            ('exchange_rate', 'Wechselkurs'),
        )
    ),
}


def _is_language_supported(language: str) -> bool:
    return language in HEADER_FIELDS


def _translation_strings_for(language: str) -> Mapping[str, str]:
    return HEADER_FIELDS[language]


def _header_values_for(language: str) -> Tuple[str, ...]:
    return tuple(_translation_strings_for(language).values())


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
                'Language {} is not supported (yet)'.format(language)
            )

        self._translation_strings = _translation_strings_for(self.language)

    def _translate(self, key):
        return self._translation_strings[key]

    def name(self):
        return 'N26 {}'.format(self.__class__.__name__)

    def file_account(self, _):
        return self.account

    def is_valid_header(self, line: str) -> bool:
        expected_values = _header_values_for(self.language)
        actual_values = [column.strip('"') for column in line.split(',')]

        if len(expected_values) != len(actual_values):
            return False

        for (expected, actual) in zip(expected_values, actual_values):
            if expected != actual:
                return False

        return True

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

                s_amount_eur = self._translate('amount_eur')
                s_amount_foreign_currency = self._translate(
                    'amount_foreign_currency'
                )
                s_date = self._translate('date')
                s_payee = self._translate('payee')
                s_payment_reference = self._translate('payment_reference')
                s_type_foreign_currency = self._translate(
                    'type_foreign_currency'
                )

                if line[s_amount_eur]:
                    amount = Decimal(line[s_amount_eur])
                    currency = 'EUR'
                else:
                    amount = Decimal(line[s_amount_foreign_currency])
                    currency = line[s_type_foreign_currency]

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
                        datetime.strptime(line[s_date], '%Y-%m-%d').date(),
                        self.FLAG,
                        line[s_payee],
                        line[s_payment_reference],
                        data.EMPTY_SET,
                        data.EMPTY_SET,
                        postings,
                    )
                )

        return entries
