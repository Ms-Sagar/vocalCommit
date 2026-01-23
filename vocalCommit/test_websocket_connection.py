#!/usr/bin/env python3
"""
Test WebSocket connection to the orchestrator
"""

import asyncio
import websockets
import json

async def test_websocket():
    """Test WebSocket connection and basic functionality."""
    
    print("🔌 Testing WebSocket Connection to Orchestrator")
    print("=" * 50)
    
    try:
        # Connect to WebSocket
        uri = "ws://localhost:8000/ws"
        print(f"Connecting to {uri}...")
        
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!")
            
            # Test 1: Send a simple text command
            test_message = {
                "type": "text_command",
                "transcript": "test connection",
                "timestamp": "2024-01-23T12:00:00Z"
            }
            
            print(f"📤 Sending test message: {test_message['transcript']}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                data = json.loads(response)
                print(f"📥 Received response:")
                print(f"   Status: {data.get('status', 'unknown')}")
                print(f"   Agent: {data.get('agent', 'unknown')}")
                print(f"   Type: {data.get('type', 'unknown')}")
                
                if data.get('response'):
                    response_text = data['response'][:100] + "..." if len(data['response']) > 100 else data['response']
                    print(f"   Response: {response_text}")
                
                print("✅ WebSocket communication working!")
                return True
                
            except asyncio.TimeoutError:
                print("⏰ Timeout waiting for response")
                return False
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error: {e}")
                return False
                
    except ConnectionRefusedError:
        print("❌ Connection refused - orchestrator not running on port 8000")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

async def test_pending_approvals():
    """Test the pending approvals endpoint."""
    print("\n🔍 Testing Pending Approvals Endpoint")
    print("-" * 40)
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8000/pending-approvals') as response:
                if response.status == 200:
                    data = await response.json()
                    approvals = data.get('pending_approvals', [])
                    print(f"✅ Pending approvals endpoint working")
                    print(f"   Found {len(approvals)} pending approvals")
                    return True
                else:
                    print(f"❌ Pending approvals endpoint returned status: {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error testing pending approvals: {e}")
        return False

if __name__ == "__main__":
    async def run_tests():
        print("🧪 VocalCommit WebSocket Connection Test")
        print("Testing connection between admin UI and orchestrator")
        print()
        
        # Test WebSocket connection
        websocket_ok = await test_websocket()
        
        # Test HTTP endpoints
        approvals_ok = await test_pending_approvals()
        
        print(f"\n📊 Test Results:")
        print(f"   WebSocket Connection: {'✅ PASS' if websocket_ok else '❌ FAIL'}")
        print(f"   Pending Approvals API: {'✅ PASS' if approvals_ok else '❌ FAIL'}")
        
        if websocket_ok and approvals_ok:
            print(f"\n🎉 All tests passed!")
            print(f"   The admin UI should be able to connect properly")
            print(f"   If you're still seeing 'Disconnected', try:")
            print(f"   1. Refresh the admin UI page (http://localhost:5173)")
            print(f"   2. Check browser console for any JavaScript errors")
            print(f"   3. Clear browser cache and reload")
        else:
            print(f"\n⚠️  Some tests failed. Check the orchestrator logs.")
    
    asyncio.run(run_tests())