#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import rosbag
import json
import SimpleHTTPServer
import SocketServer
import os
import threading
import webbrowser
import socket
import time
import math
from datetime import datetime
import shutil

# HTML content as a string
HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vehicle Dashboard</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            background-color: #1a1a1a;
            color: white;
            font-family: 'Arial', sans-serif;
            overflow: hidden;
        }
        .dashboard {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            padding: 0 50px;
        }
        .dashboard-container {
            display: flex;
            width: 100%;
            max-width: 1200px;
            justify-content: space-between;
            align-items: center;
        }
        .alerts-panel {
            width: 250px;
            height: 100px;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .alert-box {
            padding: 15px 25px;
            border-radius: 10px;
            font-size: 32px;
            font-weight: bold;
            text-align: center;
            display: none;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        .alert-box.active {
            display: block;
        }
        .too-slow {
            background-color: #0088ff;
            color: white;
        }
        .normal {
            background-color: #FFEB3B;
            color: #333;
        }
        .economy {
            background-color: #4CAF50;
            color: white;
        }
        .too-fast {
            background-color: #FF5252;
            color: white;
        }
        
        /* Lead Vehicle Section */
        .lead-vehicle-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            margin: 0 20px;
        }
        .distance-label {
            font-size: 24px;
            margin-bottom: 10px;
            color: #aaa;
        }
        .lead-vehicle-image {
            max-width: 200px;
            max-height: 150px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            border-radius: 5px;
        }
        
        .gauge-panel {
            position: relative;
            width: 500px;
            height: 500px;
        }
        .circular-gauge {
            position: relative;
            width: 100%;
            height: 100%;
        }
        .gauge-background {
            position: absolute;
            width: 100%;
            height: 100%;
            border-radius: 50%;
            background: #222;
            box-shadow: 0 10px 20px rgba(0,0,0,0.3);
        }
        .gauge-value-container {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
        }
        .speed-value {
            font-size: 80px;
            font-weight: bold;
            line-height: 1;
            margin: 0;
            color: white;
            text-shadow: 0 0 10px rgba(255, 255, 255, 0.5);
        }
        .speed-unit {
            font-size: 24px;
            color: #aaa;
            margin-top: 5px;
        }
        
        .gauge-track {
            position: absolute;
            top: 10%;
            left: 10%;
            width: 80%;
            height: 80%;
            border-radius: 50%;
            clip: rect(0, 400px, 400px, 200px);
            /* Use clip-path for modern browsers */
            clip-path: inset(0 0 0 50%);
            transform: rotate(0deg);
        }
        .gauge-indicator {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            border-radius: 50%;
            clip: rect(0, 200px, 400px, 0);
            /* Use clip-path for modern browsers */
            clip-path: inset(0 50% 0 0);
            transform: rotate(0deg);
            transition: transform 0.3s ease;
        }
        .gauge-indicator:before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            border: 25px solid;
            border-radius: 50%;
            box-sizing: border-box;
        }
        
        .scale-marks {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
        }
        .scale-mark {
            position: absolute;
            top: 15px;
            left: 50%;
            height: 30px;
            width: 2px;
            background: rgba(255, 255, 255, 0.3);
            transform-origin: bottom center;
        }
        .scale-mark.major {
            height: 40px;
            width: 3px;
            background: rgba(255, 255, 255, 0.6);
        }
        .scale-text {
            position: absolute;
            width: 40px;
            text-align: center;
            font-size: 14px;
            color: #aaa;
            transform-origin: center bottom;
        }
        
        .needle {
            position: absolute;
            top: 50%;
            left: 50%;
            width: 180px;
            height: 4px;
            background: #ff5252;
            transform-origin: left center;
            transform: rotate(0deg);
            transition: transform 0.1s linear;
            border-radius: 2px;
            z-index: 10;
        }
        .needle:after {
            content: '';
            position: absolute;
            top: -8px;
            left: 0;
            width: 20px;
            height: 20px;
            background: #ff5252;
            border-radius: 50%;
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="dashboard-container">
            <!-- Alerts Panel on Left -->
            <div class="alerts-panel">
                <!-- Just show the active alert -->
                <div class="alert-box too-slow" id="tooSlowAlert">TOO SLOW</div>
                <div class="alert-box normal" id="normalAlert">NORMAL</div>
                <div class="alert-box economy" id="economyAlert">ECONOMY</div>
                <div class="alert-box too-fast" id="tooFastAlert">TOO FAST</div>
            </div>
            
            <!-- Lead Vehicle Image in Middle -->
            <div class="lead-vehicle-container">
                <div class="distance-label">DISTANCE</div>
                <img src="lead_veh.png" alt="Lead Vehicle" class="lead-vehicle-image">
            </div>
            
            <!-- Circular Gauge on Right -->
            <div class="gauge-panel">
                <div class="circular-gauge">
                    <div class="gauge-background"></div>
                    
                    <!-- Gauge Track -->
                    <div class="gauge-track">
                        <div class="gauge-indicator" id="gaugeIndicator"></div>
                    </div>
                    
                    <!-- Scale Marks -->
                    <div class="scale-marks" id="scaleMarks"></div>
                    
                    <!-- Needle -->
                    <div class="needle" id="speedNeedle"></div>
                    
                    <!-- Digital Value -->
                    <div class="gauge-value-container">
                        <h1 class="speed-value" id="speedValue">0.0</h1>
                        <div class="speed-unit">mph</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Constants
        const KMH_TO_MPH = 0.621371;
        const SPEED_LIMITS = {
            TOO_SLOW: 30,
            NORMAL_MIN: 30,
            NORMAL_MAX: 50,
            ECO_MIN: 50,
            ECO_MAX: 70,
            TOO_FAST: 70
        };
        const MAX_KMH = 120;
        const MAX_MPH = 80;
        
        // DOM Elements
        const speedValue = document.getElementById('speedValue');
        const speedNeedle = document.getElementById('speedNeedle');
        const gaugeIndicator = document.getElementById('gaugeIndicator');
        const tooSlowAlert = document.getElementById('tooSlowAlert');
        const normalAlert = document.getElementById('normalAlert');
        const economyAlert = document.getElementById('economyAlert');
        const tooFastAlert = document.getElementById('tooFastAlert');
        const scaleMarks = document.getElementById('scaleMarks');
        
        // Create scale marks
        function createScaleMarks() {
            // Create marks from 0 to 180 degrees (half circle)
            for (let i = 0; i <= 180; i += 5) {
                const isMajor = i % 20 === 0;
                
                const mark = document.createElement('div');
                mark.className = isMajor ? 'scale-mark major' : 'scale-mark';
                mark.style.transform = `rotate(${i}deg)`;
                scaleMarks.appendChild(mark);
                
                // Add text for major marks
                if (isMajor) {
                    const value = (i / 180) * MAX_MPH;
                    
                    const text = document.createElement('div');
                    text.className = 'scale-text';
                    text.textContent = Math.round(value);
                    
                    // Position the text
                    const distance = 65; // Distance from center in %
                    const angle = i * Math.PI / 180;
                    const y = -Math.cos(angle) * distance;
                    const x = Math.sin(angle) * distance;
                    
                    text.style.top = `calc(50% + ${y}%)`;
                    text.style.left = `calc(50% + ${x}%)`;
                    text.style.transform = `translate(-50%, -50%)`;
                    
                    scaleMarks.appendChild(text);
                }
            }
        }
        
        // Update the dashboard with speed data
        function updateDashboard(speedKmh) {
            // Calculate mph
            const speedMph = speedKmh * KMH_TO_MPH;
            
            // Format value to 1 decimal place
            const formattedMph = speedMph.toFixed(1);
            
            // Update speed value
            speedValue.textContent = formattedMph;
            
            // Update needle position (0-180 degrees)
            const needleAngle = (speedMph / MAX_MPH) * 180;
            speedNeedle.style.transform = `rotate(${needleAngle}deg)`;
            
            // Update gauge color
            updateGaugeColor(speedKmh);
            
            // Update active alert
            updateActiveAlert(speedKmh);
        }
        
        // Update gauge color based on speed
        function updateGaugeColor(speedKmh) {
            let color;
            
            if (speedKmh < SPEED_LIMITS.TOO_SLOW) {
                color = '#0088ff'; // Blue for too slow
            } else if (speedKmh >= SPEED_LIMITS.NORMAL_MIN && speedKmh < SPEED_LIMITS.ECO_MIN) {
                color = '#FFEB3B'; // Yellow for normal
            } else if (speedKmh >= SPEED_LIMITS.ECO_MIN && speedKmh <= SPEED_LIMITS.ECO_MAX) {
                color = '#4CAF50'; // Green for economy
            } else if (speedKmh > SPEED_LIMITS.TOO_FAST) {
                color = '#FF5252'; // Red for too fast
            }
            
            gaugeIndicator.style.borderColor = color;
            
            // Update the indicator to show the percentage of max speed
            const percentOfMax = (speedKmh * KMH_TO_MPH) / MAX_MPH;
            const angleDegrees = percentOfMax * 180;
            gaugeIndicator.style.transform = `rotate(${angleDegrees}deg)`;
        }
        
        // Update active alert based on speed
        function updateActiveAlert(speedKmh) {
            // Hide all alerts
            tooSlowAlert.classList.remove('active');
            normalAlert.classList.remove('active');
            economyAlert.classList.remove('active');
            tooFastAlert.classList.remove('active');
            
            // Show only appropriate alert
            if (speedKmh < SPEED_LIMITS.TOO_SLOW) {
                tooSlowAlert.classList.add('active');
            } else if (speedKmh >= SPEED_LIMITS.NORMAL_MIN && speedKmh < SPEED_LIMITS.ECO_MIN) {
                normalAlert.classList.add('active');
            } else if (speedKmh >= SPEED_LIMITS.ECO_MIN && speedKmh <= SPEED_LIMITS.ECO_MAX) {
                economyAlert.classList.add('active');
            } else if (speedKmh > SPEED_LIMITS.TOO_FAST) {
                tooFastAlert.classList.add('active');
            }
        }
        
        // Connect to WebSocket for live data
        function setupWebSocket() {
            const socket = new WebSocket(`ws://${window.location.hostname}:9090`);
            
            socket.onopen = function() {
                console.log('WebSocket connection established');
            };
            
            socket.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    if (data && typeof data.speed === 'number') {
                        updateDashboard(data.speed);
                    }
                } catch (error) {
                    console.error('Error processing WebSocket message:', error);
                }
            };
            
            socket.onerror = function(error) {
                console.error('WebSocket error:', error);
            };
            
            socket.onclose = function() {
                console.log('WebSocket connection closed');
                // Try to reconnect after a delay
                setTimeout(setupWebSocket, 3000);
            };
        }
        
        // Simulate live data for testing
        function simulateLiveData() {
            let speed = 0;
            let targetSpeed = 0;
            
            setInterval(() => {
                // Occasionally set a new target speed
                if (Math.random() < 0.03) {
                    // Cycle through different speed ranges for demonstration
                    const ranges = [
                        [5, 25],    // Too slow
                        [31, 49],   // Normal
                        [50, 70],   // Economy
                        [71, 100]   // Too fast
                    ];
                    const rangeIndex = Math.floor(Math.random() * ranges.length);
                    const [min, max] = ranges[rangeIndex];
                    targetSpeed = min + Math.random() * (max - min);
                }
                
                // Gradually approach the target speed
                if (speed < targetSpeed) {
                    speed += Math.min(1.0, targetSpeed - speed);
                } else if (speed > targetSpeed) {
                    speed -= Math.min(1.0, speed - targetSpeed);
                }
                
                // Ensure speed stays in valid range
                speed = Math.max(0, Math.min(MAX_KMH, speed));
                
                // Update the dashboard with the new speed
                updateDashboard(speed);
            }, 50);
        }
        
        // Initialize dashboard
        function initialize() {
            // Create scale marks
            createScaleMarks();
            
            // Try to connect via WebSocket
            // Uncomment to use real WebSocket:
            // setupWebSocket();
            
            // For testing, use simulated data
            simulateLiveData();
        }
        
        // Start when page loads
        document.addEventListener('DOMContentLoaded', initialize);
    </script>
</body>
</html>
"""

class VehicleDataStreamer:
    def __init__(self, bag_path):
        self.bag_path = bag_path
        self.server = None
        self.clients = set()
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
    
    def start_websocket_server(self, port=9090):
        """Start WebSocket server for real-time data streaming"""
        import SimpleWebSocketServer
        
        class SpeedHandler(SimpleWebSocketServer.WebSocket):
            def __init__(self, server, sock, address):
                SimpleWebSocketServer.WebSocket.__init__(self, server, sock, address)
                self.server = server
                with self.server.streamer.lock:
                    self.server.streamer.clients.add(self)
            
            def handleConnected(self):
                print("New client connected:", self.address)
            
            def handleClose(self):
                print("Client disconnected:", self.address)
                with self.server.streamer.lock:
                    self.server.streamer.clients.remove(self)
        
        # Create custom server class with reference to streamer
        class CustomWebSocketServer(SimpleWebSocketServer.SimpleWebSocketServer):
            def __init__(self, host, port, websocketclass, streamer):
                SimpleWebSocketServer.SimpleWebSocketServer.__init__(self, host, port, websocketclass)
                self.streamer = streamer
        
        # Set up server
        self.server = CustomWebSocketServer('', port, SpeedHandler, self)
        print("WebSocket server started on port", port)
        
        # Run server in a thread
        self.thread = threading.Thread(target=self.server.serveforever)
        self.thread.daemon = True
        self.thread.start()
        
        return True
    
    def broadcast(self, message):
        """Send message to all connected clients"""
        with self.lock:
            for client in self.clients:
                try:
                    client.sendMessage(message)
                except Exception as e:
                    print("Error sending message to client:", e)
    
    def process_rosbag_realtime(self):
        """Process ROS bag file and stream data in real time"""
        import time
        import json
        
        try:
            with rosbag.Bag(self.bag_path, 'r') as bag:
                self.running = True
                
                # Extract velocity messages for streaming
                velocity_msgs = []
                gps_msgs = []
                
                for topic, msg, t in bag.read_messages(topics=['/current_velocity']):
                    velocity_msgs.append((t.to_sec(), msg))
                
                for topic, msg, t in bag.read_messages(topics=['/gps/gps']):
                    gps_msgs.append((t.to_sec(), msg))
                
                # Sort by timestamp
                velocity_msgs.sort(key=lambda x: x[0])
                gps_msgs.sort(key=lambda x: x[0])
                
                # Combine and sync messages
                all_msgs = []
                
                # Add velocity messages
                for ts, msg in velocity_msgs:
                    speed_kmh = math.sqrt(msg.twist.linear.x**2 + msg.twist.linear.y**2) * 3.6
                    all_msgs.append((ts, {'speed': speed_kmh, 'source': 'velocity'}))
                
                # Add GPS messages
                for ts, msg in gps_msgs:
                    if hasattr(msg, 'speed'):
                        speed_kmh = msg.speed * 3.6  # Convert to km/h
                        all_msgs.append((ts, {'speed': speed_kmh, 'source': 'gps'}))
                
                # Sort all messages by timestamp
                all_msgs.sort(key=lambda x: x[0])
                
                if not all_msgs:
                    print("No velocity or GPS messages found in bag file")
                    return False
                
                # Simulate real-time playback
                start_time = all_msgs[0][0]
                real_start_time = time.time()
                
                while self.running and all_msgs:
                    current_time = time.time() - real_start_time + start_time
                    
                    # Find messages to send
                    while all_msgs and all_msgs[0][0] <= current_time:
                        _, data = all_msgs.pop(0)
                        self.broadcast(json.dumps(data))
                    
                    if not all_msgs:
                        # Loop back to beginning
                        all_msgs = velocity_msgs + gps_msgs
                        all_msgs.sort(key=lambda x: x[0])
                        start_time = all_msgs[0][0]
                        real_start_time = time.time()
                    
                    time.sleep(0.01)  # Small delay to avoid busy waiting
                
                return True
                
        except Exception as e:
            print("Error processing bag file for streaming:", e)
            return False

def get_ip_addresses():
    ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            host_ip = s.getsockname()[0]
            ips.append(host_ip)
        except Exception:
            pass
        finally:
            s.close()
    except Exception as e:
        print("Error getting IP addresses: {}".format(e))
    return ips

class CustomTCPServer(SocketServer.TCPServer):
    allow_reuse_address = True

def start_server(port, html_path):
    Handler = SimpleHTTPServer.SimpleHTTPRequestHandler
    os.chdir(os.path.dirname(os.path.abspath(html_path)))
    server = CustomTCPServer(("", port), Handler)
    
    ips = get_ip_addresses()
    print("\nServer started! Access the visualization at:")
    print("Local: http://localhost:{}".format(port))
    for ip in ips:
        print("Network: http://{}:{}".format(ip, port))
    print("\nPress Ctrl+C to stop the server")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    # Set paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if not current_dir:
        current_dir = os.getcwd()
    
    # Get bag file from command line or use default
    import sys
    if len(sys.argv) > 1:
        bag_path = sys.argv[1]
    else:
        bag_path = "2023-11-01-15-18-25.bag"  # Default bag file name
    
    html_path = os.path.join(current_dir, "index.html")

    print("Current directory: {}".format(current_dir))
    print("Using bag file: {}".format(bag_path))
    
    if not os.path.exists(bag_path):
        print("Error: Bag file not found at {}".format(bag_path))
        exit(1)

    # Check for lead vehicle image
    lead_veh_path = os.path.join(current_dir, "lead_veh.png")
    if not os.path.exists(lead_veh_path):
        print("Warning: Lead vehicle image not found at {}".format(lead_veh_path))
        print("Dashboard will show a broken image icon for the lead vehicle")

    # Create HTML file
    with open(html_path, 'w') as f:
        f.write(HTML_CONTENT)
    print("HTML file created successfully")

    # Start real-time data streamer
    try:
        # Try to import websocket server module
        import SimpleWebSocketServer
        streamer = VehicleDataStreamer(bag_path)
        ws_port = 9090
        
        print("Starting WebSocket server on port {}...".format(ws_port))
        if streamer.start_websocket_server(ws_port):
            print("WebSocket server started successfully")
            
            # Start data streaming in a thread
            stream_thread = threading.Thread(target=streamer.process_rosbag_realtime)
            stream_thread.daemon = True
            stream_thread.start()
            
            print("ROS bag streaming started")
        else:
            print("Failed to start WebSocket server")
    except ImportError:
        print("SimpleWebSocketServer not found - using simulated data only")
    except Exception as e:
        print("Error setting up data streamer:", e)

    # Open web browser
    port = 8000
    url = "http://localhost:{}".format(port)
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    # Start HTTP server
    print("Starting HTTP server on port {}...".format(port))
    start_server(port, html_path)
