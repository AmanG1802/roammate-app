"""Unit tests for app.services.llm.models._clients — shared client memoization.

Pure in-memory caching logic with no network calls.
"""
import pytest
from unittest.mock import MagicMock

from app.services.llm.models._clients import get_shared_client, clear_shared_clients


class TestGetSharedClient:
    def setup_method(self):
        clear_shared_clients()

    def teardown_method(self):
        clear_shared_clients()

    def test_get_shared_client(self):
        # Test 1a - Factory is called on first access
        factory = MagicMock(return_value="client_instance")
        client = get_shared_client("openai", "sk-key", factory)
        assert client == "client_instance"
        factory.assert_called_once()

        # Test 1b - Second call returns cached client without calling factory
        factory2 = MagicMock(return_value="should_not_be_used")
        client2 = get_shared_client("openai", "sk-key", factory2)
        assert client2 == "client_instance"
        factory2.assert_not_called()

        # Test 1c - Different provider creates a new client
        factory3 = MagicMock(return_value="claude_client")
        client3 = get_shared_client("claude", "sk-ant-key", factory3)
        assert client3 == "claude_client"
        factory3.assert_called_once()

        # Test 1d - Different API key creates a new client
        factory4 = MagicMock(return_value="different_key_client")
        client4 = get_shared_client("openai", "sk-different", factory4)
        assert client4 == "different_key_client"
        factory4.assert_called_once()

        # Test 1e - None api_key is treated as empty string
        factory5 = MagicMock(return_value="no_key_client")
        client5 = get_shared_client("openai", None, factory5)
        # Should get a new client since "" != "sk-key"
        assert client5 == "no_key_client"

    def test_clear_shared_clients(self):
        # Test 1f - clear_shared_clients resets cache
        factory = MagicMock(return_value="first")
        get_shared_client("test", "key", factory)
        clear_shared_clients()

        factory2 = MagicMock(return_value="second")
        client = get_shared_client("test", "key", factory2)
        assert client == "second"
        factory2.assert_called_once()
