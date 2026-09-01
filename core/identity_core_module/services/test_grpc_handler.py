"""Tests for gRPC handler for identity service

Tests cover:
- JWT token verification with valid, invalid, expired, and missing claims
- Identity lookup with database queries
- Linked platforms retrieval
"""

from __future__ import annotations

import pytest
import grpc
from unittest.mock import MagicMock, patch, AsyncMock
from proto import identity_pb2_grpc

from identity_core_module.services.grpc_handler import (
    IdentityServiceServicer,
    LookupIdentityRequest,
    GetLinkedPlatformsRequest,
    LookupIdentityResponse,
    GetLinkedPlatformsResponse,
    PlatformIdentity,
    Config,
)


class TestVerifyToken:
    """Test JWT token verification."""

    @pytest.mark.asyncio
    async def test_empty_token_rejected(self):
        """Test that empty token is rejected."""
        servicer = IdentityServiceServicer()
        result = await servicer.verify_token("")
        assert result is None

    @pytest.mark.asyncio
    async def test_none_token_rejected(self):
        """Test that None token is rejected."""
        servicer = IdentityServiceServicer()
        result = await servicer.verify_token(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_valid_token_accepted(self):
        """Test that an approved internal service token is accepted."""
        servicer = IdentityServiceServicer()
        valid_payload = {"service": "router", "exp": 9999999999}

        with patch.object(Config, "JWT_SECRET", "test-secret"), patch(
            "identity_core_module.services.grpc_handler.verify_jwt_token"
        ) as mock_verify:
            mock_verify.return_value = valid_payload
            result = await servicer.verify_token("valid.jwt.token")
            assert result == valid_payload
            mock_verify.assert_called_once()

    @pytest.mark.asyncio
    async def test_tampered_token_rejected(self):
        """Test that tampered token (verification returns None) is rejected."""
        servicer = IdentityServiceServicer()

        with patch.object(Config, "JWT_SECRET", "test-secret"), patch(
            "identity_core_module.services.grpc_handler.verify_jwt_token"
        ) as mock_verify:
            mock_verify.return_value = None
            result = await servicer.verify_token("bad.token")
            assert result is None

    @pytest.mark.asyncio
    async def test_expired_token_rejected(self):
        """Test that expired token (verification returns None) is rejected."""
        servicer = IdentityServiceServicer()

        with patch.object(Config, "JWT_SECRET", "test-secret"), patch(
            "identity_core_module.services.grpc_handler.verify_jwt_token"
        ) as mock_verify:
            mock_verify.return_value = None
            result = await servicer.verify_token("expired.token")
            assert result is None

    @pytest.mark.asyncio
    async def test_token_without_identity_rejected(self):
        """Test that a token without a user or service identity is rejected."""
        servicer = IdentityServiceServicer()
        unidentified_payload = {"exp": 9999999999}

        with patch.object(Config, "JWT_SECRET", "test-secret"), patch(
            "identity_core_module.services.grpc_handler.verify_jwt_token"
        ) as mock_verify:
            mock_verify.return_value = unidentified_payload
            result = await servicer.verify_token("no.tenant.token")
            assert result is None

    @pytest.mark.asyncio
    async def test_unapproved_service_rejected(self):
        """Test that arbitrary internal service identities are rejected."""
        servicer = IdentityServiceServicer()
        unapproved_payload = {"service": "unknown-module", "exp": 9999999999}

        with patch.object(Config, "JWT_SECRET", "test-secret"), patch(
            "identity_core_module.services.grpc_handler.verify_jwt_token"
        ) as mock_verify:
            mock_verify.return_value = unapproved_payload
            result = await servicer.verify_token("empty.tenant.token")
            assert result is None


class TestLookupIdentity:
    """Test LookupIdentity gRPC method."""

    @pytest.mark.asyncio
    async def test_missing_platform_returns_error(self):
        """Test that request without platform returns error."""
        mock_dal = MagicMock()
        servicer = IdentityServiceServicer(dal=mock_dal)

        with patch.object(servicer, "verify_token", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"service": "router"}
            request = LookupIdentityRequest(token="valid.token", platform="", platform_user_id="pid123")
            response = await servicer.LookupIdentity(request)

            assert response.success is False
            assert "required" in response.error.message.lower()

    @pytest.mark.asyncio
    async def test_missing_platform_user_id_returns_error(self):
        """Test that request without platform_user_id returns error."""
        mock_dal = MagicMock()
        servicer = IdentityServiceServicer(dal=mock_dal)

        with patch.object(servicer, "verify_token", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"service": "router"}
            request = LookupIdentityRequest(token="valid.token", platform="twitch", platform_user_id="")
            response = await servicer.LookupIdentity(request)

            assert response.success is False
            assert "required" in response.error.message.lower()

    @pytest.mark.asyncio
    async def test_invalid_token_returns_error(self):
        """Test that invalid token returns authentication error."""
        mock_dal = MagicMock()
        servicer = IdentityServiceServicer(dal=mock_dal)

        with patch.object(servicer, "verify_token", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = None
            request = LookupIdentityRequest(token="invalid.token", platform="twitch", platform_user_id="tw123")
            response = await servicer.LookupIdentity(request)

            assert response.success is False
            assert response.error.message == "Invalid authentication token"

    @pytest.mark.asyncio
    async def test_identity_not_found_returns_error(self):
        """Test that non-existent identity returns error."""
        mock_dal = MagicMock()
        mock_dal.executesql.return_value = []
        servicer = IdentityServiceServicer(dal=mock_dal)

        with patch.object(servicer, "verify_token", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"service": "router"}
            request = LookupIdentityRequest(token="valid.token", platform="twitch", platform_user_id="tw_nonexistent")
            response = await servicer.LookupIdentity(request)

            assert response.success is False
            assert response.error.message == "Identity not found"

    @pytest.mark.asyncio
    async def test_valid_lookup_returns_db_data(self):
        """Test that valid lookup returns database data."""
        mock_dal = MagicMock()
        # First call: identity lookup returns [(42, "alice")]
        # Second call: linked platforms returns [("twitch", "tw123", "alice_tw"), ("discord", "dc456", "alice_dc")]
        mock_dal.executesql.side_effect = [
            [(42, "alice")],
            [("twitch", "tw123", "alice_tw"), ("discord", "dc456", "alice_dc")]
        ]
        servicer = IdentityServiceServicer(dal=mock_dal)

        with patch.object(servicer, "verify_token", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"service": "router"}
            request = LookupIdentityRequest(token="valid.token", platform="twitch", platform_user_id="tw123")
            response = await servicer.LookupIdentity(request)

            assert response.success is True
            assert response.hub_user_id == 42
            assert response.username == "alice"
            assert len(response.linked_platforms) == 2
            assert response.linked_platforms[0].platform == "twitch"
            assert response.linked_platforms[0].platform_user_id == "tw123"
            assert response.linked_platforms[0].platform_username == "alice_tw"
            assert response.linked_platforms[1].platform == "discord"
            assert response.linked_platforms[1].platform_user_id == "dc456"
            assert response.linked_platforms[1].platform_username == "alice_dc"

    @pytest.mark.asyncio
    async def test_user_token_cannot_lookup_another_user(self):
        mock_dal = MagicMock()
        mock_dal.executesql.return_value = [(42, "alice")]
        servicer = IdentityServiceServicer(dal=mock_dal)

        with patch.object(servicer, "verify_token", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"userId": 7}
            response = await servicer.LookupIdentity(
                LookupIdentityRequest(
                    token="valid.token",
                    platform="twitch",
                    platform_user_id="tw123",
                )
            )

        assert response.success is False
        assert response.error.message == "Not authorized to access this identity"
        assert mock_dal.executesql.call_count == 1
        assert mock_dal.executesql.call_args.args[1] == ["twitch", "tw123", 7]


class TestGetLinkedPlatforms:
    """Test GetLinkedPlatforms gRPC method."""

    @pytest.mark.asyncio
    async def test_invalid_token_returns_error(self):
        """Test that invalid token returns authentication error."""
        mock_dal = MagicMock()
        servicer = IdentityServiceServicer(dal=mock_dal)

        with patch.object(servicer, "verify_token", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = None
            request = GetLinkedPlatformsRequest(token="invalid.token", hub_user_id=42)
            response = await servicer.GetLinkedPlatforms(request)

            assert response.success is False
            assert response.error.message == "Invalid authentication token"

    @pytest.mark.asyncio
    async def test_no_platforms_returns_empty_list(self):
        """Test that user with no linked platforms returns empty list."""
        mock_dal = MagicMock()
        mock_dal.executesql.return_value = []
        servicer = IdentityServiceServicer(dal=mock_dal)

        with patch.object(servicer, "verify_token", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"userId": 42}
            request = GetLinkedPlatformsRequest(token="valid.token", hub_user_id=42)
            response = await servicer.GetLinkedPlatforms(request)

            assert response.success is True
            assert response.platforms == []

    @pytest.mark.asyncio
    async def test_returns_db_platforms(self):
        """Test that linked platforms are returned from database."""
        mock_dal = MagicMock()
        mock_dal.executesql.return_value = [
            ("twitch", "tw1", "alice"),
            ("discord", "dc2", "alice_d")
        ]
        servicer = IdentityServiceServicer(dal=mock_dal)

        with patch.object(servicer, "verify_token", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"userId": 42}
            request = GetLinkedPlatformsRequest(token="valid.token", hub_user_id=42)
            response = await servicer.GetLinkedPlatforms(request)

            assert response.success is True
            assert len(response.platforms) == 2
            assert response.platforms[0].platform == "twitch"
            assert response.platforms[0].platform_user_id == "tw1"
            assert response.platforms[0].platform_username == "alice"
            assert response.platforms[1].platform == "discord"
            assert response.platforms[1].platform_user_id == "dc2"
            assert response.platforms[1].platform_username == "alice_d"

    @pytest.mark.asyncio
    async def test_user_token_cannot_list_another_user_platforms(self):
        mock_dal = MagicMock()
        servicer = IdentityServiceServicer(dal=mock_dal)

        with patch.object(servicer, "verify_token", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"userId": 7}
            response = await servicer.GetLinkedPlatforms(
                GetLinkedPlatformsRequest(token="valid.token", hub_user_id=42)
            )

        assert response.success is False
        assert response.error.message == "Not authorized to access this identity"
        mock_dal.executesql.assert_not_called()


@pytest.mark.asyncio
async def test_servicer_registration_and_wire_round_trip():
    """Exercise the generated registration function and protobuf serializers."""
    mock_dal = MagicMock()
    mock_dal.executesql.side_effect = [
        [(42, "alice")],
        [("twitch", "tw123", "alice_tw")],
    ]
    servicer = IdentityServiceServicer(dal=mock_dal)
    servicer.verify_token = AsyncMock(return_value={"service": "router"})

    server = grpc.aio.server()
    identity_pb2_grpc.add_IdentityServiceServicer_to_server(servicer, server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()

    channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
    try:
        stub = identity_pb2_grpc.IdentityServiceStub(channel)
        response = await stub.LookupIdentity(
            LookupIdentityRequest(
                token="valid.token",
                platform="twitch",
                platform_user_id="tw123",
            )
        )
        assert response.success is True
        assert response.hub_user_id == 42
        assert response.linked_platforms[0].platform_username == "alice_tw"
    finally:
        await channel.close()
        await server.stop(grace=0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
