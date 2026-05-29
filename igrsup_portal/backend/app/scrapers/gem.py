from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup
from geopy.distance import geodesic

from app.models.api import CoordinateInput, InfrastructureProject
from app.utils.logging import logger


class GemScraper:
    def __init__(self) -> None:
        self.source = "gem"

    async def fetch_projects(self, coordinates: CoordinateInput) -> list[InfrastructureProject]:
        logger.info("Fetching GeM projects near lat={}, lng={}", coordinates.lat, coordinates.lng)
        html = self._mock_html()
        cards = self._parse_cards(html)
        return self._to_projects(cards, coordinates)

    def _parse_cards(self, html: str) -> list[dict[str, str]]:
        soup = BeautifulSoup(html, "lxml")
        projects: list[dict[str, str]] = []
        for card in soup.select("article[data-bid-id]"):
            projects.append(
                {
                    "project_id": card.get("data-bid-id", "").strip(),
                    "title": card.select_one("[data-field='title']").get_text(" ", strip=True),
                    "authority": card.select_one("[data-field='buyer']").get_text(" ", strip=True),
                    "category": card.select_one("[data-field='category']").get_text(" ", strip=True),
                    "status": card.select_one("[data-field='status']").get_text(" ", strip=True),
                    "lat": card.select_one("[data-field='lat']").get_text(" ", strip=True),
                    "lng": card.select_one("[data-field='lng']").get_text(" ", strip=True),
                }
            )
        return projects

    def _to_projects(self, cards: list[dict[str, str]], origin: CoordinateInput) -> list[InfrastructureProject]:
        projects: list[InfrastructureProject] = []
        for card in cards:
            lat = float(card["lat"])
            lng = float(card["lng"])
            distance_km = round(geodesic((origin.lat, origin.lng), (lat, lng)).km, 2)
            classification = self._classify_project(card["title"], card["category"])
            distance_band = self._distance_band(distance_km)
            projects.append(
                InfrastructureProject(
                    source="gem",
                    project_id=card["project_id"],
                    title=card["title"],
                    authority=card["authority"],
                    category=card["category"],
                    classification=classification,
                    status=card["status"],
                    coordinates=CoordinateInput(lat=lat, lng=lng),
                    distance_km=distance_km,
                    distance_band=distance_band,
                    influence_score=self._influence_score(classification, distance_band),
                )
            )
        return projects

    def _classify_project(self, title: str, category: str) -> str:
        text = f"{title} {category}".lower()
        if any(token in text for token in ["street light", "electrical", "solar", "power"]):
            return "utilities"
        if any(token in text for token in ["road", "bridge", "civil", "transport"]):
            return "transport"
        if any(token in text for token in ["hospital", "school", "college", "facility"]):
            return "social"
        if any(token in text for token in ["tourism", "heritage", "wayfinding", "plaza"]):
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
            "transport": 88.0,
            "economic": 80.0,
            "utilities": 82.0,
            "social": 70.0,
            "general": 62.0,
        }
        distance_multiplier = {
            "adjacent": 1.0,
            "near": 0.87,
            "catchment": 0.72,
            "regional": 0.55,
        }
        return round(base_by_classification[classification] * distance_multiplier[distance_band], 1)

    def _mock_html(self) -> str:
        return """
        <section>
          <article data-bid-id="GEM-AYO-101">
            <span data-field="title">Solar Street Lighting for Ayodhya Growth Corridor</span>
            <span data-field="buyer">Ayodhya Municipal Corporation</span>
            <span data-field="category">Electrical Works</span>
            <span data-field="status">Published</span>
            <span data-field="lat">26.7911</span>
            <span data-field="lng">82.2188</span>
          </article>
          <article data-bid-id="GEM-AYO-102">
            <span data-field="title">Tourism Wayfinding and Heritage Plaza Signage</span>
            <span data-field="buyer">Tourism Department</span>
            <span data-field="category">Urban Public Realm</span>
            <span data-field="status">Awarded</span>
            <span data-field="lat">26.8125</span>
            <span data-field="lng">82.2057</span>
          </article>
        </section>
        """
