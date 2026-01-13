"""
Client asynchrone pour l'API OpenSky Network.
Gère les requêtes HTTP de manière asynchrone pour supporter plusieurs utilisateurs simultanés.
"""

import httpx
from dataclasses import dataclass
from typing import Optional
import time


@dataclass
class StateVector:
    """Représente l'état d'un aéronef à un moment donné."""
    icao24: str
    callsign: Optional[str]
    origin_country: str
    time_position: Optional[int]
    last_contact: int
    longitude: Optional[float]
    latitude: Optional[float]
    baro_altitude: Optional[float]
    on_ground: bool
    velocity: Optional[float]
    true_track: Optional[float]
    vertical_rate: Optional[float]
    sensors: Optional[list]
    geo_altitude: Optional[float]
    squawk: Optional[str]
    spi: bool
    position_source: int
    category: int

    def to_dict(self) -> dict:
        """Convertit l'objet en dictionnaire."""
        return {
            "icao24": self.icao24,
            "callsign": self.callsign,
            "origin_country": self.origin_country,
            "time_position": self.time_position,
            "last_contact": self.last_contact,
            "longitude": self.longitude,
            "latitude": self.latitude,
            "baro_altitude": self.baro_altitude,
            "on_ground": self.on_ground,
            "velocity": self.velocity,
            "true_track": self.true_track,
            "vertical_rate": self.vertical_rate,
            "sensors": self.sensors,
            "geo_altitude": self.geo_altitude,
            "squawk": self.squawk,
            "spi": self.spi,
            "position_source": self.position_source,
            "category": self.category
        }


@dataclass
class FlightData:
    """Représente les données d'un vol."""
    icao24: str
    firstSeen: int
    estDepartureAirport: Optional[str]
    lastSeen: int
    estArrivalAirport: Optional[str]
    callsign: Optional[str]
    estDepartureAirportHorizDistance: Optional[int]
    estDepartureAirportVertDistance: Optional[int]
    estArrivalAirportHorizDistance: Optional[int]
    estArrivalAirportVertDistance: Optional[int]
    departureAirportCandidatesCount: int
    arrivalAirportCandidatesCount: int

    def to_dict(self) -> dict:
        """Convertit l'objet en dictionnaire."""
        return {
            "icao24": self.icao24,
            "firstSeen": self.firstSeen,
            "estDepartureAirport": self.estDepartureAirport,
            "lastSeen": self.lastSeen,
            "estArrivalAirport": self.estArrivalAirport,
            "callsign": self.callsign,
            "estDepartureAirportHorizDistance": self.estDepartureAirportHorizDistance,
            "estDepartureAirportVertDistance": self.estDepartureAirportVertDistance,
            "estArrivalAirportHorizDistance": self.estArrivalAirportHorizDistance,
            "estArrivalAirportVertDistance": self.estArrivalAirportVertDistance,
            "departureAirportCandidatesCount": self.departureAirportCandidatesCount,
            "arrivalAirportCandidatesCount": self.arrivalAirportCandidatesCount
        }


@dataclass
class Waypoint:
    """Représente un point de trajectoire."""
    time: int
    latitude: Optional[float]
    longitude: Optional[float]
    baro_altitude: Optional[float]
    true_track: Optional[float]
    on_ground: bool

    def to_dict(self) -> dict:
        """Convertit l'objet en dictionnaire."""
        return {
            "time": self.time,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "baro_altitude": self.baro_altitude,
            "true_track": self.true_track,
            "on_ground": self.on_ground
        }


@dataclass
class FlightTrack:
    """Représente la trajectoire d'un aéronef."""
    icao24: str
    startTime: int
    endTime: int
    callsign: Optional[str]
    path: list

    def to_dict(self) -> dict:
        """Convertit l'objet en dictionnaire."""
        return {
            "icao24": self.icao24,
            "startTime": self.startTime,
            "endTime": self.endTime,
            "callsign": self.callsign,
            "path": [w.to_dict() if isinstance(w, Waypoint) else w for w in self.path]
        }


class AsyncOpenSkyApi:
    """
    Client asynchrone pour l'API OpenSky Network.
    Supporte les requêtes concurrentes pour plusieurs utilisateurs.
    """
    
    BASE_URL = "https://opensky-network.org/api"
    
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        self.username = username
        self.password = password
        self._auth = (username, password) if username and password else None
        
    async def _make_request(self, endpoint: str, params: Optional[dict] = None) -> Optional[dict]:
        """Effectue une requête HTTP asynchrone."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = f"{self.BASE_URL}/{endpoint}"
                if self._auth:
                    response = await client.get(url, params=params, auth=self._auth)
                else:
                    response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    raise Exception("Rate limit exceeded. Please wait before making more requests.")
                else:
                    raise Exception(f"API request failed with status {response.status_code}: {response.text}")
            except httpx.TimeoutException:
                raise Exception("Request timeout - OpenSky API did not respond in time")
            except httpx.RequestError as e:
                raise Exception(f"Request error: {str(e)}")
    
    def _parse_state_vector(self, arr: list) -> StateVector:
        """Parse un tableau en StateVector."""
        return StateVector(
            icao24=arr[0],
            callsign=arr[1].strip() if arr[1] else None,
            origin_country=arr[2],
            time_position=arr[3],
            last_contact=arr[4],
            longitude=arr[5],
            latitude=arr[6],
            baro_altitude=arr[7],
            on_ground=arr[8],
            velocity=arr[9],
            true_track=arr[10],
            vertical_rate=arr[11],
            sensors=arr[12],
            geo_altitude=arr[13],
            squawk=arr[14],
            spi=arr[15],
            position_source=arr[16],
            category=arr[17] if len(arr) > 17 else 0
        )
    
    def _parse_flight_data(self, arr: list) -> FlightData:
        """Parse un dictionnaire en FlightData."""
        return FlightData(
            icao24=arr.get("icao24", ""),
            firstSeen=arr.get("firstSeen", 0),
            estDepartureAirport=arr.get("estDepartureAirport"),
            lastSeen=arr.get("lastSeen", 0),
            estArrivalAirport=arr.get("estArrivalAirport"),
            callsign=arr.get("callsign"),
            estDepartureAirportHorizDistance=arr.get("estDepartureAirportHorizDistance"),
            estDepartureAirportVertDistance=arr.get("estDepartureAirportVertDistance"),
            estArrivalAirportHorizDistance=arr.get("estArrivalAirportHorizDistance"),
            estArrivalAirportVertDistance=arr.get("estArrivalAirportVertDistance"),
            departureAirportCandidatesCount=arr.get("departureAirportCandidatesCount", 0),
            arrivalAirportCandidatesCount=arr.get("arrivalAirportCandidatesCount", 0)
        )
    
    def _parse_waypoint(self, arr: list) -> Waypoint:
        """Parse un tableau en Waypoint."""
        return Waypoint(
            time=arr[0],
            latitude=arr[1],
            longitude=arr[2],
            baro_altitude=arr[3],
            true_track=arr[4],
            on_ground=arr[5]
        )
    
    async def get_states(
        self,
        time_secs: int = 0,
        icao24: Optional[str] = None,
        bbox: Optional[tuple] = None
    ) -> Optional[dict]:
        """
        Récupère les vecteurs d'état pour un moment donné.
        
        Args:
            time_secs: Timestamp Unix (0 pour les plus récents)
            icao24: Adresse ICAO24 optionnelle pour filtrer
            bbox: Bounding box optionnelle (min_lat, max_lat, min_lon, max_lon)
        
        Returns:
            Dictionnaire avec 'time' et 'states' (liste de StateVector)
        """
        params = {}
        if time_secs > 0:
            params["time"] = time_secs
        if icao24:
            params["icao24"] = icao24.lower()
        if bbox and len(bbox) == 4:
            params["lamin"] = bbox[0]
            params["lamax"] = bbox[1]
            params["lomin"] = bbox[2]
            params["lomax"] = bbox[3]
        
        data = await self._make_request("states/all", params)
        if data and "states" in data and data["states"]:
            states = [self._parse_state_vector(s).to_dict() for s in data["states"]]
            return {"time": data.get("time"), "states": states}
        return {"time": data.get("time") if data else None, "states": []}
    
    async def get_arrivals_by_airport(
        self,
        airport: str,
        begin: int,
        end: int
    ) -> Optional[list]:
        """
        Récupère les vols arrivant à un aéroport dans un intervalle de temps.
        
        Args:
            airport: Code ICAO de l'aéroport
            begin: Début de l'intervalle (timestamp Unix)
            end: Fin de l'intervalle (timestamp Unix)
        
        Returns:
            Liste de FlightData
        """
        params = {"airport": airport.upper(), "begin": begin, "end": end}
        data = await self._make_request("flights/arrival", params)
        if data:
            return [self._parse_flight_data(f).to_dict() for f in data]
        return []
    
    async def get_departures_by_airport(
        self,
        airport: str,
        begin: int,
        end: int
    ) -> Optional[list]:
        """
        Récupère les vols partant d'un aéroport dans un intervalle de temps.
        
        Args:
            airport: Code ICAO de l'aéroport
            begin: Début de l'intervalle (timestamp Unix)
            end: Fin de l'intervalle (timestamp Unix)
        
        Returns:
            Liste de FlightData
        """
        params = {"airport": airport.upper(), "begin": begin, "end": end}
        data = await self._make_request("flights/departure", params)
        if data:
            return [self._parse_flight_data(f).to_dict() for f in data]
        return []
    
    async def get_flights_by_aircraft(
        self,
        icao24: str,
        begin: int,
        end: int
    ) -> Optional[list]:
        """
        Récupère les vols d'un aéronef spécifique dans un intervalle de temps.
        
        Args:
            icao24: Adresse ICAO24 de l'aéronef (hex)
            begin: Début de l'intervalle (timestamp Unix)
            end: Fin de l'intervalle (timestamp Unix)
        
        Returns:
            Liste de FlightData
        """
        params = {"icao24": icao24.lower(), "begin": begin, "end": end}
        data = await self._make_request("flights/aircraft", params)
        if data:
            return [self._parse_flight_data(f).to_dict() for f in data]
        return []
    
    async def get_flights_from_interval(
        self,
        begin: int,
        end: int
    ) -> Optional[list]:
        """
        Récupère tous les vols dans un intervalle de temps (max 2 heures).
        
        Args:
            begin: Début de l'intervalle (timestamp Unix)
            end: Fin de l'intervalle (timestamp Unix)
        
        Returns:
            Liste de FlightData
        """
        # Vérifier que l'intervalle ne dépasse pas 2 heures
        if end - begin > 7200:
            raise Exception("Time interval must not exceed 2 hours (7200 seconds)")
        
        params = {"begin": begin, "end": end}
        data = await self._make_request("flights/all", params)
        if data:
            return [self._parse_flight_data(f).to_dict() for f in data]
        return []
    
    async def get_track_by_aircraft(
        self,
        icao24: str,
        time: int = 0
    ) -> Optional[dict]:
        """
        Récupère la trajectoire d'un aéronef.
        
        Args:
            icao24: Adresse ICAO24 de l'aéronef (hex)
            time: Timestamp Unix (0 pour le suivi en direct)
        
        Returns:
            FlightTrack avec la trajectoire
        """
        params = {"icao24": icao24.lower()}
        if time > 0:
            params["time"] = time
        
        data = await self._make_request("tracks/all", params)
        if data:
            path = [self._parse_waypoint(w).to_dict() for w in data.get("path", [])]
            return {
                "icao24": data.get("icao24"),
                "startTime": data.get("startTime"),
                "endTime": data.get("endTime"),
                "callsign": data.get("callsign"),
                "path": path
            }
        return None

