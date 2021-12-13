# CHANGELOG

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

- Add optional parameter ing_entries` to `extract()` (thanks [@tbm])

## v0.3.0 (2020-05-10)

- Add support for Python 3.8

## v0.2.0 (2019-10-22)

- Support multiple languages (starting with English and German)
- Add support for Python 3.5

## v0.1.0 (2019-10-21)

- First release

[@ArthurFDLR]: https://github.com/ArthurFDLR
[@ppetru]: https://github.com/ppetru
[@tbm]: https://github.com/tbm
