import os
import time
import logging
import json
from crafty_api import CraftyAPI
from minecraft_broadcaster import MinecraftBroadcaster
from web_server import HeartbeatWebServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger('minecraft_broadcaster.main')

def main():
    """Main function to check server status and broadcast active servers"""
    # Get configuration from environment
    check_interval = int(os.environ.get("CHECK_INTERVAL", "30"))
    enable_web_server = os.environ.get("ENABLE_WEB_SERVER", "true").lower() in ("true", "1", "yes")
    
    # Initialize API client and broadcaster
    crafty = CraftyAPI()
    broadcaster = MinecraftBroadcaster()
    
    # Initialize and start web server if enabled
    web_server = None
    if enable_web_server:
        web_server = HeartbeatWebServer()
        web_server.start()
    
    logger.info("Starting Minecraft server broadcaster...")
    logger.info(f"Check interval: {check_interval} seconds")
    
    # Initial authentication
    if not crafty.login():
        logger.error("Failed to authenticate with Crafty Controller. Check credentials.")
        return
    
    while True:
        try:
            # Fetch servers from Crafty Controller
            servers = crafty.get_servers()
            
            if not servers:
                logger.warning("No servers found or could not connect to Crafty Controller")
                
                # Log to web server
                if web_server:
                    web_server.add_heartbeat("No servers found or could not connect to Crafty Controller")
                
                time.sleep(check_interval)
                continue
                
            # Track active servers for this cycle
            active_servers = []
            
            for server in servers:
                server_id = server.get("server_id")
                server_name = server.get("server_name")
                
                if not server_id:
                    logger.warning(f"Server missing ID: {server}")
                    continue
                
                # Check if server is running
                if crafty.is_server_running(server_id):
                    # Get server information
                    server_info = crafty.get_server_info(server_id)
                    
                    if not server_info:
                        logger.warning(f"Could not get info for server {server_id}")
                        continue
                    
                    logger.info(f"Server {server_info['name']} is active on port {server_info['port']}")
                    
                    # Add to active servers
                    active_servers.append({
                        "id": server_id,
                        "name": server_info['name'],
                        "port": server_info['port'],
                        "description": server_info['description'],
                        "version": server_info['version'],
                        "players": f"{server_info['online_players']}/{server_info['max_players']}"
                    })
                    
                    # Generate MOTD and broadcast
                    motd = broadcaster.generate_motd(server_info['name'], server_info['description'])
                    broadcaster.broadcast_server(server_info['name'], motd, server_info['port'])
                else:
                    logger.info(f"Server {server_name} is not active")
            
            # Log heartbeat to web server
            if web_server:
                web_server.add_heartbeat({
                    "active_servers": active_servers,
                    "total_servers": len(servers),
                    "total_active": len(active_servers)
                })
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            
            # Log error to web server
            if web_server:
                web_server.add_heartbeat(f"Error: {str(e)}")
        
        # Wait before checking again
        time.sleep(check_interval)

if __name__ == "__main__":
    main()