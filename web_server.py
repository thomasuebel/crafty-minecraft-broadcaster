import os
import logging
import threading
import time
import json
from datetime import datetime
from flask import Flask, render_template, jsonify, request

# Get logger
logger = logging.getLogger('minecraft_broadcaster.web_server')

class HeartbeatWebServer:
    """Class to run a web server for displaying heartbeat logs"""
    
    def __init__(self, host="0.0.0.0", port=8080):
        """Initialize the web server"""
        self.host = os.environ.get("WEB_SERVER_HOST", host)
        self.port = int(os.environ.get("WEB_SERVER_PORT", port))
        self.app = Flask(__name__, 
                        template_folder=os.environ.get("TEMPLATES_DIR", "templates"))
        self.heartbeats = []
        self.max_logs = 1000  # Maximum number of log entries to keep
        self.thread = None
        self.running = False
        
        # Configure routes
        self._configure_routes()
        
        logger.info(f"Initialized web server on {self.host}:{self.port}")
        logger.info(f"Using templates from {self.app.template_folder}")
    
    def _configure_routes(self):
        """Configure Flask routes"""
        @self.app.route('/')
        def home():
            """Main page with heartbeat logs"""
            return render_template('index.html')
        
        @self.app.route('/api/logs')
        def get_logs():
            """API endpoint to get logs as JSON"""
            # Parse query parameters
            limit = request.args.get('limit', default=100, type=int)
            limit = min(limit, len(self.heartbeats))  # Don't exceed available logs
            
            # Return most recent logs first
            return jsonify({
                'logs': self.heartbeats[-limit:],
                'total': len(self.heartbeats)
            })
        
        @self.app.route('/api/status')
        def get_status():
            """API endpoint to get current status"""
            return jsonify({
                'status': 'running' if self.running else 'stopped',
                'last_update': self.heartbeats[-1]['timestamp'] if self.heartbeats else None,
                'logs_count': len(self.heartbeats)
            })
    
    def add_heartbeat(self, data):
        """Add a heartbeat log entry"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        log_entry = {
            'timestamp': timestamp,
            'data': data
        }
        
        self.heartbeats.append(log_entry)
        
        # Trim logs if exceeding max size
        if len(self.heartbeats) > self.max_logs:
            self.heartbeats = self.heartbeats[-self.max_logs:]
    
    def start(self):
        """Start the web server in a separate thread"""
        if self.thread and self.thread.is_alive():
            logger.warning("Web server is already running")
            return
        
        self.running = True
        
        # Check if templates directory exists
        if not os.path.exists(self.app.template_folder):
            logger.warning(f"Templates directory {self.app.template_folder} does not exist")
            logger.warning("Creating default templates...")
            self._create_template_files()
        
        # Start the Flask server in a separate thread
        self.thread = threading.Thread(target=self._run_server)
        self.thread.daemon = True  # Make thread a daemon so it exits when main program exits
        self.thread.start()
        
        logger.info(f"Web server started on http://{self.host}:{self.port}")
    
    def _run_server(self):
        """Run the Flask server"""
        try:
            # In production, you might want to use a proper WSGI server
            self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False)
        except Exception as e:
            logger.error(f"Error running web server: {e}")
            self.running = False
    
    def _create_template_files(self):
        """Create necessary template files for Flask if they don't exist"""
        # Create templates directory if it doesn't exist
        os.makedirs(self.app.template_folder, exist_ok=True)
        
        # Create index.html template if it doesn't exist
        index_path = os.path.join(self.app.template_folder, 'index.html')
        if not os.path.exists(index_path):
            logger.info(f"Creating default index.html template at {index_path}")
            with open(index_path, 'w') as f:
                f.write(self._get_default_index_template())
    
    def _get_default_index_template(self):
        """Get the default index.html template content"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Minecraft Server Broadcaster - Heartbeat Logs</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .status-panel {
            background-color: #fff;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .logs-container {
            background-color: #fff;
            border-radius: 5px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            height: 600px;
            overflow-y: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f2f2f2;
            position: sticky;
            top: 0;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .refresh-controls {
            margin-bottom: 15px;
        }
        .timestamp {
            white-space: nowrap;
        }
        .active {
            color: green;
            font-weight: bold;
        }
        .inactive {
            color: gray;
        }
        pre {
            white-space: pre-wrap;
            margin: 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Minecraft Server Broadcaster</h1>
        
        <div class="status-panel">
            <h2>Status</h2>
            <p>Status: <span id="status">Loading...</span></p>
            <p>Last Update: <span id="last-update">Loading...</span></p>
            <p>Total Logs: <span id="logs-count">Loading...</span></p>
        </div>
        
        <div class="refresh-controls">
            <button id="refresh-btn">Refresh Now</button>
            <label>
                Auto-refresh: 
                <select id="refresh-interval">
                    <option value="0">Off</option>
                    <option value="5" selected>5 seconds</option>
                    <option value="10">10 seconds</option>
                    <option value="30">30 seconds</option>
                    <option value="60">1 minute</option>
                </select>
            </label>
            <label>
                Show entries: 
                <select id="log-limit">
                    <option value="10">10</option>
                    <option value="50">50</option>
                    <option value="100" selected>100</option>
                    <option value="500">500</option>
                    <option value="1000">1000</option>
                </select>
            </label>
        </div>
        
        <div class="logs-container">
            <table id="logs-table">
                <thead>
                    <tr>
                        <th width="180">Timestamp</th>
                        <th>Server Details</th>
                    </tr>
                </thead>
                <tbody id="logs-body">
                    <tr>
                        <td colspan="2">Loading logs...</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        // State
        let refreshInterval = 5;
        let refreshTimer = null;
        let logLimit = 100;
        
        // DOM elements
        const statusElement = document.getElementById('status');
        const lastUpdateElement = document.getElementById('last-update');
        const logsCountElement = document.getElementById('logs-count');
        const logsTableBody = document.getElementById('logs-body');
        const refreshButton = document.getElementById('refresh-btn');
        const refreshIntervalSelect = document.getElementById('refresh-interval');
        const logLimitSelect = document.getElementById('log-limit');
        
        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            refreshLogs();
            updateStatus();
            startAutoRefresh();
            
            // Event listeners
            refreshButton.addEventListener('click', () => {
                refreshLogs();
                updateStatus();
            });
            
            refreshIntervalSelect.addEventListener('change', (e) => {
                refreshInterval = parseInt(e.target.value);
                startAutoRefresh();
            });
            
            logLimitSelect.addEventListener('change', (e) => {
                logLimit = parseInt(e.target.value);
                refreshLogs();
            });
        });
        
        // Functions
        function startAutoRefresh() {
            // Clear existing timer
            if (refreshTimer) {
                clearInterval(refreshTimer);
            }
            
            // Start new timer if interval > 0
            if (refreshInterval > 0) {
                refreshTimer = setInterval(() => {
                    refreshLogs();
                    updateStatus();
                }, refreshInterval * 1000);
            }
        }
        
        function updateStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    statusElement.textContent = data.status;
                    statusElement.className = data.status === 'running' ? 'active' : 'inactive';
                    lastUpdateElement.textContent = data.last_update || 'Never';
                    logsCountElement.textContent = data.logs_count;
                })
                .catch(error => {
                    console.error('Error fetching status:', error);
                });
        }
        
        function refreshLogs() {
            fetch(`/api/logs?limit=${logLimit}`)
                .then(response => response.json())
                .then(data => {
                    renderLogs(data.logs);
                })
                .catch(error => {
                    console.error('Error fetching logs:', error);
                });
        }
        
        function renderLogs(logs) {
            if (!logs.length) {
                logsTableBody.innerHTML = '<tr><td colspan="2">No logs available</td></tr>';
                return;
            }
            
            // Sort logs by timestamp (newest first)
            logs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
            
            // Clear table
            logsTableBody.innerHTML = '';
            
            // Add each log
            logs.forEach(log => {
                const row = document.createElement('tr');
                
                // Timestamp cell
                const timestampCell = document.createElement('td');
                timestampCell.className = 'timestamp';
                timestampCell.textContent = log.timestamp;
                
                // Data cell
                const dataCell = document.createElement('td');
                
                // Format the data based on content
                if (typeof log.data === 'object') {
                    const pre = document.createElement('pre');
                    pre.textContent = JSON.stringify(log.data, null, 2);
                    dataCell.appendChild(pre);
                } else {
                    dataCell.textContent = log.data;
                }
                
                // Add cells to row
                row.appendChild(timestampCell);
                row.appendChild(dataCell);
                
                // Add row to table
                logsTableBody.appendChild(row);
            });
        }
    </script>
</body>
</html>
        """