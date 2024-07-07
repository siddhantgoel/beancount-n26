import sys
import tomllib
from pathlib import Path

from beangulp.testing import main as bg_main
from beancount_n26 import N26Importer


def main():
    config = _extract_config()

    iban = config["iban"]
    account_name = config["account_name"]
    language = config.get("language", "en")
    file_encoding = config.get("file_encoding", "utf-8")
    account_patterns = config.get("account_patterns", {})
    exchange_fees_account = config.get("exchange_fees_account")

    importer = N26Importer(
        iban,
        account_name,
        language=language,
        file_encoding=file_encoding,
        account_patterns=account_patterns,
        exchange_fees_account=exchange_fees_account,
    )
    bg_main(importer)


def _extract_config():
    pyproject = Path("pyproject.toml")

    if not pyproject.exists():
        print("pyproject.toml not found. Please run from the root of the repo.")
        sys.exit(1)

    with pyproject.open("rb") as fd:
        config = tomllib.load(fd)

    config_n26 = config.get("tool", {}).get("beancount-n26")

    if not config_n26:
        print("tool.beancount-n26 not found in pyproject.toml.")
        sys.exit(1)

    return config_n26
