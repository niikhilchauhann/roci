from __future__ import annotations

from app.models.api import BhulekhRecord, InfrastructureSummary, ParcelFeature, ScoreComponent


class RociScoringEngine:
    def score(
        self,
        parcel: ParcelFeature,
        bhulekh: BhulekhRecord,
        infrastructure: InfrastructureSummary | None = None,
    ) -> dict[str, ScoreComponent]:
        clu_score = self._clu_score(bhulekh)
        registry_velocity = ScoreComponent(
            name="Registry Velocity",
            score=61.0,
            weight=0.2,
            reason="Placeholder registry momentum for Ayodhya MVP pending sub-registrar ingestion.",
        )
        infra_score = self._infra_score(infrastructure)
        risk_score = self._risk_score(parcel, bhulekh)
        confidence_score = self._confidence_score(parcel, bhulekh)

        return {
            "clu_score": clu_score,
            "registry_velocity": registry_velocity,
            "infra_score": infra_score,
            "risk_score": risk_score,
            "confidence_score": confidence_score,
        }

    def aggregate(self, components: dict[str, ScoreComponent]) -> float:
        weighted = sum(component.score * component.weight for component in components.values())
        return round(weighted / sum(component.weight for component in components.values()), 1)

    def zone_label(self, score: float) -> str:
        if score >= 80:
            return "Zone 1"
        if score >= 70:
            return "Zone 2"
        if score >= 60:
            return "Zone 4"
        if score >= 45:
            return "Zone 5"
        return "Zone 6"

    def _clu_score(self, bhulekh: BhulekhRecord) -> ScoreComponent:
        is_positive_land_use = "आवासीय" in bhulekh.bhoomi_prakar or "residential" in bhulekh.bhoomi_prakar.lower()
        score = 78.0 if is_positive_land_use else 58.0
        reason = "Land-use classification signals residential upside." if is_positive_land_use else "Land-use remains agriculture-led with moderate conversion upside."
        return ScoreComponent(name="CLU Score", score=score, weight=0.3, reason=reason)

    def _risk_score(self, parcel: ParcelFeature, bhulekh: BhulekhRecord) -> ScoreComponent:
        mutation_clean = "स्वीकृत" in bhulekh.mutation_status or "approved" in bhulekh.mutation_status.lower()
        score = 70.0 if mutation_clean else 48.0
        if parcel.source_confidence < 0.7:
            score -= 8.0
        return ScoreComponent(
            name="Risk Score",
            score=max(0.0, score),
            weight=0.2,
            reason="Mutation quality and parcel confidence drive current legal-operational risk.",
        )

    def _infra_score(self, infrastructure: InfrastructureSummary | None) -> ScoreComponent:
        if infrastructure is None:
            return ScoreComponent(
                name="Infrastructure Access",
                score=52.0,
                weight=0.2,
                reason="Infrastructure enrichment was unavailable, so a conservative fallback baseline was applied.",
            )

        lead_project = infrastructure.projects[0] if infrastructure.projects else None
        lead_context = (
            f"Top signal is a {lead_project.classification} project at {lead_project.distance_km} km."
            if lead_project
            else "No nearby project was retained in the scoring window."
        )
        return ScoreComponent(
            name="Infrastructure Access",
            score=infrastructure.score,
            weight=0.2,
            reason=f"{lead_context} Classification and distance bands were blended across CPPP and GeM sources.",
        )

    def _confidence_score(self, parcel: ParcelFeature, bhulekh: BhulekhRecord) -> ScoreComponent:
        score = round(((parcel.source_confidence + bhulekh.confidence) / 2) * 100, 1)
        return ScoreComponent(
            name="Confidence Score",
            score=score,
            weight=0.1,
            reason="Blended confidence from Bhunaksha parcel match and Bhulekh extraction quality.",
        )
