"""
Rate limiting middleware for FastAPI
Prevents API abuse by limiting requests per IP address
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Tuple
import asyncio


class RateLimiter:
    """
    Rate limiter using sliding window algorithm
    Tracks requests per IP address and enforces limits
    """
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        requests_per_day: int = 10000
    ):
        """
        Initialize rate limiter with configurable limits
        
        Args:
            requests_per_minute: Max requests per minute per IP
            requests_per_hour: Max requests per hour per IP
            requests_per_day: Max requests per day per IP
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day
        
        # Store request timestamps per IP
        # Format: {ip_address: [timestamp1, timestamp2, ...]}
        self.request_history: Dict[str, list] = defaultdict(list)
        
        # Lock for thread-safe operations
        self.lock = asyncio.Lock()
        
        # Start cleanup task
        self.cleanup_task = None
    
    async def start_cleanup(self):
        """Start background task to clean old entries"""
        while True:
            await asyncio.sleep(3600)  # Run every hour
            await self.cleanup_old_entries()
    
    async def cleanup_old_entries(self):
        """Remove entries older than 24 hours"""
        async with self.lock:
            cutoff = datetime.now() - timedelta(days=1)
            for ip in list(self.request_history.keys()):
                self.request_history[ip] = [
                    ts for ts in self.request_history[ip]
                    if ts > cutoff
                ]
                # Remove IP if no recent requests
                if not self.request_history[ip]:
                    del self.request_history[ip]
    
    def get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request
        Handles X-Forwarded-For header for proxied requests
        """
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    async def check_rate_limit(self, request: Request) -> Tuple[bool, str, int]:
        """
        Check if request should be rate limited
        
        Returns:
            Tuple of (is_allowed, limit_type, retry_after_seconds)
        """
        ip = self.get_client_ip(request)
        now = datetime.now()
        
        async with self.lock:
            # Add current request
            self.request_history[ip].append(now)
            
            # Check minute limit
            minute_ago = now - timedelta(minutes=1)
            recent_minute = [ts for ts in self.request_history[ip] if ts > minute_ago]
            if len(recent_minute) > self.requests_per_minute:
                return False, "minute", 60
            
            # Check hour limit
            hour_ago = now - timedelta(hours=1)
            recent_hour = [ts for ts in self.request_history[ip] if ts > hour_ago]
            if len(recent_hour) > self.requests_per_hour:
                return False, "hour", 3600
            
            # Check day limit
            day_ago = now - timedelta(days=1)
            recent_day = [ts for ts in self.request_history[ip] if ts > day_ago]
            if len(recent_day) > self.requests_per_day:
                return False, "day", 86400
            
            return True, "", 0
    
    async def __call__(self, request: Request, call_next):
        """
        Middleware function to check rate limits
        """
        # Skip rate limiting for health check
        if request.url.path == "/health":
            return await call_next(request)
        
        # Check rate limit
        is_allowed, limit_type, retry_after = await self.check_rate_limit(request)
        
        if not is_allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "limit_type": limit_type,
                    "retry_after": retry_after,
                    "message": f"Too many requests. Please try again in {retry_after} seconds."
                },
                headers={"Retry-After": str(retry_after)}
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        
        # Add informational headers
        ip = self.get_client_ip(request)
        minute_ago = datetime.now() - timedelta(minutes=1)
        recent_minute = len([
            ts for ts in self.request_history[ip]
            if ts > minute_ago
        ])
        
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.requests_per_minute - recent_minute)
        )
        response.headers["X-RateLimit-Reset"] = str(int(
            (datetime.now() + timedelta(minutes=1)).timestamp()
        ))
        
        return response


# Create global rate limiter instance
rate_limiter = RateLimiter(
    requests_per_minute=60,   # 60 requests per minute
    requests_per_hour=1000,   # 1000 requests per hour
    requests_per_day=10000    # 10000 requests per day
)
