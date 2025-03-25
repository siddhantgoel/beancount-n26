import datetime
from textwrap import dedent

from beancount.parser.cmptest import TestCase as BeancountTest
from beancount.parser.booking import convert_lot_specs_to_lots
import pytest

from beancount_n26 import N26Importer, HEADER_FIELDS

IBAN_NUMBER = "DE99 9999 9999 9999 9999 99".replace(" ", "")


def assert_equal_entries(expected_entries, actual_entries, allow_incomplete=False):
    # convert CostSpec to Cost to allow comparison
    actual_with_costs = convert_lot_specs_to_lots(actual_entries)[0]
    BeancountTest.assertEqualEntries(pytest, expected_entries, actual_with_costs, allow_incomplete)

@pytest.fixture
def filename(request, tmp_path):
    with open(tmp_path / 'input.csv', 'w') as file:
        file.write(dedent(request.function.__doc__))
        file.flush()
        return file.name

@pytest.fixture
def importer():
    return N26Importer(
        IBAN_NUMBER,
        "Assets:N26",
        language="en",
        exchange_fees_account="Expenses:Exchange",
    )


def test_identify_with_optional(importer, filename):
    """\
    "Date","Payee","Account number","Transaction type","Payment reference","Category","Amount (EUR)","Amount (Foreign Currency)","Type Foreign Currency","Exchange Rate"
    "2019-10-10","MAX MUSTERMANN","DE99999999999999999999","Outgoing Transfer","Muster GmbH","Miscellaneous","-12.34","","",""
    """

    assert importer.identify(filename)


def test_identify_without_optional(importer, filename):
    """\
    "Date","Payee","Account number","Transaction type","Payment reference","Amount (EUR)","Amount (Foreign Currency)","Type Foreign Currency","Exchange Rate"
    "2019-10-10","MAX MUSTERMANN","DE99999999999999999999","Outgoing Transfer","Muster GmbH","-12.34","","",""
    """

    assert importer.identify(filename)


def test_identify_german(importer, filename):
    """\
    "Datum","Empfänger","Kontonummer","Transaktionstyp","Verwendungszweck","Kategorie","Betrag (EUR)","Betrag (Fremdwährung)","Fremdwährung","Wechselkurs"
    "2019-10-10","MAX MUSTERMANN","DE99999999999999999999","Outgoing Transfer","Muster GmbH","-12.34","","",""
    """
    importer.language = "de"

    assert importer.identify(filename)


def test_identify_french(importer, filename):
    """\
    "Date","Bénéficiaire","Numéro de compte","Type de transaction","Référence de paiement","Catégorie","Montant (EUR)","Montant (Devise étrangère)","Sélectionnez la devise étrangère","Taux de conversion"
    "2019-10-10","MAX MUSTERMANN","DE99999999999999999999","Outgoing Transfer","Muster GmbH","-12.34","","",""
    """

    importer.language = "fr"
    assert importer.identify(filename)


def test_extract_no_transactions(importer, filename):
    """
    "Date","Payee","Account number","Transaction type","Payment reference","Category","Amount (EUR)","Amount (Foreign Currency)","Type Foreign Currency","Exchange Rate"
    """
    transactions = importer.extract(filename)

    assert len(transactions) == 0


def test_extract_single_transaction(importer, filename):
    """\
    "Date","Payee","Account number","Transaction type","Payment reference","Category","Amount (EUR)","Amount (Foreign Currency)","Type Foreign Currency","Exchange Rate"
    "2019-10-10","Muster GmbH","DE99999999999999999999","Outgoing Transfer","Muster payment","Miscellaneous","-12.34","","",""
    """

    transactions = importer.extract(filename)
    date = importer.date(filename)

    assert date == datetime.date(2019, 10, 10)
    assert_equal_entries(r"""
      2019-10-10 * "Muster GmbH" "Muster payment"
        Assets:N26  -12.34 EUR
    """, transactions)

def test_extract_multiple_transactions(importer, filename):
    """\
    "Date","Payee","Account number","Transaction type","Payment reference","Category","Amount (EUR)","Amount (Foreign Currency)","Type Foreign Currency","Exchange Rate"
    "2019-12-28","MAX MUSTERMANN","DE99999999999999999999","Income","Muster GmbH","Income","-56.78","","",""
    "2020-01-05","Muster SARL","DE99999999999999999999","Outgoing Transfer","Muster Fr payment","Income","-42.24","","",""
    "2020-01-03","Muster GmbH","DE99999999999999999999","Outgoing Transfer","Muster De payment","Income","-12.34","","",""
    """

    transactions = importer.extract(filename)
    date = importer.date(filename)

    assert date == datetime.date(2020, 1, 5)
    assert_equal_entries(r"""
      2019-12-28 * "MAX MUSTERMANN" "Muster GmbH"
          Assets:N26     -56.78 EUR

      2020-01-03 * "Muster GmbH" "Muster De payment"
          Assets:N26  -12.34 EUR

      2020-01-05 * "Muster SARL" "Muster Fr payment"
          Assets:N26  -42.24 EUR
    """, transactions)

def test_extract_multiple_transactions_with_classification(filename):
    """\
    "Date","Payee","Account number","Transaction type","Payment reference","Category","Amount (EUR)","Amount (Foreign Currency)","Type Foreign Currency","Exchange Rate"
    "2019-12-28","MAX MUSTERMANN","DE99999999999999999999","Income","Muster GmbH","Income","-56.78","","",""
    "2020-01-05","Muster SARL","DE99999999999999999999","Outgoing Transfer","Muster Fr payment","Income","-42.24","","",""
    "2020-01-03","Muster GmbH","DE99999999999999999999","Outgoing Transfer","Muster De payment","Income","-12.34","","",""
    """

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

    transactions = importer.extract(filename)
    date = importer.date(filename)

    assert date == datetime.date(2020, 1, 5)
    assert_equal_entries(r"""
      2019-12-28 * "MAX MUSTERMANN" "Muster GmbH"
          Assets:N26     -56.78 EUR
          Expenses:Misc

      2020-01-03 * "Muster GmbH" "Muster De payment"
          Assets:N26  -12.34 EUR

      2020-01-05 * "Muster SARL" "Muster Fr payment"
          Assets:N26  -42.24 EUR
    """, transactions, allow_incomplete=True)


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
    """\
    "Date","Payee","Account number","Transaction type","Payment reference","Category","Amount (EUR)","Amount (Foreign Currency)","Type Foreign Currency","Exchange Rate"
    "2022-08-01","Alice","DE99999999999999999999","Income","Muster GmbH","Income","56.78","","",""
    "2022-08-02","Bob","DE99999999999999999999","Outgoing Transfer","Home food","Foo","-42.0","","",""
    "2022-08-03","Charlie","DE99999999999999999999","Outgoing Transfer in a foreign currency","Foreign food","Bar","-10.0","9.13","CHF","0.9687"
    "2022-08-04","Mustermann GmbH","DE99999999999999999999","-","MasterCard Payment","-","-12.21","-12.21","EUR","1.0"
    """

    transactions = importer.extract(filename)

    date = importer.date(filename)
    assert date == datetime.date(2022, 8, 4)

    assert_equal_entries(r"""
      2022-08-01 * "Alice" "Muster GmbH"
        Assets:N26  56.78 EUR

      2022-08-02 * "Bob" "Home food"
        Assets:N26  -42.0 EUR

      2022-08-03 * "Charlie" "Foreign food"
        Assets:N26          0.574997419221637245793331269 EUR
        Expenses:Exchange  -0.574997419221637245793331269 EUR
        Assets:N26         -9.425002580778362754206668731 EUR {0.9687 CHF}

      2022-08-04 * "Mustermann GmbH" "MasterCard Payment"
        Assets:N26  -12.21 EUR {1.0 EUR}
   """, transactions, allow_incomplete=True)

def test_extract_updated_header(importer, filename):
    """\
    "Booking Date","Value Date","Partner Name","Partner Iban",Type,"Payment Reference","Account Name","Amount (EUR)","Original Amount","Original Currency","Exchange Rate"
    2019-10-10,2019-10-10,Muster GmbH,DE99999999999999999999,Presentment,Muster payment,"Main Account",-12.34,,,
    """

    transactions = importer.extract(filename)
    date = importer.date(filename)

    assert date == datetime.date(2019, 10, 10)

    assert_equal_entries(r"""
      2019-10-10 * "Muster GmbH" "Muster payment"
        Assets:N26  -12.34 EUR
    """, transactions)
