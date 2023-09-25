"""Utility for getting the Google Maps client for api integration.

The api is used for geocoding and converting addresses.
"""
import functools
import os

@functools.cache
def get_client(api_key=None):
    """Returns a googlemaps client for api use with the given key or a key exported in GM_API_KEY variable.

    Result is cached so repeated calls return the same Client object.
    """
    try:
        import googlemaps
    except ImportError:
        raise ImportError("This function requires the googlemaps package and it is not installed.")
    GM_API_KEY = os.environ.get("GM_API_KEY")
    api_key = api_key or GM_API_KEY
    if not api_key:
        raise ValueError("Google Maps API key not in argument or GM_API_KEY environment variable.")
    client = googlemaps.Client(key=api_key)
    return client
