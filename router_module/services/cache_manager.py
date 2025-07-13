"""
High-performance caching manager for command and entity lookups
"""

import time
import threading
from typing import Any, Optional, Dict
from dataclasses import dataclass

@dataclass
class CacheEntry:
    """Cache entry with TTL"""
    value: Any
    expires_at: float

class CacheManager:
    """Thread-safe in-memory cache with TTL support"""
    
    def __init__(self, command_ttl: int = 300, entity_ttl: int = 600):
        self.command_ttl = command_ttl
        self.entity_ttl = entity_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_expired, daemon=True)
        self._cleanup_thread.start()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            
            if time.time() > entry.expires_at:
                del self._cache[key]
                return None
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL"""
        if ttl is None:
            # Determine TTL based on key prefix
            if key.startswith("command:"):
                ttl = self.command_ttl
            elif key.startswith("entity:") or key.startswith("permission:"):
                ttl = self.entity_ttl
            else:
                ttl = 300  # Default 5 minutes
        
        expires_at = time.time() + ttl
        
        with self._lock:
            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        with self._lock:
            return len(self._cache)
    
    def _cleanup_expired(self) -> None:
        """Background thread to clean up expired entries"""
        while True:
            try:
                current_time = time.time()
                expired_keys = []
                
                with self._lock:
                    for key, entry in self._cache.items():
                        if current_time > entry.expires_at:
                            expired_keys.append(key)
                    
                    for key in expired_keys:
                        del self._cache[key]
                
                # Sleep for 30 seconds before next cleanup
                time.sleep(30)
                
            except Exception:
                # Continue cleanup loop even if error occurs
                time.sleep(30)
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        with self._lock:
            total_entries = len(self._cache)
            expired_entries = 0
            current_time = time.time()
            
            for entry in self._cache.values():
                if current_time > entry.expires_at:
                    expired_entries += 1
            
            return {
                "total_entries": total_entries,
                "expired_entries": expired_entries,
                "active_entries": total_entries - expired_entries
            }