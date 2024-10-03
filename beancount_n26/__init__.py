from collections import OrderedDict, namedtuple
import csv
import re
from datetime import datetime
from typing import Dict, List, Optional

from beancount.core import data, flags
from beancount.core.amount import Amount
from beancount.core.number import Decimal
from beancount.core.position import CostSpec
from beangulp.importer import Importer

HeaderField = namedtuple("HeaderField", ["label", "optional"])

HEADER_FIELDS = {
    "en": (
        OrderedDict(
            {
                "date": HeaderField("Date", False),
                "payee": HeaderField("Payee", False),
                "account_number": HeaderField("Account number", False),
                "transaction_type": HeaderField("Transaction type", False),
                "payment_reference": HeaderField("Payment reference", False),
                "category": HeaderField("Category", True),
                "amount_eur": HeaderField("Amount (EUR)", False),
                "amount_foreign_currency": HeaderField(
                    "Amount (Foreign Currency)", False
                ),
                "type_foreign_currency": HeaderField("Type Foreign Currency", False),
                "exchange_rate": HeaderField("Exchange Rate", False),
            }
        ),
        OrderedDict(
            {
                "date": HeaderField("Booking Date", False),
                "value_date": HeaderField("Value Date", False),
                "payee": HeaderField("Partner Name", False),
                "account_number": HeaderField("Partner Iban", False),
                "transaction_type": HeaderField("Type", False),
                "payment_reference": HeaderField("Payment Reference", False),
                "category": HeaderField("Category", True),
                "account_name": HeaderField("Account Name", False),
                "amount_eur": HeaderField("Amount (EUR)", False),
                "amount_foreign_currency": HeaderField("Original Amount", False),
                "type_foreign_currency": HeaderField("Original Currency", False),
                "exchange_rate": HeaderField("Exchange Rate", False),
            }
        ),
    ),
    "de": (
        OrderedDict(
            {
                "date": HeaderField("Datum", False),
                "payee": HeaderField("Empfänger", False),
                "account_number": HeaderField("Kontonummer", False),
                "transaction_type": HeaderField("Transaktionstyp", False),
                "payment_reference": HeaderField("Verwendungszweck", False),
                "category": HeaderField("Kategorie", True),
                "amount_eur": HeaderField("Betrag (EUR)", False),
                "amount_foreign_currency": HeaderField("Betrag (Fremdwährung)", False),
                "type_foreign_currency": HeaderField("Fremdwährung", False),
                "exchange_rate": HeaderField("Wechselkurs", False),
            }
        ),
    ),
    "fr": (
        OrderedDict(
            {
                "date": HeaderField("Date", False),
                "payee": HeaderField("Bénéficiaire", False),
                "account_number": HeaderField("Numéro de compte", False),
                "transaction_type": HeaderField("Type de transaction", False),
                "payment_reference": HeaderField("Référence de paiement", False),
                "category": HeaderField("Catégorie", True),
                "amount_eur": HeaderField("Montant (EUR)", False),
                "amount_foreign_currency": HeaderField(
                    "Montant (Devise étrangère)", False
                ),
                "type_foreign_currency": HeaderField(
                    "Sélectionnez la devise étrangère", False
                ),
                "exchange_rate": HeaderField("Taux de conversion", False),
            }
        ),
    ),
}


def _is_language_supported(language: str) -> bool:
    return language in HEADER_FIELDS


def _header_values_for(language: str, include_optional: bool = True) -> List[List[str]]:
    result = []
    translations = HEADER_FIELDS[language]

    for translation in translations:
        if include_optional:
            entries = OrderedDict(
                (key, value.label) for (key, value) in translation.items()
            )
        else:
            entries = OrderedDict(
                (key, value.label)
                for (key, value) in translation.items()
                if not value.optional
            )
        result.append(list(entries.values()))

    return result


class InvalidFormatError(Exception):
    pass


PayeePattern = namedtuple("PayeePattern", ["regex", "account"])


class N26Importer(Importer):
    def __init__(
        self,
        iban: str,
        account_name: str,
        language: str = "en",
        file_encoding: str = "utf-8",
        account_patterns: Dict[str, List[str]] = {},
        exchange_fees_account: Optional[str] = None,
    ):
        self.iban = iban
        self.account_name = account_name
        self.language = language
        self.file_encoding = file_encoding
        self.payee_patterns = set()
        self.exchange_fees_account = exchange_fees_account

        self._filepath = None
        self._translation_strings = None

        if not _is_language_supported(language):
            raise InvalidFormatError(
                "Language {} is not supported (yet)".format(language)
            )

        # Compile account and payee pattern regular expressions

        seen_patterns = set()

        for account, patterns in account_patterns.items():
            for pattern in patterns:
                assert (
                    pattern not in seen_patterns
                ), f"{pattern} defined in multiple accounts"

                seen_patterns.add(pattern)
                self.payee_patterns.add(
                    PayeePattern(
                        regex=re.compile(pattern, flags=re.IGNORECASE),
                        account=account,
                    )
                )

    def account(self, _) -> data.Account:
        return data.Account(self.account_name)

    def _update_translations(self, filepath: str):
        with open(filepath, encoding=self.file_encoding) as fd:
            line = fd.readline().strip()

        actual_header = [column.strip('"') for column in line.split(",")]

        translations = HEADER_FIELDS[self.language]

        for translation in translations:
            fields = translation.values()
            header_with_optional = [field.label for field in fields]
            header_without_optional = [
                field.label for field in fields if not field.optional
            ]

            if (
                actual_header == header_with_optional
                or actual_header == header_without_optional
            ):
                self._translation_strings = {
                    key: value.label for (key, value) in translation.items()
                }
                return

        raise InvalidFormatError(
            "File {} does not contain any of the expected headers".format(filepath)
        )

    def _translate(self, key):
        return self._translation_strings[key]

    def _parse_date(self, entry):
        return datetime.strptime(entry[self._translate("date")], "%Y-%m-%d").date()

    def name(self):
        return "N26 {}".format(self.__class__.__name__)

    def date(self, filepath: str) -> Optional[datetime.date]:
        if not self.identify(filepath):
            return None

        self._update_translations(filepath)

        date = None

        with open(filepath, encoding=self.file_encoding) as fd:
            reader = csv.DictReader(
                fd, delimiter=",", quoting=csv.QUOTE_MINIMAL, quotechar='"'
            )

            for line in reader:
                date_tmp = self._parse_date(line)

                if not date or date_tmp > date:
                    date = date_tmp

        return date

    def identify(self, filepath: str) -> bool:
        try:
            with open(filepath, encoding=self.file_encoding) as fd:
                line = fd.readline().strip()

            expected_headers = _header_values_for(self.language) + _header_values_for(
                self.language, include_optional=False
            )
            actual_header = [column.strip('"') for column in line.split(",")]

            for expected_header in expected_headers:
                if expected_header != actual_header:
                    continue
                return True

            return False
        except ValueError:
            return False

    def extract(self, filepath: str, existing: data.Entries = None) -> data.Entries:
        entries = []

        if not self.identify(filepath):
            return []

        self._update_translations(filepath)

        s_amount_eur = self._translate("amount_eur")
        s_amount_foreign_currency = self._translate("amount_foreign_currency")
        s_payee = self._translate("payee")
        s_payment_reference = self._translate("payment_reference")
        s_type_foreign_currency = self._translate("type_foreign_currency")
        s_exchange_rate = self._translate("exchange_rate")

        with open(filepath, encoding=self.file_encoding) as fd:
            reader = csv.DictReader(
                fd, delimiter=",", quoting=csv.QUOTE_MINIMAL, quotechar='"'
            )

            for index, line in enumerate(reader):
                meta = data.new_metadata(filepath, index)

                postings = []

                if line[s_amount_foreign_currency]:
                    exchange_rate = Decimal(line[s_exchange_rate])
                    amount_eur = Decimal(line[s_amount_eur])
                    amount_foreign = Decimal(line[s_amount_foreign_currency])
                    currency = line[s_type_foreign_currency]

                    fees = amount_eur + abs(amount_foreign / exchange_rate)

                    if fees != 0:
                        assert (
                            self.exchange_fees_account
                        ), "exchange_fees_account required for conversion fees"

                        postings += [
                            data.Posting(
                                self.account(filepath),
                                Amount(-fees, "EUR"),
                                None,
                                None,
                                None,
                                None,
                            ),
                            data.Posting(
                                self.exchange_fees_account,
                                Amount(fees, "EUR"),
                                None,
                                None,
                                None,
                                None,
                            ),
                        ]

                    postings += [
                        data.Posting(
                            self.account(filepath),
                            Amount(amount_eur - fees, "EUR"),
                            CostSpec(exchange_rate, None, currency, None, None, None),
                            None,
                            None,
                            None,
                        ),
                    ]
                else:
                    amount = Decimal(line[s_amount_eur])

                    postings += [
                        data.Posting(
                            self.account(filepath),
                            Amount(amount, "EUR"),
                            None,
                            None,
                            None,
                            None,
                        ),
                    ]

                match = None
                for pattern in self.payee_patterns:
                    if pattern.regex.match(line[s_payee]):
                        match = pattern.account
                if match:
                    postings += [
                        data.Posting(
                            match,
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
                        flags.FLAG_OKAY,
                        line[s_payee],
                        line[s_payment_reference],
                        data.EMPTY_SET,
                        data.EMPTY_SET,
                        postings,
                    )
                )

        return entries
