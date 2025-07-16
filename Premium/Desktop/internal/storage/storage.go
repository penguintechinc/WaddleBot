package storage

// Storage defines the interface for data storage operations
type Storage interface {
	// Basic operations
	Set(key string, value []byte) error
	Get(key string) ([]byte, error)
	Delete(key string) error
	Exists(key string) bool
	List(prefix string) ([]string, error)
	
	// Bucket operations
	SetWithBucket(bucketName, key string, value []byte) error
	GetWithBucket(bucketName, key string) ([]byte, error)
	DeleteWithBucket(bucketName, key string) error
	ListWithBucket(bucketName, prefix string) ([]string, error)
	GetAllFromBucket(bucketName string) (map[string][]byte, error)
	ClearBucket(bucketName string) error
	
	// Utility operations
	Close() error
	Backup(backupPath string) error
	Stats() map[string]interface{}
}