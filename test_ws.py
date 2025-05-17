import asyncio
import websockets
import ssl

async def test():
    uri = "wss://ws.gomarket-cpp.goquant.io/ws/l2-orderbook/okx/BTC-USDT-SWAP"
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        async with websockets.connect(uri, ssl=ssl_context) as ws:
            print("Connected!")
            data = await ws.recv()
            print(f"Received data: {data[:100]}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())