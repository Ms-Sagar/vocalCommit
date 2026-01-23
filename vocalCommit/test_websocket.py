#!/usr/bin/env python3
"""
Test script for VocalCommit WebSocket connection
"""

import asyncio
import websockets
import json

async def test_vocalcommit():
    uri = "ws://localhost:8000/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to VocalCommit WebSocket")
            
            # Test message
            test_message = {
                "type": "voice_command",
                "transcript": "Create a user authentication system",
                "timestamp": "2024-01-23T00:00:00Z"
            }
            
            print(f"📤 Sending: {test_message['transcript']}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for response
            print("⏳ Waiting for agent response...")
            response = await websocket.recv()
            response_data = json.loads(response)
            
            print("📥 Response received:")
            print(f"   Status: {response_data.get('status')}")
            print(f"   Agent: {response_data.get('agent')}")
            print(f"   Response: {response_data.get('response')[:100]}...")
            
            if response_data.get('details'):
                details = response_data['details']
                print(f"   Code Files: {details.get('code_files')}")
                print(f"   Security Findings: {details.get('security_findings')}")
                print(f"   Deployment Ready: {details.get('deployment_ready')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🎤 Testing VocalCommit WebSocket Connection")
    print("=" * 50)
    asyncio.run(test_vocalcommit())