"""
Implementation of the Almgren-Chriss market impact model.
"""
import numpy as np
from loguru import logger
from ..config import AC_PARAMETERS

class AlmgrenChrissModel:
    """
    Almgren-Chriss market impact model for optimal execution.
    This model estimates the market impact of a trade based on order size,
    market volatility, and liquidity parameters.
    """
    
    def __init__(self, 
                 market_impact_factor=AC_PARAMETERS['market_impact_factor'],
                 volatility_factor=AC_PARAMETERS['volatility_factor'],
                 risk_aversion=AC_PARAMETERS['risk_aversion']):
        """
        Initialize the Almgren-Chriss model.
        
        Args:
            market_impact_factor (float): Temporary market impact factor
            volatility_factor (float): Volatility scaling factor
            risk_aversion (float): Risk aversion parameter
        """
        self.market_impact_factor = market_impact_factor
        self.volatility_factor = volatility_factor
        self.risk_aversion = risk_aversion
    
    def estimate_market_impact(self, quantity, price, volatility, book_depth):
        """
        Estimate the market impact of a trade using the Almgren-Chriss model.
        
        Args:
            quantity (float): Order quantity in base currency units
            price (float): Current price of the asset
            volatility (float): Asset price volatility
            book_depth (float): Order book depth (liquidity)
            
        Returns:
            tuple: (temporary_impact, permanent_impact, total_impact)
        """
        try:
            # Normalize quantity by book depth for impact calculation
            normalized_quantity = quantity / book_depth if book_depth > 0 else quantity
            
            # Calculate the temporary impact (immediate price change due to the order)
            # This is based on the square-root law: impact ~ sigma * sqrt(quantity/volume)
            temporary_impact = self.market_impact_factor * volatility * price * np.sqrt(normalized_quantity)
            
            # Calculate the permanent impact (long-term price change)
            # This is based on a linear model: permanent impact ~ quantity/volume
            permanent_impact = self.market_impact_factor * volatility * price * normalized_quantity * 0.1
            
            # Total impact is the sum of temporary and permanent impact
            total_impact = temporary_impact + permanent_impact
            
            # Adjust impact based on risk aversion parameter
            total_impact *= (1 + self.risk_aversion * volatility)
            
            # Return the calculated market impact components
            return {
                "temporary_impact": temporary_impact,
                "permanent_impact": permanent_impact,
                "total_impact": total_impact,
                "impact_percentage": (total_impact / price) * 100 if price > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating market impact: {e}")
            return {
                "temporary_impact": 0,
                "permanent_impact": 0,
                "total_impact": 0,
                "impact_percentage": 0
            }
    
    def optimize_execution_schedule(self, total_quantity, target_time, volatility, book_depth, price):
        """
        Optimize the execution schedule for a large order using the Almgren-Chriss model.
        
        Args:
            total_quantity (float): Total order quantity
            target_time (float): Target execution time (in hours)
            volatility (float): Asset price volatility
            book_depth (float): Order book depth
            price (float): Current price of the asset
            
        Returns:
            dict: Optimal execution schedule and estimated costs
        """
        try:
            # Number of execution steps
            n_steps = 10  # Fixed number of steps for simplicity
            
            # Time between steps
            time_per_step = target_time / n_steps
            
            # Calculate the optimal trading trajectory
            # The classical Almgren-Chriss model gives a time-weighted trading schedule
            # For simplicity, we'll use a linear decay model
            
            # For a risk-neutral trader, linear decay is optimal
            # For a risk-averse trader, front-loading is optimal
            
            # Adjust the schedule based on risk aversion
            if self.risk_aversion > 0.5:
                # Front-loaded schedule for risk-averse traders
                schedule = np.array([np.exp(-self.risk_aversion * i / n_steps) for i in range(n_steps)])
            else:
                # Linear schedule for risk-neutral traders
                schedule = np.array([1 - (i / n_steps) for i in range(n_steps)])
            
            # Normalize the schedule to sum to 1
            schedule = schedule / np.sum(schedule)
            
            # Calculate the trade sizes at each step
            trade_sizes = schedule * total_quantity
            
            # Calculate the expected impact at each step
            impacts = []
            total_impact = 0
            
            for i, trade_size in enumerate(trade_sizes):
                step_impact = self.estimate_market_impact(
                    trade_size, price, volatility, book_depth
                )["total_impact"]
                
                impacts.append(step_impact)
                total_impact += step_impact
            
            # Calculate the expected execution price
            expected_price = price - (total_impact / total_quantity) if total_quantity > 0 else price
            
            return {
                "schedule": schedule.tolist(),
                "trade_sizes": trade_sizes.tolist(),
                "impacts": impacts,
                "total_impact": total_impact,
                "expected_price": expected_price,
                "time_per_step": time_per_step
            }
            
        except Exception as e:
            logger.error(f"Error optimizing execution schedule: {e}")
            return {
                "schedule": [],
                "trade_sizes": [],
                "impacts": [],
                "total_impact": 0,
                "expected_price": price,
                "time_per_step": 0
            }
