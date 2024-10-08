import datetime
import os.path
from textwrap import dedent

from beancount.core.number import Decimal
from beancount.core.data import Transaction
import pytest

from typing import Optional, List, Tuple

from beancount_n26 import _header_values_for, N26Importer, HEADER_FIELDS

IBAN_NUMBER = "DE99 9999 9999 9999 9999 99".replace(" ", "")


def _format(string, **kwargs):
    headers = _header_values_for(**kwargs)

    kwargs.update(
        {
            "iban_number": IBAN_NUMBER,
            "header": ",".join(headers[0]),
        }
    )

    return dedent(string).format(**kwargs).lstrip().encode("utf-8")


@pytest.fixture
def filename(tmp_path):
    return os.path.join(str(tmp_path), "{}.csv".format(IBAN_NUMBER))


@pytest.fixture
def importer():
    return N26Importer(
        IBAN_NUMBER,
        "Assets:N26",
        language="en",
        exchange_fees_account="Expenses:Exchange",
    )


def test_identify_with_optional(importer, filename):
    with open(filename, "wb") as fd:
        fd.write(
            _format(
                """
                "Date","Payee","Account number","Transaction type","Payment reference","Category","Amount (EUR)","Amount (Foreign Currency)","Type Foreign Currency","Exchange Rate"
                "2019-10-10","MAX MUSTERMANN","{iban_number}","Outgoing Transfer","Muster GmbH","Miscellaneous","-12.34","","",""
                """,  # NOQA
                language=importer.language,
            )
        )

    assert importer.identify(filename)


def test_identify_without_optional(importer, filename):
    with open(filename, "wb") as fd:
        fd.write(
            _format(
                """
                "Date","Payee","Account number","Transaction type","Payment reference","Amount (EUR)","Amount (Foreign Currency)","Type Foreign Currency","Exchange Rate"
                "2019-10-10","MAX MUSTERMANN","{iban_number}","Outgoing Transfer","Muster GmbH","-12.34","","",""
                """,  # NOQA
                language=importer.language,
            )
        )

    assert importer.identify(filename)


def test_identify_german(importer, filename):
    importer.language = "de"

    with open(filename, "wb") as fd:
        fd.write(
            _format(
                """
                "Datum","Empfänger","Kontonummer","Transaktionstyp","Verwendungszweck","Kategorie","Betrag (EUR)","Betrag (Fremdwährung)","Fremdwährung","Wechselkurs"
                "2019-10-10","MAX MUSTERMANN","{iban_number}","Outgoing Transfer","Muster GmbH","-12.34","","",""
                """,  # NOQA
                language=importer.language,
            )
        )

    assert importer.identify(filename)


def test_identify_french(importer, filename):
    importer.language = "fr"

    with open(filename, "wb") as fd:
        fd.write(
            _format(
                """
                "Date","Bénéficiaire","Numéro de compte","Type de transaction","Référence de paiement","Catégorie","Montant (EUR)","Montant (Devise étrangère)","Sélectionnez la devise étrangère","Taux de conversion"
                "2019-10-10","MAX MUSTERMANN","{iban_number}","Outgoing Transfer","Muster GmbH","-12.34","","",""
                """,  # NOQA
                language=importer.language,
            )
        )

    assert importer.identify(filename)


def test_extract_no_transactions(importer, filename):
    with open(filename, "wb") as fd:
        fd.write(
            _format(
                """
                "Date","Payee","Account number","Transaction type","Payment reference","Category","Amount (EUR)","Amount (Foreign Currency)","Type Foreign Currency","Exchange Rate"
                """,
                language=importer.language,
            )
        )

    transactions = importer.extract(filename)

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
            if len(expected) > 3:
                assert actual.cost.currency == expected[3][0]
                assert actual.cost.number_per == expected[3][1]


def test_extract_single_transaction(importer, filename):
    with open(filename, "wb") as fd:
        fd.write(
            _format(
                """
                "Date","Payee","Account number","Transaction type","Payment reference","Category","Amount (EUR)","Amount (Foreign Currency)","Type Foreign Currency","Exchange Rate"
                "2019-10-10","Muster GmbH","{iban_number}","Outgoing Transfer","Muster payment","Miscellaneous","-12.34","","",""
                """,  # NOQA
                language=importer.language,
            )
        )

    transactions = importer.extract(filename)
    date = importer.date(filename)

    assert date == datetime.date(2019, 10, 10)

    assert len(transactions) == 1
    assert_transaction(
        transaction=transactions[0],
        date=datetime.date(2019, 10, 10),
        payee="Muster GmbH",
        narration="Muster payment",
        postings=[
            ("Assets:N26", "EUR", Decimal("-12.34")),
        ],
    )


def test_extract_multiple_transactions(importer, filename):
    with open(filename, "wb") as fd:
        fd.write(
            _format(
                """
                "Date","Payee","Account number","Transaction type","Payment reference","Category","Amount (EUR)","Amount (Foreign Currency)","Type Foreign Currency","Exchange Rate"
                "2019-12-28","MAX MUSTERMANN","{iban_number}","Income","Muster GmbH","Income","-56.78","","",""
                "2020-01-05","Muster SARL","{iban_number}","Outgoing Transfer","Muster Fr payment","Income","-42.24","","",""
                "2020-01-03","Muster GmbH","{iban_number}","Outgoing Transfer","Muster De payment","Income","-12.34","","",""
                """,  # NOQA
                language=importer.language,
            )
        )

    transactions = importer.extract(filename)
    date = importer.date(filename)

    assert date == datetime.date(2020, 1, 5)
    assert len(transactions) == 3

    assert_transaction(
        transaction=transactions[0],
        date=datetime.date(2019, 12, 28),
        payee="MAX MUSTERMANN",
        narration="Muster GmbH",
        postings=[
            ("Assets:N26", "EUR", Decimal("-56.78")),
        ],
    )

    assert_transaction(
        transaction=transactions[1],
        date=datetime.date(2020, 1, 5),
        payee="Muster SARL",
        narration="Muster Fr payment",
        postings=[
            ("Assets:N26", "EUR", Decimal("-42.24")),
        ],
    )

    assert_transaction(
        transaction=transactions[2],
        date=datetime.date(2020, 1, 3),
        payee="Muster GmbH",
        narration="Muster De payment",
        postings=[
            ("Assets:N26", "EUR", Decimal("-12.34")),
        ],
    )


def test_extract_multiple_transactions_with_classification(filename):
    importer = N26Importer(
        IBAN_NUMBER,
        "Assets:N26",
        language="en",
        account_patterns={
            "Expenses:Misc": [
                "MAX MUSTERMANN",
            ]
        },
    )

    with open(filename, "wb") as fd:
        fd.write(
            _format(
                """
                "Date","Payee","Account number","Transaction type","Payment reference","Category","Amount (EUR)","Amount (Foreign Currency)","Type Foreign Currency","Exchange Rate"
                "2019-12-28","MAX MUSTERMANN","{iban_number}","Income","Muster GmbH","Income","-56.78","","",""
                "2020-01-05","Muster SARL","{iban_number}","Outgoing Transfer","Muster Fr payment","Income","-42.24","","",""
                "2020-01-03","Muster GmbH","{iban_number}","Outgoing Transfer","Muster De payment","Income","-12.34","","",""
                """,  # NOQA
                language=importer.language,
            )
        )

    transactions = importer.extract(filename)
    date = importer.date(filename)

    assert date == datetime.date(2020, 1, 5)
    assert len(transactions) == 3

    assert_transaction(
        transaction=transactions[0],
        date=datetime.date(2019, 12, 28),
        payee="MAX MUSTERMANN",
        narration="Muster GmbH",
        postings=[
            ("Assets:N26", "EUR", Decimal("-56.78")),
            ("Expenses:Misc", None, None),
        ],
    )

    assert_transaction(
        transaction=transactions[1],
        date=datetime.date(2020, 1, 5),
        payee="Muster SARL",
        narration="Muster Fr payment",
        postings=[
            ("Assets:N26", "EUR", Decimal("-42.24")),
        ],
    )

    assert_transaction(
        transaction=transactions[2],
        date=datetime.date(2020, 1, 3),
        payee="Muster GmbH",
        narration="Muster De payment",
        postings=[
            ("Assets:N26", "EUR", Decimal("-12.34")),
        ],
    )


@pytest.mark.parametrize("language", HEADER_FIELDS.keys())
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
    with open(filename, "wb") as fd:
        fd.write(
            _format(
                """
                "Date","Payee","Account number","Transaction type","Payment reference","Category","Amount (EUR)","Amount (Foreign Currency)","Type Foreign Currency","Exchange Rate"
                "2022-08-01","Alice","{iban_number}","Income","Muster GmbH","Income","56.78","","",""
                "2022-08-02","Bob","{iban_number}","Outgoing Transfer","Home food","Foo","-42.0","","",""
                "2022-08-03","Charlie","{iban_number}","Outgoing Transfer in a foreign currency","Foreign food","Bar","-10.0","9.13","CHF","0.9687"
                "2022-08-04","Mustermann GmbH","{iban_number}","-","MasterCard Payment","-","-12.21","-12.21","EUR","1.0"
                """,  # NOQA
                language=importer.language,
            )
        )

    transactions = importer.extract(filename)
    date = importer.date(filename)

    assert date == datetime.date(2022, 8, 4)
    assert len(transactions) == 4

    assert_transaction(
        transaction=transactions[0],
        date=datetime.date(2022, 8, 1),
        payee="Alice",
        narration="Muster GmbH",
        postings=[
            ("Assets:N26", "EUR", Decimal("56.78")),
        ],
    )

    assert_transaction(
        transaction=transactions[1],
        date=datetime.date(2022, 8, 2),
        payee="Bob",
        narration="Home food",
        postings=[
            ("Assets:N26", "EUR", Decimal("-42.0")),
        ],
    )

    assert_transaction(
        transaction=transactions[2],
        date=datetime.date(2022, 8, 3),
        payee="Charlie",
        narration="Foreign food",
        postings=[
            ("Assets:N26", "EUR", Decimal("0.574997419221637245793331269")),
            (
                "Expenses:Exchange",
                "EUR",
                Decimal("-0.574997419221637245793331269"),
            ),
            (
                "Assets:N26",
                "EUR",
                Decimal("-9.13") / Decimal("0.9687"),
                ("CHF", Decimal("0.9687")),
            ),
        ],
    )

    assert_transaction(
        transaction=transactions[3],
        date=datetime.date(2022, 8, 4),
        payee="Mustermann GmbH",
        narration="MasterCard Payment",
        postings=[
            (
                "Assets:N26",
                "EUR",
                Decimal("-12.21") / Decimal("1"),
                ("EUR", Decimal("1")),
            ),
        ],
    )


def test_extract_updated_header(importer, filename):
    with open(filename, "wb") as fd:
        fd.write(
            _format(
                """
                "Booking Date","Value Date","Partner Name","Partner Iban",Type,"Payment Reference","Account Name","Amount (EUR)","Original Amount","Original Currency","Exchange Rate"
                2019-10-10,2019-10-10,Muster GmbH,{iban_number},Presentment,Muster payment,"Main Account",-12.34,,,
                """,  # NOQA
                language=importer.language,
            )
        )

    transactions = importer.extract(filename)
    date = importer.date(filename)

    assert date == datetime.date(2019, 10, 10)

    assert len(transactions) == 1
    assert_transaction(
        transaction=transactions[0],
        date=datetime.date(2019, 10, 10),
        payee="Muster GmbH",
        narration="Muster payment",
        postings=[
            ("Assets:N26", "EUR", Decimal("-12.34")),
        ],
    )
