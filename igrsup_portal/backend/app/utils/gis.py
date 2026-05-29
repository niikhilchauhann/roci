from __future__ import annotations

from typing import Any

from geopy.distance import geodesic
from shapely.geometry import Point, shape

from app.config import settings


def assert_within_ayodhya(lat: float, lng: float) -> None:
    if lat == 0 and lng == 0:
        raise ValueError("Coordinates 0,0 are invalid for Ayodhya parcel analysis.")

    if not (settings.ayodhya_min_lat <= lat <= settings.ayodhya_max_lat):
        raise ValueError("Latitude is outside the Ayodhya operating bounds.")

    if not (settings.ayodhya_min_lng <= lng <= settings.ayodhya_max_lng):
        raise ValueError("Longitude is outside the Ayodhya operating bounds.")

    center = (settings.ayodhya_center_lat, settings.ayodhya_center_lng)
    distance_km = geodesic(center, (lat, lng)).km
    if distance_km > settings.ayodhya_radius_km:
        raise ValueError("Coordinates are outside the Ayodhya MVP operating boundary.")


def geometry_contains_point(geometry: dict[str, Any], lat: float, lng: float) -> bool:
    parcel_shape = shape(geometry)
    return parcel_shape.contains(Point(lng, lat)) or parcel_shape.touches(Point(lng, lat))
