Release history
---------------

development
+++++++++++

0.3.2 (2023-03-02)
++++++++++++++++++

- Relax version constraint on ``importlib-metadata`` backport

0.3.1 (2022-11-17)
++++++++++++++++++

- Relax ``importlib`` backport dependency

0.3.0 (2022-11-16)
++++++++++++++++++

- Official Python 3.10 and 3.11 support, drop 3.6
- Update docs theme

0.2.3 (2021-05-14)
++++++++++++++++++

- Move to use poetry, github actions

0.2.2 (2020-12-05)
++++++++++++++++++

- Official Python 3.9 support

0.2.1 (2020-09-11)
++++++++++++++++++

- Drop Python 3.5 support

0.2.0 (2019-10-28)
++++++++++++++++++

- Drop Python 2 support
- Add Python 3.8 support

0.1.6 (2019-04-07)
++++++++++++++++++

- Drop python 3.4 suport

0.1.5 (2019-03-16)
++++++++++++++++++

- Include request/response metadata in responses (#95)

0.1.4 (2019-03-05)
++++++++++++++++++

- Fixed issue with single-type unions (#100)

0.1.3 (2019-02-16)
++++++++++++++++++

- Add request context to `HTTPError` (#82)

0.1.2 (2019-01-11)
++++++++++++++++++

- Handle error responses without ``data`` correctly

0.1.1 (2018-10-30)
++++++++++++++++++

- Fixed deserialization of ``Enum`` values

0.1.0 (2018-10-30)
++++++++++++++++++

- Fixed handling of HTTP error status codes (#10)
- Fix in validation exceptions (#11)
- Implement custom scalars
- Improvements to documentation

0.0.4 (2018-10-17)
++++++++++++++++++

- Remove some unneeded fields from introspection query
- Improvements to documentation
- Small fixes to API, tests

0.0.3 (2018-09-23)
++++++++++++++++++

- Established initial public API
- Improved documentation, user guide
- Field aliases
- Deserialization

0.0.2 (2018-08-21)
++++++++++++++++++

- Execution of basic GraphQL queries
- Convert GraphQL schema to python types (undocumented)
- Write GraphQL in python syntax (undocumented)

0.0.1
+++++

- initial version
