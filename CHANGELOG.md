# Changelog

## Unreleased (2020-05-11)

#### New Features

* raise an DeviceNotFound if requested device not present
#### Refactorings

* unify auth variables name
#### Docs

* update README.rst

## v0.2.0 (2020-05-08)

#### New Features

* select fastest server automatically
#### Refactorings

* add typing for all SC return elements
#### Others

* add more logs
* add retry mechanism for server call
* suppress https warnings
* add mypy and fix errors
* import from facecast_io scope

## v0.1.2 (2020-05-08)

#### Fixes

* add wait 3 sec before stream output creation
* update create_output regarding API changes

## v0.1.1 (2020-04-13)

#### New Features

* add FacecastAPI for end user
#### Others

* add bumpversion
* all basic api calls are works in server_connector.py
