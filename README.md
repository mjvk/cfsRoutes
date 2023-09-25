
# CFS Routes

This is a python module used to find efficient delivery routes for a collection of addresses. It is written for one specific application and is not suitable for public use.

## Usage

cfsRoutes is designed to be usable both locally and as a server-side API. Usage requires providing a configuration file and an input `.csv` file.

For usage examples, see the `examples` directory.

## Setup

### Installing locally

Download the latest package `.whl` from the **Assets** section of the [releases page](https://github.com/mjvk/cfsRoutes/releases).

Install the `whl` file with `pip install --user cfsroutes-0.0.1a0-py3-none-any.whl`. The `cfsroutes` module should now be usable in python with `import cfsroutes`,
or through the command line with `cfsroutes [--config CONFIG.json] [--outfile OUTFILE.csv] infile.csv`. 

### Working with the source

If you are working with the source code, having an editable installation in a virtual environment is recommended.

  1. Clone the repository.
  2. In the `cfsroutes` directory, setup a virtual environment with

    python -m venv .venv
    source .venv/bin/activate  # linux
    pip install --upgrade setuptools wheel

  3. Install the requirements and create an editable source installation with

    pip install -r requirements.txt
    pip install -e .


### Geocoding sources

This project needs to geocode provided addresses to their `lat/lng` location. Previously this was done with the `googlemaps` API, which requires an API key,
but this is now optional. By default cfsRoutes uses the BC government Address Geocoder API.
