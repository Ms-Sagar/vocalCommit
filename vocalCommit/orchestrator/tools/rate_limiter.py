#!/usr/bin/env python3
"""
Rate Limiter for Gemini API calls to stay under 5 requests per minute
"""

import time
import threading
from collections import deque
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter to ensure we don't exceed API limits."""
    
    def __init__(self, max_requests: int = 5, time_window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds (default: 60 seconds = 1 minute)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = threading.Lock()
    
    def wait_if_needed(self) -> Optional[float]:
        """
        Check if we need to wait before making another request.
        If needed, wait until we can make the request.
        
        Returns:
            float: Number of seconds waited (0 if no wait was needed)
        """
        with self.lock:
            current_time = time.time()
            
            # Remove requests older than the time window
            while self.requests and current_time - self.requests[0] >= self.time_window:
                self.requests.popleft()
            
            # Check if we're at the limit
            if len(self.requests) >= self.max_requests:
                # Calculate how long to wait
                oldest_request = self.requests[0]
                wait_time = self.time_window - (current_time - oldest_request)
                
                if wait_time > 0:
                    logger.info(f"Rate limit reached. Waiting {wait_time:.1f} seconds before next Gemini API call")
                    time.sleep(wait_time)
                    return wait_time
            
            # Record this request
            self.requests.append(current_time)
            return 0.0
    
    def get_remaining_requests(self) -> int:
        """Get number of remaining requests in current window."""
        with self.lock:
            current_time = time.time()
            
            # Remove requests older than the time window
            while self.requests and current_time - self.requests[0] >= self.time_window:
                self.requests.popleft()
            
            return max(0, self.max_requests - len(self.requests))
    
    def get_reset_time(self) -> Optional[float]:
        """Get time until the rate limit resets (oldest request expires)."""
        with self.lock:
            if not self.requests:
                return None
            
            current_time = time.time()
            oldest_request = self.requests[0]
            reset_time = self.time_window - (current_time - oldest_request)
            
            return max(0, reset_time)

# Global rate limiter instance for Gemini API
# 5 requests per minute as per Gemini API limits
gemini_rate_limiter = RateLimiter(max_requests=5, time_window=60)

def wait_for_gemini_api():
    """
    Wait if needed before making a Gemini API call.
    Call this before every Gemini API request.
    
    Returns:
        float: Number of seconds waited
    """
    return gemini_rate_limiter.wait_if_needed()

def get_gemini_api_status():
    """
    Get current status of Gemini API rate limiting.
    
    Returns:
        dict: Status information
    """
    remaining = gemini_rate_limiter.get_remaining_requests()
    reset_time = gemini_rate_limiter.get_reset_time()
    
    return {
        'remaining_requests': remaining,
        'reset_in_seconds': reset_time,
        'max_requests_per_minute': gemini_rate_limiter.max_requests
    }