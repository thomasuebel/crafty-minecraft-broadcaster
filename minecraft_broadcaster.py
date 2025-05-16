import os
import socket
import struct
import logging

# Get logger
logger = logging.getLogger('minecraft_broadcaster.broadcaster')

class MinecraftBroadcaster:
    """Class to broadcast Minecraft servers on LAN"""
    
    def __init__(self, broadcast_ip=None, broadcast_port=None):
        """Initialize the Minecraft broadcaster"""
        self.broadcast_ip = broadcast_ip or os.environ.get("BROADCAST_IP", "255.255.255.255")
        self.broadcast_port = int(broadcast_port or os.environ.get("MINECRAFT_BROADCAST_PORT", "4445"))
        
        logger.info(f"Initialized Minecraft broadcaster for: {self.broadcast_ip}:{self.broadcast_port}")
    
    def broadcast_server(self, server_name, motd, port):
        """Broadcast a Minecraft server to the LAN"""
        try:
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Format the announcement message according to Minecraft LAN protocol
            announcement = f"[MOTD]{motd}[/MOTD][AD]{port}[/AD]"
            
            # Encode and send the message
            data = bytearray([0x00, 0x00]) + struct.pack('>h', len(announcement)) + announcement.encode('utf-8')
            sock.sendto(data, (self.broadcast_ip, self.broadcast_port))
            
            logger.info(f"Broadcasted server {server_name} on port {port} with MOTD: {motd}")
            sock.close()
            return True
        except Exception as e:
            logger.error(f"Error broadcasting server {server_name}: {e}")
            return False
    
    @staticmethod
    def generate_motd(server_name, server_desc):
        """Generate a colorful MOTD for the server"""
        # Use the server description, but enhance it with color codes
        if server_desc == "A Minecraft Server" or not server_desc:
            # If using default description, create a more colorful one based on server name
            if "survival" in server_name.lower():
                return f"§6{server_name} - Survival Mode"
            elif "creative" in server_name.lower():
                return f"§b{server_name} - Creative Mode"
            else:
                return f"§a{server_name} - Minecraft Server"
        else:
            # Use the server's configured description
            # Add a color code if it doesn't already have one
            if not server_desc.startswith("§"):
                return f"§a{server_desc}"
            return server_desc