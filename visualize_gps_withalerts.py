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
from datetime import datetime

# HTML content as a string
HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ROS GPS Path Animation</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/leaflet.css" />
    <style>
        #map { height: 600px; width: 100%; }
        body { margin: 0; padding: 20px; font-family: Arial, sans-serif; }
        .control-panel {
            background: white;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin-bottom: 15px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin: 10px 0;
        }
        .stat-item {
            background: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            font-weight: bold;
        }
        .controls {
            display: flex;
            gap: 10px;
            align-items: center;
            margin-top: 10px;
        }
        .progress-bar {
            flex-grow: 1;
            height: 20px;
            background: #eee;
            border-radius: 10px;
            overflow: hidden;
        }
        .progress {
            height: 100%;
            background: #4CAF50;
            width: 0%;
            transition: width 0.3s ease;
        }
        button {
            padding: 8px 15px;
            border: none;
            border-radius: 4px;
            background: #4CAF50;
            color: white;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover { background: #45a049; }
        button:disabled { background: #cccccc; }
        #speed-indicator {
            transition: color 0.3s ease;
        }
        .car-icon {
            font-size: 24px;
            transition: transform 0.2s ease;
        }
        /* New alert system styles */
        .speed-alert {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #ff5252;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            display: none;
            animation: pulse 1.5s infinite;
            z-index: 1000;
            font-weight: bold;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        .speed-alert button {
            background: white;
            color: #ff5252;
            border: none;
            padding: 5px 10px;
            border-radius: 4px;
            margin-left: 10px;
            cursor: pointer;
        }
        .speed-normal { color: #43a047; }
        .speed-warning { color: #fb8c00; }
        .speed-danger { color: #e53935; }
    </style>
</head>
<body>
    <!-- Speed alert div -->
    <div id="speedAlert" class="speed-alert">
        ⚠️ Speed Alert: Slow Down!
        <button onclick="acknowledgeSpeedAlert()">OK</button>
    </div>

    <div class="control-panel">
        <div class="stats">
            <div class="stat-item" id="current-time">Time: --:--:--</div>
            <div class="stat-item" id="position">Position: Waiting...</div>
            <div class="stat-item" id="speed-indicator">Speed: 0 km/h</div>
            <div class="stat-item" id="progress">Progress: 0%</div>
        </div>
        <div class="controls">
            <button id="playPauseBtn">▶ Play</button>
            <button id="resetBtn">⟲ Reset</button>
            <select id="speedControl">
                <option value="1">1x Speed</option>
                <option value="2">2x Speed</option>
                <option value="5">5x Speed</option>
                <option value="10">10x Speed</option>
            </select>
            <div class="progress-bar">
                <div class="progress" id="progressBar"></div>
            </div>
        </div>
    </div>
    <div id="map"></div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/leaflet.js"></script>
    <script>
        let map, pathLine, carMarker;
        let gpsData = [];
        let currentIndex = 0;
        let isPlaying = false;
        let animationFrame;
        let lastTimestamp = 0;
        let speedMultiplier = 1;
        let speedAlertShown = false;
        let speedAlertAcknowledged = false;
        const SPEED_LIMIT = 45; // km/h

        // Custom car icon with rotation
        const carIcon = L.divIcon({
            className: 'car-icon',
            html: '🚗',
            iconSize: [24, 24],
            iconAnchor: [12, 12]
        });

        // Initialize map
        map = L.map('map');
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);

        // Alert system functions
        function showSpeedAlert() {
            if (!speedAlertShown && !speedAlertAcknowledged) {
                document.getElementById('speedAlert').style.display = 'block';
                speedAlertShown = true;
            }
        }

        function hideSpeedAlert() {
            document.getElementById('speedAlert').style.display = 'none';
            speedAlertShown = false;
        }

        function acknowledgeSpeedAlert() {
            hideSpeedAlert();
            speedAlertAcknowledged = true;
            setTimeout(() => {
                speedAlertAcknowledged = false;
            }, 30000); // Reset acknowledgment after 30 seconds
        }

        function updateStats(point, progress) {
            const time = new Date(point.timestamp * 1000);
            document.getElementById('current-time').textContent = 
                `Time: ${time.toLocaleTimeString()}`;
            document.getElementById('position').textContent = 
                `Position: ${point.latitude.toFixed(6)}, ${point.longitude.toFixed(6)}`;
            
            const speedEl = document.getElementById('speed-indicator');
            const speed = point.speed;
            speedEl.textContent = `Speed: ${speed.toFixed(1)} km/h`;
            
            // Update speed indicator with new alert system
            if (speed > SPEED_LIMIT) {
                speedEl.className = 'stat-item speed-danger';
                showSpeedAlert();
            } else if (speed > SPEED_LIMIT * 0.8) {
                speedEl.className = 'stat-item speed-warning';
                hideSpeedAlert();
            } else {
                speedEl.className = 'stat-item speed-normal';
                hideSpeedAlert();
            }
            
            document.getElementById('progress').textContent = 
                `Progress: ${Math.round(progress * 100)}%`;
            document.getElementById('progressBar').style.width = 
                `${Math.round(progress * 100)}%`;
        }

        function updateCarPosition(point, prevPoint) {
            const newLatLng = [point.latitude, point.longitude];
            
            if (!carMarker) {
                carMarker = L.marker(newLatLng, {icon: carIcon}).addTo(map);
            } else {
                carMarker.setLatLng(newLatLng);
            }

            if (prevPoint) {
                const dx = point.longitude - prevPoint.longitude;
                const dy = point.latitude - prevPoint.latitude;
                const angle = Math.atan2(dx, dy) * 180 / Math.PI;
                carMarker.getElement().style.transform += ` rotate(${angle}deg)`;
            }

            map.panTo(newLatLng);
        }

        function animate(timestamp) {
            if (!isPlaying) return;
            
            if (!lastTimestamp) lastTimestamp = timestamp;
            const deltaTime = (timestamp - lastTimestamp) * speedMultiplier;
            lastTimestamp = timestamp;

            if (currentIndex < gpsData.length - 1) {
                const currentPoint = gpsData[currentIndex];
                const nextPoint = gpsData[currentIndex + 1];
                const prevPoint = currentIndex > 0 ? gpsData[currentIndex - 1] : null;

                const timeProgress = (currentPoint.timestamp - gpsData[0].timestamp) / 
                                   (gpsData[gpsData.length-1].timestamp - gpsData[0].timestamp);
                
                updateCarPosition(currentPoint, prevPoint);
                updateStats(currentPoint, timeProgress);

                const timeToNext = (nextPoint.timestamp - currentPoint.timestamp) * 1000;
                if (deltaTime >= timeToNext) {
                    currentIndex++;
                }

                animationFrame = requestAnimationFrame(animate);
            } else {
                isPlaying = false;
                document.getElementById('playPauseBtn').textContent = '▶ Play';
            }
        }

        async function loadAndDisplayPath() {
            try {
                const response = await fetch('gps_data.json?' + new Date().getTime());
                gpsData = await response.json();
                
                const points = gpsData.map(point => [point.latitude, point.longitude]);
                
                if (pathLine) map.removeLayer(pathLine);
                pathLine = L.polyline(points, {
                    color: '#2196F3',
                    weight: 3,
                    opacity: 0.7
                }).addTo(map);
                
                map.fitBounds(pathLine.getBounds());
                
                if (gpsData.length > 0) {
                    updateCarPosition(gpsData[0], null);
                    updateStats(gpsData[0], 0);
                }
            } catch (error) {
                console.error('Error loading GPS data:', error);
            }
        }

        // Event Listeners
        document.getElementById('playPauseBtn').addEventListener('click', () => {
            isPlaying = !isPlaying;
            document.getElementById('playPauseBtn').textContent = 
                isPlaying ? '⏸ Pause' : '▶ Play';
            
            if (isPlaying) {
                lastTimestamp = 0;
                animationFrame = requestAnimationFrame(animate);
            }
        });

        document.getElementById('resetBtn').addEventListener('click', () => {
            currentIndex = 0;
            isPlaying = false;
            speedAlertAcknowledged = false;
            hideSpeedAlert();
            document.getElementById('playPauseBtn').textContent = '▶ Play';
            if (gpsData.length > 0) {
                updateCarPosition(gpsData[0], null);
                updateStats(gpsData[0], 0);
            }
        });

        document.getElementById('speedControl').addEventListener('change', (e) => {
            speedMultiplier = parseFloat(e.target.value);
        });

        // Initial load
        loadAndDisplayPath();
    </script>
</body>
</html>
"""

class GPSDataHandler:
    def __init__(self, bag_path):
        self.bag_path = bag_path
        self.data = []
        self.lock = threading.Lock()

    def extract_data(self):
        try:
            with rosbag.Bag(self.bag_path, 'r') as bag:
                initial_time = None
                temp_data = []
                
                for topic, msg, t in bag.read_messages(topics=['/gps/gps']):
                    if not initial_time:
                        initial_time = t.to_sec()
                    
                    data_point = {
                        'timestamp': t.to_sec(),
                        'relative_time': t.to_sec() - initial_time,
                        'latitude': msg.latitude,
                        'longitude': msg.longitude,
                        'altitude': msg.altitude,
                        'track': msg.track,
                        'speed': msg.speed * 3.6,  # Convert to km/h
                        'err_horizontal': msg.err_horz
                    }
                    temp_data.append(data_point)
                
                with self.lock:
                    self.data = temp_data
                    
                print("Processed {} GPS points from {} to {}".format(
                    len(self.data),
                    datetime.fromtimestamp(self.data[0]['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
                    datetime.fromtimestamp(self.data[-1]['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                ))
                return True
                
        except Exception as e:
            print("Error processing bag file: {}".format(e))
            return False

    def save_to_json(self, json_path):
        try:
            with self.lock:
                with open(json_path, 'w') as f:
                    json.dump(self.data, f)
            return True
        except Exception as e:
            print("Error saving JSON file: {}".format(e))
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
    
    bag_path = "2023-11-01-15-18-25.bag"  # Update this to your bag file name
    json_path = os.path.join(current_dir, "gps_data.json")
    html_path = os.path.join(current_dir, "index.html")

    print("Current directory: {}".format(current_dir))
    print("Looking for bag file: {}".format(bag_path))
    
    if not os.path.exists(bag_path):
        print("Error: Bag file not found at {}".format(bag_path))
        exit(1)

    # Process GPS data
    gps_handler = GPSDataHandler(bag_path)
    print("Processing GPS data...")
    
    if gps_handler.extract_data() and gps_handler.save_to_json(json_path):
        # Create HTML file
        with open(html_path, 'w') as f:
            f.write(HTML_CONTENT)
        print("Files created successfully")

        # Open web browser
        port = 8000
        url = "http://localhost:{}".format(port)
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

        # Start server
        start_server(port, html_path)
    else:
        print("Failed to process GPS data")
