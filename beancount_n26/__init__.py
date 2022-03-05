from collections import OrderedDict
import csv
import re
import logging
from datetime import datetime
from typing import Mapping, Tuple, Dict, List

from beancount.core import data
from beancount.core.amount import Amount
from beancount.core.number import Decimal
from beancount.ingest import importer

HEADER_FIELDS = {
    "en": OrderedDict(
        {
            "date": {"label": "Date", "optional": False},
            "payee": {"label": "Payee", "optional": False},
            "account_number": {"label": "Account number", "optional": False},
            "transaction_type": {
                "label": "Transaction type",
                "optional": False,
            },
            "payment_reference": {
                "label": "Payment reference",
                "optional": False,
            },
            "category": {"label": "Category", "optional": True},
            "amount_eur": {"label": "Amount (EUR)", "optional": False},
            "amount_foreign_currency": {
                "label": "Amount (Foreign Currency)",
                "optional": False,
            },
            "type_foreign_currency": {
                "label": "Type Foreign Currency",
                "optional": False,
            },
            "exchange_rate": {"label": "Exchange Rate", "optional": False},
        }
    ),
    "de": OrderedDict(
        {
            "date": {"label": "Datum", "optional": False},
            "payee": {"label": "Empfänger", "optional": False},
            "account_number": {"label": "Kontonummer", "optional": False},
            "transaction_type": {
                "label": "Transaktionstyp",
                "optional": False,
            },
            "payment_reference": {
                "label": "Verwendungszweck",
                "optional": False,
            },
            "category": {"label": "Kategorie", "optional": True},
            "amount_eur": {"label": "Betrag (EUR)", "optional": False},
            "amount_foreign_currency": {
                "label": "Betrag (Fremdwährung)",
                "optional": False,
            },
            "type_foreign_currency": {
                "label": "Fremdwährung",
                "optional": False,
            },
            "exchange_rate": {"label": "Wechselkurs", "optional": False},
        }
    ),
    "fr": OrderedDict(
        {
            "date": {"label": "Date", "optional": False},
            "payee": {"label": "Bénéficiaire", "optional": False},
            "account_number": {"label": "Numéro de compte", "optional": False},
            "transaction_type": {
                "label": "Type de transaction",
                "optional": False,
            },
            "payment_reference": {
                "label": "Référence de paiement",
                "optional": False,
            },
            "category": {"label": "Catégorie", "optional": True},
            "amount_eur": {"label": "Montant (EUR)", "optional": False},
            "amount_foreign_currency": {
                "label": "Montant (Devise étrangère)",
                "optional": False,
            },
            "type_foreign_currency": {
                "label": "Sélectionnez la devise étrangère",
                "optional": False,
            },
            "exchange_rate": {
                "label": "Taux de conversion",
                "optional": False,
            },
        }
    ),
}


def _is_language_supported(language: str) -> bool:
    return language in HEADER_FIELDS


def _translation_strings_for(language: str) -> Mapping[str, str]:
    return OrderedDict(
        ((k, v["label"]) for (k, v) in HEADER_FIELDS[language].items())
    )


def _header_values_for(
    language: str, include_optional: bool = True
) -> Tuple[str, ...]:
    headers = _translation_strings_for(language)
    if not include_optional:
        for k, v in HEADER_FIELDS[language].items():
            if v["optional"]:
                del headers[k]
    return headers.values()


class InvalidFormatError(Exception):
    pass


class N26Importer(importer.ImporterProtocol):
    def __init__(
        self,
        iban: str,
        account: str,
        language: str = "en",
        file_encoding: str = "utf-8",
        account_to_payees: Dict[str, List[str]] = {},
        fill_default: bool = False,
        default_tbd_account: str = "Expenses:TBD",
    ):
        self.iban = iban
        self.account = account
        self.language = language
        self.file_encoding = file_encoding
        self.account_to_payees = account_to_payees
        self.fill_default = fill_default
        self.default_tbd_account = default_tbd_account
        self.regexes = {}

        if not _is_language_supported(language):
            raise InvalidFormatError(
                f"Language {language} is not supported (yet)"
            )

        self._translation_strings = _translation_strings_for(self.language)

        self.payee_to_account = {}

        for account, payees in self.account_to_payees.items():
            for payee in set(payees):
                if payee in self.payee_to_account:
                    logging.warning(f"{payee} in multiple accounts")
                    self.payee_to_account[payee] = "Expenses:TBD"
                else:
                    self.payee_to_account[payee] = account

        for payee, account in self.payee_to_account.items():
            self.regexes[payee] = re.compile(payee, flags=re.IGNORECASE)

    def _translate(self, key):
        return self._translation_strings[key]

    def _parse_date(self, entry, key="date"):
        return datetime.strptime(
            entry[self._translate(key)], "%Y-%m-%d"
        ).date()

    def name(self):
        return f"N26 {self.__class__.__name__}"

    def file_account(self, _):
        return self.account

    def file_date(self, file_):
        if not self.identify(file_):
            return None

        date = None

        with open(file_.name, encoding=self.file_encoding) as fd:
            reader = csv.DictReader(
                fd, delimiter=",", quoting=csv.QUOTE_MINIMAL, quotechar='"'
            )

            for line in reader:
                date_tmp = self._parse_date(line)

                if not date or date_tmp > date:
                    date = date_tmp

        return date

    def is_valid_header(self, line: str) -> bool:
        expected_values = _header_values_for(self.language)
        actual_values = [column.strip('"') for column in line.split(",")]

        if len(expected_values) != len(actual_values):
            expected_values = _header_values_for(
                self.language, include_optional=False
            )
            if len(expected_values) != len(actual_values):
                return False

        for (expected, actual) in zip(expected_values, actual_values):
            if expected != actual:
                return False

        return True

    def identify(self, file_) -> bool:
        try:
            with open(file_.name, encoding=self.file_encoding) as fd:
                line = fd.readline().strip()
        except ValueError:
            return False
        else:
            return self.is_valid_header(line)

    def extract(self, file_, existing_entries=None):
        entries = []

        if not self.identify(file_):
            return []

        with open(file_.name, encoding=self.file_encoding) as fd:
            reader = csv.DictReader(
                fd, delimiter=",", quoting=csv.QUOTE_MINIMAL, quotechar='"'
            )

            for index, line in enumerate(reader):
                meta = data.new_metadata(file_.name, index)

                s_amount_eur = self._translate("amount_eur")
                s_amount_foreign_currency = self._translate(
                    "amount_foreign_currency"
                )
                s_payee = self._translate("payee")
                s_payment_reference = self._translate("payment_reference")
                s_type_foreign_currency = self._translate(
                    "type_foreign_currency"
                )

                if line[s_amount_eur]:
                    amount = Decimal(line[s_amount_eur])
                    currency = "EUR"
                else:
                    amount = Decimal(line[s_amount_foreign_currency])
                    currency = line[s_type_foreign_currency]

                match = None
                for payee, prog in self.regexes.items():
                    if prog.match(line[s_payee]):
                        match = self.payee_to_account[payee]

                postings = [
                    data.Posting(
                        self.account,
                        Amount(amount, currency),
                        None,
                        None,
                        None,
                        None,
                    ),
                ]
                if self.fill_default or match:
                    postings += [
                        data.Posting(
                            match if match else self.default_tbd_account,
                            None,
                            None,
                            None,
                            None,
                            None,
                        ),
                    ]

                entries.append(
                    data.Transaction(
                        meta,
                        self._parse_date(line),
                        self.FLAG,
                        line[s_payee],
                        line[s_payment_reference],
                        data.EMPTY_SET,
                        data.EMPTY_SET,
                        postings,
                    )
                )

        return entries
