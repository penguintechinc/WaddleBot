"""
Rate limiting service for command execution
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Tuple
from collections import defaultdict, deque

from ..models import db

class RateLimiter:
    """Thread-safe rate limiter with sliding window"""
    
    def __init__(self, default_limit: int = 60, window_seconds: int = 60):
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        
        # In-memory sliding window counters
        self._windows: Dict[str, deque] = defaultdict(deque)
        self._lock = threading.RLock()
        
        # Cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_old_windows, daemon=True)
        self._cleanup_thread.start()
    
    async def check_rate_limit(self, command_id: int, entity_id: str, user_id: str, limit: int) -> bool:
        """Check if request is within rate limit"""
        key = f"{command_id}:{entity_id}:{user_id}"
        current_time = time.time()
        
        with self._lock:
            # Get or create window for this key
            window = self._windows[key]
            
            # Remove old entries outside the time window
            cutoff_time = current_time - self.window_seconds
            while window and window[0] <= cutoff_time:
                window.popleft()
            
            # Check if we're within the limit
            if len(window) >= limit:
                # Log rate limit hit to database (async)
                self._log_rate_limit_hit(command_id, entity_id, user_id)
                return False
            
            # Add current request to window
            window.append(current_time)
            return True
    
    def _log_rate_limit_hit(self, command_id: int, entity_id: str, user_id: str):
        """Log rate limit hit to database"""
        try:
            # Get entity record
            entity_record = db(db.entities.entity_id == entity_id).select().first()
            if not entity_record:
                return
            
            # Find existing rate limit record for current window
            window_start = datetime.utcnow().replace(second=0, microsecond=0)
            
            rate_limit_record = db(
                (db.rate_limits.command_id == command_id) &
                (db.rate_limits.entity_id == entity_record.id) &
                (db.rate_limits.user_id == user_id) &
                (db.rate_limits.window_start == window_start)
            ).select().first()
            
            if rate_limit_record:
                # Update existing record
                db.rate_limits[rate_limit_record.id] = dict(
                    request_count=rate_limit_record.request_count + 1
                )
            else:
                # Create new record
                db.rate_limits.insert(
                    command_id=command_id,
                    entity_id=entity_record.id,
                    user_id=user_id,
                    window_start=window_start,
                    request_count=1
                )
            
            db.commit()
            
        except Exception as e:
            # Don't let rate limit logging failures affect the main flow
            pass
    
    def _cleanup_old_windows(self):
        """Background cleanup of old rate limit windows"""
        while True:
            try:
                current_time = time.time()
                cutoff_time = current_time - (self.window_seconds * 2)  # Keep extra buffer
                
                with self._lock:
                    keys_to_remove = []
                    
                    for key, window in self._windows.items():
                        # Remove old entries from each window
                        while window and window[0] <= cutoff_time:
                            window.popleft()
                        
                        # Remove empty windows
                        if not window:
                            keys_to_remove.append(key)
                    
                    for key in keys_to_remove:
                        del self._windows[key]
                
                # Sleep for 60 seconds before next cleanup
                time.sleep(60)
                
            except Exception:
                # Continue cleanup even if error occurs
                time.sleep(60)
    
    def get_stats(self) -> Dict[str, int]:
        """Get rate limiter statistics"""
        with self._lock:
            total_windows = len(self._windows)
            total_requests = sum(len(window) for window in self._windows.values())
            
            return {
                "active_windows": total_windows,
                "tracked_requests": total_requests
            }
    
    def reset_user_limits(self, user_id: str):
        """Reset rate limits for a specific user (admin function)"""
        with self._lock:
            keys_to_remove = [key for key in self._windows.keys() if key.endswith(f":{user_id}")]
            for key in keys_to_remove:
                del self._windows[key]