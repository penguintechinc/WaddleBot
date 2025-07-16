"""
Unit tests for API endpoints
"""

import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from app import inventory_service, InventoryItem, InventoryStats


class TestInventoryAPI:
    """Test cases for inventory API endpoints"""

    @pytest.fixture
    def mock_request(self):
        """Mock request object"""
        mock_req = Mock()
        mock_req.headers = {
            "X-Community-ID": "test_community",
            "X-User-ID": "test_user"
        }
        mock_req.method = "GET"
        mock_req.query = {}
        mock_req.json = {}
        return mock_req

    @pytest.fixture
    def mock_inventory_service(self):
        """Mock inventory service"""
        with patch('app.inventory_service') as mock_service:
            yield mock_service

    def test_inventory_api_missing_headers(self, mock_request):
        """Test API with missing headers"""
        mock_request.headers = {}
        
        with patch('app.request', mock_request):
            from app import inventory_api
            result = inventory_api()
        
        # Assertions
        assert result["success"] is False
        assert "Missing community or user context" in result["error"]

    def test_inventory_api_list_all(self, mock_request, mock_inventory_service):
        """Test listing all items"""
        mock_request.query = {"action": "list", "filter": "all"}
        
        # Mock service response
        mock_items = [
            InventoryItem(id=1, item_name="item1", community_id="test_community"),
            InventoryItem(id=2, item_name="item2", community_id="test_community")
        ]
        mock_inventory_service.list_items.return_value = mock_items
        
        with patch('app.request', mock_request):
            from app import inventory_api
            result = inventory_api()
        
        # Assertions
        assert result["success"] is True
        assert len(result["items"]) == 2
        assert result["count"] == 2
        mock_inventory_service.list_items.assert_called_once_with("test_community", "all")

    def test_inventory_api_list_available(self, mock_request, mock_inventory_service):
        """Test listing available items"""
        mock_request.query = {"action": "list", "filter": "available"}
        
        # Mock service response
        mock_items = [
            InventoryItem(id=1, item_name="item1", community_id="test_community", is_checked_out=False)
        ]
        mock_inventory_service.list_items.return_value = mock_items
        
        with patch('app.request', mock_request):
            from app import inventory_api
            result = inventory_api()
        
        # Assertions
        assert result["success"] is True
        assert len(result["items"]) == 1
        assert result["count"] == 1
        mock_inventory_service.list_items.assert_called_once_with("test_community", "available")

    def test_inventory_api_search(self, mock_request, mock_inventory_service):
        """Test searching items"""
        mock_request.query = {"action": "search", "query": "laptop"}
        
        # Mock service response
        mock_items = [
            InventoryItem(id=1, item_name="laptop", community_id="test_community")
        ]
        mock_inventory_service.search_items.return_value = mock_items
        
        with patch('app.request', mock_request):
            from app import inventory_api
            result = inventory_api()
        
        # Assertions
        assert result["success"] is True
        assert len(result["items"]) == 1
        assert result["query"] == "laptop"
        mock_inventory_service.search_items.assert_called_once_with("test_community", "laptop")

    def test_inventory_api_status(self, mock_request, mock_inventory_service):
        """Test getting item status"""
        mock_request.query = {"action": "status", "item_name": "test_item"}
        
        # Mock service response
        mock_item = InventoryItem(id=1, item_name="test_item", community_id="test_community")
        mock_inventory_service.get_item_status.return_value = (True, "Item is available", mock_item)
        
        with patch('app.request', mock_request):
            from app import inventory_api
            result = inventory_api()
        
        # Assertions
        assert result["success"] is True
        assert result["message"] == "Item is available"
        assert result["item"] is not None
        mock_inventory_service.get_item_status.assert_called_once_with("test_community", "test_item")

    def test_inventory_api_stats(self, mock_request, mock_inventory_service):
        """Test getting inventory stats"""
        mock_request.query = {"action": "stats"}
        
        # Mock service response
        mock_stats = InventoryStats(
            total_items=10,
            checked_out_items=3,
            available_items=7
        )
        mock_inventory_service.get_stats.return_value = mock_stats
        
        with patch('app.request', mock_request):
            from app import inventory_api
            result = inventory_api()
        
        # Assertions
        assert result["success"] is True
        assert result["stats"]["total_items"] == 10
        assert result["stats"]["checked_out_items"] == 3
        assert result["stats"]["available_items"] == 7
        mock_inventory_service.get_stats.assert_called_once_with("test_community")

    def test_inventory_api_invalid_get_action(self, mock_request, mock_inventory_service):
        """Test invalid GET action"""
        mock_request.query = {"action": "invalid_action"}
        
        with patch('app.request', mock_request):
            from app import inventory_api
            result = inventory_api()
        
        # Assertions
        assert result["success"] is False
        assert "Invalid action" in result["error"]

    def test_inventory_api_add_item(self, mock_request, mock_inventory_service):
        """Test adding item via POST"""
        mock_request.method = "POST"
        mock_request.json = {
            "action": "add",
            "item_name": "new_item",
            "description": "Test item",
            "labels": ["electronics"]
        }
        
        # Mock service response
        mock_item = InventoryItem(
            id=1,
            item_name="new_item",
            description="Test item",
            labels=["electronics"],
            community_id="test_community"
        )
        mock_inventory_service.add_item.return_value = (True, "Item added successfully", mock_item)
        
        with patch('app.request', mock_request):
            from app import inventory_api
            result = inventory_api()
        
        # Assertions
        assert result["success"] is True
        assert result["message"] == "Item added successfully"
        assert result["item"] is not None
        mock_inventory_service.add_item.assert_called_once_with(
            "test_community",
            "new_item",
            "Test item",
            ["electronics"],
            "test_user"
        )

    def test_inventory_api_checkout_item(self, mock_request, mock_inventory_service):
        """Test checking out item via POST"""
        mock_request.method = "POST"
        mock_request.json = {
            "action": "checkout",
            "item_name": "test_item",
            "checked_out_to": "target_user"
        }
        
        # Mock service response
        mock_item = InventoryItem(
            id=1,
            item_name="test_item",
            is_checked_out=True,
            checked_out_to="target_user",
            community_id="test_community"
        )
        mock_inventory_service.checkout_item.return_value = (True, "Item checked out", mock_item)
        
        with patch('app.request', mock_request):
            from app import inventory_api
            result = inventory_api()
        
        # Assertions
        assert result["success"] is True
        assert result["message"] == "Item checked out"
        assert result["item"] is not None
        mock_inventory_service.checkout_item.assert_called_once_with(
            "test_community",
            "test_item",
            "target_user",
            "test_user"
        )

    def test_inventory_api_checkin_item(self, mock_request, mock_inventory_service):
        """Test checking in item via POST"""
        mock_request.method = "POST"
        mock_request.json = {
            "action": "checkin",
            "item_name": "test_item"
        }
        
        # Mock service response
        mock_item = InventoryItem(
            id=1,
            item_name="test_item",
            is_checked_out=False,
            checked_out_to=None,
            community_id="test_community"
        )
        mock_inventory_service.checkin_item.return_value = (True, "Item checked in", mock_item)
        
        with patch('app.request', mock_request):
            from app import inventory_api
            result = inventory_api()
        
        # Assertions
        assert result["success"] is True
        assert result["message"] == "Item checked in"
        assert result["item"] is not None
        mock_inventory_service.checkin_item.assert_called_once_with(
            "test_community",
            "test_item",
            "test_user"
        )

    def test_inventory_api_delete_item(self, mock_request, mock_inventory_service):
        """Test deleting item via POST"""
        mock_request.method = "POST"
        mock_request.json = {
            "action": "delete",
            "item_name": "test_item"
        }
        
        # Mock service response
        mock_inventory_service.delete_item.return_value = (True, "Item deleted")
        
        with patch('app.request', mock_request):
            from app import inventory_api
            result = inventory_api()
        
        # Assertions
        assert result["success"] is True
        assert result["message"] == "Item deleted"
        assert "item" not in result or result["item"] is None
        mock_inventory_service.delete_item.assert_called_once_with(
            "test_community",
            "test_item",
            "test_user"
        )

    def test_inventory_api_manage_labels(self, mock_request, mock_inventory_service):
        """Test managing labels via POST"""
        mock_request.method = "POST"
        mock_request.json = {
            "action": "labels",
            "item_name": "test_item",
            "label_action": "add",
            "label": "new_label"
        }
        
        # Mock service response
        mock_item = InventoryItem(
            id=1,
            item_name="test_item",
            labels=["existing_label", "new_label"],
            community_id="test_community"
        )
        mock_inventory_service.manage_labels.return_value = (True, "Label added", mock_item)
        
        with patch('app.request', mock_request):
            from app import inventory_api
            result = inventory_api()
        
        # Assertions
        assert result["success"] is True
        assert result["message"] == "Label added"
        assert result["item"] is not None
        mock_inventory_service.manage_labels.assert_called_once_with(
            "test_community",
            "test_item",
            "add",
            "new_label",
            "test_user"
        )

    def test_inventory_api_invalid_post_action(self, mock_request, mock_inventory_service):
        """Test invalid POST action"""
        mock_request.method = "POST"
        mock_request.json = {
            "action": "invalid_action"
        }
        
        with patch('app.request', mock_request):
            from app import inventory_api
            result = inventory_api()
        
        # Assertions
        assert result["success"] is False
        assert "Invalid action" in result["error"]

    def test_inventory_api_unsupported_method(self, mock_request, mock_inventory_service):
        """Test unsupported HTTP method"""
        mock_request.method = "DELETE"
        
        with patch('app.request', mock_request):
            from app import inventory_api
            result = inventory_api()
        
        # Assertions
        assert result["success"] is False
        assert "Method not allowed" in result["error"]

    def test_inventory_api_exception_handling(self, mock_request, mock_inventory_service):
        """Test exception handling in API"""
        mock_request.query = {"action": "list"}
        
        # Mock service to raise exception
        mock_inventory_service.list_items.side_effect = Exception("Database error")
        
        with patch('app.request', mock_request):
            from app import inventory_api
            result = inventory_api()
        
        # Assertions
        assert result["success"] is False
        assert "Internal server error" in result["error"]
        assert "Database error" in result["error"]


class TestHealthCheck:
    """Test cases for health check endpoint"""

    def test_health_check_success(self):
        """Test successful health check"""
        with patch('app.db') as mock_db:
            mock_db.executesql = Mock()
            
            with patch('app.inventory_service') as mock_service:
                mock_service.get_stats.return_value = InventoryStats()
                
                from app import health_check
                result = health_check()
        
        # Assertions
        assert result["status"] == "healthy"
        assert result["service"] == "inventory_interaction_module"
        assert result["version"] == "1.0.0"
        assert result["database"] == "connected"
        assert result["cache"] == "active"
        assert result["thread_pool"] == "running"

    def test_health_check_failure(self):
        """Test health check failure"""
        with patch('app.db') as mock_db:
            mock_db.executesql.side_effect = Exception("Database connection failed")
            
            from app import health_check
            result = health_check()
        
        # Assertions
        assert result["status"] == "unhealthy"
        assert "Database connection failed" in result["error"]

    def test_health_check_service_failure(self):
        """Test health check with service failure"""
        with patch('app.db') as mock_db:
            mock_db.executesql = Mock()
            
            with patch('app.inventory_service') as mock_service:
                mock_service.get_stats.side_effect = Exception("Service error")
                
                from app import health_check
                result = health_check()
        
        # Assertions
        assert result["status"] == "unhealthy"
        assert "Service error" in result["error"]


class TestMetrics:
    """Test cases for metrics endpoint"""

    def test_metrics_success(self):
        """Test successful metrics collection"""
        with patch('app.inventory_service') as mock_service:
            mock_stats = InventoryStats(
                total_items=100,
                checked_out_items=25,
                available_items=75
            )
            mock_service.get_stats.return_value = mock_stats
            
            mock_request = Mock()
            mock_request.headers = {"X-Community-ID": "test_community"}
            
            with patch('app.request', mock_request):
                from app import metrics
                result = metrics()
        
        # Assertions
        assert result["service"] == "inventory_interaction_module"
        assert result["version"] == "1.0.0"
        assert result["stats"]["total_items"] == 100
        assert result["stats"]["checked_out_items"] == 25
        assert result["stats"]["available_items"] == 75
        assert result["performance"]["thread_pool_size"] == 20
        assert result["performance"]["max_labels_per_item"] == 5

    def test_metrics_no_community_header(self):
        """Test metrics without community header"""
        with patch('app.inventory_service') as mock_service:
            mock_stats = InventoryStats()
            mock_service.get_stats.return_value = mock_stats
            
            mock_request = Mock()
            mock_request.headers = {}
            
            with patch('app.request', mock_request):
                from app import metrics
                result = metrics()
        
        # Assertions
        assert result["service"] == "inventory_interaction_module"
        mock_service.get_stats.assert_called_once_with("system")

    def test_metrics_failure(self):
        """Test metrics collection failure"""
        with patch('app.inventory_service') as mock_service:
            mock_service.get_stats.side_effect = Exception("Metrics error")
            
            mock_request = Mock()
            mock_request.headers = {"X-Community-ID": "test_community"}
            
            with patch('app.request', mock_request):
                from app import metrics
                result = metrics()
        
        # Assertions
        assert "error" in result
        assert "Metrics error" in result["error"]


class TestDatabaseIntegration:
    """Integration tests for database operations"""

    def test_database_table_creation(self):
        """Test that database tables are created correctly"""
        with patch('app.db') as mock_db:
            mock_db.define_table = Mock()
            mock_db.executesql = Mock()
            
            # Import to trigger table creation
            from app import define_tables
            define_tables()
            
            # Verify tables were defined
            assert mock_db.define_table.call_count == 2  # inventory_items and inventory_activity
            assert mock_db.executesql.call_count >= 5  # Multiple index creation calls

    def test_database_indexes(self):
        """Test that database indexes are created"""
        with patch('app.db') as mock_db:
            mock_db.executesql = Mock()
            
            from app import define_tables
            define_tables()
            
            # Verify index creation calls
            expected_indexes = [
                "idx_inventory_community",
                "idx_inventory_name",
                "idx_inventory_checkout",
                "idx_activity_community",
                "idx_activity_item"
            ]
            
            # Check that index creation was attempted
            assert mock_db.executesql.call_count >= len(expected_indexes)


class TestConcurrency:
    """Test cases for concurrent operations"""

    def test_thread_pool_executor(self):
        """Test thread pool executor initialization"""
        from app import executor
        
        # Assertions
        assert executor is not None
        assert executor._max_workers == 20  # Default MAX_WORKERS

    def test_cache_thread_safety(self):
        """Test cache thread safety"""
        from app import cache, cache_lock
        
        # Assertions
        assert cache is not None
        assert cache_lock is not None
        assert hasattr(cache_lock, '__enter__')
        assert hasattr(cache_lock, '__exit__')

    def test_concurrent_cache_operations(self):
        """Test concurrent cache operations"""
        with patch('app.inventory_service') as mock_service:
            # Test that clear_cache uses the lock
            mock_service.cache = {"test_key": "test_value"}
            mock_service.cache_lock = Mock()
            mock_service.cache_lock.__enter__ = Mock()
            mock_service.cache_lock.__exit__ = Mock()
            
            mock_service.clear_cache("test_community")
            
            # Verify lock was used
            mock_service.cache_lock.__enter__.assert_called_once()
            mock_service.cache_lock.__exit__.assert_called_once()