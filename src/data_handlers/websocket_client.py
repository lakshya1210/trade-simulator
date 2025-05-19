"""
WebSocket client to connect to exchange API for L2 orderbook data.
"""
import asyncio
import json
import time
import ssl
from loguru import logger
import websockets
from ..config import WEBSOCKET_URL

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
        self.last_error = None
        self.connection_task = None
        
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
            self.last_error = None
            logger.info("WebSocket connection established")
            
            try:
                logger.info("Sending ping to test connection...")
                await self.ws.ping()
                logger.info("Ping successful!")
                
                # If using OKX's direct endpoint, subscribe to orderbook
                if "okx.com" in self.url:
                    subscription = {
                        "op": "subscribe",
                        "args": [{"channel": "books", "instId": "BTC-USDT"}]
                    }
                    logger.info(f"Sending subscription: {subscription}")
                    await self.ws.send(json.dumps(subscription))
                    logger.info("Subscription sent")
            except Exception as e:
                logger.error(f"Error during handshake: {e}")
            
            return True
        except Exception as e:
            self.last_error = str(e)
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
                logger.error(f"Failed to connect: {self.last_error}")
                return
        
        try:
            retry_count = 0
            max_retries = 5
            
            while self.running:
                try:
                    message = await self.ws.recv()
                    self.last_message_time = time.time()
                    self.message_count += 1
                    retry_count = 0  # Reset retry counter on success
                    
                    # Process the message
                    data = json.loads(message)
                    logger.debug(f"Received message: length={len(message)}")
                    
                    # Call the callback function if provided
                    if self.callback:
                        self.callback(data)
                        
                except websockets.exceptions.ConnectionClosed as e:
                    self.connected = False
                    retry_count += 1
                    logger.warning(f"WebSocket connection closed unexpectedly: {e}")
                    
                    if retry_count > max_retries:
                        logger.error(f"Exceeded max retries ({max_retries}), giving up")
                        self.last_error = f"Connection failed after {max_retries} retries"
                        break
                    
                    logger.info(f"Reconnecting attempt {retry_count}/{max_retries}...")
                    await asyncio.sleep(2 ** min(retry_count, 6))  # Exponential backoff
                    
                    success = await self.connect()
                    if not success:
                        logger.warning(f"Reconnection attempt {retry_count} failed")
                        continue
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message as JSON: {e}")
                    # Continue trying, don't break the loop
                    
                except Exception as e:
                    logger.error(f"Unexpected error in WebSocket receive loop: {e}")
                    self.last_error = str(e)
                    
                    # Wait before retrying
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            logger.info("WebSocket receive task cancelled")
            raise
        except Exception as e:
            logger.error(f"Fatal error in WebSocket receive loop: {e}")
            self.connected = False
            self.last_error = str(e)
    
    def start(self):
        """Start the WebSocket client."""
        if self.running:
            logger.warning("WebSocket client already running")
            return False
            
        self.running = True
        self.connection_task = asyncio.create_task(self.receive_data())
        logger.info("WebSocket client started")
        return True
    
    def stop(self):
        """Stop the WebSocket client."""
        if not self.running:
            logger.warning("WebSocket client not running")
            return False
            
        self.running = False
        
        # Cancel the task
        if self.connection_task:
            self.connection_task.cancel()
        
        # Create a task to disconnect
        asyncio.create_task(self.disconnect())
        logger.info("WebSocket client stopped")
        return True
    
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
            "messages_per_second": self.message_count / elapsed if elapsed > 0 else 0,
            "last_error": self.last_error
        }
    
    def get_last_error(self):
        """Get the last error message."""
        return self.last_error
