# Changelog

## v0.4.1 (2020-09-13)
#### Fixes
* failed to fetch device if stream is active

## v0.4.0 (2020-08-03)
#### New Features
* add input_params of device
#### Fixes
* missing import of Optional
#### Refactorings
* move devices related call from api to special class
* remove auth_required
* make entities more clear and reusable
* use pydantic for input data serialization
#### Docs
* update README.rst
#### Others
* improve displaying of Device(s) info
* add more tests for API

## v0.3.1 (2020-08-01)
#### New Features
* find available facecast server
#### Fixes
* create device and output updated protocol
#### Others
* display logs during creation of output ad device
* cache devices inside `get_devices`
* update description for PyPi

## v0.3.0 (2020-05-11)
#### New Features
* raise an DeviceNotFound if requested device not present
#### Refactorings
* unify auth variables name
#### Docs
* update CHANGELOG.md
* update README.rst
#### Others
* update GH publishing

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
