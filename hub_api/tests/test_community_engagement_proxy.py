"""`services/community_engagement_proxy.py` -- direct unit tests, real wrapper functions.

`test_community_polls.py`/`test_community_forms.py` monkeypatch these
wrapper functions themselves to test the *blueprint* routes in
isolation; this file exercises the wrapper functions' own bodies
(request shaping, default fields, 404-degrades-to-empty-list) against a
mocked `httpx.AsyncClient` -- the actual external I/O boundary, per
`writing-python-tests` skill (mock external deps, not the unit under
test).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from services import community_engagement_proxy as proxy


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


def _mock_client(response: _FakeResponse) -> AsyncMock:
    client = AsyncMock()
    client.request = AsyncMock(return_value=response)
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    return client


class TestPolls:
    async def test_get_polls_success(self) -> None:
        with patch(
            "httpx.AsyncClient",
            return_value=_mock_client(_FakeResponse(200, {"polls": [{"id": 1}]})),
        ):
            data, status = await proxy.get_polls(1, "Bearer tok")
        assert status == 200
        assert data == {"success": True, "polls": [{"id": 1}]}

    async def test_get_polls_404_degrades_to_empty_list(self) -> None:
        with patch("httpx.AsyncClient", return_value=_mock_client(_FakeResponse(404, {}))):
            data, status = await proxy.get_polls(1, None)
        assert status == 200
        assert data == {"success": True, "polls": []}

    async def test_create_poll_applies_defaults(self) -> None:
        mock = _mock_client(_FakeResponse(201, {"poll": {"id": 1}}))
        with patch("httpx.AsyncClient", return_value=mock):
            data, status = await proxy.create_poll(
                1, {"title": "Q?", "options": ["a", "b"]}, "Bearer tok"
            )
        assert status == 201
        assert data == {"success": True, "poll": {"id": 1}}
        sent_body = mock.request.call_args.kwargs["json"]
        assert sent_body["view_visibility"] == "community"
        assert sent_body["allow_multiple_choices"] is False
        assert sent_body["max_choices"] == 1

    async def test_delete_poll_success(self) -> None:
        with patch("httpx.AsyncClient", return_value=_mock_client(_FakeResponse(200, {}))):
            data, status = await proxy.delete_poll(1, 5, "Bearer tok")
        assert status == 200
        assert data == {"success": True, "message": "Poll deleted"}

    async def test_delete_poll_failure_surfaces_error(self) -> None:
        with patch(
            "httpx.AsyncClient", return_value=_mock_client(_FakeResponse(500, {"error": "boom"}))
        ):
            data, status = await proxy.delete_poll(1, 5, "Bearer tok")
        assert status == 500
        assert data == {"success": False, "error": "boom"}

    async def test_get_poll_single(self) -> None:
        with patch(
            "httpx.AsyncClient", return_value=_mock_client(_FakeResponse(200, {"poll": {"id": 9}}))
        ):
            data, status = await proxy.get_poll(1, 9, "Bearer tok")
        assert status == 200
        assert data["poll"]["id"] == 9


class TestForms:
    async def test_get_forms_404_degrades_to_empty_list(self) -> None:
        with patch("httpx.AsyncClient", return_value=_mock_client(_FakeResponse(404, {}))):
            data, status = await proxy.get_forms(1, None)
        assert status == 200
        assert data == {"success": True, "forms": []}

    async def test_create_form_applies_defaults(self) -> None:
        mock = _mock_client(_FakeResponse(201, {"form": {"id": 1}}))
        with patch("httpx.AsyncClient", return_value=mock):
            data, status = await proxy.create_form(
                1, {"title": "Signup", "fields": []}, "Bearer tok"
            )
        assert status == 201
        sent_body = mock.request.call_args.kwargs["json"]
        assert sent_body["results_visibility"] == "submitter_and_admins"
        assert sent_body["submit_once_per_user"] is True

    async def test_delete_form_success(self) -> None:
        with patch("httpx.AsyncClient", return_value=_mock_client(_FakeResponse(200, {}))):
            data, status = await proxy.delete_form(1, 5, "Bearer tok")
        assert data == {"success": True, "message": "Form deleted"}

    async def test_get_form_submissions_success(self) -> None:
        with patch(
            "httpx.AsyncClient",
            return_value=_mock_client(_FakeResponse(200, {"submissions": [{"id": 1}]})),
        ):
            data, status = await proxy.get_form_submissions(1, 5, "Bearer tok")
        assert status == 200
        assert data["submissions"] == [{"id": 1}]

    async def test_get_form_single(self) -> None:
        with patch(
            "httpx.AsyncClient", return_value=_mock_client(_FakeResponse(200, {"form": {"id": 3}}))
        ):
            data, status = await proxy.get_form(1, 3, "Bearer tok")
        assert data["form"]["id"] == 3


class TestConnectionFailure:
    async def test_request_error_returns_502(self) -> None:
        import httpx

        client = AsyncMock()
        client.request = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
        client.__aenter__.return_value = client
        client.__aexit__.return_value = False
        with patch("httpx.AsyncClient", return_value=client):
            data, status = await proxy.get_polls(1, None)
        assert status == 502
        assert data["success"] is False


@pytest.mark.parametrize(
    "fn,args",
    [
        (proxy.get_polls, (1, None)),
        (proxy.get_forms, (1, None)),
    ],
)
async def test_non_json_response_body_degrades_gracefully(fn: Any, args: tuple[Any, ...]) -> None:
    class _BadJsonResponse(_FakeResponse):
        def json(self) -> dict[str, Any]:
            raise ValueError("not json")

    with patch("httpx.AsyncClient", return_value=_mock_client(_BadJsonResponse(200, {}))):
        data, status = await fn(*args)
    assert status == 200
