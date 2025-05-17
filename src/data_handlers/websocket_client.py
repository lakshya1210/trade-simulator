"""
WebSocket client to connect to exchange API for L2 orderbook data.
"""
import asyncio
import json
import time
from loguru import logger
import websockets
from ..config import WEBSOCKET_URL
import ssl

class WebSocketClient:
    """Client to connect to WebSocket endpoint and stream L2 orderbook data."""
    
    def __init__(self, url=WEBSOCKET_URL, callback=None):
        """
        Initialize WebSocket client.
        
        Args:
            url (str): WebSocket endpoint URL
            callback (callable): Function to call with received data
        """
        self.url = url
        self.callback = callback
        self.ws = None
        self.running = False
        self.last_message_time = 0
        self.message_count = 0
        self.connected = False
        
    async def connect(self):
        """Connect to WebSocket endpoint."""
        try:
            logger.info(f"Connecting to {self.url}")
            
            # Create SSL context with verification disabled
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Connect with SSL context
            self.ws = await websockets.connect(self.url, ssl=ssl_context)
            
            self.connected = True
            logger.info("WebSocket connection established")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            self.connected = False
            return False
        
    async def disconnect(self):
        """Disconnect from WebSocket endpoint."""
        if self.ws and self.connected:
            await self.ws.close()
            self.connected = False
            logger.info("WebSocket connection closed")
    
    async def receive_data(self):
        """Receive and process data from WebSocket."""
        if not self.ws or not self.connected:
            success = await self.connect()
            if not success:
                return
        
        try:
            while self.running:
                try:
                    message = await self.ws.recv()
                    logger.info(f"Received message: length={len(message)}")
                    logger.debug(f"Message sample: {message[:100]}")
                    self.last_message_time = time.time()
                    self.message_count += 1
                    
                    # Process the message
                    data = json.loads(message)
                    
                    # Call the callback function if provided
                    if self.callback:
                        self.callback(data)
                        
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed unexpectedly, reconnecting...")
                    await self.connect()
                    
        except Exception as e:
            logger.error(f"Error in WebSocket receive loop: {e}")
            self.connected = False
    
    def start(self):
        """Start the WebSocket client."""
        self.running = True
        asyncio.create_task(self.receive_data())
        logger.info("WebSocket client started")
    
    def stop(self):
        """Stop the WebSocket client."""
        self.running = False
        asyncio.create_task(self.disconnect())
        logger.info("WebSocket client stopped")
    
    def is_connected(self):
        """Check if the client is connected."""
        return self.connected
    
    def get_stats(self):
        """Get statistics about the WebSocket connection."""
        current_time = time.time()
        elapsed = current_time - self.last_message_time if self.last_message_time > 0 else 0
        
        return {
            "connected": self.connected,
            "message_count": self.message_count,
            "last_message_elapsed": elapsed,
            "messages_per_second": self.message_count / elapsed if elapsed > 0 else 0
        }
