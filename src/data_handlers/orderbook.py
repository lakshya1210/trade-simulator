"""
Orderbook processor for handling L2 market data.
"""
import time
import numpy as np
from loguru import logger
import json

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
        
    def update(self, data):
        """
        Update the orderbook with new data.
        
        Args:
            data (dict): L2 orderbook data from WebSocket
        """
        start_time = time.time()
        
        try:
            # Debug the incoming data
            logger.debug(f"Received data: {json.dumps(data)[:100]}...")
            
            # Handle potential different data formats
            # Check if we have a nested data structure
            if "data" in data:
                # Extract the orderbook data from the nested structure
                orderbook_data = data["data"][0] if isinstance(data["data"], list) else data["data"]
            else:
                orderbook_data = data
            
            # Update metadata
            self.timestamp = orderbook_data.get("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ"))
            self.exchange = orderbook_data.get("exchange", "OKX")
            self.symbol = orderbook_data.get("symbol", "BTC-USDT")
            
            # Find the bids and asks in the data
            bids_key = next((k for k in orderbook_data if k.lower() in ["bids", "bid"]), None)
            asks_key = next((k for k in orderbook_data if k.lower() in ["asks", "ask"]), None)
            
            # Update bids
            if bids_key and orderbook_data[bids_key]:
                # Clear previous bids
                self.bids.clear()
                
                # Add new bids
                for bid in orderbook_data[bids_key]:
                    if isinstance(bid, list) and len(bid) >= 2:
                        price = float(bid[0])
                        quantity = float(bid[1])
                        self.bids[price] = quantity
                
                logger.debug(f"Updated {len(self.bids)} bid prices")
            
            # Update asks
            if asks_key and orderbook_data[asks_key]:
                # Clear previous asks
                self.asks.clear()
                
                # Add new asks
                for ask in orderbook_data[asks_key]:
                    if isinstance(ask, list) and len(ask) >= 2:
                        price = float(ask[0])
                        quantity = float(ask[1])
                        self.asks[price] = quantity
                
                logger.debug(f"Updated {len(self.asks)} ask prices")
                
            # Record processing time
            end_time = time.time()
            processing_time = (end_time - start_time) * 1000  # Convert to milliseconds
            self.processing_times.append(processing_time)
            
            # Keep only the last 100 processing times
            if len(self.processing_times) > 100:
                self.processing_times = self.processing_times[-100:]
            
            self.last_update_time = end_time
            logger.debug(f"Orderbook valid: {self.is_valid()}")
            
        except Exception as e:
            logger.error(f"Error updating orderbook: {e}")
        
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
        return (self.timestamp is not None and 
                self.bids and 
                self.asks and 
                self.last_update_time > 0)
