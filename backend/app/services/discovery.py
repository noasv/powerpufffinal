"""Source-backed opportunity discovery, independent from the AI provider.

Search API output is deliberately treated as untrusted candidate data.  Only the
validator in this module can turn it into a persisted Opportunity row.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from datetime import datetime
from urllib.parse import urlparse
from typing import Any

import httpx
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config.settings import settings
from ..models import Opportunity
from .domains import clean, detect_opportunity_type, field_relevance, requested_domains


class DiscoveryRequest(BaseModel):
    query: str
    domains: list[str] = Field(default_factory=list)
    opportunity_types: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    delivery_modes: list[str] = Field(default_factory=list)
    funding_required: bool = False
    student_level: str = "HIGH_SCHOOL"


class DiscoveredOpportunity(BaseModel):
    title: str
    provider: str | None = None
    opportunity_type: str
    description: str | None = None
    official_url: str | None = None
    source_url: str
    source_domain: str
    source_label: str
    source_type: str = "EXTERNAL"
    country: str | None = None
    delivery_mode: str | None = None
    eligible_countries: list[str] = Field(default_factory=list)
    education_levels: list[str] = Field(default_factory=list)
    fields: list[str] = Field(default_factory=list)
    funding_type: str | None = None
    funding_amount_text: str | None = None
    language_requirements: str | None = None
    deadline: str | None = None
    start_date: str | None = None
    requirements_text: str | None = None
    gap_categories: list[str] = Field(default_factory=list)
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    verified_at: datetime | None = None
    verification_status: str = "SOURCE_FOUND"


def parse_discovery_request(query: str, student_level: str = "HIGH_SCHOOL") -> DiscoveryRequest:
    domains = requested_domains(query)
    typ = detect_opportunity_type(query)
    return DiscoveryRequest(
        query=query.strip(), domains=domains, opportunity_types=[typ] if typ else [],
        funding_required=typ == "SCHOLARSHIP", student_level=student_level,
    )


PLACEHOLDER_DOMAINS = {"example.com", "example.org", "example.net", "localhost"}


def validated_candidate(candidate: DiscoveredOpportunity) -> DiscoveredOpportunity | None:
    """Validate provenance without claiming that a search snippet verifies facts."""
    title = re.sub(r"\s+", " ", candidate.title or "").strip()
    parsed = urlparse(candidate.source_url or "")
    domain = (parsed.hostname or "").lower().removeprefix("www.")
    if len(title) < 3 or parsed.scheme not in {"http", "https"} or not domain:
        return None
    status = candidate.verification_status
    if domain in PLACEHOLDER_DOMAINS or domain.endswith(".example.org"):
        status = "UNVERIFIED"
    # A search result establishes provenance, not factual verification. VERIFIED
    # is reserved for a future first-party page verification adapter.
    if status == "VERIFIED" and candidate.source_type != "OFFICIAL":
        status = "SOURCE_FOUND"
    return candidate.model_copy(update={"title": title, "source_domain": domain, "verification_status": status})


def deduplicate(candidates: list[DiscoveredOpportunity]) -> list[DiscoveredOpportunity]:
    unique, urls, names = [], set(), set()
    for raw in candidates:
        item = validated_candidate(raw)
        if not item:
            continue
        url_key = item.source_url.rstrip("/").lower()
        name_key = (clean(item.title), clean(item.provider or ""))
        if url_key in urls or name_key in names:
            continue
        urls.add(url_key); names.add(name_key); unique.append(item)
    return unique


class OpportunityDiscoveryProvider(ABC):
    @abstractmethod
    def search(self, request: DiscoveryRequest) -> list[DiscoveredOpportunity]: ...


class RealOpportunityDiscoveryProvider(OpportunityDiscoveryProvider):
    """Serper-compatible web search. Credentials stay exclusively server-side."""
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key if api_key is not None else settings.opportunity_search_api_key

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def search(self, request: DiscoveryRequest) -> list[DiscoveredOpportunity]:
        if not self.available:
            raise RuntimeError("External opportunity discovery is not configured")
        query = request.query + " official application opportunity"
        response = httpx.post(
            settings.opportunity_search_base_url,
            headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
            json={"q": query, "num": 10}, timeout=settings.opportunity_search_timeout_seconds,
        )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict) or not isinstance(body.get("organic", []), list):
            raise ValueError("Malformed discovery response")
        results = []
        for hit in body.get("organic", []):
            if not isinstance(hit, dict) or not hit.get("title") or not hit.get("link"):
                continue
            parsed = urlparse(str(hit["link"]))
            domain = (parsed.hostname or "").removeprefix("www.")
            typ = request.opportunity_types[0] if request.opportunity_types else "PROGRAM"
            results.append(DiscoveredOpportunity(
                title=str(hit["title"]), provider=None, opportunity_type=typ,
                description=str(hit.get("snippet")) if hit.get("snippet") else None,
                source_url=str(hit["link"]), source_domain=domain,
                source_label=domain, source_type="EXTERNAL_SEARCH",
                fields=request.domains, education_levels=[request.student_level],
                verification_status="SOURCE_FOUND",
            ))
        return deduplicate(results)


class DemoOpportunityDiscoveryProvider(OpportunityDiscoveryProvider):
    def __init__(self, records: list[Opportunity]): self.records = records

    def search(self, request: DiscoveryRequest) -> list[DiscoveredOpportunity]:
        results = []
        for row in self.records:
            fields = json.loads(row.fields or "[]")
            if request.domains and not any(field_relevance(d, fields) >= 70 for d in request.domains):
                continue
            if request.opportunity_types and row.opportunity_type not in request.opportunity_types:
                continue
            results.append(DiscoveredOpportunity(
                title=row.title, provider=row.provider, opportunity_type=row.opportunity_type,
                description=row.description, source_url=row.source_url or row.official_url or f"https://example.org/pathly-demo/{row.id}",
                source_domain="example.org", source_label="Pathly Demo Dataset", source_type="DEMO",
                country=row.country, delivery_mode=row.delivery_mode, eligible_countries=json.loads(row.eligible_countries or "[]"),
                education_levels=json.loads(row.education_levels or "[]"), fields=fields,
                funding_type=row.funding_type, funding_amount_text=row.funding_amount_text,
                language_requirements=row.language_requirements, deadline=row.deadline.isoformat() if row.deadline else None,
                requirements_text=row.requirements_text, gap_categories=json.loads(row.gap_categories or "[]"),
                verification_status="DEMO",
            ))
        return results


class DiscoveryResult(BaseModel):
    request: DiscoveryRequest
    records: list[Any]
    mode: str
    fallback_used: bool = False
    error: str | None = None


def _persist(db: Session, item: DiscoveredOpportunity) -> Opportunity:
    row = db.query(Opportunity).filter(Opportunity.source_url == item.source_url).first()
    if not row and item.provider:
        row = db.query(Opportunity).filter(Opportunity.title == item.title, Opportunity.provider == item.provider).first()
    if not row:
        row = Opportunity(title=item.title, provider=item.provider or "", opportunity_type=item.opportunity_type, description=item.description or "")
        db.add(row)
    values = {
        "title": item.title, "provider": item.provider or "", "opportunity_type": item.opportunity_type,
        "description": item.description or "", "official_url": item.official_url or "", "source_url": item.source_url,
        "source_domain": item.source_domain, "source_label": item.source_label, "source_type": item.source_type,
        "verification_status": item.verification_status, "discovered_at": item.discovered_at,
        "country": item.country or "Unknown", "delivery_mode": item.delivery_mode or "UNKNOWN",
        "eligible_countries": json.dumps(item.eligible_countries), "education_levels": json.dumps(item.education_levels),
        "fields": json.dumps(item.fields), "funding_type": item.funding_type or "UNKNOWN",
        "funding_amount_text": item.funding_amount_text, "language_requirements": item.language_requirements,
        "requirements_text": item.requirements_text or "", "gap_categories": json.dumps(item.gap_categories),
        "verified_at": item.verified_at.date() if item.verified_at else None,
    }
    # Unknown source fields remain unknown rather than retaining/inventing values.
    for key, value in values.items(): setattr(row, key, value)
    db.flush(); return row


def discover(db: Session, request: DiscoveryRequest) -> DiscoveryResult:
    real = RealOpportunityDiscoveryProvider()
    if settings.opportunity_discovery_provider.lower() != "demo" and real.available:
        try:
            records = [_persist(db, x) for x in real.search(request)]
            return DiscoveryResult(request=request, records=records, mode="EXTERNAL")
        except (httpx.HTTPError, ValueError, RuntimeError) as exc:
            error = str(exc)
    else:
        error = "External discovery is not configured"
    demo_rows = db.query(Opportunity).filter(Opportunity.verification_status == "DEMO").all()
    demo = DemoOpportunityDiscoveryProvider(demo_rows).search(request)
    return DiscoveryResult(request=request, records=[_persist(db, x) for x in demo], mode="DEMO", fallback_used=True, error=error)
