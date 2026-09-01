"""Unit tests for TwitchEmoteProvider app access token flow."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time
import os


class TestTwitchEmoteProviderAccessToken:
    """Test suite for Twitch app access token implementation."""

    @pytest.mark.asyncio
    async def test_get_app_access_token_missing_creds(self):
        """Test that missing credentials returns empty string and logs warning."""
        from processing.router_module.services.emote_providers.twitch_emote_provider import (
            TwitchEmoteProvider,
        )

        # Initialize with no credentials
        provider = TwitchEmoteProvider(client_id=None)

        with patch.dict(os.environ, {}, clear=False):
            with patch('processing.router_module.services.emote_providers.twitch_emote_provider.logger') as mock_logger:
                token = provider._get_app_access_token()

                # Should return empty string
                assert token == ""

                # Should log warning about missing credentials
                mock_logger.warning.assert_called()
                warning_msg = mock_logger.warning.call_args[0][0]
                assert 'Twitch app credentials not configured' in warning_msg or 'not configured' in warning_msg

    @pytest.mark.asyncio
    async def test_get_app_access_token_success(self):
        """Test successful token fetch and cache."""
        from processing.router_module.services.emote_providers.twitch_emote_provider import (
            TwitchEmoteProvider,
        )

        provider = TwitchEmoteProvider(client_id="test-client-id")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-token-12345",
            "expires_in": 3600,
            "token_type": "bearer"
        }

        with patch('processing.router_module.services.emote_providers.twitch_emote_provider.httpx.post') as mock_post:
            mock_post.return_value = mock_response

            # Provide credentials via environment
            with patch.dict(os.environ, {'TWITCH_CLIENT_ID': 'test-client-id', 'TWITCH_CLIENT_SECRET': 'test-secret'}):
                token = provider._get_app_access_token()

                # Should return valid token
                assert token == "test-token-12345"

                # Verify POST call was made to correct URL with correct params
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                assert 'https://id.twitch.tv/oauth2/token' in str(call_args)
                assert 'client_credentials' in str(call_args)

    @pytest.mark.asyncio
    async def test_get_app_access_token_cached(self):
        """Test that token is cached and reused within expiry."""
        from processing.router_module.services.emote_providers.twitch_emote_provider import (
            TwitchEmoteProvider,
        )

        provider = TwitchEmoteProvider(client_id="test-client-id")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "cached-token-xyz",
            "expires_in": 3600,
            "token_type": "bearer"
        }

        with patch('processing.router_module.services.emote_providers.twitch_emote_provider.httpx.post') as mock_post:
            mock_post.return_value = mock_response

            with patch.dict(os.environ, {'TWITCH_CLIENT_ID': 'test-client-id', 'TWITCH_CLIENT_SECRET': 'test-secret'}):
                token1 = provider._get_app_access_token()
                token2 = provider._get_app_access_token()

                # Both should return same token
                assert token1 == token2 == "cached-token-xyz"

                # HTTP POST should be called only once (cached on second call)
                assert mock_post.call_count == 1

    @pytest.mark.asyncio
    async def test_get_app_access_token_refresh_on_expiry(self):
        """Test that token is refreshed when less than 60s remaining."""
        from processing.router_module.services.emote_providers.twitch_emote_provider import (
            TwitchEmoteProvider,
        )

        provider = TwitchEmoteProvider(client_id="test-client-id")

        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "access_token": "token-1",
            "expires_in": 3600,
            "token_type": "bearer"
        }

        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            "access_token": "token-2-refreshed",
            "expires_in": 3600,
            "token_type": "bearer"
        }

        with patch('processing.router_module.services.emote_providers.twitch_emote_provider.httpx.post') as mock_post:
            mock_post.side_effect = [mock_response1, mock_response2]

            with patch.dict(os.environ, {'TWITCH_CLIENT_ID': 'test-client-id', 'TWITCH_CLIENT_SECRET': 'test-secret'}):
                with patch('processing.router_module.services.emote_providers.twitch_emote_provider.time.time') as mock_time_func:
                    # Scenario: t=1000 fetch token (expires 4600), t=1000 reuse, t=4541 refresh (59s left)
                    # Each call to time.time() consumes one value from side_effect
                    # Call 1: POST returns token-1, expiry calc uses time.time() = 1000
                    # Call 2: Check cache uses time.time() = 1000
                    # Call 3: Check cache uses time.time() = 4541, then POST returns token-2, expiry calc uses 4541
                    mock_time_func.side_effect = [1000, 1000, 4541, 4541]

                    # First call: fetch token-1 at t=1000, expires at 4600
                    token1 = provider._get_app_access_token()
                    assert token1 == "token-1"

                    # Second call: at same time, 3600s left > 60s threshold, reuse
                    token2 = provider._get_app_access_token()
                    assert token2 == "token-1"  # Still cached
                    assert mock_post.call_count == 1

                    # Third call: at t=4541, only 59s left < 60s threshold, refresh
                    token3 = provider._get_app_access_token()
                    assert token3 == "token-2-refreshed"
                    assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_get_app_access_token_network_error(self):
        """Test that network errors return empty string and log error."""
        from processing.router_module.services.emote_providers.twitch_emote_provider import (
            TwitchEmoteProvider,
        )

        provider = TwitchEmoteProvider(client_id="test-client-id")

        with patch('processing.router_module.services.emote_providers.twitch_emote_provider.httpx.post') as mock_post:
            mock_post.side_effect = Exception("Network error")

            with patch.dict(os.environ, {'TWITCH_CLIENT_ID': 'test-client-id', 'TWITCH_CLIENT_SECRET': 'test-secret'}):
                with patch('processing.router_module.services.emote_providers.twitch_emote_provider.logger') as mock_logger:
                    token = provider._get_app_access_token()

                    # Should return empty string on error
                    assert token == ""

                    # Should log error
                    mock_logger.error.assert_called()
                    error_msg = mock_logger.error.call_args[0][0]
                    assert 'Network error' in error_msg or 'Failed' in error_msg

    @pytest.mark.asyncio
    async def test_get_app_access_token_non_200_response(self):
        """Test that non-200 responses return empty string and log error."""
        from processing.router_module.services.emote_providers.twitch_emote_provider import (
            TwitchEmoteProvider,
        )

        provider = TwitchEmoteProvider(client_id="test-client-id")

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch('processing.router_module.services.emote_providers.twitch_emote_provider.httpx.post') as mock_post:
            mock_post.return_value = mock_response

            with patch.dict(os.environ, {'TWITCH_CLIENT_ID': 'test-client-id', 'TWITCH_CLIENT_SECRET': 'test-secret'}):
                with patch('processing.router_module.services.emote_providers.twitch_emote_provider.logger') as mock_logger:
                    token = provider._get_app_access_token()

                    # Should return empty string on error status
                    assert token == ""

                    # Should log error with status code
                    mock_logger.error.assert_called()
                    error_msg = mock_logger.error.call_args[0][0]
                    assert '401' in error_msg or 'status' in error_msg.lower()

    @pytest.mark.asyncio
    async def test_fetch_twitch_emotes_with_valid_token(self):
        """Test that fetch uses the app access token in Authorization header."""
        from processing.router_module.services.emote_providers.twitch_emote_provider import (
            TwitchEmoteProvider,
        )

        provider = TwitchEmoteProvider(client_id="test-client-id")

        # Mock token response
        token_response = MagicMock()
        token_response.status_code = 200
        token_response.json.return_value = {
            "access_token": "valid-token",
            "expires_in": 3600,
            "token_type": "bearer"
        }

        # Mock emote response
        emote_response = MagicMock()
        emote_response.status_code = 200
        emote_response.json.return_value = {
            "data": [
                {
                    "id": "12345",
                    "name": "Kappa",
                    "images": {"url_1x": "https://example.com/kappa.png"}
                }
            ]
        }

        with patch('processing.router_module.services.emote_providers.twitch_emote_provider.httpx.post') as mock_post:
            mock_post.return_value = token_response

            with patch('processing.router_module.services.emote_providers.twitch_emote_provider.httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.is_closed = False
                mock_client.get = AsyncMock(return_value=emote_response)
                mock_client_class.return_value = mock_client

                with patch.dict(os.environ, {'TWITCH_CLIENT_ID': 'test-client-id', 'TWITCH_CLIENT_SECRET': 'test-secret'}):
                    # Fetch emotes - should use valid token in header
                    emotes = await provider.fetch_emotes(sources=['twitch'])

                    # Verify Authorization header was set with token
                    assert mock_client.get.called
                    # Get the first call to client.get (for Twitch global emotes)
                    first_call = mock_client.get.call_args_list[0]
                    call_kwargs = first_call[1]  # Get the kwargs
                    headers = call_kwargs.get('headers', {})
                    assert 'Authorization' in headers
                    assert headers['Authorization'] == 'Bearer valid-token'
