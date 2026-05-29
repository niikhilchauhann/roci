from __future__ import annotations

from collections import Counter

from app.models.api import CoordinateInput, InfrastructureProject, InfrastructureSummary
from app.scrapers.cppp import CpppScraper
from app.scrapers.gem import GemScraper


class InfrastructureService:
    def __init__(self) -> None:
        self.cppp_scraper = CpppScraper()
        self.gem_scraper = GemScraper()

    async def analyze(self, coordinates: CoordinateInput) -> InfrastructureSummary:
        cppp_projects = await self.cppp_scraper.fetch_projects(coordinates)
        gem_projects = await self.gem_scraper.fetch_projects(coordinates)
        projects = sorted(cppp_projects + gem_projects, key=lambda item: (item.distance_km, -item.influence_score))

        if not projects:
            return InfrastructureSummary(
                score=40.0,
                project_count=0,
                dominant_classification="none",
                projects=[],
                methodology="No nearby CPPP or GeM projects matched within the Ayodhya MVP context window.",
            )

        score = self._score_projects(projects)
        dominant_classification = Counter(project.classification for project in projects).most_common(1)[0][0]
        return InfrastructureSummary(
            score=score,
            project_count=len(projects),
            dominant_classification=dominant_classification,
            projects=projects[:6],
            methodology="Weighted blend of project classification priority and parcel-to-project geodesic distance across CPPP and GeM sources.",
        )

    def _score_projects(self, projects: list[InfrastructureProject]) -> float:
        top_projects = projects[:5]
        weighted_sum = sum(project.influence_score * self._source_weight(project.source) for project in top_projects)
        total_weight = sum(self._source_weight(project.source) for project in top_projects)
        diversity_bonus = min(len({project.classification for project in top_projects}) * 1.8, 6.0)
        return round(min((weighted_sum / total_weight) + diversity_bonus, 100.0), 1)

    def _source_weight(self, source: str) -> float:
        return 1.0 if source == "cppp" else 0.92
