package storage

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"
)

func TestNewBoltStorage(t *testing.T) {
	tmpDir := t.TempDir()
	
	storage, err := NewBoltStorage(tmpDir)
	if err != nil {
		t.Fatalf("NewBoltStorage failed: %v", err)
	}
	defer storage.Close()
	
	if storage == nil {
		t.Fatal("Expected non-nil storage")
	}
	
	if storage.db == nil {
		t.Fatal("Expected non-nil database")
	}
	
	// Check that database file was created
	dbPath := filepath.Join(tmpDir, "waddlebot-bridge.db")
	if _, err := os.Stat(dbPath); os.IsNotExist(err) {
		t.Error("Database file was not created")
	}
}

func TestBoltStorage_Set_Get(t *testing.T) {
	tmpDir := t.TempDir()
	storage, err := NewBoltStorage(tmpDir)
	if err != nil {
		t.Fatalf("NewBoltStorage failed: %v", err)
	}
	defer storage.Close()
	
	key := "test-key"
	value := []byte("test-value")
	
	// Test Set
	err = storage.Set(key, value)
	if err != nil {
		t.Fatalf("Set failed: %v", err)
	}
	
	// Test Get
	retrievedValue, err := storage.Get(key)
	if err != nil {
		t.Fatalf("Get failed: %v", err)
	}
	
	if string(retrievedValue) != string(value) {
		t.Errorf("Expected value %s, got %s", string(value), string(retrievedValue))
	}
}

func TestBoltStorage_Get_NotFound(t *testing.T) {
	tmpDir := t.TempDir()
	storage, err := NewBoltStorage(tmpDir)
	if err != nil {
		t.Fatalf("NewBoltStorage failed: %v", err)
	}
	defer storage.Close()
	
	_, err = storage.Get("nonexistent-key")
	if err == nil {
		t.Error("Expected error for nonexistent key")
	}
}

func TestBoltStorage_Delete(t *testing.T) {
	tmpDir := t.TempDir()
	storage, err := NewBoltStorage(tmpDir)
	if err != nil {
		t.Fatalf("NewBoltStorage failed: %v", err)
	}
	defer storage.Close()
	
	key := "test-key"
	value := []byte("test-value")
	
	// Set a value
	err = storage.Set(key, value)
	if err != nil {
		t.Fatalf("Set failed: %v", err)
	}
	
	// Verify it exists
	_, err = storage.Get(key)
	if err != nil {
		t.Fatalf("Get failed: %v", err)
	}
	
	// Delete the value
	err = storage.Delete(key)
	if err != nil {
		t.Fatalf("Delete failed: %v", err)
	}
	
	// Verify it no longer exists
	_, err = storage.Get(key)
	if err == nil {
		t.Error("Expected error for deleted key")
	}
}

func TestBoltStorage_Exists(t *testing.T) {
	tmpDir := t.TempDir()
	storage, err := NewBoltStorage(tmpDir)
	if err != nil {
		t.Fatalf("NewBoltStorage failed: %v", err)
	}
	defer storage.Close()
	
	key := "test-key"
	value := []byte("test-value")
	
	// Test non-existent key
	if storage.Exists(key) {
		t.Error("Expected false for non-existent key")
	}
	
	// Set a value
	err = storage.Set(key, value)
	if err != nil {
		t.Fatalf("Set failed: %v", err)
	}
	
	// Test existing key
	if !storage.Exists(key) {
		t.Error("Expected true for existing key")
	}
}

func TestBoltStorage_List(t *testing.T) {
	tmpDir := t.TempDir()
	storage, err := NewBoltStorage(tmpDir)
	if err != nil {
		t.Fatalf("NewBoltStorage failed: %v", err)
	}
	defer storage.Close()
	
	// Set multiple values with same prefix
	prefix := "test-"
	keys := []string{"test-key1", "test-key2", "test-key3", "other-key"}
	
	for _, key := range keys {
		err = storage.Set(key, []byte("value-"+key))
		if err != nil {
			t.Fatalf("Set failed for key %s: %v", key, err)
		}
	}
	
	// List keys with prefix
	foundKeys, err := storage.List(prefix)
	if err != nil {
		t.Fatalf("List failed: %v", err)
	}
	
	// Should find 3 keys with the prefix
	expectedCount := 3
	if len(foundKeys) != expectedCount {
		t.Errorf("Expected %d keys, got %d", expectedCount, len(foundKeys))
	}
	
	// Verify all found keys have the prefix
	for _, key := range foundKeys {
		if len(key) < len(prefix) || key[:len(prefix)] != prefix {
			t.Errorf("Found key %s does not have prefix %s", key, prefix)
		}
	}
}

func TestBoltStorage_BucketOperations(t *testing.T) {
	tmpDir := t.TempDir()
	storage, err := NewBoltStorage(tmpDir)
	if err != nil {
		t.Fatalf("NewBoltStorage failed: %v", err)
	}
	defer storage.Close()
	
	bucketName := "test-bucket"
	key := "test-key"
	value := []byte("test-value")
	
	// Test SetWithBucket
	err = storage.SetWithBucket(bucketName, key, value)
	if err != nil {
		t.Fatalf("SetWithBucket failed: %v", err)
	}
	
	// Test GetWithBucket
	retrievedValue, err := storage.GetWithBucket(bucketName, key)
	if err != nil {
		t.Fatalf("GetWithBucket failed: %v", err)
	}
	
	if string(retrievedValue) != string(value) {
		t.Errorf("Expected value %s, got %s", string(value), string(retrievedValue))
	}
	
	// Test DeleteWithBucket
	err = storage.DeleteWithBucket(bucketName, key)
	if err != nil {
		t.Fatalf("DeleteWithBucket failed: %v", err)
	}
	
	// Verify deletion
	_, err = storage.GetWithBucket(bucketName, key)
	if err == nil {
		t.Error("Expected error for deleted key")
	}
}

func TestBoltStorage_ListWithBucket(t *testing.T) {
	tmpDir := t.TempDir()
	storage, err := NewBoltStorage(tmpDir)
	if err != nil {
		t.Fatalf("NewBoltStorage failed: %v", err)
	}
	defer storage.Close()
	
	bucketName := "test-bucket"
	prefix := "test-"
	keys := []string{"test-key1", "test-key2", "test-key3", "other-key"}
	
	// Set multiple values in bucket
	for _, key := range keys {
		err = storage.SetWithBucket(bucketName, key, []byte("value-"+key))
		if err != nil {
			t.Fatalf("SetWithBucket failed for key %s: %v", key, err)
		}
	}
	
	// List keys with prefix in bucket
	foundKeys, err := storage.ListWithBucket(bucketName, prefix)
	if err != nil {
		t.Fatalf("ListWithBucket failed: %v", err)
	}
	
	// Should find 3 keys with the prefix
	expectedCount := 3
	if len(foundKeys) != expectedCount {
		t.Errorf("Expected %d keys, got %d", expectedCount, len(foundKeys))
	}
}

func TestBoltStorage_GetAllFromBucket(t *testing.T) {
	tmpDir := t.TempDir()
	storage, err := NewBoltStorage(tmpDir)
	if err != nil {
		t.Fatalf("NewBoltStorage failed: %v", err)
	}
	defer storage.Close()
	
	bucketName := "test-bucket"
	testData := map[string][]byte{
		"key1": []byte("value1"),
		"key2": []byte("value2"),
		"key3": []byte("value3"),
	}
	
	// Set multiple values in bucket
	for key, value := range testData {
		err = storage.SetWithBucket(bucketName, key, value)
		if err != nil {
			t.Fatalf("SetWithBucket failed for key %s: %v", key, err)
		}
	}
	
	// Get all from bucket
	allData, err := storage.GetAllFromBucket(bucketName)
	if err != nil {
		t.Fatalf("GetAllFromBucket failed: %v", err)
	}
	
	// Verify all data is returned
	if len(allData) != len(testData) {
		t.Errorf("Expected %d items, got %d", len(testData), len(allData))
	}
	
	for key, expectedValue := range testData {
		actualValue, exists := allData[key]
		if !exists {
			t.Errorf("Key %s not found in results", key)
			continue
		}
		
		if string(actualValue) != string(expectedValue) {
			t.Errorf("Expected value %s for key %s, got %s", string(expectedValue), key, string(actualValue))
		}
	}
}

func TestBoltStorage_ClearBucket(t *testing.T) {
	tmpDir := t.TempDir()
	storage, err := NewBoltStorage(tmpDir)
	if err != nil {
		t.Fatalf("NewBoltStorage failed: %v", err)
	}
	defer storage.Close()
	
	bucketName := "test-bucket"
	keys := []string{"key1", "key2", "key3"}
	
	// Set multiple values in bucket
	for _, key := range keys {
		err = storage.SetWithBucket(bucketName, key, []byte("value-"+key))
		if err != nil {
			t.Fatalf("SetWithBucket failed for key %s: %v", key, err)
		}
	}
	
	// Verify data exists
	allData, err := storage.GetAllFromBucket(bucketName)
	if err != nil {
		t.Fatalf("GetAllFromBucket failed: %v", err)
	}
	
	if len(allData) != len(keys) {
		t.Errorf("Expected %d items before clear, got %d", len(keys), len(allData))
	}
	
	// Clear bucket
	err = storage.ClearBucket(bucketName)
	if err != nil {
		t.Fatalf("ClearBucket failed: %v", err)
	}
	
	// Verify bucket is empty
	allData, err = storage.GetAllFromBucket(bucketName)
	if err != nil {
		t.Fatalf("GetAllFromBucket failed after clear: %v", err)
	}
	
	if len(allData) != 0 {
		t.Errorf("Expected 0 items after clear, got %d", len(allData))
	}
}

func TestBoltStorage_Stats(t *testing.T) {
	tmpDir := t.TempDir()
	storage, err := NewBoltStorage(tmpDir)
	if err != nil {
		t.Fatalf("NewBoltStorage failed: %v", err)
	}
	defer storage.Close()
	
	stats := storage.Stats()
	
	if stats == nil {
		t.Fatal("Expected non-nil stats")
	}
	
	// Check that stats contains expected fields
	expectedFields := []string{
		"free_page_n",
		"pending_page_n",
		"free_alloc",
		"free_list_inuse",
		"tx_n",
		"tx_stats",
		"open_tx_n",
	}
	
	for _, field := range expectedFields {
		if _, exists := stats[field]; !exists {
			t.Errorf("Expected stats field %s not found", field)
		}
	}
}

func TestBoltStorage_Backup(t *testing.T) {
	tmpDir := t.TempDir()
	storage, err := NewBoltStorage(tmpDir)
	if err != nil {
		t.Fatalf("NewBoltStorage failed: %v", err)
	}
	defer storage.Close()
	
	// Add some data
	err = storage.Set("test-key", []byte("test-value"))
	if err != nil {
		t.Fatalf("Set failed: %v", err)
	}
	
	// Create backup
	backupPath := filepath.Join(tmpDir, "backup.db")
	err = storage.Backup(backupPath)
	if err != nil {
		t.Fatalf("Backup failed: %v", err)
	}
	
	// Verify backup file exists
	if _, err := os.Stat(backupPath); os.IsNotExist(err) {
		t.Error("Backup file was not created")
	}
	
	// Verify backup file has content
	info, err := os.Stat(backupPath)
	if err != nil {
		t.Fatalf("Failed to stat backup file: %v", err)
	}
	
	if info.Size() == 0 {
		t.Error("Backup file is empty")
	}
}

func TestBoltStorage_Close(t *testing.T) {
	tmpDir := t.TempDir()
	storage, err := NewBoltStorage(tmpDir)
	if err != nil {
		t.Fatalf("NewBoltStorage failed: %v", err)
	}
	
	// Test that storage works before closing
	err = storage.Set("test-key", []byte("test-value"))
	if err != nil {
		t.Fatalf("Set failed before close: %v", err)
	}
	
	// Close storage
	err = storage.Close()
	if err != nil {
		t.Fatalf("Close failed: %v", err)
	}
	
	// Test that operations fail after closing
	err = storage.Set("test-key2", []byte("test-value2"))
	if err == nil {
		t.Error("Expected error after closing storage")
	}
}

func TestBoltStorage_ConcurrentAccess(t *testing.T) {
	tmpDir := t.TempDir()
	storage, err := NewBoltStorage(tmpDir)
	if err != nil {
		t.Fatalf("NewBoltStorage failed: %v", err)
	}
	defer storage.Close()
	
	// Test concurrent writes
	done := make(chan bool)
	numGoroutines := 10
	
	for i := 0; i < numGoroutines; i++ {
		go func(id int) {
			defer func() { done <- true }()
			
			key := fmt.Sprintf("key-%d", id)
			value := []byte(fmt.Sprintf("value-%d", id))
			
			err := storage.Set(key, value)
			if err != nil {
				t.Errorf("Concurrent Set failed for key %s: %v", key, err)
				return
			}
			
			retrievedValue, err := storage.Get(key)
			if err != nil {
				t.Errorf("Concurrent Get failed for key %s: %v", key, err)
				return
			}
			
			if string(retrievedValue) != string(value) {
				t.Errorf("Concurrent access: expected value %s, got %s", string(value), string(retrievedValue))
			}
		}(i)
	}
	
	// Wait for all goroutines to complete
	for i := 0; i < numGoroutines; i++ {
		<-done
	}
}

func TestBoltStorage_InitBuckets(t *testing.T) {
	tmpDir := t.TempDir()
	storage, err := NewBoltStorage(tmpDir)
	if err != nil {
		t.Fatalf("NewBoltStorage failed: %v", err)
	}
	defer storage.Close()
	
	// Test that default buckets were created
	buckets := []string{"waddlebot", "sessions", "modules", "config"}
	
	for _, bucket := range buckets {
		// Try to set a value in each bucket
		err = storage.SetWithBucket(bucket, "test-key", []byte("test-value"))
		if err != nil {
			t.Errorf("Failed to set value in bucket %s: %v", bucket, err)
		}
	}
}

