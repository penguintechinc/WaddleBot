"""transports/http.py -- webhook/rest_api/graphql/grpc outbound, rest_pull inbound."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json

import httpx
import pytest

from waddle_transports.base import NonRetryableTransportError, RetryableTransportError
from waddle_transports.transports.http import HttpTransport


def _client(handler) -> httpx.AsyncClient:  # noqa: ANN001
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)


# --- webhook -----------------------------------------------------------------


class TestWebhookSubType:
    async def test_signs_body_with_hmac_sha256(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_WEBHOOK_SECRET", "s3cr3t")
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["signature"] = request.headers["X-Waddle-Signature"]
            captured["body"] = request.content
            return httpx.Response(200)

        async with _client(handler) as client:
            transport = HttpTransport(http_client=client)
            result = await transport.send(
                {
                    "sub_type": "webhook",
                    "url": "https://8.8.8.8/hook",
                    "secret_ref": "TEST_WEBHOOK_SECRET",
                },
                {"user": "alice"},
            )

        expected_sig = hmac.new(b"s3cr3t", captured["body"], hashlib.sha256).hexdigest()
        assert captured["signature"] == expected_sig
        assert result.transport == "http"
        assert result.sub_type == "webhook"
        assert result.http_status == 200

    async def test_missing_secret_ref_config_is_non_retryable(self) -> None:
        async with _client(lambda r: httpx.Response(200)) as client:
            transport = HttpTransport(http_client=client)
            with pytest.raises(NonRetryableTransportError, match="secret_ref"):
                await transport.send({"sub_type": "webhook", "url": "https://8.8.8.8/hook"}, {})

    async def test_unresolvable_secret_is_non_retryable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("TEST_WEBHOOK_SECRET_2", raising=False)
        async with _client(lambda r: httpx.Response(200)) as client:
            transport = HttpTransport(http_client=client)
            with pytest.raises(NonRetryableTransportError, match="secret resolution failed"):
                await transport.send(
                    {
                        "sub_type": "webhook",
                        "url": "https://8.8.8.8/hook",
                        "secret_ref": "TEST_WEBHOOK_SECRET_2",
                    },
                    {},
                )

    async def test_body_template_payload_cannot_inject_a_json_field(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fail-first regression for JSON body-template injection.

        A payload value carrying JSON metacharacters must not break out of
        `body_template`'s JSON string and inject a sibling field.
        """
        monkeypatch.setenv("TEST_WEBHOOK_SECRET_5", "s3cr3t")
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200)

        async with _client(handler) as client:
            transport = HttpTransport(http_client=client)
            await transport.send(
                {
                    "sub_type": "webhook",
                    "url": "https://8.8.8.8/hook",
                    "secret_ref": "TEST_WEBHOOK_SECRET_5",
                    "body_template": '{"user": "{{name}}"}',
                },
                {"name": '",\"admin\":true'},
            )

        assert captured["body"] == {"user": '",\"admin\":true'}
        assert "admin" not in captured["body"]

    async def test_private_host_is_blocked_non_retryable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TEST_WEBHOOK_SECRET_3", "s3cr3t")
        called = False

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200)

        async with _client(handler) as client:
            transport = HttpTransport(http_client=client)
            with pytest.raises(NonRetryableTransportError, match="SSRF"):
                await transport.send(
                    {
                        "sub_type": "webhook",
                        "url": "http://169.254.169.254/latest/meta-data/",
                        "secret_ref": "TEST_WEBHOOK_SECRET_3",
                    },
                    {},
                )
        assert called is False


# --- rest_api ------------------------------------------------------------------


class TestRestApiSubType:
    async def test_defaults_to_post(self) -> None:
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["method"] = request.method
            return httpx.Response(200)

        async with _client(handler) as client:
            transport = HttpTransport(http_client=client)
            await transport.send({"sub_type": "rest_api", "url": "https://8.8.8.8/api"}, {})
        assert captured["method"] == "POST"

    @pytest.mark.parametrize("status", [401, 403])
    async def test_auth_rejection_is_non_retryable(self, status: int) -> None:
        async with _client(lambda r: httpx.Response(status)) as client:
            transport = HttpTransport(http_client=client)
            with pytest.raises(NonRetryableTransportError):
                await transport.send({"sub_type": "rest_api", "url": "https://8.8.8.8/api"}, {})

    async def test_5xx_is_retryable(self) -> None:
        async with _client(lambda r: httpx.Response(503)) as client:
            transport = HttpTransport(http_client=client)
            with pytest.raises(RetryableTransportError):
                await transport.send({"sub_type": "rest_api", "url": "https://8.8.8.8/api"}, {})

    async def test_missing_url_is_non_retryable(self) -> None:
        async with _client(lambda r: httpx.Response(200)) as client:
            transport = HttpTransport(http_client=client)
            with pytest.raises(NonRetryableTransportError, match="url"):
                await transport.send({"sub_type": "rest_api"}, {})


# --- graphql ---------------------------------------------------------------------


class TestGraphqlSubType:
    async def test_sends_query_and_variables(self) -> None:
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={"data": {"viewer": {"id": "1"}}})

        async with _client(handler) as client:
            transport = HttpTransport(http_client=client)
            result = await transport.send(
                {
                    "sub_type": "graphql",
                    "url": "https://8.8.8.8/graphql",
                    "query": "query { viewer { id } }",
                    "variables": {"x": 1},
                },
                {},
            )

        assert captured["body"] == {"query": "query { viewer { id } }", "variables": {"x": 1}}
        assert result.sub_type == "graphql"

    async def test_200_with_errors_array_is_non_retryable(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"errors": [{"message": "field not found"}]})

        async with _client(handler) as client:
            transport = HttpTransport(http_client=client)
            with pytest.raises(NonRetryableTransportError, match="1 error"):
                await transport.send(
                    {"sub_type": "graphql", "url": "https://8.8.8.8/graphql", "query": "{ x }"}, {}
                )


# --- grpc ---------------------------------------------------------------------


class TestGrpcSubType:
    def _grpc_response(self, message: bytes, *, grpc_status: str | None = "0") -> httpx.Response:
        frame = b"\x00" + len(message).to_bytes(4, "big") + message
        headers = {} if grpc_status is None else {"grpc-status": grpc_status}
        return httpx.Response(200, content=frame, headers=headers)

    async def test_sends_real_grpc_frame(self) -> None:
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["content_type"] = request.headers["content-type"]
            captured["te"] = request.headers["te"]
            captured["body"] = request.content
            return self._grpc_response(b"world")

        async with _client(handler) as client:
            transport = HttpTransport(http_client=client)
            result = await transport.send(
                {
                    "sub_type": "grpc",
                    "url": "https://8.8.8.8/pkg.Service/Method",
                    "grpc_message_b64": base64.b64encode(b"hello").decode("ascii"),
                },
                {},
            )

        assert captured["content_type"] == "application/grpc+proto"
        assert captured["te"] == "trailers"
        assert captured["body"] == b"\x00\x00\x00\x00\x05hello"
        assert result.sub_type == "grpc"

    async def test_invalid_base64_is_non_retryable(self) -> None:
        async with _client(lambda r: httpx.Response(200)) as client:
            transport = HttpTransport(http_client=client)
            with pytest.raises(NonRetryableTransportError, match="not valid base64"):
                await transport.send(
                    {"sub_type": "grpc", "url": "https://8.8.8.8/x", "grpc_message_b64": "!!!"}, {}
                )

    async def test_nonzero_grpc_status_unavailable_is_retryable(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return self._grpc_response(b"", grpc_status="14")

        async with _client(handler) as client:
            transport = HttpTransport(http_client=client)
            with pytest.raises(RetryableTransportError, match="grpc-status=14"):
                await transport.send(
                    {"sub_type": "grpc", "url": "https://8.8.8.8/x", "grpc_message_b64": ""}, {}
                )

    async def test_missing_grpc_status_well_formed_frame_is_optimistic_success(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return self._grpc_response(b"world", grpc_status=None)

        async with _client(handler) as client:
            transport = HttpTransport(http_client=client)
            result = await transport.send(
                {"sub_type": "grpc", "url": "https://8.8.8.8/x", "grpc_message_b64": ""}, {}
            )
        assert result.http_status == 200

    async def test_missing_grpc_status_malformed_body_is_non_retryable(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"\x01\x02")

        async with _client(handler) as client:
            transport = HttpTransport(http_client=client)
            with pytest.raises(NonRetryableTransportError, match="cannot confirm RPC outcome"):
                await transport.send(
                    {"sub_type": "grpc", "url": "https://8.8.8.8/x", "grpc_message_b64": ""}, {}
                )


# --- rest_pull (inbound) --------------------------------------------------------


class TestRestPullSubType:
    async def test_yields_each_array_item_once(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[{"id": 1}, {"id": 2}])

        async with _client(handler) as client:
            transport = HttpTransport(http_client=client)
            items = [
                item
                async for item in transport.receive(
                    {"sub_type": "rest_pull", "url": "https://8.8.8.8/events", "_max_iterations": 1}
                )
            ]
        assert items == [{"id": 1}, {"id": 2}]

    async def test_polls_multiple_iterations(self) -> None:
        call_count = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            call_count["n"] += 1
            return httpx.Response(200, json=[{"n": call_count["n"]}])

        async with _client(handler) as client:
            transport = HttpTransport(http_client=client)
            items = [
                item
                async for item in transport.receive(
                    {
                        "sub_type": "rest_pull",
                        "url": "https://8.8.8.8/events",
                        "poll_interval_s": 0.001,
                        "_max_iterations": 3,
                    }
                )
            ]
        assert [i["n"] for i in items] == [1, 2, 3]

    async def test_non_array_response_is_non_retryable(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"not": "an array"})

        async with _client(handler) as client:
            transport = HttpTransport(http_client=client)
            with pytest.raises(NonRetryableTransportError, match="JSON array"):
                async for _item in transport.receive(
                    {"sub_type": "rest_pull", "url": "https://8.8.8.8/events", "_max_iterations": 1}
                ):
                    pass


async def test_webhook_transport_builds_and_closes_its_own_client_when_none_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No explicit `http_client` -- `_client_or_new` builds a real one and closes it after."""
    import waddle_transports.transports.http as http_module

    monkeypatch.setenv("TEST_WEBHOOK_SECRET_4", "s3cr3t")
    captured = {}
    real_aclose = httpx.AsyncClient.aclose

    async def _spy_aclose(self: httpx.AsyncClient) -> None:
        captured["closed"] = True
        await real_aclose(self)

    async def _fake_guarded_request(client, method, url, **kwargs):  # noqa: ANN001, ANN202
        captured["client_is_real_httpx_client"] = isinstance(client, httpx.AsyncClient)
        return httpx.Response(200)

    monkeypatch.setattr(http_module, "guarded_request", _fake_guarded_request)
    monkeypatch.setattr(httpx.AsyncClient, "aclose", _spy_aclose)

    transport = HttpTransport()  # no http_client -- forces _client_or_new's own-build path
    result = await transport.send(
        {
            "sub_type": "webhook",
            "url": "https://8.8.8.8/hook",
            "secret_ref": "TEST_WEBHOOK_SECRET_4",
        },
        {},
    )

    assert result.http_status == 200
    assert captured["client_is_real_httpx_client"] is True
    assert captured["closed"] is True


async def test_rest_api_missing_url_is_non_retryable() -> None:
    async with _client(lambda r: httpx.Response(200)) as client:
        transport = HttpTransport(http_client=client)
        with pytest.raises(NonRetryableTransportError, match="url"):
            await transport.send({"sub_type": "rest_api"}, {})


async def test_rest_api_network_error_is_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    async with _client(handler) as client:
        transport = HttpTransport(http_client=client)
        with pytest.raises(RetryableTransportError, match="request failed"):
            await transport.send({"sub_type": "rest_api", "url": "https://8.8.8.8/api"}, {})


async def test_graphql_missing_url_is_non_retryable() -> None:
    async with _client(lambda r: httpx.Response(200)) as client:
        transport = HttpTransport(http_client=client)
        with pytest.raises(NonRetryableTransportError, match="url"):
            await transport.send({"sub_type": "graphql", "query": "{ x }"}, {})


async def test_graphql_missing_query_is_non_retryable() -> None:
    async with _client(lambda r: httpx.Response(200)) as client:
        transport = HttpTransport(http_client=client)
        with pytest.raises(NonRetryableTransportError, match="query"):
            await transport.send({"sub_type": "graphql", "url": "https://8.8.8.8/graphql"}, {})


async def test_graphql_network_error_is_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    async with _client(handler) as client:
        transport = HttpTransport(http_client=client)
        with pytest.raises(RetryableTransportError, match="request failed"):
            await transport.send(
                {"sub_type": "graphql", "url": "https://8.8.8.8/graphql", "query": "{ x }"}, {}
            )


async def test_grpc_missing_url_is_non_retryable() -> None:
    async with _client(lambda r: httpx.Response(200)) as client:
        transport = HttpTransport(http_client=client)
        with pytest.raises(NonRetryableTransportError, match="url"):
            await transport.send({"sub_type": "grpc", "grpc_message_b64": ""}, {})


async def test_grpc_missing_message_field_is_non_retryable() -> None:
    async with _client(lambda r: httpx.Response(200)) as client:
        transport = HttpTransport(http_client=client)
        with pytest.raises(NonRetryableTransportError, match="grpc_message_b64"):
            await transport.send({"sub_type": "grpc", "url": "https://8.8.8.8/x"}, {})


async def test_grpc_network_error_is_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    async with _client(handler) as client:
        transport = HttpTransport(http_client=client)
        with pytest.raises(RetryableTransportError, match="request failed"):
            await transport.send(
                {"sub_type": "grpc", "url": "https://8.8.8.8/x", "grpc_message_b64": ""}, {}
            )


async def test_rest_pull_ssrf_rejected_is_non_retryable() -> None:
    async with _client(lambda r: httpx.Response(200)) as client:
        transport = HttpTransport(http_client=client)
        with pytest.raises(NonRetryableTransportError, match="SSRF"):
            async for _item in transport.receive(
                {"sub_type": "rest_pull", "url": "http://169.254.169.254/x", "_max_iterations": 1}
            ):
                pass


async def test_rest_pull_network_error_is_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    async with _client(handler) as client:
        transport = HttpTransport(http_client=client)
        with pytest.raises(RetryableTransportError, match="request failed"):
            async for _item in transport.receive(
                {"sub_type": "rest_pull", "url": "https://8.8.8.8/events", "_max_iterations": 1}
            ):
                pass


async def test_unsupported_receive_sub_type_is_non_retryable() -> None:
    transport = HttpTransport()
    with pytest.raises(NonRetryableTransportError, match="not supported"):
        async for _item in transport.receive({"sub_type": "carrier_pigeon"}):
            pass


async def test_webhook_push_receive_is_explicitly_rejected_not_a_stub() -> None:
    """`webhook_push` is server-side -- receive() explains this rather than pretending."""
    transport = HttpTransport()
    with pytest.raises(NonRetryableTransportError, match="server-side"):
        async for _item in transport.receive({"sub_type": "webhook_push"}):
            pass


async def test_unsupported_send_sub_type_is_non_retryable() -> None:
    async with _client(lambda r: httpx.Response(200)) as client:
        transport = HttpTransport(http_client=client)
        with pytest.raises(NonRetryableTransportError, match="not supported"):
            await transport.send({"sub_type": "soap", "url": "https://8.8.8.8/x"}, {})


# --- response size cap ------------------------------------------------------------


class TestResponseSizeCap:
    """Fail-first regression for the missing response-body size cap.

    An oversized response must be rejected, not buffered fully into
    memory, for every sub_type sharing `guarded_request()`.
    """

    async def test_rest_pull_oversized_response_is_non_retryable(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[{"id": i} for i in range(50)])

        async with _client(handler) as client:
            transport = HttpTransport(http_client=client)
            with pytest.raises(NonRetryableTransportError, match="exceeded"):
                async for _item in transport.receive(
                    {
                        "sub_type": "rest_pull",
                        "url": "https://8.8.8.8/events",
                        "_max_iterations": 1,
                        "max_response_bytes": 10,
                    }
                ):
                    pass

    async def test_graphql_oversized_response_is_non_retryable(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": {"x": "y" * 1000}})

        async with _client(handler) as client:
            transport = HttpTransport(http_client=client)
            with pytest.raises(NonRetryableTransportError, match="exceeded"):
                await transport.send(
                    {
                        "sub_type": "graphql",
                        "url": "https://8.8.8.8/graphql",
                        "query": "{ x }",
                        "max_response_bytes": 10,
                    },
                    {},
                )

    async def test_grpc_oversized_response_is_non_retryable(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            message = b"x" * 1000
            frame = b"\x00" + len(message).to_bytes(4, "big") + message
            return httpx.Response(200, content=frame, headers={"grpc-status": "0"})

        async with _client(handler) as client:
            transport = HttpTransport(http_client=client)
            with pytest.raises(NonRetryableTransportError, match="exceeded"):
                await transport.send(
                    {
                        "sub_type": "grpc",
                        "url": "https://8.8.8.8/x",
                        "grpc_message_b64": "",
                        "max_response_bytes": 10,
                    },
                    {},
                )

    async def test_webhook_oversized_response_is_non_retryable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Confirm the cap protects every sub_type, not just the three named.

        The cap is enforced centrally in `guarded_request()` -- every
        sub_type is protected, not just the three named in the finding.
        """
        monkeypatch.setenv("TEST_WEBHOOK_SECRET_6", "s3cr3t")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"x" * 1000)

        async with _client(handler) as client:
            transport = HttpTransport(http_client=client)
            with pytest.raises(NonRetryableTransportError, match="exceeded"):
                await transport.send(
                    {
                        "sub_type": "webhook",
                        "url": "https://8.8.8.8/hook",
                        "secret_ref": "TEST_WEBHOOK_SECRET_6",
                        "max_response_bytes": 10,
                    },
                    {},
                )

    async def test_rest_api_oversized_response_is_non_retryable(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"x" * 1000)

        async with _client(handler) as client:
            transport = HttpTransport(http_client=client)
            with pytest.raises(NonRetryableTransportError, match="exceeded"):
                await transport.send(
                    {
                        "sub_type": "rest_api",
                        "url": "https://8.8.8.8/api",
                        "max_response_bytes": 10,
                    },
                    {},
                )

    async def test_response_within_configured_cap_succeeds(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[{"id": 1}])

        async with _client(handler) as client:
            transport = HttpTransport(http_client=client)
            items = [
                item
                async for item in transport.receive(
                    {
                        "sub_type": "rest_pull",
                        "url": "https://8.8.8.8/events",
                        "_max_iterations": 1,
                        "max_response_bytes": 1024,
                    }
                )
            ]
        assert items == [{"id": 1}]
