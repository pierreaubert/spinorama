# Speaker Metadata Manager

A web-based interface for managing speaker metadata in the Spinorama project. This tool allows you to add, edit, and remove speaker metadata with automatic validation and Git integration for creating pull requests.

## Features

- **Browse Speakers**: View and search through existing speaker metadata
- **Add New Speakers**: Create new speaker entries with comprehensive metadata
- **Edit Speakers**: Modify existing speaker information
- **Validation**: Real-time validation of metadata according to Spinorama standards
- **Git Integration**: Automatic branch creation and commit generation for pull requests
- **Export Changes**: Generate Python code for metadata files

## Coding

- The application will be written in Javascript without extra javascript packages and with bulma.io CSS library.
- The tests will use vitest and jsdom.
- Deployement will be handle by vite.
- A minimum amount of code will be written.

## Specifications: the application will have a 3 step process.

In the application, you can nagivate from one step to another in both direction.

### Speaker selection

A first form will propose either to pick from a list of speakers or to create a new one. A new speaker has a brand (from a list or a new one) and a name.

The list of speakers will be fetched from a REST API (https://api.spinorama.org/v1/speakers).

The list of brands will be fetched from a REST API (https://api.spinorama.org/v1/brands).

The user select either an existing speaker in the list or add a new one with a brand and a name.

### Adding parameters for a speaker or editing an existing one.

A large form will allow to set all the parameters.

The parameters are defined in Python in the file ./datas/__init__.py.

Since we can have multiple measurements, they will be displayed as a list Bulma pannel.

### Parameter validation

The parameters will be validated by sending the proposed set of parameters to the the API.

- The api will be https://api.spinorama.org/v1/validate.
- In order to tests the correctness of the parameters, the list of checks is in ./scripts/check_meta.py.
- You will add a method to ./src/api/main.py to do the validation.
- You will move the logic to test from ./scripts/check_meta.py to ./datas/checks.py.

If the parameters are correct, all the parameters will be outputed as a python dict that you can easily download.

## Deployement

- A shell script will copy all the static files to the production computers.
- The application can be accessed directly from the URL `https://spinorama.org/metadata-manager.

