from __future__ import annotations

import asyncio
from types import SimpleNamespace

from services import abr_client, provider_ingestion, source_approvals
from services.places_client import PLACES_FIELD_MASK, PLACES_TEXT_SEARCH_ENDPOINT, PlacesClient


LEGACY_TEST_APPROVAL = {
    "version": 1,
    "sources": [
        {"provider": "google_places", "approved": True, "approved_by": "owner", "terms_reviewed_at": "2026-09-10", "approved_uses": ["trainer_discovery"]},
        {"provider": "abr_web_services", "approved": True, "approved_by": "owner", "terms_reviewed_at": "2026-09-10", "approved_uses": ["abn_verification"]},
    ],
}


def test_checked_in_source_registry_is_fail_closed():
    registry = source_approvals.load()
    assert registry["state"] == "approved_for_initial_website_abr_batch"
    assert source_approvals.approved(registry, "public_business_websites", "trainer_profile_source") is True
    assert source_approvals.approved(registry, "google_places", "trainer_discovery") is False
    assert source_approvals.approved(registry, "abr_web_services", "abn_verification") is True
    assert source_approvals.approved(registry, "sensis_thryv_business_feed", "trainer_discovery") is False
    assert source_approvals.approved(registry, "thryv_macromatch_totalcheck", "trainer_discovery") is False


def test_places_adapter_blocks_before_transport_without_terms_or_key():
    class Transport:
        @staticmethod
        def post(*_args, **_kwargs):
            raise AssertionError("transport must not run")

    no_terms = asyncio.run(PlacesClient(api_key="test-key", transport=Transport).search_trainers("Richmond", approved=False, allow_network=True))
    no_key = asyncio.run(PlacesClient(api_key="", transport=Transport).search_trainers("Richmond", approved=True, allow_network=True))
    no_network = asyncio.run(PlacesClient(api_key="test-key", transport=Transport).search_trainers("Richmond", approved=True, allow_network=False))
    assert no_terms["reason_code"] == "source_terms_not_approved"
    assert no_key["reason_code"] == "google_places_key_missing"
    assert no_network["reason_code"] == "provider_network_not_authorised"


def test_legacy_places_probe_contract_can_be_exercised_only_with_explicit_test_approval():
    calls = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "places": [{
                    "id": "place_1",
                    "displayName": {"text": "Richmond Reward Dogs"},
                    "formattedAddress": "1 Swan St, Richmond VIC 3121",
                    "location": {"latitude": -37.82, "longitude": 144.99},
                    "nationalPhoneNumber": "03 9000 1111",
                    "websiteUri": "https://rewarddogs.example.au",
                    "rating": 4.8,
                    "userRatingCount": 20,
                    "businessStatus": "OPERATIONAL",
                }]
            }

    class Transport:
        @staticmethod
        def post(url, **kwargs):
            calls.append((url, kwargs))
            return Response()

    result = asyncio.run(PlacesClient(api_key="test-key", transport=Transport).search_trainers("Richmond", approved=True, allow_network=True))
    assert result["ok"] is True
    assert calls[0][0] == PLACES_TEXT_SEARCH_ENDPOINT
    assert calls[0][1]["headers"]["X-Goog-FieldMask"] == PLACES_FIELD_MASK
    assert calls[0][1]["json"]["includePureServiceAreaBusinesses"] is True
    candidate = result["candidates"][0]
    assert candidate["provider_record_id"] == "place_1"
    assert candidate["raw_evidence"]["matched_name"] == "Richmond Reward Dogs"


def test_provider_pipeline_enriches_abn_but_never_allows_publication():
    class Places:
        async def search_trainers(self, suburb, **_kwargs):
            return {"state": "complete", "reason_code": "", "candidates": [{"name": "ABN Dogs", "suburb": suburb, "abn": "51 824 753 556"}]}

    class Abr:
        async def lookup(self, _abn):
            return {"state": "active", "abn_verified": True, "data": {"retrieved_at": "2026-09-10T00:00:00+00:00", "entity_name": "ABN Dogs Pty Ltd"}}

    result = asyncio.run(
        provider_ingestion.prepare_candidates(
            SimpleNamespace(),
            ["Richmond"],
            registry=LEGACY_TEST_APPROVAL,
            places=Places(),
            abr=Abr(),
            allow_network=True,
        )
    )
    assert result["ok"] is True
    assert result["publication_allowed"] is False
    assert result["candidates"][0]["abr_evidence"]["status"] == "active"


def test_abr_dry_run_can_return_evidence_without_mongo(monkeypatch):
    class Response:
        status_code = 200
        text = '{"Abn":"51824753556","AbnStatus":"Active","EntityName":"ABN Dogs Pty Ltd","AddressState":"VIC"}'

    monkeypatch.setattr(abr_client.requests, "get", lambda *_args, **_kwargs: Response())
    result = asyncio.run(abr_client.AbrClient(None, guid="test-guid").lookup("51 824 753 556"))
    assert result["ok"] is True
    assert result["state"] == "active"
    assert result["data"]["entity_name"] == "ABN Dogs Pty Ltd"


def test_abr_name_search_caps_results_and_normalises_current_flag(monkeypatch):
    calls = []

    class Response:
        status_code = 200
        text = 'callback({"Names":[{"Abn":"87452240636","IsCurrent":true,"Name":"HELLOPUPPY DOG TRAINING","NameType":"Business Name","Postcode":"3191","Score":99,"State":"VIC"}]});'

    def fake_get(*_args, **kwargs):
        calls.append(kwargs)
        return Response()

    monkeypatch.setattr(abr_client.requests, "get", fake_get)
    result = asyncio.run(abr_client.AbrClient(None, guid="test-guid").search_names("  Hello Puppy  ", max_results=99))
    assert result["ok"] is True
    assert calls[0]["params"]["name"] == "Hello Puppy"
    assert calls[0]["params"]["maxResults"] == 20
    assert result["matches"][0]["abn"] == "87452240636"
    assert result["matches"][0]["is_current"] is True


def test_provider_pipeline_real_configuration_stays_blocked_without_approval():
    result = asyncio.run(
        provider_ingestion.prepare_candidates(
            SimpleNamespace(),
            ["Richmond"],
            registry=source_approvals.load(),
            places=PlacesClient(api_key=""),
            allow_network=False,
        )
    )
    assert result["ok"] is False
    assert result["candidates"] == []
    assert result["blocked"][0]["reason_code"] == "source_terms_not_approved"
