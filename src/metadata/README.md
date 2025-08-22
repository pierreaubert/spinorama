# Speaker Metadata Manager

A web-based interface for managing speaker metadata in the Spinorama project. This tool allows you to add, edit, and remove speaker metadata with automatic validation and Git integration for creating pull requests.

## Features

- **Browse Speakers**: View and search through existing speaker metadata
- **Add New Speakers**: Create new speaker entries with comprehensive metadata
- **Edit Speakers**: Modify existing speaker information
- **Validation**: Real-time validation of metadata according to Spinorama standards
- **Git Integration**: Automatic branch creation and commit generation for pull requests
- **Export Changes**: Generate Python code for metadata files

## How to Use

- Coding
  - The application will be written in Javascript without extra packages and with bulma.io CSS library.
  - The tests will use vitest and jsdom.
  - Deployement will be handle by vite.
  - A minimum amount of code will be written and tested.

- Specifications: the application will have a 3 steps process.

  1. Select a speaker to edit or add a new one. The list of speakers will be fetched from a REST API (https://api.spinorama.org/v1/speakers). The use select either a speaker in the list or add a new one with a brand and a name.
  2. A large form will allow to set all the parameters. The parameters are defined in Python in the file ./datas/__init__.py. Since we can have multiple measurements, they will be displayed as a list Bulma pannel.
  3. The parameters will be validated by sending the proposed set to the the API. The api will be https://api.spinorama.org/v1/validate). If the parameters are correct, all the parameters will be outputed as a python dict that you can easily download.

- Deployement
  - A shell script will copy all the static files to the production computers.
  - The application can be accessed directly from the URL `https://meta.spinorama.org.

