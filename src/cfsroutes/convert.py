"""Functions for preprocessing and checking that given addresses can be parsed sensibly."""
from . import matrix
from . import values
from . import client as gm_client

import re
import csv
import json
import requests
import functools
from pathlib import Path
from typing import List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_json(infile):
    if not isinstance(infile, Path):
        infile = Path(infile)
    with infile.open() as f:
        content = f.read()
    return json.loads(content)


class BaseConfig():
    """Set attributes from config"""

    default_config = {
        "city": "Victoria",
        "origin": "",
        "csv_keys": None,
        "slips_header": "",
        "geocoding_service": "bcgov",
        "enable_filter": True,
        "drivers": None, 
    }

    def __init__(self, config=None):
        self.config = self.init_config(config)
        self.city = self.config.get("city")
        self.origin = self.config.get("origin") or self.city
        self.csv_keys = self.config.get("csv_keys")
        self.slips_header = self.config.get("slips_header") or self.csv_keys
        self.geocoding_func = self.init_geocode_func(self.config.get("geocoding_service"))
        self.enable_filter = bool(self.config.get("enable_filter"))
        self.drivers = self.driver_data(self.config.get("drivers"))
    

    def init_config(self, config_data):
        """Update config dict from a dict or file."""
        config = {}
        config.update(self.default_config)
        if isinstance(config_data, dict):
            config.update(config_data)
            return config
        if isinstance(config_data, str) or isinstance(config_data, Path):
            config_file = Path(config_data)
            if config_file.is_file() and config_file.suffix == ".json":
                config.update(load_json(config_file))
                return config
        logger.warning("No configuration found. Using default values.")
        return config
    

    def init_geocode_func(self, geocode_func):
        """Abstract method. Set the geocoding function from config."""
        ...


class Converter(BaseConfig):

    def __init__(self, config=None, signup=None):
        super().__init__(config=config)
        self.data = []
        self.filtered = []
    
    def init_geocode_func(self, geocode_func):
        """Set the geocoding function from config."""
        if callable(geocode_func):
            return geocode_func
        if geocode_func == "bcgov":
            return self.bcgov_get_location
        if geocode_func == "google":
            return self.gm_get_location
        raise ValueError(f'Unknown geocoding function "{geocode_func}"')


    def preprocess_address(self, address):
        """Strip multiline addresses and unit numbers."""
        address = address.strip().replace("\n", ", ").replace("/", "-")
        address = address[:50]
        # Attempt to remove unit numbers
        address = re.sub(r"^(#?[0-9]+)\s*\-+\s*(.*)", r"\2", address)
        if self.city.lower() not in address.lower():
            address = f"{address}, {self.city}"
        return address


    @functools.cache
    def gm_get_location(self, address):
        """Use google geocoding api to get coordinates and parsed address."""
        client = gm_client.get_client()
        address = self.preprocess_address(address) + ", BC"
        result = client.geocode(address)
        if not result:
            logger.warning('No result for address "%s".', address)
            return {"location": None}
        result = result[0]
        location = result["geometry"].get("location")
        street = []
        postal = ""
        city = []
        for component in result.get("address_components"):
            types = component.get("types")
            if "street_number" in types:
                street += [component["long_name"]]
            elif "route" in types:
                street += [component["long_name"]]
            elif "locality" in types:
                city += [component["long_name"]]
            elif "administrative_area_level_1" in types:
                city += [component["long_name"]]
            elif "country" in types:
                city += [component["long_name"]]
            elif "postal_code" in types:
                postal = component["long_name"]
        city = ", ".join(city)
        street = " ".join(street)
        data = {
            "full_address" : f"{street}, {city}",
            "postal": postal,
            "location" : location,
        }
        return data


    @functools.cache
    def bcgov_get_location(self, address):
        """Geocoding function using the BC Government address api.

        See https://github.com/bcgov/ols-geocoder
        """
        address = self.preprocess_address(address)
        payload = {"addressString": address, "maxResults": 1}
        service_url = f"https://geocoder.api.gov.bc.ca/addresses.json"
        response = requests.get(service_url, params=payload)
        try:
            features = response.json()["features"][0]
            lng, lat = features["geometry"]["coordinates"]
            full_address = features["properties"]["fullAddress"]
            return {"location": {"lat": lat, "lng": lng}, "full_address": full_address}
        except:
            return None

    def add_origin(self, data, origin):
        """Mutate data to include origin address."""
        if data and data[0].get("address") == origin:
            return # Origin already in data
        origin_data = {"address": origin}
        data.insert(0, origin_data)


    def add_coordinates(self, data):
        """Mutate data to add coordinates for addresses."""
        for row in data:
            if row.get("location"):
                continue # Has coordinates
            address = row["address"]
            location_data = self.geocoding_func(address)
            if location_data:
                row.update(location_data)
            else:
                source_index = row.get("source_index")
                logger.warning('%2d| No coordinates found for "%s".', source_index, address)


    def check_coordinates(self, data, threshold=10000) -> Tuple[list, list]:
        """Check for missing or excessively distant coordinates.

        Returns two lists: `(keep, filtered)`. 
        
        If the `enable_filter=False` in config, all addresses will be kept and given coordinates based on postal code.
        """
        origin_data, data = data[0], data[1:]
        origin = origin_data.get("location")
        if not origin:
            raise ValueError(f"Coordinates required in {origin_data}")
        keep = []
        filtered = []
        for row in data:
            address = row.get("address").replace("\n", " ")
            location = row.get("location")
            full_address = row.get("full_address")
            if full_address in ("Victoria, BC", "BC"):
                logger.warning("Skipping %2d| %s. Failed to parse.", row.get("source_index"), address)
            distance = matrix.distance(location, origin) if location else None
            logger.info("%2d| %s, distance=%sm", row.get("source_index"), address, int(distance))
            if distance is None or distance > threshold:
                logger.warning("Skipping %2d| %s. Distance %s exceeds %s", row.get("source_index"), address, int(distance), threshold)
                if self.enable_filter:
                    filtered += [row]
                    continue
                else:
                    postal = row.get("postal")
                    postal = postal and postal.upper()
                    fallback_location = values.postal_code_fallback.get(postal, values.default_location)
                    row["location"] = fallback_location
            keep += [row]
        return keep, filtered


    def column_name_to_index(self, title_row: List[str]) -> dict:
        """Return a dictionary of indices of required columns."""
        result_dict = {}
        for i, title in enumerate(title_row):
            for key in self.csv_keys:
                # Arbitrary cutoff for long titles
                if key in title.lower()[:21]:
                    result_dict[key] = i

        # Asserts all `keys_needed` are in `result_dict`
        if (missing := set(self.csv_keys) - set(result_dict.keys())):
            logger.error("Title row: %s\nMissing: %s", title_row, missing)
            raise ValueError(f"Could not find required keys in first row of csv input.")

        return result_dict


    def from_csv(self, csv_file: Path) -> list:
        """Convert rows from csv input into dictionaries of required values."""
        data = []
        with csv_file.open("r") as f:
            reader = csv.reader(f)
            title_row = next(reader)
            index = self.column_name_to_index(title_row)
            for i, row in enumerate(reader):
                i += 1 
                row_data = {key: row[index[key]].strip() for key in self.csv_keys}
                row_data["source_index"] = i
                logger.debug("%2d| %s", i, row_data)
                data += [row_data]
        return data


    def load_signups(self, source):
        """Load data from `source` input.
        
        `source` can be the path to a .csv or .json file, or a dictionary.
        """
        data = None
        filtered = []
        if isinstance(source, str):
            source = Path(source)
        if isinstance(source, Path):
            if source.suffix == ".csv":
                data = self.from_csv(source)
            elif source.suffix == ".json":
                data = load_json(source)
        elif isinstance(source, dict):
            data = source
        if data is None:
            raise ValueError(f'Nothing found for signup input "{source}".')

        self.add_origin(data, self.origin)
        self.add_coordinates(data)
        data, filtered = self.check_coordinates(data)
        if filtered:
            logger.warning("Skipped: %s", filtered)

        return data, filtered


    def drivers_json(self, infile) -> List[dict]:
        infile = Path(infile)
        if infile.suffix == ".json":
            with infile.open() as f:
                json_content = f.read()
            driver_locations = json.loads(json_content)

        else:
            driver_locations = []
            with infile.open() as f:
                lines = f.read().splitlines()
            for line in lines:
                driver, postal_code = line.split(',')
                driver_locations += [{"name": driver, "postal": postal_code}]

        return driver_locations


    def driver_data(self, drivers) -> List[dict]:
        if not drivers:
            return []
        if isinstance(drivers, str):
            drivers = self.drivers_json(drivers)
        # Else assume sequence of dicts
        for driver in drivers:
            postal = driver.get("postal")
            location = self.gm_get_location(postal)["location"] if postal else None
            driver["location"] = location
        return drivers
    

