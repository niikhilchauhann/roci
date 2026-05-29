from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup
from geopy.distance import geodesic

from app.models.api import CoordinateInput, InfrastructureProject
from app.utils.logging import logger


class CpppScraper:
    def __init__(self) -> None:
        self.source = "cppp"

    async def fetch_projects(self, coordinates: CoordinateInput) -> list[InfrastructureProject]:
        logger.info("Fetching CPPP projects near lat={}, lng={}", coordinates.lat, coordinates.lng)
        html = self._mock_html()
        rows = self._parse_rows(html)
        return self._to_projects(rows, coordinates)

    def _parse_rows(self, html: str) -> list[dict[str, str]]:
        soup = BeautifulSoup(html, "lxml")
        projects: list[dict[str, str]] = []
        for row in soup.select("tr[data-project]"):
            cells = row.find_all("td")
            if len(cells) < 7:
                continue
            projects.append(
                {
                    "project_id": row.get("data-project", "").strip(),
                    "title": cells[0].get_text(" ", strip=True),
                    "authority": cells[1].get_text(" ", strip=True),
                    "category": cells[2].get_text(" ", strip=True),
                    "status": cells[3].get_text(" ", strip=True),
                    "lat": cells[4].get_text(" ", strip=True),
                    "lng": cells[5].get_text(" ", strip=True),
                    "classification_hint": cells[6].get_text(" ", strip=True),
                }
            )
        return projects

    def _to_projects(self, rows: list[dict[str, str]], origin: CoordinateInput) -> list[InfrastructureProject]:
        projects: list[InfrastructureProject] = []
        for row in rows:
            lat = float(row["lat"])
            lng = float(row["lng"])
            distance_km = round(geodesic((origin.lat, origin.lng), (lat, lng)).km, 2)
            classification = self._classify_project(row["title"], row["category"], row["classification_hint"])
            distance_band = self._distance_band(distance_km)
            projects.append(
                InfrastructureProject(
                    source="cppp",
                    project_id=row["project_id"],
                    title=row["title"],
                    authority=row["authority"],
                    category=row["category"],
                    classification=classification,
                    status=row["status"],
                    coordinates=CoordinateInput(lat=lat, lng=lng),
                    distance_km=distance_km,
                    distance_band=distance_band,
                    influence_score=self._influence_score(classification, distance_band),
                )
            )
        return projects

    def _classify_project(self, title: str, category: str, hint: str) -> str:
        text = f"{title} {category} {hint}".lower()
        if any(token in text for token in ["road", "expressway", "transport", "mobility", "terminal"]):
            return "transport"
        if any(token in text for token in ["hospital", "medical", "health"]):
            return "social"
        if any(token in text for token in ["sewer", "water", "drainage", "utility", "power"]):
            return "utilities"
        if any(token in text for token in ["tourism", "riverfront", "heritage", "township"]):
            return "economic"
        return "general"

    def _distance_band(self, distance_km: float) -> str:
        if distance_km <= 1:
            return "adjacent"
        if distance_km <= 3:
            return "near"
        if distance_km <= 8:
            return "catchment"
        return "regional"

    def _influence_score(self, classification: str, distance_band: str) -> float:
        base_by_classification = {
            "transport": 92.0,
            "economic": 84.0,
            "utilities": 79.0,
            "social": 72.0,
            "general": 65.0,
        }
        distance_multiplier = {
            "adjacent": 1.0,
            "near": 0.88,
            "catchment": 0.74,
            "regional": 0.58,
        }
        return round(base_by_classification[classification] * distance_multiplier[distance_band], 1)

    def _mock_html(self) -> str:
        return """
        <table>
          <tr data-project="CPPP-AYO-001">
            <td>Ayodhya Riverfront Mobility Corridor</td>
            <td>Ayodhya Development Authority</td>
            <td>Urban Transport</td>
            <td>Under Implementation</td>
            <td>26.8068</td>
            <td>82.1977</td>
            <td>mobility corridor</td>
          </tr>
          <tr data-project="CPPP-AYO-002">
            <td>Integrated Water Supply Upgrade</td>
            <td>Jal Nigam</td>
            <td>Water Utility</td>
            <td>Bid Stage</td>
            <td>26.7842</td>
            <td>82.2114</td>
            <td>utility expansion</td>
          </tr>
        </table>
        """
