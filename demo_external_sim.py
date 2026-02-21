"""
External Simulator Demo Script.

This script demonstrates how an external system (like CARLA, Unreal Engine, or 
a custom testing rig) can push high-frequency telemetry data to the GenAI Vehicle
Diagnostics backend using three different protocols:

1. REST (HTTP POST) - Good for occasional updates or simpler architectures.
2. WebSocket - Good for bidirectional communication or browser-based sim.
3. UDP - The automotive standard for high-frequency, low-latency telemetry.

Usage:
  python demo_external_sim.py --protocol udp
  python demo_external_sim.py --protocol ws
  python demo_external_sim.py --protocol rest
"""

import argparse
import json
import time
import math
import random
import asyncio
import socket

try:
    import requests
    import websockets
except ImportError:
    print("Please install required packages: pip install requests websockets")
    exit(1)

# Backend configuration
HOST = "127.0.0.1"
REST_URL = f"http://{HOST}:8000/simulator/external/feed"
WS_URL = f"ws://{HOST}:8000/simulator/external/ws-stream"
UDP_PORT = 9000

def generate_carla_frame(tick):
    """Generate a realistic mock frame of telemetry driving in a circle."""
    speed = 50.0 + math.sin(tick * 0.1) * 20.0  # 30 to 70 km/h
    throttle = max(0, speed / 1.5)
    steering = math.cos(tick * 0.05) * 45.0
    
    return {
        "speed": round(speed, 2),
        "throttle": round(throttle, 2),
        "brake": 0.0 if throttle > 0 else 10.0,
        "steering_angle": round(steering, 2),
        "tire_fl": round(32.0 - (tick * 0.001), 2),  # Slow leak simulator
        "battery_soc": round(80.0 - (tick * 0.05), 2),
        "vehicle_variant": "EV"
    }

async def stream_websocket():
    """Stream telemetry over WebSocket."""
    print(f"Connecting to WebSocket: {WS_URL} ...")
    try:
        async with websockets.connect(WS_URL) as ws:
            tick = 0
            while True:
                data = generate_carla_frame(tick)
                await ws.send(json.dumps(data))
                print(f"[WS] Sent -> Speed: {data['speed']} km/h, Steer: {data['steering_angle']}°")
                tick += 1
                await asyncio.sleep(0.1) # 10Hz
    except Exception as e:
        print(f"WebSocket Error: {e}")

def stream_udp():
    """Stream telemetry over UDP (CARLA style)."""
    print(f"Streaming UDP to {HOST}:{UDP_PORT} ...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    tick = 0
    try:
        while True:
            data = generate_carla_frame(tick)
            payload = json.dumps(data).encode('utf-8')
            sock.sendto(payload, (HOST, UDP_PORT))
            print(f"[UDP] Sent -> Speed: {data['speed']} km/h, Steer: {data['steering_angle']}°")
            tick += 1
            time.sleep(0.05) # 20Hz
    except KeyboardInterrupt:
        print("Stopping UDP Stream.")
    finally:
        sock.close()

def stream_rest():
    """Stream telemetry over HTTP POST."""
    print(f"Streaming REST POST to {REST_URL} ...")
    tick = 0
    try:
        while True:
            data = generate_carla_frame(tick)
            res = requests.post(REST_URL, json=data)
            if res.status_code == 200:
                print(f"[REST] Sent -> Speed: {data['speed']} km/h, Steer: {data['steering_angle']}°")
            else:
                print(f"[REST] Error: {res.status_code}")
            tick += 1
            time.sleep(0.5) # 2Hz (REST is slower)
    except KeyboardInterrupt:
        print("Stopping REST Stream.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="External Simulator Telemetry Demo")
    parser.add_argument("--protocol", choices=["rest", "ws", "udp"], default="udp", 
                        help="Protocol to use for streaming (default: udp)")
    
    args = parser.parse_args()
    
    print("=========================================")
    print(" EXTERNAL SIMULATOR DEMO (CARLA Fallback)")
    print("=========================================")
    print(f"Using Protocol: {args.protocol.upper()}")
    print("Make sure the FastAPI backend is running!")
    print("Press Ctrl+C to stop.")
    print("=========================================\n")
    
    if args.protocol == "udp":
        stream_udp()
    elif args.protocol == "rest":
        stream_rest()
    elif args.protocol == "ws":
        asyncio.run(stream_websocket())
