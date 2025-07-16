package storage

import (
	"fmt"
	"path/filepath"
	"time"

	"go.etcd.io/bbolt"
)

const (
	// Default bucket for general storage
	defaultBucket = "waddlebot"
	
	// Additional buckets for specific data types
	sessionsBucket = "sessions"
	modulesBucket  = "modules"
	configBucket   = "config"
)

// BoltStorage implements the Storage interface using BoltDB
type BoltStorage struct {
	db *bbolt.DB
}

// NewBoltStorage creates a new BoltDB storage instance
func NewBoltStorage(dataDir string) (*BoltStorage, error) {
	// Create the database file path
	dbPath := filepath.Join(dataDir, "waddlebot-bridge.db")
	
	// Open the database
	db, err := bbolt.Open(dbPath, 0600, &bbolt.Options{
		Timeout: 1 * time.Second,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to open bolt database: %w", err)
	}

	storage := &BoltStorage{db: db}

	// Initialize buckets
	if err := storage.initBuckets(); err != nil {
		db.Close()
		return nil, fmt.Errorf("failed to initialize buckets: %w", err)
	}

	return storage, nil
}

// initBuckets creates the required buckets if they don't exist
func (s *BoltStorage) initBuckets() error {
	return s.db.Update(func(tx *bbolt.Tx) error {
		buckets := []string{defaultBucket, sessionsBucket, modulesBucket, configBucket}
		
		for _, bucket := range buckets {
			if _, err := tx.CreateBucketIfNotExists([]byte(bucket)); err != nil {
				return fmt.Errorf("failed to create bucket %s: %w", bucket, err)
			}
		}
		
		return nil
	})
}

// Set stores a key-value pair
func (s *BoltStorage) Set(key string, value []byte) error {
	return s.db.Update(func(tx *bbolt.Tx) error {
		bucket := tx.Bucket([]byte(defaultBucket))
		if bucket == nil {
			return fmt.Errorf("bucket %s not found", defaultBucket)
		}
		
		return bucket.Put([]byte(key), value)
	})
}

// Get retrieves a value by key
func (s *BoltStorage) Get(key string) ([]byte, error) {
	var value []byte
	
	err := s.db.View(func(tx *bbolt.Tx) error {
		bucket := tx.Bucket([]byte(defaultBucket))
		if bucket == nil {
			return fmt.Errorf("bucket %s not found", defaultBucket)
		}
		
		data := bucket.Get([]byte(key))
		if data == nil {
			return fmt.Errorf("key %s not found", key)
		}
		
		// Make a copy of the data since it's only valid during the transaction
		value = make([]byte, len(data))
		copy(value, data)
		
		return nil
	})
	
	return value, err
}

// Delete removes a key
func (s *BoltStorage) Delete(key string) error {
	return s.db.Update(func(tx *bbolt.Tx) error {
		bucket := tx.Bucket([]byte(defaultBucket))
		if bucket == nil {
			return fmt.Errorf("bucket %s not found", defaultBucket)
		}
		
		return bucket.Delete([]byte(key))
	})
}

// Exists checks if a key exists
func (s *BoltStorage) Exists(key string) bool {
	err := s.db.View(func(tx *bbolt.Tx) error {
		bucket := tx.Bucket([]byte(defaultBucket))
		if bucket == nil {
			return fmt.Errorf("bucket %s not found", defaultBucket)
		}
		
		data := bucket.Get([]byte(key))
		if data == nil {
			return fmt.Errorf("key not found")
		}
		
		return nil
	})
	
	return err == nil
}

// List returns all keys with a given prefix
func (s *BoltStorage) List(prefix string) ([]string, error) {
	var keys []string
	
	err := s.db.View(func(tx *bbolt.Tx) error {
		bucket := tx.Bucket([]byte(defaultBucket))
		if bucket == nil {
			return fmt.Errorf("bucket %s not found", defaultBucket)
		}
		
		cursor := bucket.Cursor()
		prefixBytes := []byte(prefix)
		
		for k, _ := cursor.Seek(prefixBytes); k != nil && len(k) >= len(prefixBytes); k, _ = cursor.Next() {
			if len(k) >= len(prefixBytes) && string(k[:len(prefixBytes)]) == prefix {
				keys = append(keys, string(k))
			} else {
				break
			}
		}
		
		return nil
	})
	
	return keys, err
}

// SetWithBucket stores a key-value pair in a specific bucket
func (s *BoltStorage) SetWithBucket(bucketName, key string, value []byte) error {
	return s.db.Update(func(tx *bbolt.Tx) error {
		bucket := tx.Bucket([]byte(bucketName))
		if bucket == nil {
			return fmt.Errorf("bucket %s not found", bucketName)
		}
		
		return bucket.Put([]byte(key), value)
	})
}

// GetWithBucket retrieves a value by key from a specific bucket
func (s *BoltStorage) GetWithBucket(bucketName, key string) ([]byte, error) {
	var value []byte
	
	err := s.db.View(func(tx *bbolt.Tx) error {
		bucket := tx.Bucket([]byte(bucketName))
		if bucket == nil {
			return fmt.Errorf("bucket %s not found", bucketName)
		}
		
		data := bucket.Get([]byte(key))
		if data == nil {
			return fmt.Errorf("key %s not found", key)
		}
		
		value = make([]byte, len(data))
		copy(value, data)
		
		return nil
	})
	
	return value, err
}

// DeleteWithBucket removes a key from a specific bucket
func (s *BoltStorage) DeleteWithBucket(bucketName, key string) error {
	return s.db.Update(func(tx *bbolt.Tx) error {
		bucket := tx.Bucket([]byte(bucketName))
		if bucket == nil {
			return fmt.Errorf("bucket %s not found", bucketName)
		}
		
		return bucket.Delete([]byte(key))
	})
}

// ListWithBucket returns all keys with a given prefix from a specific bucket
func (s *BoltStorage) ListWithBucket(bucketName, prefix string) ([]string, error) {
	var keys []string
	
	err := s.db.View(func(tx *bbolt.Tx) error {
		bucket := tx.Bucket([]byte(bucketName))
		if bucket == nil {
			return fmt.Errorf("bucket %s not found", bucketName)
		}
		
		cursor := bucket.Cursor()
		prefixBytes := []byte(prefix)
		
		for k, _ := cursor.Seek(prefixBytes); k != nil && len(k) >= len(prefixBytes); k, _ = cursor.Next() {
			if len(k) >= len(prefixBytes) && string(k[:len(prefixBytes)]) == prefix {
				keys = append(keys, string(k))
			} else {
				break
			}
		}
		
		return nil
	})
	
	return keys, err
}

// GetAllFromBucket returns all key-value pairs from a specific bucket
func (s *BoltStorage) GetAllFromBucket(bucketName string) (map[string][]byte, error) {
	data := make(map[string][]byte)
	
	err := s.db.View(func(tx *bbolt.Tx) error {
		bucket := tx.Bucket([]byte(bucketName))
		if bucket == nil {
			return fmt.Errorf("bucket %s not found", bucketName)
		}
		
		return bucket.ForEach(func(k, v []byte) error {
			// Make copies of the key and value
			key := make([]byte, len(k))
			value := make([]byte, len(v))
			copy(key, k)
			copy(value, v)
			
			data[string(key)] = value
			return nil
		})
	})
	
	return data, err
}

// ClearBucket removes all data from a specific bucket
func (s *BoltStorage) ClearBucket(bucketName string) error {
	return s.db.Update(func(tx *bbolt.Tx) error {
		// Delete the bucket
		if err := tx.DeleteBucket([]byte(bucketName)); err != nil {
			return fmt.Errorf("failed to delete bucket %s: %w", bucketName, err)
		}
		
		// Recreate the bucket
		if _, err := tx.CreateBucket([]byte(bucketName)); err != nil {
			return fmt.Errorf("failed to recreate bucket %s: %w", bucketName, err)
		}
		
		return nil
	})
}

// Close closes the database connection
func (s *BoltStorage) Close() error {
	return s.db.Close()
}

// Backup creates a backup of the database
func (s *BoltStorage) Backup(backupPath string) error {
	return s.db.View(func(tx *bbolt.Tx) error {
		return tx.CopyFile(backupPath, 0600)
	})
}

// Stats returns database statistics
func (s *BoltStorage) Stats() map[string]interface{} {
	stats := s.db.Stats()
	
	return map[string]interface{}{
		"free_page_n":       stats.FreePageN,
		"pending_page_n":    stats.PendingPageN,
		"free_alloc":        stats.FreeAlloc,
		"free_list_inuse":   stats.FreelistInuse,
		"tx_n":              stats.TxN,
		"tx_stats":          stats.TxStats,
		"open_tx_n":         stats.OpenTxN,
	}
}