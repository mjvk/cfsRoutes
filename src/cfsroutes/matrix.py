import numpy as np
from typing import Dict, Tuple

def radians(deg):
    return deg * np.pi / 180

def pair_euclid_distance(source: Tuple[float, float], dest: Tuple[float, float]) -> float:
    """Approximate Euclidian distance between given lat/lng coordinates."""

    def coords(lat, lng, R):
        x = R * np.cos(lat) * np.cos(lng)
        y = R * np.cos(lat) * np.sin(lng)
        z = R * np.sin(lat)
        return (x, y, z)

    lat1, lng1 = map(radians, source)
    lat2, lng2 = map(radians, dest)

    R = 6378137 # Approximate radius of the earth

    x1, y1, z1 = coords(lat1, lng1, R)
    x2, y2, z2 = coords(lat2, lng2, R)
    distance = np.sqrt( (x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2 )
    return distance


def distance(source: Dict[str, float], dest: Dict[str, float]) -> float:
    s_lat, s_lng = source.get("lat"), source.get("lng")
    d_lat, d_lng = dest.get("lat"), dest.get("lng")
    if None in (s_lat, s_lng, d_lat, d_lng):
        return None
    source_tuple = (s_lat, s_lng)
    dest_tuple = (d_lat, d_lng)
    return pair_euclid_distance(source_tuple, dest_tuple)


def pair_haversine_distance(src: Tuple[float, float], dst: Tuple[float, float]) -> float:
    """Approximate distance between given lat/lng coordinates."""
    # https://en.wikipedia.org/wiki/Haversine_formula

    lat_src, lng_src = map(radians, src)
    lat_dst, lng_dst = map(radians, dst)

    R = 6378137 # Approximate radius of the earth

    # TODO: Make these calculations work on a matrix level
    distance = 2 * R * np.arcsin(
        np.sqrt(
            np.sin((lat_dst - lat_src) / 2)**2
            + np.cos(lat_src)
            * np.cos(lat_dst)
            * np.sin((lng_dst - lng_src) / 2)**2
        )
    )

    return distance


def distance_matrix(data) -> np.ndarray:
    """Matrix of pairwise distances from sequence of addresses."""
    locations = [k["location"] for k in data]
    size = len(locations)
    result_matrix = np.zeros((size, size))

    for i, source in enumerate(locations):
        for j, dest in enumerate(locations):
            coord1 = source.values()
            coord2 = dest.values()
            distance = pair_euclid_distance(coord1, coord2)
            result_matrix[(i,j)] = distance

    # We add a final row and column of 0s to tell the route solver that the end destination can be anywhere
    result_matrix = np.concatenate((result_matrix, np.zeros((1, len(result_matrix)))))
    result_matrix = np.concatenate((result_matrix, np.zeros((len(result_matrix), 1))), axis=1)
    return result_matrix 
