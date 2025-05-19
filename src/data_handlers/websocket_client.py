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

logger.critical("WEBSOCKET_CLIENT_MODULE_LOADED")

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
        logger.critical(f"WebSocketClient INITIALIZED with URL: {self.url}")
        self.ws = None
        self.running = False
        self.last_message_time = 0
        self.message_count = 0
        self.connected = False
        self.last_error = None
        self.connection_task = None
        self.heartbeat_task = None
        
    async def connect(self):
        """Connect to WebSocket endpoint."""
        logger.critical("CONNECT_METHOD_ATTEMPTING")
        # If already connected, don't reconnect
        if self.ws and self.connected:
            logger.info("Already connected to WebSocket")
            return True
            
        # If we have an existing connection, close it first
        if self.ws:
            try:
                await self.ws.close()
                logger.info("Closed existing WebSocket connection")
            except Exception as e:
                logger.warning(f"Error closing existing connection: {e}")
        
        try:
            logger.critical("CONNECT_METHOD_TRY_BLOCK_ENTERED")
            logger.info(f"Connecting to {self.url}")
            
            # Create SSL context with verification disabled
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            logger.critical("SSL context created.")
            
            logger.critical("ATTEMPTING_WEBSOCKETS_CONNECT_CALL")
            # Connect with SSL context
            self.ws = await websockets.connect(
                self.url, 
                ssl=ssl_context,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
                open_timeout=10 # Added open_timeout
            )
            logger.critical("WEBSOCKETS_CONNECT_CALL_RETURNED")
            
            self.connected = True
            self.last_error = None
            logger.info("WebSocket connection established")
            
            # Handle OKX subscription
            if "okx.com" in self.url:
                logger.critical("ATTEMPTING_OKX_SUBSCRIPTION")
                try:
                    # Subscribe to orderbook data with correct parameters
                    subscription = {
                        "op": "subscribe",
                        "args": [
                            {
                                "channel": "books5",
                                "instId": "BTC-USDT"
                            }
                        ]
                    }
                    
                    logger.info(f"Sending subscription: {subscription}")
                    await self.ws.send(json.dumps(subscription))
                    logger.critical("SUBSCRIPTION_SENT_WAITING_FOR_RESPONSE")
                    
                    # Wait for subscription response
                    response = await asyncio.wait_for(self.ws.recv(), timeout=10.0) # Increased timeout
                    logger.critical(f"SUBSCRIPTION_RESPONSE_RAW: {{response}}") # Log raw response
                    response_data = json.loads(response)
                    
                    if response_data.get("event") == "subscribe" and response_data.get("code") == "0":
                        logger.info("Successfully subscribed to orderbook")
                    else:
                        logger.warning(f"Unexpected subscription response: {response_data}")
                        
                except Exception as e:
                    logger.critical(f"CRITICAL_ERROR_DURING_SUBSCRIPTION: {e}", exc_info=True)
                    # Continue anyway, the connection is still valid for pings, but data might not flow
            
            # Start heartbeat task for connection monitoring
            self.start_heartbeat()
            
            return True
        except asyncio.TimeoutError as e_timeout: # Catch TimeoutError specifically from connect or subscription
            self.last_error = f"Connection or Subscription timed out: {e_timeout}"
            logger.critical(f"CRITICAL_TIMEOUT_ERROR_IN_CONNECT: {self.last_error}", exc_info=True)
            self.connected = False
            if self.ws: # Attempt to close if partially opened
                try: await self.ws.close()
                except: pass
            self.ws = None
            return False
        except Exception as e:
            self.last_error = str(e)
            logger.critical(f"CRITICAL_ERROR_IN_CONNECT: {e}", exc_info=True)
            self.connected = False
            if self.ws: # Attempt to close if partially opened
                try: await self.ws.close()
                except: pass
            self.ws = None
            return False
    
    def start_heartbeat(self):
        """Start a heartbeat task to ensure connection stays alive."""
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
        
        self.heartbeat_task = asyncio.create_task(self.heartbeat_loop())
    
    async def heartbeat_loop(self):
        """Send periodic pings to check connection status."""
        try:
            while self.running and self.connected:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                if not self.ws or not self.connected:
                    logger.critical("HEARTBEAT_LOOP_TERMINATING_DUE_TO_DISCONNECTION")
                    continue # Or break, as connection is lost
                
                # Check if we've received a message in the last 60 seconds
                if time.time() - self.last_message_time > 60 and self.last_message_time > 0:
                    logger.warning("No messages received for 60 seconds, checking connection...")
                    
                    try:
                        # Send a ping to check connection
                        if "okx.com" in self.url:
                            # OKX uses a custom ping format
                            ping = {"op": "ping"}
                            await self.ws.send(json.dumps(ping))
                            logger.debug("Sent ping to OKX")
                        else:
                            # Standard WebSocket ping
                            pong_waiter = await self.ws.ping()
                            await asyncio.wait_for(pong_waiter, timeout=5)
                    except Exception as e:
                        logger.critical(f"HEARTBEAT_PING_FAILED_CONNECTION_MAY_BE_DEAD: {e}", exc_info=True)
                        self.connected = False
                        # Try to reconnect (or let receive_data handle it)
                        # await self.connect() # Be careful with direct reconnects here
                        break # Exit heartbeat loop, connection is likely dead
        except asyncio.CancelledError:
            logger.debug("Heartbeat task cancelled")
        except Exception as e:
            logger.critical(f"CRITICAL_ERROR_IN_HEARTBEAT_LOOP: {e}", exc_info=True)
        finally:
            logger.critical("HEARTBEAT_LOOP_EXITED")
        
    async def disconnect(self):
        """Disconnect from WebSocket endpoint."""
        logger.critical("DISCONNECT_METHOD_CALLED")
        # Cancel heartbeat task
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
            
        if self.ws and self.connected: # Check self.connected as well
            # Handle OKX unsubscription
            if "okx.com" in self.url:
                try:
                    # Unsubscribe from orderbook data
                    unsubscription = {
                        "op": "unsubscribe",
                        "args": [
                            {
                                "channel": "books5",
                                "instId": "BTC-USDT"
                            }
                        ]
                    }
                    
                    logger.info("Sending unsubscription request")
                    await self.ws.send(json.dumps(unsubscription))
                except Exception as e:
                    logger.error(f"Error during unsubscription: {e}", exc_info=True)
            
            try:
                await self.ws.close()
                logger.info("WebSocket connection closed")
            except Exception as e:
                logger.error(f"Error closing WebSocket connection: {e}", exc_info=True)
            finally: # Ensure state is updated
                self.connected = False
                self.ws = None
        else:
            logger.info("Disconnect called but no active or connected WebSocket.")
        self.connected = False # Explicitly set to false
        self.ws = None # Explicitly set to None
    
    async def receive_data(self):
        print("RECEIVE_DATA_TASK_STARTED_RAW_PRINT", flush=True) # Added raw print for immediate feedback
        logger.critical("RECEIVE_DATA_TASK_RUNNING")
        if not self.ws or not self.connected:
            logger.critical("RECEIVE_DATA_ATTEMPTING_INITIAL_CONNECT")
            success = await self.connect()
            if not success:
                logger.critical(f"RECEIVE_DATA_INITIAL_CONNECT_FAILED: {self.last_error}")
                self.running = False # Stop running if initial connect fails
                return
        
        logger.critical("RECEIVE_DATA_ENTERING_MAIN_LOOP")
        try:
            retry_count = 0
            max_retries = 3 # Reduced max_retries for faster feedback on persistent failures
            
            while self.running:
                logger.critical(f"RECEIVE_DATA_LOOP_ITERATION_START (Running: {self.running}, Connected: {self.connected})")
                if not self.connected or not self.ws:
                    logger.warning("Connection lost, attempting to reconnect...")
                    success = await self.connect() # connect() now handles its own logging better
                    if not success:
                        await asyncio.sleep(2 ** min(retry_count, 4)) # Shorter max backoff
                        retry_count += 1
                        logger.critical(f"RECONNECT_ATTEMPT_{retry_count}_FAILED: {self.last_error}")
                        if retry_count > max_retries:
                            logger.critical(f"MAX_RECONNECTION_ATTEMPTS ({max_retries}) REACHED, GIVING UP.")
                            self.running = False # Stop running
                            break
                        continue
                    else:
                        logger.info("Successfully reconnected in receive_data loop.")
                        retry_count = 0
                
                try:
                    logger.critical("RECEIVE_DATA_AWAITING_MESSAGE")
                    message = await asyncio.wait_for(self.ws.recv(), timeout=30)
                    self.last_message_time = time.time()
                    self.message_count += 1
                    retry_count = 0  # Reset retry counter on successful message
                    
                    try:
                        data = json.loads(message)
                        logger.info(f"RAW MESSAGE: {message[:500]}")
                    except json.JSONDecodeError as e:
                        logger.critical(f"CRITICAL_FAILED_TO_PARSE_MESSAGE_AS_JSON: {e}", exc_info=True)
                        logger.error(f"Raw message snippet: {message[:500]}")
                        continue # Skip this message
                    
                    # Skip heartbeat and subscription confirmation messages from general processing
                    if "event" in data and data["event"] in ["subscribe", "unsubscribe", "error"]:
                        logger.debug(f"Received event message: {data['event']} - {data}")
                        continue
                        
                    if "arg" in data and "data" in data and len(data["data"]) > 0:
                        logger.debug(f"Received orderbook data: {len(data['data'][0].get('bids', []))} bids, {len(data['data'][0].get('asks', []))} asks")
                    else:
                        logger.debug(f"Received other message: length={len(message)}")
                    
                    # Heartbeat handling for OKX (ping/pong)
                    if "okx.com" in self.url:
                        if isinstance(data, dict):
                            if data.get("op") == "ping":
                                logger.debug("Received ping from OKX, sending pong")
                                pong = {"op": "pong"}
                                await self.ws.send(json.dumps(pong))
                                continue
                            # Event type messages (error, subscribe) handled above
                    
                    # Call the callback function if provided
                    if self.callback:
                        try:
                            self.callback(data)
                        except Exception as e:
                            logger.error(f"Error in callback: {e}", exc_info=True)
                        
                except asyncio.TimeoutError:
                    logger.warning("Receive timeout (30s), checking connection...")
                    # Heartbeat loop should also be checking, this is an additional check
                    # If heartbeat fails, it sets self.connected = False, loop should try to reconnect.
                    if self.connected: # Only try ping if we think we are connected
                        try:
                            if "okx.com" in self.url:
                                ping = {"op": "ping"}
                                await self.ws.send(json.dumps(ping))
                            else:
                                pong_waiter = await self.ws.ping()
                                await asyncio.wait_for(pong_waiter, timeout=5)
                            logger.info("Receive timeout: Ping sent successfully to check connection.")
                        except Exception as ping_e:
                            logger.critical(f"RECEIVE_TIMEOUT_PING_FAILED_CONNECTION_DEAD: {ping_e}", exc_info=True)
                            self.connected = False # Mark as disconnected
                            # The main loop's reconnect logic will take over
                        
                except websockets.exceptions.ConnectionClosed as e:
                    self.connected = False # Mark as disconnected
                    retry_count += 1
                    logger.warning(f"WebSocket connection closed unexpectedly: Code={e.code}, Reason='{e.reason}'")
                    
                    if retry_count > max_retries:
                        logger.critical(f"EXCEEDED_MAX_RETRIES_AFTER_CONNECTION_CLOSED ({max_retries}), GIVING UP.")
                        self.last_error = f"Connection failed after {max_retries} retries (closed)"
                        self.running = False # Stop running
                        break
                    
                    logger.info(f"Reconnecting attempt {retry_count}/{max_retries} due to connection closed...")
                    await asyncio.sleep(2 ** min(retry_count, 4))
                    
                except Exception as e: # Catch-all for other errors in the loop
                    logger.critical(f"UNEXPECTED_ERROR_IN_RECEIVE_LOOP_INNER_TRY: {e}", exc_info=True)
                    self.last_error = str(e)
                    # Potentially mark as disconnected or attempt recovery
                    self.connected = False # Assume connection is compromised
                    await asyncio.sleep(1) # Brief pause before attempting reconnect via loop
                    
            logger.critical("RECEIVE_DATA_WHILE_LOOP_EXITED")
                    
        except asyncio.CancelledError:
            logger.critical("RECEIVE_DATA_TASK_CANCELLED", exc_info=True)
            # Ensure cleanup if cancelled
            # await self.disconnect() # disconnect() is called by stop()
            raise
        except Exception as e:
            logger.critical(f"FATAL_ERROR_IN_RECEIVE_DATA_OUTER_TRY: {e}", exc_info=True)
            self.connected = False
            self.last_error = str(e)
            self.running = False # Stop running on fatal error
        finally:
            logger.critical(f"RECEIVE_DATA_TASK_EXITING (Running: {self.running}, Connected: {self.connected})")
            # If the task exits and was supposed to be running, ensure disconnect is called.
            # However, stop() should handle this.
    
    def start(self):
        """Start the WebSocket client."""
        logger.critical("START_METHOD_CALLED")
        if self.running:
            logger.warning("WebSocket client already running")
            return False
        
        # Reset connection state
        self.connected = False # Ensure reset before start
        self.running = True
        self.last_error = None
        
        logger.critical("CREATING_RECEIVE_DATA_TASK")
        self.connection_task = asyncio.create_task(self.receive_data())
        self.connection_task.set_name("ReceiveDataTask") # Name the task

        # Add a callback to log the task's completion status
        def task_done_callback(task):
            try:
                task.result() # This will raise an exception if the task failed
                logger.critical(f"Connection task '{task.get_name()}' finished successfully.")
            except asyncio.CancelledError:
                logger.critical(f"Connection task '{task.get_name()}' was cancelled.")
            except Exception as e:
                logger.critical(f"Connection task '{task.get_name()}' FAILED: {type(e).__name__}: {e}", exc_info=True)

        self.connection_task.add_done_callback(task_done_callback)
        
        logger.info("WebSocket client start initiated with diagnostic callback.")
        return True
    
    def stop(self):
        """Stop the WebSocket client."""
        logger.critical("STOP_METHOD_CALLED")
        if not self.running:
            logger.warning("WebSocket client not running")
            return False
            
        self.running = False # Set running to False first
        
        # Cancel tasks
        if self.heartbeat_task and not self.heartbeat_task.done():
            logger.info("Cancelling heartbeat task.")
            self.heartbeat_task.cancel()
            
        if self.connection_task and not self.connection_task.done():
            logger.info("Cancelling connection task.")
            self.connection_task.cancel()
        
        # It's better to await disconnect if called from an async context,
        # but stop() might be called from sync. Creating a task is safer.
        # Ensure disconnect is robust.
        logger.info("Scheduling disconnect task.")
        asyncio.create_task(self.disconnect()) # Ensure disconnect runs
        
        logger.info("WebSocket client stop process initiated.")
        return True
    
    def is_connected(self):
        """Check if the client is connected and recently active."""
        if not self.connected or not self.ws:
            return False
            
        # Consider if last_message_time check is still needed or if self.connected is sufficient
        # For now, keeping it:
        if self.last_message_time > 0 and time.time() - self.last_message_time > 70: # Slightly increased timeout
            logger.warning("Connection stale - no messages in over 70 seconds")
            # This might indicate a problem even if 'connected' flag is true.
            # Consider setting self.connected = False here if strictness is needed.
            return False 
            
        return True
    
    def get_stats(self):
        """Get statistics about the WebSocket connection."""
        current_time = time.time()
        elapsed = current_time - self.last_message_time if self.last_message_time > 0 else 0
        
        return {
            "connected": self.connected,
            "running": self.running, # Added running state
            "message_count": self.message_count,
            "last_message_elapsed_sec": round(elapsed, 2),
            "last_error": self.last_error
        }
    
    def get_last_error(self):
        """Get the last error message."""
        return self.last_error
