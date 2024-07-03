import json

from beancount.core import data
from beancount import loader

from collections import defaultdict


def generate_payees_to_account(main_file: str, dump_file: str):
    """
    main_file: str
        The beancount file from which you want to dump the transactions
    dump_file: str
        The file in which you want to write the json object

    Generates a Dict[str, List[str]] containing for each "payee" in the
    transaction it's associated list of accounts
    """
    entries, errors, options = loader.load_file(main_file)
    transactions = list(filter(lambda x: isinstance(x, data.Transaction), entries))
    payees_to_account = defaultdict(set)
    for item in transactions:
        payees_to_account[item.payee.lower() if item.payee else None].add(
            item.postings[1].account
        )

    for k, v in payees_to_account.items():
        payees_to_account[k] = sorted(list(v))

    with open(dump_file, "w") as f:
        json.dump(payees_to_account, f, indent=2)


def generate_account_to_payees(main_file: str, dump_file: str):
    """
    main_file: str
        The beancount file from which you want to dump the transactions
    dump_file: str
        The file in which you want to write the json object

    Generates a Dict[str, List[str]] containing for each account in the
    transaction it's associated list of payees
    """
    entries, errors, options = loader.load_file(main_file)
    transactions = list(filter(lambda x: isinstance(x, data.Transaction), entries))
    account_to_payees = defaultdict(set)
    for item in transactions:
        account_to_payees[item.postings[1].account].add(
            item.payee.lower() if item.payee else None
        )

    for k, v in account_to_payees.items():
        account_to_payees[k] = sorted(list(filter(None, v)))

    with open(dump_file, "w") as f:
        json.dump(account_to_payees, f, indent=2)
