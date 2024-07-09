import sys
import tomllib
from pathlib import Path

from beangulp.testing import main as bg_main
from beancount_n26 import N26Importer


def ec():
    config = _extract_config("ec")

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


def _extract_config(section: str):
    pyproject = Path("pyproject.toml")

    if not pyproject.exists():
        print("pyproject.toml not found. Please run from the root of the repo.")
        sys.exit(1)

    with pyproject.open("rb") as fd:
        config = tomllib.load(fd)

    config_section = config.get("tool", {}).get("beancount-n26", {}).get(section)

    if not config_section:
        print("tool.beancount-n26 not found in pyproject.toml.")
        sys.exit(1)

    return config_section
