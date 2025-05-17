"""
Main entry point for the trading simulator application.
"""
import asyncio
import sys
import signal
from loguru import logger

from src.config import LOG_LEVEL
from src.data_handlers.websocket_client import WebSocketClient
from src.data_handlers.orderbook import Orderbook
from src.models.almgren_chriss import AlmgrenChrissModel
from src.models.regression_models import SlippageRegressionModel, MakerTakerRegressionModel
from src.ui.app import SimulatorController, run_application


def setup_logging():
    """Configure the logger."""
    logger.remove()  # Remove default handler
    logger.add(sys.stderr, level=LOG_LEVEL)
    logger.add("simulator.log", rotation="10 MB", level=LOG_LEVEL)


async def main():
    """Main entry point for the application."""
    # Set up logging
    setup_logging()
    logger.info("Starting trade simulator application")
    
    # Create orderbook instance
    orderbook = Orderbook()
    logger.info("Created orderbook processor")
    
    # Create WebSocket client
    def orderbook_callback(data):
        """Callback function for WebSocket data."""
        orderbook.update(data)
    
    ws_client = WebSocketClient(callback=orderbook_callback)
    logger.info("Created WebSocket client")
    
    # Create regression models
    slippage_model = SlippageRegressionModel()
    maker_taker_model = MakerTakerRegressionModel()
    logger.info("Created regression models")
    
    # Create market impact model
    market_impact_model = AlmgrenChrissModel()
    logger.info("Created market impact model")
    
    # Create simulator controller
    controller = SimulatorController(
        orderbook, slippage_model, maker_taker_model, market_impact_model
    )
    logger.info("Created simulator controller")
    
    # Start WebSocket client
    ws_client.start()
    logger.info("Started WebSocket client")
    
    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        """Handle termination signals."""
        logger.info("Received termination signal, shutting down...")
        ws_client.stop()
        loop.stop()
    
    # Register signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    # Run the application
    logger.info("Starting UI application")
    
    # This will block until the UI is closed
    run_application(controller)
    
    # Clean up
    ws_client.stop()
    logger.info("Application terminated")


if __name__ == "__main__":
    # Run the asyncio event loop
    asyncio.run(main())
