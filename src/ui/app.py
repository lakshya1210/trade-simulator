"""
UI implementation for the trading simulator.
"""
import sys
import time
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QColor, QPalette
from loguru import logger

from ..config import (
    DEFAULT_EXCHANGE, DEFAULT_ASSET, DEFAULT_ORDER_TYPE,
    DEFAULT_QUANTITY, DEFAULT_VOLATILITY, DEFAULT_FEE_TIER,
    AVAILABLE_ASSETS, ORDER_TYPES, FEE_TIERS, UI_REFRESH_RATE_MS,
    WEBSOCKET_URL
)


class SimulatorUI(QMainWindow):
    """Main UI window for the trading simulator."""
    
    def __init__(self, simulator_controller):
        """
        Initialize the UI.
        
        Args:
            simulator_controller: Controller for the simulator logic
        """
        super().__init__()
        
        self.controller = simulator_controller
        self.last_update_time = 0
        
        # Set up the UI
        self.init_ui()
        
        # Set up the timer for UI updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(UI_REFRESH_RATE_MS)
    
    def init_ui(self):
        """Initialize the UI components."""
        # Set window properties
        self.setWindowTitle("Trade Simulator")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for left and right panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Create left panel (input parameters)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Add input form
        input_group = QGroupBox("Input Parameters")
        input_layout = QFormLayout()
        
        # Exchange
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItem(DEFAULT_EXCHANGE)
        input_layout.addRow("Exchange:", self.exchange_combo)
        
        # Asset
        self.asset_combo = QComboBox()
        for asset in AVAILABLE_ASSETS:
            self.asset_combo.addItem(asset)
        self.asset_combo.setCurrentText(DEFAULT_ASSET)
        input_layout.addRow("Spot Asset:", self.asset_combo)
        
        # Order Type
        self.order_type_combo = QComboBox()
        for order_type in ORDER_TYPES:
            self.order_type_combo.addItem(order_type)
        self.order_type_combo.setCurrentText(DEFAULT_ORDER_TYPE)
        input_layout.addRow("Order Type:", self.order_type_combo)
        
        # Quantity
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(1, 100000)
        self.quantity_spin.setValue(DEFAULT_QUANTITY)
        self.quantity_spin.setSuffix(" USD")
        input_layout.addRow("Quantity:", self.quantity_spin)
        
        # Volatility
        self.volatility_spin = QDoubleSpinBox()
        self.volatility_spin.setRange(0.001, 1.0)
        self.volatility_spin.setValue(DEFAULT_VOLATILITY)
        self.volatility_spin.setDecimals(4)
        self.volatility_spin.setSingleStep(0.001)
        input_layout.addRow("Volatility:", self.volatility_spin)
        
        # Fee Tier
        self.fee_tier_combo = QComboBox()
        for tier in FEE_TIERS.keys():
            self.fee_tier_combo.addItem(tier)
        self.fee_tier_combo.setCurrentText(DEFAULT_FEE_TIER)
        input_layout.addRow("Fee Tier:", self.fee_tier_combo)
        
        # Add input layout to group
        input_group.setLayout(input_layout)
        
        # Add calculate button
        self.calculate_button = QPushButton("Calculate")
        self.calculate_button.clicked.connect(self.on_calculate)
        
        # Add connection status
        self.connection_status = QLabel("Connection Status: Disconnected")
        self.connection_status.setStyleSheet("color: red;")
        
        # Add input group and button to left layout
        left_layout.addWidget(input_group)
        left_layout.addWidget(self.calculate_button)
        left_layout.addWidget(self.connection_status)
        left_layout.addStretch()
        
        # Create right panel (output parameters)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Add output form
        output_group = QGroupBox("Output Parameters")
        output_layout = QFormLayout()
        
        # Create output labels
        self.price_label = QLabel("N/A")
        self.slippage_label = QLabel("N/A")
        self.fees_label = QLabel("N/A")
        self.market_impact_label = QLabel("N/A")
        self.net_cost_label = QLabel("N/A")
        self.maker_taker_label = QLabel("N/A")
        self.latency_label = QLabel("N/A")
        
        # Add output labels to form
        output_layout.addRow("Current Price:", self.price_label)
        output_layout.addRow("Expected Slippage:", self.slippage_label)
        output_layout.addRow("Expected Fees:", self.fees_label)
        output_layout.addRow("Expected Market Impact:", self.market_impact_label)
        output_layout.addRow("Net Cost:", self.net_cost_label)
        output_layout.addRow("Maker/Taker Proportion:", self.maker_taker_label)
        output_layout.addRow("Internal Latency:", self.latency_label)
        
        # Add output layout to group
        output_group.setLayout(output_layout)
        
        # Add orderbook visualization
        orderbook_group = QGroupBox("Order Book")
        orderbook_layout = QVBoxLayout()
        
        # Create orderbook table
        self.orderbook_table = QTableWidget(20, 4)  # 20 rows, 4 columns
        self.orderbook_table.setHorizontalHeaderLabels(["Bid Price", "Bid Size", "Ask Price", "Ask Size"])
        self.orderbook_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Add orderbook table to layout
        orderbook_layout.addWidget(self.orderbook_table)
        orderbook_group.setLayout(orderbook_layout)
        
        # Add output group to right layout
        right_layout.addWidget(output_group)
        right_layout.addWidget(orderbook_group)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # Set initial splitter sizes
        splitter.setSizes([400, 800])
        
        # Show the UI
        self.show()
    
    def update_ui(self):
        """Update the UI with the latest data."""
        # Only update every UI_REFRESH_RATE_MS milliseconds
        current_time = time.time()
        if current_time - self.last_update_time < UI_REFRESH_RATE_MS / 1000:
            return
        
        self.last_update_time = current_time
        
        # Update connection status
        if self.controller.is_connected():
            self.connection_status.setText("Connection Status: Connected")
            self.connection_status.setStyleSheet("color: green;")
        else:
            self.connection_status.setText("Connection Status: Disconnected")
            self.connection_status.setStyleSheet("color: red;")
        
        # Update price
        mid_price = self.controller.get_mid_price()
        if mid_price:
            self.price_label.setText(f"${mid_price:.2f}")
        
        # Update orderbook visualization
        self.update_orderbook_table()
        
        # If a calculation was performed, update the results
        if hasattr(self, 'last_results') and self.last_results:
            self.update_results(self.last_results)
    
    def update_orderbook_table(self):
        """Update the orderbook table with the latest data."""
        bids = self.controller.get_bids()
        asks = self.controller.get_asks()
        
        # Clear the table
        self.orderbook_table.clearContents()
        
        # Get the top 10 bids and asks
        top_bids = sorted(bids.items(), reverse=True)[:10]
        top_asks = sorted(asks.items())[:10]
        
        # Fill in the bids
        for i, (price, size) in enumerate(top_bids):
            if i < self.orderbook_table.rowCount():
                # Bid price
                price_item = QTableWidgetItem(f"{price:.2f}")
                price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                price_item.setForeground(QColor(0, 128, 0))  # Green color for bids
                self.orderbook_table.setItem(i, 0, price_item)
                
                # Bid size
                size_item = QTableWidgetItem(f"{size:.4f}")
                size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.orderbook_table.setItem(i, 1, size_item)
        
        # Fill in the asks
        for i, (price, size) in enumerate(top_asks):
            if i < self.orderbook_table.rowCount():
                # Ask price
                price_item = QTableWidgetItem(f"{price:.2f}")
                price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                price_item.setForeground(QColor(255, 0, 0))  # Red color for asks
                self.orderbook_table.setItem(i, 2, price_item)
                
                # Ask size
                size_item = QTableWidgetItem(f"{size:.4f}")
                size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.orderbook_table.setItem(i, 3, size_item)
    
    def on_calculate(self):
        """Handle calculate button click event."""
        # Get input parameters
        exchange = self.exchange_combo.currentText()
        asset = self.asset_combo.currentText()
        order_type = self.order_type_combo.currentText()
        quantity = self.quantity_spin.value()
        volatility = self.volatility_spin.value()
        fee_tier = self.fee_tier_combo.currentText()
        
        # Call the controller to calculate results
        results = self.controller.calculate_transaction_costs(
            exchange, asset, order_type, quantity, volatility, fee_tier
        )
        
        # Save results for UI updates
        self.last_results = results
        
        # Update the UI with results
        self.update_results(results)
    
    def update_results(self, results):
        """Update the UI with calculation results."""
        # Update output labels
        self.slippage_label.setText(f"{results['slippage']:.4f}% (${results['slippage_usd']:.2f})")
        self.fees_label.setText(f"{results['fees']:.4f}% (${results['fees_usd']:.2f})")
        self.market_impact_label.setText(f"{results['market_impact']:.4f}% (${results['market_impact_usd']:.2f})")
        self.net_cost_label.setText(f"{results['net_cost']:.4f}% (${results['net_cost_usd']:.2f})")
        self.maker_taker_label.setText(f"{results['maker_proportion']*100:.1f}% / {100-results['maker_proportion']*100:.1f}%")
        self.latency_label.setText(f"{results['latency_ms']:.2f} ms")


class SimulatorController:
    """
    Controller class for the simulator.
    Acts as an interface between the UI and the data/models.
    """
    
    def __init__(self, orderbook, slippage_model, maker_taker_model, market_impact_model):
        """
        Initialize the controller.
        
        Args:
            orderbook: Orderbook instance
            slippage_model: Slippage regression model
            maker_taker_model: Maker/taker regression model
            market_impact_model: Market impact model
        """
        self.orderbook = orderbook
        self.slippage_model = slippage_model
        self.maker_taker_model = maker_taker_model
        self.market_impact_model = market_impact_model
    
    def is_connected(self):
        """Check if the WebSocket connection is active."""
        return self.orderbook.is_valid()
    
    def get_mid_price(self):
        """Get the current mid price."""
        return self.orderbook.get_mid_price()
    
    def get_bids(self):
        """Get the current bids."""
        return self.orderbook.bids
    
    def get_asks(self):
        """Get the current asks."""
        return self.orderbook.asks
    
    def calculate_transaction_costs(self, exchange, asset, order_type, quantity, volatility, fee_tier):
        """
        Calculate transaction costs for the given parameters.
        
        Args:
            exchange (str): Exchange name
            asset (str): Asset name
            order_type (str): Order type
            quantity (float): Order quantity in USD
            volatility (float): Market volatility
            fee_tier (str): Fee tier
            
        Returns:
            dict: Transaction cost components
        """
        # Get current mid price
        mid_price = self.orderbook.get_mid_price()
        if mid_price is None:
            logger.warning("Cannot calculate costs: no valid orderbook data")
            return {
                "slippage": 0,
                "slippage_usd": 0,
                "fees": 0,
                "fees_usd": 0,
                "market_impact": 0,
                "market_impact_usd": 0,
                "net_cost": 0,
                "net_cost_usd": 0,
                "maker_proportion": 0.5,
                "latency_ms": 0
            }
        
        # Convert USD quantity to asset quantity
        asset_quantity = quantity / mid_price
        
        # Calculate expected slippage
        book_imbalance = self.orderbook.calculate_order_book_imbalance()
        bid_depth, ask_depth = self.orderbook.get_orderbook_depth()
        book_depth = ask_depth  # For buy orders, we use ask depth
        
        # Get spread percentage
        spread_pct = self.orderbook.get_spread_percentage() or 0
        
        # Calculate slippage
        slippage_pct = self.slippage_model.predict_slippage(
            asset_quantity, mid_price, volatility, book_depth, book_imbalance
        )
        slippage_usd = (slippage_pct / 100) * quantity
        
        # Calculate fees
        maker_proportion = self.maker_taker_model.predict_maker_proportion(
            asset_quantity, book_depth, volatility, book_imbalance, spread_pct
        )
        
        # Get fee rates from the fee tier
        maker_fee = FEE_TIERS[fee_tier]["maker"]
        taker_fee = FEE_TIERS[fee_tier]["taker"]
        
        # Calculate weighted average fee
        avg_fee_rate = maker_proportion * maker_fee + (1 - maker_proportion) * taker_fee
        fee_usd = avg_fee_rate * quantity
        fee_pct = avg_fee_rate * 100
        
        # Calculate market impact
        impact_result = self.market_impact_model.estimate_market_impact(
            asset_quantity, mid_price, volatility, book_depth
        )
        market_impact_usd = impact_result["total_impact"] * asset_quantity
        market_impact_pct = impact_result["impact_percentage"]
        
        # Calculate net cost
        net_cost_usd = slippage_usd + fee_usd + market_impact_usd
        net_cost_pct = (net_cost_usd / quantity) * 100
        
        # Get latency
        latency_ms = self.orderbook.get_average_processing_time()
        
        # Return the results
        return {
            "slippage": slippage_pct,
            "slippage_usd": slippage_usd,
            "fees": fee_pct,
            "fees_usd": fee_usd,
            "market_impact": market_impact_pct,
            "market_impact_usd": market_impact_usd,
            "net_cost": net_cost_pct,
            "net_cost_usd": net_cost_usd,
            "maker_proportion": maker_proportion,
            "latency_ms": latency_ms
        }


def run_application(simulator_controller):
    """
    Run the application.
    
    Args:
        simulator_controller: Controller for the simulator
    """
    app = QApplication(sys.argv)
    window = SimulatorUI(simulator_controller)
    sys.exit(app.exec())
