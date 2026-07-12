from __future__ import annotations

from typing import Any, Dict, List

from app.scanners.candidate import CandidateRecord


def build_candidates(
    instruments: List[Dict[str, Any]],
    quality_rows: List[Dict[str, Any]],
    liquidity_rows: List[Dict[str, Any]],
    preferred_exchange: Dict[str, Dict[str, Any]],
    created_at: str,
) -> List[Dict[str, Any]]:
    quality_by_instrument = {row["instrument_id"]: row for row in quality_rows}
    liquidity_by_instrument = {row["instrument_id"]: row for row in liquidity_rows}
    candidates: List[Dict[str, Any]] = []
    for instrument in instruments:
        quality = quality_by_instrument[instrument["instrument_id"]]
        liquidity = liquidity_by_instrument[instrument["instrument_id"]]
        company_preference = preferred_exchange.get(instrument["company_id"], {})
        rejection_reasons: List[str] = []
        selection_reasons: List[str] = [company_preference.get("selection_reason", "Preferred exchange evaluated.")]
        if instrument["segment"] != "CASH":
            rejection_reasons.append("Only cash instruments are promoted as base scanner candidates in this sprint.")
        if instrument["exchange"] != company_preference.get("preferred_exchange"):
            rejection_reasons.append("Instrument is not on the preferred exchange.")
        if quality["quality_class"] in {"FAILED", "SUSPECT", "NOT_READY"}:
            rejection_reasons.append(f"Data quality {quality['quality_class']} blocks candidate.")
        if quality["staleness_state"] in {"STALE", "EXPIRED"}:
            rejection_reasons.append(f"Quote state {quality['staleness_state']} blocks executable candidate.")
        if not liquidity["eligible_for_intraday"] and not liquidity["eligible_for_swing"]:
            rejection_reasons.append("Liquidity thresholds not met.")

        strategy_scope = "INTRADAY" if liquidity["eligible_for_intraday"] else "SWING"
        eligible = not rejection_reasons
        score = round((quality["quality_score"] * 0.55) + (liquidity["liquidity_score"] * 0.45), 2)
        confidence = round(min(score, 100.0), 2)
        candidates.append(
            CandidateRecord(
                candidate_id=f"candidate-{instrument['instrument_id']}",
                company_id=instrument["company_id"],
                instrument_id=instrument["instrument_id"],
                symbol=instrument["symbol"],
                exchange=instrument["exchange"],
                direction="LONG",
                instrument_type=instrument["instrument_type"],
                strategy_scope=strategy_scope,
                score=score,
                confidence=confidence,
                liquidity_score=float(liquidity["liquidity_score"]),
                data_quality_score=float(quality["quality_score"]),
                fno_eligible=bool(instrument["fno_eligible"]),
                preferred_exchange=company_preference.get("preferred_exchange") or instrument["exchange"],
                data_mode=quality.get("data_mode", "FIXTURE"),
                eligible=eligible,
                candidate_bucket="foundation",
                decision="WATCH" if eligible else "AVOID",
                risk_level="LOW" if eligible else "HIGH",
                payload_json={
                    "reason": selection_reasons[0] if selection_reasons else "",
                    "quality_class": quality["quality_class"],
                    "liquidity_class": liquidity["liquidity_class"],
                },
                rejection_reasons_json=rejection_reasons,
                selection_reasons_json=[reason for reason in selection_reasons if reason],
                created_at=created_at,
                updated_at=created_at,
            ).to_dict()
        )
    return candidates
