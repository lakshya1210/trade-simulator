"""
Orderbook processor for handling L2 market data.
"""
import time
import json
import numpy as np
from loguru import logger

class Orderbook:
    """
    Class to manage and process the orderbook data.
    Keeps track of bids and asks, and provides methods to calculate statistics.
    """
    
    def __init__(self):
        """Initialize an empty orderbook."""
        self.bids = {}  # price -> quantity
        self.asks = {}  # price -> quantity
        self.timestamp = None
        self.exchange = None
        self.symbol = None
        self.last_update_time = 0
        self.processing_times = []  # To track processing latency
        self.status_message = "Waiting for data..."
        self.received_data = False
        
    def update(self, data):
        """
        Update the orderbook with new data.
        
        Args:
            data (dict): L2 orderbook data from WebSocket
        """
        start_time = time.time()
        
        try:
            # Debug the incoming data structure more thoroughly
            logger.debug(f"Data keys: {list(data.keys())}")
            if "arg" in data:
                logger.debug(f"Arg: {data['arg']}")
            if "data" in data:
                if isinstance(data["data"], list) and len(data["data"]) > 0:
                    logger.debug(f"First data item keys: {list(data['data'][0].keys())}")
                    
                    # Print sample of bids and asks if they exist
                    if "bids" in data["data"][0]:
                        logger.debug(f"First 3 bids: {data['data'][0]['bids'][:3]}")
                    if "asks" in data["data"][0]:
                        logger.debug(f"First 3 asks: {data['data'][0]['asks'][:3]}")
            
            # Handle OKX format
            if "arg" in data and "data" in data:
                # This is OKX format
                logger.info("Processing OKX format data")
                
                arg = data.get("arg", {})
                self.exchange = "OKX"
                self.symbol = arg.get("instId", "BTC-USDT")
                
                # Get the orderbook data
                ob_data = data.get("data", [])
                if not ob_data or len(ob_data) == 0:
                    logger.warning("Empty orderbook data received")
                    self.status_message = "Received empty orderbook data"
                    return
                
                # Get the first orderbook entry
                orderbook = ob_data[0]
                
                # Log full orderbook for debugging
                logger.info(f"ORDERBOOK DATA: {json.dumps(orderbook)[:500]}")
                
                # Extract timestamp
                self.timestamp = orderbook.get("ts")
                
                # Clear previous bids and asks
                self.bids.clear()
                self.asks.clear()
                
                # Process bids
                if "bids" in orderbook and orderbook["bids"]:
                    logger.info(f"Processing {len(orderbook['bids'])} bids")
                    for bid in orderbook["bids"]:
                        if len(bid) >= 2:
                            try:
                                price = float(bid[0])
                                quantity = float(bid[1])
                                self.bids[price] = quantity
                            except (ValueError, TypeError) as e:
                                logger.error(f"Error parsing bid: {bid} - {e}")
                
                # Process asks
                if "asks" in orderbook and orderbook["asks"]:
                    logger.info(f"Processing {len(orderbook['asks'])} asks")
                    for ask in orderbook["asks"]:
                        if len(ask) >= 2:
                            try:
                                price = float(ask[0])
                                quantity = float(ask[1])
                                self.asks[price] = quantity
                            except (ValueError, TypeError) as e:
                                logger.error(f"Error parsing ask: {ask} - {e}")
                
                logger.info(f"Updated orderbook: {len(self.bids)} bids, {len(self.asks)} asks")
                self.received_data = True
                self.status_message = "Orderbook updated successfully"
            
            # Original format from the project spec
            elif "bids" in data and "asks" in data:
                # Standard orderbook format
                # Update metadata
                self.timestamp = data.get("timestamp")
                self.exchange = data.get("exchange")
                self.symbol = data.get("symbol")
                
                # Update bids and asks
                if "bids" in data:
                    # Clear previous bids
                    self.bids.clear()
                    
                    # Add new bids
                    for bid in data["bids"]:
                        if len(bid) >= 2:
                            price = float(bid[0])
                            quantity = float(bid[1])
                            self.bids[price] = quantity
                
                if "asks" in data:
                    # Clear previous asks
                    self.asks.clear()
                    
                    # Add new asks
                    for ask in data["asks"]:
                        if len(ask) >= 2:
                            price = float(ask[0])
                            quantity = float(ask[1])
                            self.asks[price] = quantity
                            
                self.received_data = True
                self.status_message = "Orderbook updated successfully"
            elif "event" in data:
                # Process event messages
                if data.get("event") == "subscribe" and data.get("code") == "0":
                    logger.info("Subscription confirmed")
                    self.status_message = "WebSocket subscription confirmed"
                elif data.get("event") == "error":
                    logger.error(f"WebSocket error event: {data}")
                    self.status_message = f"WebSocket error: {data.get('msg', 'Unknown error')}"
                else:
                    logger.debug(f"Skipping event message: {data.get('event')}")
            else:
                logger.warning(f"Unrecognized data format: {list(data.keys())}")
                self.status_message = f"Unrecognized data format: {list(data.keys())}"
                return
            
            # Record processing time
            end_time = time.time()
            processing_time = (end_time - start_time) * 1000  # Convert to milliseconds
            self.processing_times.append(processing_time)
            
            # Keep only the last 100 processing times
            if len(self.processing_times) > 100:
                self.processing_times = self.processing_times[-100:]
            
            self.last_update_time = end_time
            
            # Log whether the orderbook is valid
            valid = self.is_valid()
            logger.debug(f"Orderbook valid: {valid}")
            if valid:
                mid_price = self.get_mid_price()
                spread = self.get_spread_percentage()
                logger.info(f"Orderbook: price=${mid_price:.2f}, spread={spread:.4f}%")
            
        except Exception as e:
            logger.error(f"Error updating orderbook: {e}")
            self.status_message = f"Error updating orderbook: {e}"
    
    def get_best_bid(self):
        """Get the best (highest) bid price and quantity."""
        if not self.bids:
            return None, 0
        
        best_price = max(self.bids.keys())
        return best_price, self.bids[best_price]
    
    def get_best_ask(self):
        """Get the best (lowest) ask price and quantity."""
        if not self.asks:
            return None, 0
        
        best_price = min(self.asks.keys())
        return best_price, self.asks[best_price]
    
    def get_mid_price(self):
        """Get the mid price (average of best bid and best ask)."""
        best_bid, _ = self.get_best_bid()
        best_ask, _ = self.get_best_ask()
        
        if best_bid is None or best_ask is None:
            return None
        
        return (best_bid + best_ask) / 2
    
    def get_spread(self):
        """Get the spread (difference between best ask and best bid)."""
        best_bid, _ = self.get_best_bid()
        best_ask, _ = self.get_best_ask()
        
        if best_bid is None or best_ask is None:
            return None
        
        return best_ask - best_bid
    
    def get_spread_percentage(self):
        """Get the spread as a percentage of the mid price."""
        spread = self.get_spread()
        mid_price = self.get_mid_price()
        
        if spread is None or mid_price is None or mid_price == 0:
            return None
        
        return (spread / mid_price) * 100
    
    def estimate_slippage(self, quantity, side="buy"):
        """
        Estimate slippage for a market order of the given quantity.
        
        Args:
            quantity (float): Order quantity in base currency
            side (str): "buy" or "sell"
            
        Returns:
            tuple: (slippage_amount, slippage_percentage)
        """
        if side.lower() == "buy":
            # For buy orders, we walk up the ask side
            if not self.asks:
                return None, None
            
            # Sort asks by price (ascending)
            sorted_asks = sorted(self.asks.items())
            
            # Calculate the weighted average price
            remaining_quantity = quantity
            total_cost = 0
            
            for price, available_quantity in sorted_asks:
                if remaining_quantity <= 0:
                    break
                
                filled_quantity = min(remaining_quantity, available_quantity)
                total_cost += filled_quantity * price
                remaining_quantity -= filled_quantity
            
            # If we couldn't fill the entire order
            if remaining_quantity > 0:
                logger.warning(f"Not enough liquidity to fill buy order of {quantity}")
                return None, None
            
            # Calculate effective price
            effective_price = total_cost / quantity
            
            # Calculate slippage
            best_ask, _ = self.get_best_ask()
            slippage_amount = effective_price - best_ask
            slippage_percentage = (slippage_amount / best_ask) * 100
            
            return slippage_amount, slippage_percentage
            
        elif side.lower() == "sell":
            # For sell orders, we walk down the bid side
            if not self.bids:
                return None, None
            
            # Sort bids by price (descending)
            sorted_bids = sorted(self.bids.items(), reverse=True)
            
            # Calculate the weighted average price
            remaining_quantity = quantity
            total_revenue = 0
            
            for price, available_quantity in sorted_bids:
                if remaining_quantity <= 0:
                    break
                
                filled_quantity = min(remaining_quantity, available_quantity)
                total_revenue += filled_quantity * price
                remaining_quantity -= filled_quantity
            
            # If we couldn't fill the entire order
            if remaining_quantity > 0:
                logger.warning(f"Not enough liquidity to fill sell order of {quantity}")
                return None, None
            
            # Calculate effective price
            effective_price = total_revenue / quantity
            
            # Calculate slippage
            best_bid, _ = self.get_best_bid()
            slippage_amount = best_bid - effective_price
            slippage_percentage = (slippage_amount / best_bid) * 100
            
            return slippage_amount, slippage_percentage
        
        else:
            logger.error(f"Invalid side: {side}")
            return None, None
    
    def calculate_order_book_imbalance(self):
        """Calculate order book imbalance as a ratio of bid volume to total volume."""
        total_bid_volume = sum(self.bids.values())
        total_ask_volume = sum(self.asks.values())
        
        total_volume = total_bid_volume + total_ask_volume
        
        if total_volume == 0:
            return 0.5  # Neutral when no volume
        
        return total_bid_volume / total_volume
    
    def get_average_processing_time(self):
        """Get the average processing time in milliseconds."""
        if not self.processing_times:
            return 0
        
        return np.mean(self.processing_times)
    
    def get_orderbook_depth(self, levels=10):
        """
        Get the depth of the orderbook at the specified levels.
        
        Args:
            levels (int): Number of price levels to consider
            
        Returns:
            tuple: (bid_depth, ask_depth) in base currency
        """
        # Sort bids and asks
        sorted_bids = sorted(self.bids.items(), reverse=True)
        sorted_asks = sorted(self.asks.items())
        
        # Calculate bid depth
        bid_depth = sum(quantity for _, quantity in sorted_bids[:levels])
        
        # Calculate ask depth
        ask_depth = sum(quantity for _, quantity in sorted_asks[:levels])
        
        return bid_depth, ask_depth
    
    def get_volatility_estimate(self, window_size=20):
        """
        Estimate volatility from mid price changes.
        This is a placeholder - in a real system, you would track price changes over time.
        
        Args:
            window_size (int): Number of price changes to consider
            
        Returns:
            float: Estimated volatility
        """
        # In a real implementation, you would calculate this from historical mid prices
        # For demonstration purposes, return a random value between 0.005 and 0.02
        return 0.01  # Placeholder
    
    def is_valid(self):
        """Check if the orderbook has valid data."""
        return (self.bids and 
                self.asks and 
                self.last_update_time > 0)
    
    def get_status(self):
        """Get current orderbook status."""
        if self.is_valid():
            return f"Connected: {self.symbol}, {len(self.bids)} bids, {len(self.asks)} asks"
        elif self.received_data:
            return "Partial data received, waiting for complete orderbook"
        else:
            return self.status_message
