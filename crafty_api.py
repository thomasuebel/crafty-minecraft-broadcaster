import os
import logging
import requests
from urllib3.exceptions import InsecureRequestWarning
from requests.exceptions import RequestException

# Disable SSL warnings for local development
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Get logger
logger = logging.getLogger('minecraft_broadcaster.crafty_api')

class CraftyAPI:
    """Class to interact with Crafty Controller API"""
    
    def __init__(self, api_url=None, api_token=None):
        """Initialize the Crafty API client"""
        self.api_url = api_url or os.environ.get("CRAFTY_API_URL", "https://localhost:8443/api/v2")
        self.api_token = api_token or os.environ.get("CRAFTY_API_TOKEN", "")
        
        if not self.api_token:
            logger.warning("CRAFTY_API_TOKEN is not set! Authentication will likely fail.")
        
        logger.info(f"Initialized Crafty API client for: {self.api_url}")
        
    def _make_request(self, endpoint, method="GET"):
        """Make a request to the Crafty API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_token}"
            }
            url = f"{self.api_url}/{endpoint.lstrip('/')}"
            
            if method == "GET":
                response = requests.get(url, headers=headers, verify=False)
            else:
                # Add other methods if needed
                logger.error(f"Unsupported HTTP method: {method}")
                return None
                
            response.raise_for_status()
            
            data = response.json()
            if data.get("status") == "ok" and "data" in data:
                return data["data"]
            else:
                logger.error(f"Unexpected API response format: {data}")
                return None
                
        except RequestException as e:
            logger.error(f"Error making request to {endpoint}: {e}")
            return None
    
    def get_servers(self):
        """Fetch the list of servers from Crafty Controller"""
        return self._make_request("servers") or []
    
    def get_server_stats(self, server_id):
        """Get stats for a specific server"""
        return self._make_request(f"servers/{server_id}/stats")
    
    def is_server_running(self, server_id):
        """Check if a server is running"""
        stats = self.get_server_stats(server_id)
        if stats:
            return stats.get("running", False)
        return False
    
    def get_server_info(self, server_id):
        """Get info about a server including name, port, description, etc."""
        stats = self.get_server_stats(server_id)
        if not stats:
            return None
            
        return {
            "name": stats.get("server_id", {}).get("server_name", "Unknown Server"),
            "port": stats.get("server_port", 25565),
            "description": stats.get("desc", "A Minecraft Server"),
            "version": stats.get("version", "Unknown"),
            "max_players": stats.get("max", 20),
            "online_players": stats.get("online", 0),
        }