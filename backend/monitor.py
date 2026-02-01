
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

    def to_dict(self):
        return {
            "url": self.url,
            "status": self.status,
            "response_time": self.response_time,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "is_up": self.is_up
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
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                start_time = datetime.now()
                response = await client.get(website.url)
                end_time = datetime.now()
                
                duration = (end_time - start_time).total_seconds() * 1000
                website.response_time = int(duration)
                website.last_checked = end_time
                
                if 200 <= response.status_code < 400:
                    website.status = f"{response.status_code} OK"
                    website.is_up = True
                else:
                    website.status = f"HTTP {response.status_code}"
                    website.is_up = False
                    
        except httpx.RequestError as e:
            website.status = "DOWN"
            website.is_up = False
            website.response_time = 0
            website.last_checked = datetime.now()
            logger.error(f"Error checking {website.url}: {e}")
        except Exception as e:
            website.status = "ERROR"
            website.is_up = False
            website.response_time = 0
            website.last_checked = datetime.now()
            logger.error(f"Unexpected error checking {website.url}: {e}")

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
