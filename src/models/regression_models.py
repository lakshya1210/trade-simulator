"""
Regression models for slippage estimation and maker/taker proportion prediction.
"""
import numpy as np
from sklearn.linear_model import LinearRegression, LogisticRegression
from loguru import logger

class SlippageRegressionModel:
    """
    Linear regression model for slippage estimation.
    
    This model uses order size, market volatility, and order book depth
    to predict the expected slippage for a trade.
    """
    
    def __init__(self):
        """Initialize the slippage regression model."""
        # Initialize linear regression model
        self.model = LinearRegression()
        
        # Initialize data storage for training
        self.X_data = []  # Features: [order_size_normalized, volatility, book_imbalance]
        self.y_data = []  # Target: slippage_percentage
        
        # Model trained flag
        self.is_trained = False
    
    def add_training_data(self, order_size, mid_price, volatility, book_depth, book_imbalance, actual_slippage_pct):
        """
        Add a data point for training.
        
        Args:
            order_size (float): Size of the order
            mid_price (float): Mid price of the asset
            volatility (float): Market volatility
            book_depth (float): Order book depth
            book_imbalance (float): Order book imbalance (0-1)
            actual_slippage_pct (float): Actual slippage percentage
        """
        # Normalize order size by book depth
        order_size_normalized = order_size / book_depth if book_depth > 0 else order_size
        
        # Add features and target
        self.X_data.append([order_size_normalized, volatility, book_imbalance])
        self.y_data.append(actual_slippage_pct)
    
    def train(self, min_samples=10):
        """
        Train the regression model.
        
        Args:
            min_samples (int): Minimum number of samples required for training
            
        Returns:
            bool: True if training was successful, False otherwise
        """
        try:
            if len(self.X_data) < min_samples:
                logger.warning(f"Not enough training data: {len(self.X_data)}/{min_samples}")
                return False
            
            # Convert to numpy arrays
            X = np.array(self.X_data)
            y = np.array(self.y_data)
            
            # Train the model
            self.model.fit(X, y)
            self.is_trained = True
            
            # Log model coefficients
            logger.info(f"Slippage model trained. Coefficients: {self.model.coef_}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error training slippage model: {e}")
            return False
    
    def predict_slippage(self, order_size, mid_price, volatility, book_depth, book_imbalance):
        """
        Predict slippage percentage for a given order.
        
        Args:
            order_size (float): Size of the order
            mid_price (float): Mid price of the asset
            volatility (float): Market volatility
            book_depth (float): Order book depth
            book_imbalance (float): Order book imbalance (0-1)
            
        Returns:
            float: Predicted slippage percentage
        """
        try:
            # If model is not trained, use a simple heuristic
            if not self.is_trained:
                # Simple heuristic: 0.1% slippage per 1% of book depth
                return 0.1 * (order_size / book_depth * 100) if book_depth > 0 else 0.1
            
            # Normalize order size by book depth
            order_size_normalized = order_size / book_depth if book_depth > 0 else order_size
            
            # Create input features
            X = np.array([[order_size_normalized, volatility, book_imbalance]])
            
            # Predict slippage percentage
            slippage_pct = self.model.predict(X)[0]
            
            # Ensure slippage is non-negative
            return max(0, slippage_pct)
            
        except Exception as e:
            logger.error(f"Error predicting slippage: {e}")
            return 0.1  # Default to 0.1% slippage on error


class MakerTakerRegressionModel:
    """
    Logistic regression model for predicting maker/taker proportion.
    
    This model predicts the probability that an order will be filled as a maker
    vs. taker based on order book characteristics.
    """
    
    def __init__(self):
        """Initialize the maker/taker regression model."""
        # Initialize logistic regression model
        self.model = LogisticRegression()
        
        # Initialize data storage for training
        self.X_data = []  # Features: [order_size_normalized, volatility, book_imbalance, spread_pct]
        self.y_data = []  # Target: 1 for maker, 0 for taker
        
        # Model trained flag
        self.is_trained = False
    
    def add_training_data(self, order_size, book_depth, volatility, book_imbalance, spread_pct, is_maker):
        """
        Add a data point for training.
        
        Args:
            order_size (float): Size of the order
            book_depth (float): Order book depth
            volatility (float): Market volatility
            book_imbalance (float): Order book imbalance (0-1)
            spread_pct (float): Spread as percentage of price
            is_maker (bool): True if the order was filled as a maker, False for taker
        """
        # Normalize order size by book depth
        order_size_normalized = order_size / book_depth if book_depth > 0 else order_size
        
        # Add features and target
        self.X_data.append([order_size_normalized, volatility, book_imbalance, spread_pct])
        self.y_data.append(1 if is_maker else 0)
    
    def train(self, min_samples=20):
        """
        Train the logistic regression model.
        
        Args:
            min_samples (int): Minimum number of samples required for training
            
        Returns:
            bool: True if training was successful, False otherwise
        """
        try:
            if len(self.X_data) < min_samples:
                logger.warning(f"Not enough training data: {len(self.X_data)}/{min_samples}")
                return False
            
            # Convert to numpy arrays
            X = np.array(self.X_data)
            y = np.array(self.y_data)
            
            # Train the model
            self.model.fit(X, y)
            self.is_trained = True
            
            # Log model coefficients
            logger.info(f"Maker/Taker model trained. Coefficients: {self.model.coef_}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error training maker/taker model: {e}")
            return False
    
    def predict_maker_proportion(self, order_size, book_depth, volatility, book_imbalance, spread_pct):
        """
        Predict the probability of an order being filled as a maker.
        
        Args:
            order_size (float): Size of the order
            book_depth (float): Order book depth
            volatility (float): Market volatility
            book_imbalance (float): Order book imbalance (0-1)
            spread_pct (float): Spread as percentage of price
            
        Returns:
            float: Probability of being filled as a maker (0-1)
        """
        try:
            # If model is not trained, use a simple heuristic
            if not self.is_trained:
                # Simple heuristic: probability decreases with order size and volatility
                # and increases with spread
                p_maker = 0.5 - (order_size / book_depth) * 0.5 + spread_pct * 0.1
                return max(0, min(1, p_maker))
            
            # Normalize order size by book depth
            order_size_normalized = order_size / book_depth if book_depth > 0 else order_size
            
            # Create input features
            X = np.array([[order_size_normalized, volatility, book_imbalance, spread_pct]])
            
            # Predict maker probability
            p_maker = self.model.predict_proba(X)[0][1]
            
            return p_maker
            
        except Exception as e:
            logger.error(f"Error predicting maker proportion: {e}")
            return 0.5  # Default to 50% on error
