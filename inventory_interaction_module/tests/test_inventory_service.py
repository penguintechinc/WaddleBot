"""
Unit tests for InventoryService
"""

import pytest
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

# Set up test environment
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app import InventoryService, InventoryItem, InventoryStats, db


class TestInventoryService:
    """Test cases for InventoryService"""

    @pytest.fixture
    def service(self):
        """Create a fresh InventoryService instance for each test"""
        # Create a new database for each test
        test_db_path = tempfile.mktemp(suffix='.db')
        test_db_uri = f"sqlite:///{test_db_path}"
        
        # Mock the database
        with patch('app.db') as mock_db:
            mock_db.executesql = Mock()
            mock_db.inventory_items = Mock()
            mock_db.inventory_activity = Mock()
            mock_db.commit = Mock()
            
            service = InventoryService()
            service.db = mock_db
            yield service
        
        # Clean up
        if os.path.exists(test_db_path):
            os.unlink(test_db_path)

    def test_add_item_success(self, service):
        """Test successful item addition"""
        # Mock database response
        service.db.inventory_items.return_value = None  # No existing item
        service.db.inventory_items.insert.return_value = 1
        
        # Mock get_item_by_id
        expected_item = InventoryItem(
            id=1,
            community_id="test_community",
            item_name="test_item",
            description="Test description",
            labels=["electronics"],
            created_by="test_user",
            created_at=datetime.now(timezone.utc)
        )
        service.get_item_by_id = Mock(return_value=expected_item)
        
        # Test
        success, message, item = service.add_item(
            "test_community",
            "test_item",
            "Test description",
            ["electronics"],
            "test_user"
        )
        
        # Assertions
        assert success is True
        assert "added to inventory" in message
        assert item is not None
        assert item.item_name == "test_item"
        service.db.inventory_items.insert.assert_called_once()

    def test_add_item_duplicate_name(self, service):
        """Test adding item with duplicate name"""
        # Mock existing item
        existing_item = Mock()
        existing_item.item_name = "test_item"
        service.db.inventory_items.return_value = existing_item
        
        # Test
        success, message, item = service.add_item(
            "test_community",
            "test_item",
            "Test description",
            ["electronics"],
            "test_user"
        )
        
        # Assertions
        assert success is False
        assert "already exists" in message
        assert item is None

    def test_add_item_empty_name(self, service):
        """Test adding item with empty name"""
        success, message, item = service.add_item(
            "test_community",
            "",
            "Test description",
            ["electronics"],
            "test_user"
        )
        
        # Assertions
        assert success is False
        assert "cannot be empty" in message
        assert item is None

    def test_add_item_too_many_labels(self, service):
        """Test adding item with too many labels"""
        too_many_labels = ["label1", "label2", "label3", "label4", "label5", "label6"]
        
        success, message, item = service.add_item(
            "test_community",
            "test_item",
            "Test description",
            too_many_labels,
            "test_user"
        )
        
        # Assertions
        assert success is False
        assert "Maximum 5 labels" in message
        assert item is None

    def test_add_item_duplicate_labels(self, service):
        """Test adding item with duplicate labels"""
        duplicate_labels = ["electronics", "Electronics", "ELECTRONICS"]
        
        success, message, item = service.add_item(
            "test_community",
            "test_item",
            "Test description",
            duplicate_labels,
            "test_user"
        )
        
        # Assertions
        assert success is False
        assert "Duplicate labels" in message
        assert item is None

    def test_checkout_item_success(self, service):
        """Test successful item checkout"""
        # Mock existing available item
        mock_item = Mock()
        mock_item.id = 1
        mock_item.item_name = "test_item"
        mock_item.is_checked_out = False
        mock_item.update_record = Mock()
        service.db.inventory_items.return_value = mock_item
        
        # Mock get_item_by_id
        expected_item = InventoryItem(
            id=1,
            community_id="test_community",
            item_name="test_item",
            is_checked_out=True,
            checked_out_to="test_user"
        )
        service.get_item_by_id = Mock(return_value=expected_item)
        
        # Test
        success, message, item = service.checkout_item(
            "test_community",
            "test_item",
            "test_user",
            "admin"
        )
        
        # Assertions
        assert success is True
        assert "checked out to" in message
        assert item is not None
        assert item.checked_out_to == "test_user"
        mock_item.update_record.assert_called_once()

    def test_checkout_item_not_found(self, service):
        """Test checkout of non-existent item"""
        service.db.inventory_items.return_value = None
        
        success, message, item = service.checkout_item(
            "test_community",
            "nonexistent_item",
            "test_user",
            "admin"
        )
        
        # Assertions
        assert success is False
        assert "not found" in message
        assert item is None

    def test_checkout_item_already_checked_out(self, service):
        """Test checkout of already checked out item"""
        # Mock existing checked out item
        mock_item = Mock()
        mock_item.item_name = "test_item"
        mock_item.is_checked_out = True
        mock_item.checked_out_to = "other_user"
        service.db.inventory_items.return_value = mock_item
        
        success, message, item = service.checkout_item(
            "test_community",
            "test_item",
            "test_user",
            "admin"
        )
        
        # Assertions
        assert success is False
        assert "already checked out" in message
        assert item is None

    def test_checkin_item_success(self, service):
        """Test successful item checkin"""
        # Mock existing checked out item
        mock_item = Mock()
        mock_item.id = 1
        mock_item.item_name = "test_item"
        mock_item.is_checked_out = True
        mock_item.checked_out_to = "test_user"
        mock_item.update_record = Mock()
        service.db.inventory_items.return_value = mock_item
        
        # Mock get_item_by_id
        expected_item = InventoryItem(
            id=1,
            community_id="test_community",
            item_name="test_item",
            is_checked_out=False,
            checked_out_to=None
        )
        service.get_item_by_id = Mock(return_value=expected_item)
        
        # Test
        success, message, item = service.checkin_item(
            "test_community",
            "test_item",
            "admin"
        )
        
        # Assertions
        assert success is True
        assert "checked in" in message
        assert item is not None
        mock_item.update_record.assert_called_once()

    def test_checkin_item_not_checked_out(self, service):
        """Test checkin of item that's not checked out"""
        # Mock existing available item
        mock_item = Mock()
        mock_item.item_name = "test_item"
        mock_item.is_checked_out = False
        service.db.inventory_items.return_value = mock_item
        
        success, message, item = service.checkin_item(
            "test_community",
            "test_item",
            "admin"
        )
        
        # Assertions
        assert success is False
        assert "not checked out" in message
        assert item is None

    def test_delete_item_success(self, service):
        """Test successful item deletion"""
        # Mock existing item
        mock_item = Mock()
        mock_item.id = 1
        mock_item.item_name = "test_item"
        mock_item.is_checked_out = False
        mock_item.checked_out_to = None
        mock_item.delete_record = Mock()
        service.db.inventory_items.return_value = mock_item
        
        # Test
        success, message = service.delete_item(
            "test_community",
            "test_item",
            "admin"
        )
        
        # Assertions
        assert success is True
        assert "deleted" in message
        mock_item.delete_record.assert_called_once()

    def test_delete_item_not_found(self, service):
        """Test deletion of non-existent item"""
        service.db.inventory_items.return_value = None
        
        success, message = service.delete_item(
            "test_community",
            "nonexistent_item",
            "admin"
        )
        
        # Assertions
        assert success is False
        assert "not found" in message

    def test_list_items_all(self, service):
        """Test listing all items"""
        # Mock database response
        mock_items = [
            Mock(id=1, item_name="item1", description="desc1", labels=["label1"], 
                 is_checked_out=False, community_id="test_community"),
            Mock(id=2, item_name="item2", description="desc2", labels=["label2"], 
                 is_checked_out=True, community_id="test_community")
        ]
        
        mock_select = Mock()
        mock_select.select.return_value = mock_items
        service.db.return_value = mock_select
        
        # Test
        items = service.list_items("test_community", "all")
        
        # Assertions
        assert len(items) == 2
        assert all(isinstance(item, InventoryItem) for item in items)

    def test_list_items_available_only(self, service):
        """Test listing only available items"""
        # Mock database response
        mock_items = [
            Mock(id=1, item_name="item1", description="desc1", labels=["label1"], 
                 is_checked_out=False, community_id="test_community")
        ]
        
        mock_select = Mock()
        mock_select.select.return_value = mock_items
        service.db.return_value = mock_select
        
        # Test
        items = service.list_items("test_community", "available")
        
        # Assertions
        assert len(items) == 1
        assert items[0].is_checked_out is False

    def test_search_items_by_name(self, service):
        """Test searching items by name"""
        # Mock database response
        mock_items = [
            Mock(id=1, item_name="laptop", description="Work laptop", labels=["electronics"], 
                 is_checked_out=False, community_id="test_community")
        ]
        
        mock_select = Mock()
        mock_select.select.return_value = mock_items
        service.db.return_value = mock_select
        
        # Test
        items = service.search_items("test_community", "laptop")
        
        # Assertions
        assert len(items) == 1
        assert items[0].item_name == "laptop"

    def test_search_items_empty_query(self, service):
        """Test searching with empty query"""
        items = service.search_items("test_community", "")
        
        # Assertions
        assert len(items) == 0

    def test_get_item_status_available(self, service):
        """Test getting status of available item"""
        # Mock available item
        mock_item = Mock()
        mock_item.id = 1
        mock_item.item_name = "test_item"
        mock_item.is_checked_out = False
        mock_item.checked_in_at = datetime.now(timezone.utc)
        service.db.inventory_items.return_value = mock_item
        
        success, message, item = service.get_item_status("test_community", "test_item")
        
        # Assertions
        assert success is True
        assert "available" in message
        assert item is not None

    def test_get_item_status_checked_out(self, service):
        """Test getting status of checked out item"""
        # Mock checked out item
        mock_item = Mock()
        mock_item.id = 1
        mock_item.item_name = "test_item"
        mock_item.is_checked_out = True
        mock_item.checked_out_to = "test_user"
        mock_item.checked_out_at = datetime.now(timezone.utc)
        service.db.inventory_items.return_value = mock_item
        
        success, message, item = service.get_item_status("test_community", "test_item")
        
        # Assertions
        assert success is True
        assert "checked out to" in message
        assert item is not None

    def test_manage_labels_add_success(self, service):
        """Test successfully adding a label"""
        # Mock existing item
        mock_item = Mock()
        mock_item.id = 1
        mock_item.item_name = "test_item"
        mock_item.labels = ["existing_label"]
        mock_item.update_record = Mock()
        service.db.inventory_items.return_value = mock_item
        
        # Mock get_item_by_id
        expected_item = InventoryItem(
            id=1,
            community_id="test_community",
            item_name="test_item",
            labels=["existing_label", "new_label"]
        )
        service.get_item_by_id = Mock(return_value=expected_item)
        
        # Test
        success, message, item = service.manage_labels(
            "test_community",
            "test_item",
            "add",
            "new_label",
            "admin"
        )
        
        # Assertions
        assert success is True
        assert "added" in message
        assert item is not None
        mock_item.update_record.assert_called_once()

    def test_manage_labels_add_duplicate(self, service):
        """Test adding duplicate label"""
        # Mock existing item
        mock_item = Mock()
        mock_item.item_name = "test_item"
        mock_item.labels = ["existing_label"]
        service.db.inventory_items.return_value = mock_item
        
        # Test
        success, message, item = service.manage_labels(
            "test_community",
            "test_item",
            "add",
            "existing_label",
            "admin"
        )
        
        # Assertions
        assert success is False
        assert "already exists" in message
        assert item is None

    def test_manage_labels_add_too_many(self, service):
        """Test adding label when at maximum"""
        # Mock existing item with max labels
        mock_item = Mock()
        mock_item.item_name = "test_item"
        mock_item.labels = ["label1", "label2", "label3", "label4", "label5"]
        service.db.inventory_items.return_value = mock_item
        
        # Test
        success, message, item = service.manage_labels(
            "test_community",
            "test_item",
            "add",
            "new_label",
            "admin"
        )
        
        # Assertions
        assert success is False
        assert "Maximum 5 labels" in message
        assert item is None

    def test_manage_labels_remove_success(self, service):
        """Test successfully removing a label"""
        # Mock existing item
        mock_item = Mock()
        mock_item.id = 1
        mock_item.item_name = "test_item"
        mock_item.labels = ["label1", "label2"]
        mock_item.update_record = Mock()
        service.db.inventory_items.return_value = mock_item
        
        # Mock get_item_by_id
        expected_item = InventoryItem(
            id=1,
            community_id="test_community",
            item_name="test_item",
            labels=["label2"]
        )
        service.get_item_by_id = Mock(return_value=expected_item)
        
        # Test
        success, message, item = service.manage_labels(
            "test_community",
            "test_item",
            "remove",
            "label1",
            "admin"
        )
        
        # Assertions
        assert success is True
        assert "removed" in message
        assert item is not None
        mock_item.update_record.assert_called_once()

    def test_manage_labels_remove_not_found(self, service):
        """Test removing non-existent label"""
        # Mock existing item
        mock_item = Mock()
        mock_item.item_name = "test_item"
        mock_item.labels = ["label1", "label2"]
        service.db.inventory_items.return_value = mock_item
        
        # Test
        success, message, item = service.manage_labels(
            "test_community",
            "test_item",
            "remove",
            "nonexistent_label",
            "admin"
        )
        
        # Assertions
        assert success is False
        assert "not found" in message
        assert item is None

    def test_manage_labels_invalid_action(self, service):
        """Test invalid label action"""
        # Mock existing item
        mock_item = Mock()
        mock_item.item_name = "test_item"
        mock_item.labels = ["label1"]
        service.db.inventory_items.return_value = mock_item
        
        # Test
        success, message, item = service.manage_labels(
            "test_community",
            "test_item",
            "invalid_action",
            "label",
            "admin"
        )
        
        # Assertions
        assert success is False
        assert "Invalid action" in message
        assert item is None

    def test_get_stats(self, service):
        """Test getting inventory statistics"""
        # Mock database responses
        service.db.return_value.count.side_effect = [10, 3]  # total, checked out
        
        # Mock items for label statistics
        mock_items = [
            Mock(labels=["electronics", "valuable"]),
            Mock(labels=["electronics", "tools"]),
            Mock(labels=["books"]),
            Mock(labels=None)
        ]
        mock_select = Mock()
        mock_select.select.return_value = mock_items
        service.db.return_value = mock_select
        
        # Mock activity
        mock_activity = Mock()
        mock_activity.select.return_value = []
        service.db.return_value = mock_activity
        
        # Test
        stats = service.get_stats("test_community")
        
        # Assertions
        assert isinstance(stats, InventoryStats)
        assert stats.total_items == 10
        assert stats.checked_out_items == 3
        assert stats.available_items == 7

    def test_log_activity(self, service):
        """Test logging activity"""
        # Mock database
        mock_insert = Mock()
        service.db.inventory_activity.insert = mock_insert
        
        # Test
        service.log_activity(
            "test_community",
            1,
            "add",
            "test_user",
            {"item_name": "test_item"}
        )
        
        # Assertions
        mock_insert.assert_called_once()
        service.db.commit.assert_called_once()

    def test_clear_cache(self, service):
        """Test clearing cache"""
        # Set up cache
        service.cache = {
            "inventory_test_community_items": "data1",
            "inventory_test_community_stats": "data2",
            "inventory_other_community_items": "data3"
        }
        
        # Test
        service.clear_cache("test_community")
        
        # Assertions
        assert "inventory_test_community_items" not in service.cache
        assert "inventory_test_community_stats" not in service.cache
        assert "inventory_other_community_items" in service.cache

    def test_get_item_by_id_success(self, service):
        """Test getting item by ID"""
        # Mock database response
        mock_item = Mock()
        mock_item.id = 1
        mock_item.community_id = "test_community"
        mock_item.item_name = "test_item"
        mock_item.description = "Test description"
        mock_item.labels = ["electronics"]
        mock_item.is_checked_out = False
        mock_item.checked_out_to = None
        mock_item.checked_out_at = None
        mock_item.checked_in_at = None
        mock_item.created_by = "test_user"
        mock_item.created_at = datetime.now(timezone.utc)
        mock_item.updated_at = datetime.now(timezone.utc)
        
        service.db.inventory_items.return_value = mock_item
        
        # Test
        item = service.get_item_by_id(1)
        
        # Assertions
        assert item is not None
        assert item.id == 1
        assert item.item_name == "test_item"
        assert item.labels == ["electronics"]

    def test_get_item_by_id_not_found(self, service):
        """Test getting non-existent item by ID"""
        service.db.inventory_items.return_value = None
        
        # Test
        item = service.get_item_by_id(999)
        
        # Assertions
        assert item is None


class TestInventoryItem:
    """Test cases for InventoryItem dataclass"""

    def test_to_dict(self):
        """Test converting InventoryItem to dictionary"""
        now = datetime.now(timezone.utc)
        item = InventoryItem(
            id=1,
            community_id="test_community",
            item_name="test_item",
            description="Test description",
            labels=["electronics"],
            is_checked_out=True,
            checked_out_to="test_user",
            checked_out_at=now,
            created_by="admin",
            created_at=now
        )
        
        # Test
        result = item.to_dict()
        
        # Assertions
        assert result["id"] == 1
        assert result["item_name"] == "test_item"
        assert result["labels"] == ["electronics"]
        assert result["is_checked_out"] is True
        assert result["checked_out_to"] == "test_user"
        assert result["checked_out_at"] == now.isoformat()
        assert result["created_at"] == now.isoformat()

    def test_to_dict_with_none_dates(self):
        """Test converting InventoryItem with None dates to dictionary"""
        item = InventoryItem(
            id=1,
            community_id="test_community",
            item_name="test_item",
            checked_out_at=None,
            checked_in_at=None,
            created_at=None,
            updated_at=None
        )
        
        # Test
        result = item.to_dict()
        
        # Assertions
        assert result["checked_out_at"] is None
        assert result["checked_in_at"] is None
        assert result["created_at"] is None
        assert result["updated_at"] is None


class TestInventoryStats:
    """Test cases for InventoryStats dataclass"""

    def test_default_values(self):
        """Test default values for InventoryStats"""
        stats = InventoryStats()
        
        # Assertions
        assert stats.total_items == 0
        assert stats.checked_out_items == 0
        assert stats.available_items == 0
        assert stats.total_labels == 0
        assert stats.most_used_labels == []
        assert stats.recent_activity == []

    def test_custom_values(self):
        """Test custom values for InventoryStats"""
        stats = InventoryStats(
            total_items=100,
            checked_out_items=25,
            available_items=75,
            total_labels=50,
            most_used_labels=["electronics", "tools"],
            recent_activity=[{"action": "add", "item": "test"}]
        )
        
        # Assertions
        assert stats.total_items == 100
        assert stats.checked_out_items == 25
        assert stats.available_items == 75
        assert stats.total_labels == 50
        assert stats.most_used_labels == ["electronics", "tools"]
        assert len(stats.recent_activity) == 1