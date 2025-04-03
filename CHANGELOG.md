# CHANGELOG

## v1.4.0 (2025-04-03)
- Fix incorrect cross-currency postings (thanks [@sarg])

## v1.3.0 (2025-04-03)

- Remove `beancount-n26-ec` CLI in favor of a `beangulp.Ingest` based workflow
  - Beangulp examples suggest using a Python script that instantiates `Beangulp.Ingest`
    with a list of importers, which makes the CLI script redundant.

## v1.2.1 (2025-03-05)

- Update CLI error message for missing configuration
- Add Python 3.12 support
- Drop Python 3.8 support

## v1.2.0 (2024-10-03)

- Support updated format of CSV exports (noticed towards September 2023)

## v1.1.0 (2024-07-09)

- Rename `beancount-n26` command to `beancount-n26-ec`

## v1.0.0 (2024-07-07)

- Add Beancount 3.x support (thus removing Beancount 2.x support)
- Add `beancount-n26` CLI command
- Rename `account` parameter to `account_name` (overlapping with the `account()` method
  definition required by `beangulp.importer.Importer`)
- Add Python 3.11 support
- Drop Python 3.7 support

## v0.8.0 (2022-12-11)

- Add Python 3.10 support
- Drop Python 3.6 support

## v0.7.0 (2022-08-24)

- Allow marking transaction fees for multiple-currency transactions
  (thanks [@Fumesover])

## v0.6.0 (2022-05-08)

- Allow `account_patterns` to automatically classify recurring transactions
  (thanks [@Eazhi])

## v0.5.0 (2021-12-13)

- Mark `category` field as optional because recent N26 CSV exports have dropped
  it (thanks [@ppetru])
- Drop Python 3.5 support

## v0.4.1 (2020-12-06)

- Avoid `UnicodeDecodeError` while trying to `identify` non-N26 files

## v0.4.0 (2020-09-13)

- Support header fields in French (thanks [@ArthurFDLR])
- Implement `file_date` (thanks [@ArthurFDLR])

## v0.3.1 (2020-05-12)

- Add optional parameter `existing_entries` to `extract()` (thanks [@tbm])

## v0.3.0 (2020-05-10)

- Add support for Python 3.8

## v0.2.0 (2019-10-22)

- Support multiple languages (starting with English and German)
- Add support for Python 3.5

## v0.1.0 (2019-10-21)

- First release

[@ArthurFDLR]: https://github.com/ArthurFDLR
[@Eazhi]: https://github.com/Eazhi
[@Fumesover]: https://github.com/Fumesover
[@ppetru]: https://github.com/ppetru
[@sarg]: https://github.com/sarg
[@tbm]: https://github.com/tbm
