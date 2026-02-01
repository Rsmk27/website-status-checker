
import asyncio
import httpx
from datetime import datetime
from typing import List, Dict, Callable
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Website:
    def __init__(self, url: str):
        self.url = url
        self.status = "UNKNOWN"
        self.response_time = 0
        self.last_checked = None
        self.is_up = False
        # New features
        self.total_checks = 0
        self.successful_checks = 0
        self.status_history = []  # List of status change events
        self.response_times = []  # Track last 100 response times
        self.ssl_expiry_date = None
        self.created_at = datetime.now()

    def calculate_uptime(self):
        """Calculate uptime percentage"""
        if self.total_checks == 0:
            return 0.0
        return (self.successful_checks / self.total_checks) * 100

    def add_check_result(self, is_success: bool, response_time: int):
        """Record a check result"""
        self.total_checks += 1
        if is_success:
            self.successful_checks += 1
        
        # Keep only last 100 response times
        if response_time > 0:
            self.response_times.append(response_time)
            if len(self.response_times) > 100:
                self.response_times.pop(0)

    def add_status_change(self, old_status: str, new_status: str):
        """Log a status change event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "old_status": old_status,
            "new_status": new_status
        }
        self.status_history.append(event)
        # Keep only last 50 events
        if len(self.status_history) > 50:
            self.status_history.pop(0)

    def get_average_response_time(self):
        """Calculate average response time from recent checks"""
        if not self.response_times:
            return 0
        return sum(self.response_times) // len(self.response_times)

    def to_dict(self):
        return {
            "url": self.url,
            "status": self.status,
            "response_time": self.response_time,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "is_up": self.is_up,
            "uptime_percentage": round(self.calculate_uptime(), 2),
            "total_checks": self.total_checks,
            "avg_response_time": self.get_average_response_time(),
            "status_history": self.status_history[-10:],  # Last 10 events
            "ssl_expiry_date": self.ssl_expiry_date.isoformat() if self.ssl_expiry_date else None,
            "created_at": self.created_at.isoformat()
        }

class StatusManager:
    def __init__(self):
        self.websites: Dict[str, Website] = {}
        self.listeners: List[Callable] = []

    def add_website(self, url: str):
        if url not in self.websites:
            self.websites[url] = Website(url)
            logger.info(f"Added website: {url}")
            return True
        return False

    def remove_website(self, url: str):
        if url in self.websites:
            del self.websites[url]
            logger.info(f"Removed website: {url}")
            return True
        return False

    def get_all_websites(self):
        return [site.to_dict() for site in self.websites.values()]

    async def check_website(self, website: Website):
        old_status = website.status
        old_is_up = website.is_up
        
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                start_time = datetime.now()
                response = await client.get(website.url)
                end_time = datetime.now()
                
                duration = (end_time - start_time).total_seconds() * 1000
                website.response_time = int(duration)
                website.last_checked = end_time
                
                if 200 <= response.status_code < 400:
                    website.status = f"{response.status_code} OK"
                    website.is_up = True
                    website.add_check_result(True, website.response_time)
                else:
                    website.status = f"HTTP {response.status_code}"
                    website.is_up = False
                    website.add_check_result(False, website.response_time)
                
                # Check SSL certificate expiry if HTTPS
                if website.url.startswith("https://"):
                    try:
                        # Get SSL info from response
                        # Note: httpx doesn't expose SSL cert directly, would need separate SSL check
                        pass
                    except:
                        pass
                    
        except httpx.RequestError as e:
            website.status = "DOWN"
            website.is_up = False
            website.response_time = 0
            website.last_checked = datetime.now()
            website.add_check_result(False, 0)
            logger.error(f"Error checking {website.url}: {e}")
        except Exception as e:
            website.status = "ERROR"
            website.is_up = False
            website.response_time = 0
            website.last_checked = datetime.now()
            website.add_check_result(False, 0)
            logger.error(f"Unexpected error checking {website.url}: {e}")
        
        # Log status changes
        if old_status != website.status or old_is_up != website.is_up:
            website.add_status_change(old_status, website.status)
            logger.info(f"Status change for {website.url}: {old_status} -> {website.status}")

    async def monitor_loop(self):
        logger.info("Starting monitor loop...")
        while True:
            tasks = [self.check_website(site) for site in self.websites.values()]
            if tasks:
                await asyncio.gather(*tasks)
                await self.notify_listeners()
            
            await asyncio.sleep(5)  # Check every 5 seconds

    async def notify_listeners(self):
        data = self.get_all_websites()
        to_remove = []
        for listener in self.listeners:
            try:
                await listener(data)
            except Exception as e:
                logger.error(f"Error notifying listener: {e}")
                to_remove.append(listener)
        
        for listener in to_remove:
            if listener in self.listeners:
                self.listeners.remove(listener)

    def add_listener(self, listener: Callable):
        self.listeners.append(listener)

    def remove_listener(self, listener: Callable):
        if listener in self.listeners:
            self.listeners.remove(listener)

# Singleton instance
manager = StatusManager()
