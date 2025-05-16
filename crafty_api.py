import os
import logging
import requests
import time
from urllib3.exceptions import InsecureRequestWarning
from requests.exceptions import RequestException

# Disable SSL warnings for local development
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Get logger
logger = logging.getLogger('minecraft_broadcaster.crafty_api')

class CraftyAPI:
    """Class to interact with Crafty Controller API"""
    
    def __init__(self, api_url=None, username=None, password=None):
        """Initialize the Crafty API client"""
        self.api_url = api_url or os.environ.get("CRAFTY_API_URL", "https://localhost:8443/api/v2")
        self.username = username or os.environ.get("CRAFTY_USERNAME", "")
        self.password = password or os.environ.get("CRAFTY_PASSWORD", "")
        self.token = ""  # Token will always be fetched via login
        self.token_expiry = 0
        self.token_ttl = 3600  # Default token expiry time (1 hour)
        
        if not self.username or not self.password:
            if not self.token:
                logger.warning("Neither login credentials nor API token provided! Authentication will likely fail.")
            else:
                logger.info("Using provided API token for authentication")
        
        logger.info(f"Initialized Crafty API client for: {self.api_url}")
    
    def login(self):
        """Authenticate with Crafty Controller to get an API token"""
        if self.token and time.time() < self.token_expiry:
            logger.debug("Using existing token")
            return True
            
        try:
            logger.info("Authenticating with Crafty Controller")
            url = f"{self.api_url}/auth/login"
            
            # Prepare login data
            login_data = {
                "username": self.username, 
                "password": self.password
            }
            
            # Make login request
            response = requests.post(
                url, 
                json=login_data, 
                verify=False
            )
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            if data.get("status") == "ok" and "data" in data:
                self.token = data["data"].get("token", "")
                if self.token:
                    self.token_expiry = time.time() + self.token_ttl
                    logger.info("Successfully authenticated with Crafty Controller")
                    return True
                else:
                    logger.error("Authentication successful but no token received")
                    return False
            else:
                logger.error(f"Unexpected API response format during login: {data}")
                return False
                
        except RequestException as e:
            logger.error(f"Error authenticating with Crafty Controller: {e}")
            return False
    
    def _make_request(self, endpoint, method="GET", data=None):
        """Make a request to the Crafty API"""
        # Try to login if we don't have a valid token
        if not self.token or time.time() >= self.token_expiry:
            if not self.login():
                logger.error("Failed to authenticate, cannot make API request")
                return None
        
        try:
            headers = {
                "Authorization": f"Bearer {self.token}"
            }
            url = f"{self.api_url}/{endpoint.lstrip('/')}"
            
            if method == "GET":
                response = requests.get(url, headers=headers, verify=False)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, verify=False)
            else:
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
            # Check if it's an authentication error
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 401:
                logger.warning("Authentication token expired, attempting to re-authenticate")
                self.token = ""
                self.token_expiry = 0
                
                # Try one more time with a fresh login
                return self._make_request(endpoint, method, data)
            
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
            
        server_info = stats.get("server_id", {})
        
        return {
            "name": server_info.get("server_name", "Unknown Server"),
            "port": stats.get("server_port", 25565),
            "description": stats.get("desc", "A Minecraft Server"),
            "version": stats.get("version", "Unknown"),
            "max_players": stats.get("max", 20),
            "online_players": stats.get("online", 0),
        }