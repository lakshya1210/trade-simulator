import asyncio
import websockets
import ssl
import json
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_websocket():
    # URL from your config
    url = "wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP"
    
    # Create SSL context with verification disabled
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        logger.info(f"Connecting to {url}")
        async with websockets.connect(url, ssl=ssl_context) as ws:
            logger.info("Connected successfully!")
            
            # Wait for and process 5 messages
            for i in range(5):
                logger.info(f"Waiting for message {i+1}...")
                message = await ws.recv()
                data = json.loads(message)
                logger.info(f"Received: {json.dumps(data, indent=2)[:200]}...")
                
                # Display some orderbook data
                if "asks" in data and data["asks"]:
                    logger.info(f"First ask: {data['asks'][0]}")
                if "bids" in data and data["bids"]:
                    logger.info(f"First bid: {data['bids'][0]}")
                
                await asyncio.sleep(1)
    
    except Exception as e:
        logger.error(f"Error: {e}")

asyncio.run(test_websocket())