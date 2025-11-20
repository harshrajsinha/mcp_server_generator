"""
Rate Limiting Module

Implements request rate limiting to prevent abuse and ensure fair usage.
"""

import time
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class RateLimit:
    """Rate limit configuration"""
    max_requests: int
    window_seconds: int
    burst_limit: Optional[int] = None


class RateLimiter:
    """
    Token bucket rate limiter with per-connection tracking
    
    Implements sliding window rate limiting with burst capability.
    """
    
    def __init__(self, 
                 max_requests: int = 100, 
                 window_minutes: int = 60,
                 burst_limit: Optional[int] = None):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests allowed in window
            window_minutes: Time window in minutes
            burst_limit: Optional burst limit (defaults to max_requests // 4)
        """
        self.logger = logging.getLogger(__name__)
        self.max_requests = max_requests
        self.window_seconds = window_minutes * 60
        self.burst_limit = burst_limit or max_requests // 4
        
        # Track requests per connection using sliding window
        self.request_timestamps: Dict[str, deque] = defaultdict(lambda: deque())
        self.burst_tokens: Dict[str, int] = defaultdict(lambda: self.burst_limit)
        self.last_refill: Dict[str, float] = defaultdict(lambda: time.time())
        
        self.logger.info(f"Rate limiter initialized: {max_requests} requests per {window_minutes} minutes")
    
    def check_rate_limit(self, connection_id: str, operation: str = "query") -> Tuple[bool, str]:
        """
        Check if request is within rate limit
        
        Args:
            connection_id: Connection identifier
            operation: Operation type (for logging)
            
        Returns:
            Tuple of (is_allowed, message)
        """
        current_time = time.time()
        
        # Clean old timestamps outside the window
        cutoff_time = current_time - self.window_seconds
        connection_timestamps = self.request_timestamps[connection_id]
        
        # Remove timestamps outside the window
        while connection_timestamps and connection_timestamps[0] <= cutoff_time:
            connection_timestamps.popleft()
        
        # Check burst limit first (for immediate requests)
        if self.burst_limit > 0:
            self._refill_burst_tokens(connection_id, current_time)
            
            if self.burst_tokens[connection_id] > 0:
                # Use burst token
                self.burst_tokens[connection_id] -= 1
                connection_timestamps.append(current_time)
                
                remaining_burst = self.burst_tokens[connection_id]
                remaining_window = self.max_requests - len(connection_timestamps)
                
                return True, f"Request allowed (burst: {remaining_burst}, window: {remaining_window})"
        
        # Check window limit
        if len(connection_timestamps) >= self.max_requests:
            next_available = connection_timestamps[0] + self.window_seconds
            wait_seconds = int(next_available - current_time)
            
            self.logger.warning(
                f"Rate limit exceeded for {connection_id}: {len(connection_timestamps)}/{self.max_requests} requests"
            )
            
            return False, f"Rate limit exceeded. Try again in {wait_seconds} seconds"
        
        # Add current request
        connection_timestamps.append(current_time)
        
        remaining = self.max_requests - len(connection_timestamps)
        
        self.logger.debug(f"Rate limit check passed for {connection_id}: {remaining} requests remaining")
        
        return True, f"Request allowed. {remaining} requests remaining in window"
    
    def _refill_burst_tokens(self, connection_id: str, current_time: float):
        """
        Refill burst tokens based on elapsed time
        
        Args:
            connection_id: Connection identifier
            current_time: Current timestamp
        """
        elapsed = current_time - self.last_refill[connection_id]
        
        # Refill rate: restore one burst token per 60 seconds
        refill_rate = 1 / 60  # tokens per second
        tokens_to_add = int(elapsed * refill_rate)
        
        if tokens_to_add > 0:
            self.burst_tokens[connection_id] = min(
                self.burst_limit,
                self.burst_tokens[connection_id] + tokens_to_add
            )
            self.last_refill[connection_id] = current_time
    
    def get_rate_limit_status(self, connection_id: str) -> Dict[str, any]:
        """
        Get current rate limit status for a connection
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            Dictionary with rate limit status information
        """
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        
        connection_timestamps = self.request_timestamps[connection_id]
        
        # Count requests in current window
        active_requests = sum(1 for ts in connection_timestamps if ts > cutoff_time)
        
        # Calculate time until next slot is available
        next_available = None
        if connection_timestamps and active_requests >= self.max_requests:
            next_available = connection_timestamps[0] + self.window_seconds
        
        return {
            "connection_id": connection_id,
            "requests_in_window": active_requests,
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "remaining_requests": max(0, self.max_requests - active_requests),
            "burst_tokens": self.burst_tokens.get(connection_id, 0),
            "next_available_at": next_available,
            "seconds_until_next": max(0, int(next_available - current_time)) if next_available else 0
        }
    
    def reset_rate_limit(self, connection_id: str):
        """
        Reset rate limit for a specific connection
        
        Args:
            connection_id: Connection identifier to reset
        """
        if connection_id in self.request_timestamps:
            del self.request_timestamps[connection_id]
        
        if connection_id in self.burst_tokens:
            self.burst_tokens[connection_id] = self.burst_limit
        
        if connection_id in self.last_refill:
            self.last_refill[connection_id] = time.time()
        
        self.logger.info(f"Rate limit reset for connection: {connection_id}")
    
    def cleanup_old_entries(self):
        """
        Cleanup old entries to prevent memory leaks
        """
        current_time = time.time()
        cutoff_time = current_time - (self.window_seconds * 2)  # Keep extra buffer
        
        connections_to_remove = []
        
        for connection_id, timestamps in self.request_timestamps.items():
            # Remove old timestamps
            while timestamps and timestamps[0] <= cutoff_time:
                timestamps.popleft()
            
            # If no recent activity, mark for cleanup
            if not timestamps:
                connections_to_remove.append(connection_id)
        
        # Clean up inactive connections
        for connection_id in connections_to_remove:
            del self.request_timestamps[connection_id]
            if connection_id in self.burst_tokens:
                del self.burst_tokens[connection_id]
            if connection_id in self.last_refill:
                del self.last_refill[connection_id]
        
        if connections_to_remove:
            self.logger.debug(f"Cleaned up {len(connections_to_remove)} inactive connections")


class GlobalRateLimiter:
    """
    Global rate limiter for the entire server
    """
    
    def __init__(self, max_requests_per_minute: int = 1000):
        self.max_requests = max_requests_per_minute
        self.window_seconds = 60
        self.request_timestamps = deque()
        self.logger = logging.getLogger(__name__)
    
    def check_global_rate_limit(self) -> Tuple[bool, str]:
        """
        Check global server rate limit
        
        Returns:
            Tuple of (is_allowed, message)
        """
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        
        # Remove old timestamps
        while self.request_timestamps and self.request_timestamps[0] <= cutoff_time:
            self.request_timestamps.popleft()
        
        if len(self.request_timestamps) >= self.max_requests:
            return False, f"Global rate limit exceeded: {self.max_requests} requests per minute"
        
        self.request_timestamps.append(current_time)
        remaining = self.max_requests - len(self.request_timestamps)
        
        return True, f"Global rate limit OK. {remaining} requests remaining"