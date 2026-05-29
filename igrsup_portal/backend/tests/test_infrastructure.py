import pytest

from app.models.api import CoordinateInput
from app.scrapers.cppp import CpppScraper
from app.scrapers.gem import GemScraper
from app.services.infrastructure_service import InfrastructureService


@pytest.mark.asyncio
async def test_cppp_scraper_returns_classified_projects() -> None:
    scraper = CpppScraper()

    projects = await scraper.fetch_projects(CoordinateInput(lat=26.7999, lng=82.2042))

    assert projects
    assert projects[0].source == "cppp"
    assert projects[0].classification in {"transport", "utilities", "economic", "social", "general"}
    assert projects[0].distance_band in {"adjacent", "near", "catchment", "regional"}


@pytest.mark.asyncio
async def test_gem_scraper_returns_distance_scores() -> None:
    scraper = GemScraper()

    projects = await scraper.fetch_projects(CoordinateInput(lat=26.7999, lng=82.2042))

    assert projects
    assert all(project.influence_score > 0 for project in projects)
    assert all(project.distance_km >= 0 for project in projects)


@pytest.mark.asyncio
async def test_infrastructure_service_builds_summary() -> None:
    service = InfrastructureService()

    summary = await service.analyze(CoordinateInput(lat=26.7999, lng=82.2042))

    assert summary.project_count >= 2
    assert summary.score > 0
    assert summary.dominant_classification in {"transport", "utilities", "economic", "social", "general"}
    assert summary.projects
