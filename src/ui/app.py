"""
UI implementation for the trading simulator.
"""
import sys
import time
# Removed PyQt6 imports
# from PyQt6.QtWidgets import (
#     QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
#     QLabel, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox,
#     QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
#     QSplitter, QTextEdit
# )
# from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
# from PyQt6.QtGui import QFont, QColor, QPalette
from loguru import logger
import asyncio
import tkinter # Keep this for tkinter.WORD and tkinter.DISABLED etc.
import customtkinter # Main UI framework

from ..config import (
    DEFAULT_EXCHANGE, DEFAULT_ASSET, DEFAULT_ORDER_TYPE,
    DEFAULT_QUANTITY, DEFAULT_VOLATILITY, DEFAULT_FEE_TIER,
    AVAILABLE_ASSETS, ORDER_TYPES, FEE_TIERS, UI_REFRESH_RATE_MS, # Keep UI_REFRESH_RATE_MS
    WEBSOCKET_URL
)
from typing import TYPE_CHECKING # For type hinting SimulatorController

if TYPE_CHECKING:
    from ..controllers.simulator_controller import SimulatorController


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class SimulatorUI(customtkinter.CTk):
    """Main UI window for the trading simulator."""
    
    def __init__(self, controller: 'SimulatorController'): # Changed simulator_controller to controller
        """
        Initialize the UI.
        
        Args:
            controller: Controller for the simulator logic
        """
        super().__init__()
        
        self.controller = controller
        self.last_update_time = 0 # Still useful for debouncing if needed, or can be removed if periodic_ui_update is sole timer
        self.connected = False # Tracks UI's perception of connection status
        self.loop = None
        self.is_ui_running = False # Flag to control the main UI loop
        
        # self._configure_logging() # Removed, logging is global via loguru
        self._initialize_ui()
        logger.info("SimulatorUI initialized")
        
        # Removed QTimer setup, using self.after in _initialize_ui for periodic_ui_update
        # self.update_timer = QTimer() 
        # self.update_timer.timeout.connect(self.update_ui)
        # self.update_timer.start(UI_REFRESH_RATE_MS)
    
    # def _configure_logging(self): # Removed, not needed with loguru
    #     pass

    def _initialize_ui(self):
        """Initialize the UI components."""
        self.title("Trade Simulator")
        self.geometry("1200x800") # Default window size
        
        # Main layout
        self.grid_columnconfigure(0, weight=1) # Input panel column
        self.grid_columnconfigure(1, weight=2) # Output panel column
        self.grid_rowconfigure(0, weight=1)    # Main row

        # Input Parameters Frame (Left Panel)
        self.input_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.input_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self._create_input_widgets(self.input_frame) # Placeholder for actual input widgets

        # Output Area (Right Panel)
        self.output_main_frame = customtkinter.CTkFrame(self, corner_radius=10)
        self.output_main_frame.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")
        self.output_main_frame.grid_columnconfigure(0, weight=1)
        self.output_main_frame.grid_rowconfigure(0, weight=1) # Output parameters display
        self.output_main_frame.grid_rowconfigure(1, weight=2) # Order book display
        self.output_main_frame.grid_rowconfigure(2, weight=1) # Log messages display

        self.output_params_frame = customtkinter.CTkFrame(self.output_main_frame, corner_radius=10)
        self.output_params_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self._create_output_parameters_display(self.output_params_frame) # Placeholder

        self.order_book_frame = customtkinter.CTkFrame(self.output_main_frame, corner_radius=10)
        self.order_book_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self._create_order_book_display(self.order_book_frame) # Placeholder
        
        self.log_frame = customtkinter.CTkFrame(self.output_main_frame, corner_radius=10)
        self.log_frame.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        self._create_log_display(self.log_frame) # Actual CTkTextbox
        
        # Start the periodic UI update loop using self.after
        self.after(UI_REFRESH_RATE_MS, self.periodic_ui_update)
    
    def _create_input_widgets(self, parent_frame):
        """Create input widgets for the simulation parameters."""
        parent_frame.grid_columnconfigure(0, weight=1) # Allow widgets to expand
        
        # Example: Exchange
        customtkinter.CTkLabel(parent_frame, text="Exchange:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.exchange_combo = customtkinter.CTkComboBox(parent_frame, values=[DEFAULT_EXCHANGE])
        self.exchange_combo.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        # Example: Spot Asset
        customtkinter.CTkLabel(parent_frame, text="Spot Asset:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.asset_combo = customtkinter.CTkComboBox(parent_frame, values=AVAILABLE_ASSETS)
        self.asset_combo.set(DEFAULT_ASSET)
        self.asset_combo.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        # ... Add other CTk input widgets (Order Type, Quantity, Volatility, Fee Tier) ...
        # For CTk Entries/Spinboxes, use .get() to retrieve values.

        # Connect Button
        self.connect_button = customtkinter.CTkButton(parent_frame, text="Connect", command=self.on_connect)
        self.connect_button.grid(row=6, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # Calculate Button
        self.calculate_button = customtkinter.CTkButton(parent_frame, text="Calculate", command=self.on_calculate)
        self.calculate_button.grid(row=7, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # Connection Status Label
        self.connection_status_label = customtkinter.CTkLabel(parent_frame, text="Connection Status: Disconnected", text_color="red")
        self.connection_status_label.grid(row=8, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        logger.info("Input widgets created (CTk stubs).")


    def _create_output_parameters_display(self, parent_frame):
        """Create display area for output parameters."""
        parent_frame.grid_columnconfigure(1, weight=1) # Allow labels to expand if needed
        # Example: Current Price
        customtkinter.CTkLabel(parent_frame, text="Current Price:").grid(row=0, column=0, padx=10, pady=2, sticky="w")
        self.price_label = customtkinter.CTkLabel(parent_frame, text="N/A")
        self.price_label.grid(row=0, column=1, padx=10, pady=2, sticky="w")
        # ... Add other CTkLabels for slippage, fees, etc. ...
        self.slippage_label = customtkinter.CTkLabel(parent_frame, text="N/A") # Placeholder
        self.slippage_label.grid(row=1, column=1, padx=10, pady=2, sticky="w")
        self.fees_label = customtkinter.CTkLabel(parent_frame, text="N/A") # Placeholder
        self.fees_label.grid(row=2, column=1, padx=10, pady=2, sticky="w")
        # ... and so on for other output labels
        logger.info("Output parameters display created (CTk stubs).")

    def _create_order_book_display(self, parent_frame):
        """Create display area for the L2 order book."""
        # This needs a CustomTkinter implementation for displaying tabular data.
        # For now, a simple placeholder label.
        self.orderbook_label_placeholder = customtkinter.CTkLabel(parent_frame, text="Order Book Data (CTk Implementation Needed)")
        self.orderbook_label_placeholder.pack(padx=10, pady=10, fill="both", expand=True)
        logger.info("Order book display created (CTk placeholder).")


    def _create_log_display(self, parent_frame):
        """Create display area for log messages."""
        parent_frame.grid_rowconfigure(0, weight=1)
        parent_frame.grid_columnconfigure(0, weight=1)
        self.log_text_area = customtkinter.CTkTextbox(
            parent_frame, wrap=tkinter.WORD, state=tkinter.DISABLED, corner_radius=5, border_spacing=5, activate_scrollbars=True
        )
        self.log_text_area.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        logger.info("Log display (CTkTextbox) created.")


    def periodic_ui_update(self):
        """Periodically called by self.after to refresh the UI."""
        self.update_ui()
        if self.is_ui_running: # Reschedule only if UI is supposed to be running
            self.after(UI_REFRESH_RATE_MS, self.periodic_ui_update)

    def update_ui(self):
        """Update the UI with the latest data from the controller."""
        # Update connection status display
        is_connected_from_controller = self.controller.is_connected() # Renamed for clarity
        if is_connected_from_controller != self.connected: # Update if changed
            self.connected = is_connected_from_controller
            self.update_connection_status_display() # Use a more specific name
        
        # Get orderbook status message from controller and log it
        orderbook_status_msg = self.controller.get_orderbook_status() # Renamed for clarity
        if orderbook_status_msg:
            self.log_message_to_ui(orderbook_status_msg) # Use a more specific name
        
        # Update current mid-price display
        mid_price = self.controller.get_mid_price()
        if mid_price is not None: # Check for None explicitly
            self.price_label.configure(text=f"${mid_price:.2f}")
        else:
            self.price_label.configure(text="N/A")
        
        # Update orderbook visualization (needs CTk implementation)
        self.update_orderbook_table_display() # Use a more specific name
        
        # If a calculation was performed, update the results display
        # Assuming self.last_results is set by on_calculate
        if hasattr(self, 'last_results') and self.last_results:
            self.update_results_display(self.last_results) # Use a more specific name
    
    def update_orderbook_table_display(self):
        """Update the orderbook table display. Needs CTk implementation."""
        bids = self.controller.get_bids()
        asks = self.controller.get_asks()
        
        # --- Needs CustomTkinter implementation below ---
        # The following is PyQt6 code and needs to be replaced.
        # For now, just logging that it needs replacement.
        # self.orderbook_table.clearContents() 
        # top_bids = sorted(bids.items(), reverse=True)[:10]
        # top_asks = sorted(asks.items())[:10]
        # ... (PyQt6 specific table filling logic) ...
        if not hasattr(self, '_orderbook_warning_logged'):
             logger.warning("update_orderbook_table_display: Needs CustomTkinter implementation for table.")
             self._orderbook_warning_logged = True # Log warning only once
        # Example: self.orderbook_label_placeholder.configure(text=f"Bids: {len(bids)}, Asks: {len(asks)}")


    def on_connect(self):
        """Handle connect/disconnect button click event."""
        if not self.connected:
            self.log_message_to_ui("Attempting to connect to WebSocket...")
            # Assuming controller.connect() now correctly starts the WebSocketClient
            # and doesn't block if it's async.
            # If controller.connect() is async, main.py or controller needs to handle task creation.
            # For now, assuming it's a non-blocking call that triggers an async start.
            asyncio.create_task(self.controller.connect_async()) # Assuming controller has connect_async
            # Success/failure will be reflected in is_connected() status during next UI update
        else:
            self.log_message_to_ui("Disconnecting from WebSocket...")
            asyncio.create_task(self.controller.disconnect_async()) # Assuming controller has disconnect_async
        
        # UI connection status will update in the next periodic_ui_update cycle
    
    def update_connection_status_display(self):
        """Update the connection status display elements (label and button text)."""
        if self.connected:
            self.connection_status_label.configure(text="Connection Status: Connected", text_color="green")
            self.connect_button.configure(text="Disconnect")
        else:
            self.connection_status_label.configure(text="Connection Status: Disconnected", text_color="red")
            self.connect_button.configure(text="Connect")
    
    def on_calculate(self):
        """Handle calculate button click event."""
        # Get input parameters from CTk widgets
        # exchange = self.exchange_combo.get()
        # asset = self.asset_combo.get()
        # order_type = self.order_type_combo.get() # Assuming CTkComboBox
        # quantity = float(self.quantity_entry.get()) # Assuming CTkEntry
        # volatility = float(self.volatility_entry.get()) # Assuming CTkEntry
        # fee_tier = self.fee_tier_combo.get() # Assuming CTkComboBox
        
        logger.warning("on_calculate: Needs implementation to get values from CTk widgets.")
        # Placeholder values for now
        exchange, asset, order_type, quantity, volatility, fee_tier = DEFAULT_EXCHANGE, DEFAULT_ASSET, DEFAULT_ORDER_TYPE, DEFAULT_QUANTITY, DEFAULT_VOLATILITY, DEFAULT_FEE_TIER

        results = self.controller.calculate_transaction_costs(
            exchange, asset, order_type, quantity, volatility, fee_tier
        )
        self.last_results = results # Save for UI updates
        self.update_results_display(results)
    
    def update_results_display(self, results):
        """Update the UI with calculation results."""
        # Update CTkLabels, e.g.:
        # self.slippage_label.configure(text=f"{results['slippage']:.4f}% (${results['slippage_usd']:.2f})")
        # self.fees_label.configure(text=f"{results['fees']:.4f}% (${results['fees_usd']:.2f})")
        # ... and so on for other result labels.
        if not hasattr(self, '_results_warning_logged'):
            logger.warning("update_results_display: Needs CTkLabels to be configured with results.")
            self._results_warning_logged = True # Log warning only once

    
    def log_message_to_ui(self, message: str): # Renamed for clarity
        """Add a message to the log display text area."""
        timestamp = time.strftime("%H:%M:%S")
        current_text = f"[{timestamp}] {message}\n"
        
        self.log_text_area.configure(state=tkinter.NORMAL)
        self.log_text_area.insert(tkinter.END, current_text)
        self.log_text_area.configure(state=tkinter.DISABLED)
        self.log_text_area.see(tkinter.END) # Auto-scroll

    async def run_async(self):
        """Run the UI asynchronously, allowing asyncio tasks to run concurrently."""
        logger.info("run_async: Starting UI event integration with asyncio.")
        self.loop = asyncio.get_event_loop() # Should be already set by main.py if using asyncio.run()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.is_ui_running = True
        logger.info("run_async: Entering main UI loop.")
        try:
            while self.is_ui_running:
                self.update() # Process CustomTkinter events
                # self.update_idletasks() # Usually not needed/less critical with CTk & asyncio.sleep
                await asyncio.sleep(0.02) # Approx 50 FPS, adjust as needed

                if not self.winfo_exists(): # More robust check
                    logger.warning("run_async: Main window (self) no longer exists. Stopping UI loop.")
                    self.is_ui_running = False
                    break
            logger.info(f"run_async: Exited main UI loop. self.is_ui_running = {self.is_ui_running}")
        except tkinter.TclError as e: # Can happen if window is destroyed while update() is called
            if self.is_ui_running: # Only log as error if not part of intentional shutdown
                logger.error(f"run_async: Tkinter TclError in UI loop: {e}", exc_info=True)
            else: # Likely benign, happening during shutdown
                logger.info(f"run_async: Tkinter TclError (likely during shutdown): {e}")
            self.is_ui_running = False
        except Exception as e:
            logger.error(f"run_async: Unexpected error in UI loop: {e}", exc_info=True)
            self.is_ui_running = False
        finally:
            logger.info("run_async: UI loop finished. Cleaning up UI resources.")
            # self.destroy() is usually called by on_closing or if loop breaks due to winfo_exists()
            # If loop exits for other reasons, ensure destroy is called if window still exists and not already being destroyed
            if self.winfo_exists() and not self._is_destroyed_internal_check():
                logger.info("run_async: Explicitly destroying window in finally block.")
                self.destroy() 

    def on_closing(self):
        """Handle window close event (WM_DELETE_WINDOW)."""
        logger.info("on_closing: Window close requested by user.")
        if self.is_ui_running:
            logger.info("on_closing: Setting self.is_ui_running to False to terminate the UI loop.")
            self.is_ui_running = False # Signal the loop in run_async to stop
        else:
            logger.warning("on_closing: UI loop was already not running (is_ui_running is False).")
        
        # Let run_async's finally block handle the actual self.destroy()
        # This avoids TclErrors if destroy() is called while run_async's loop is in self.update()

    def _is_destroyed_internal_check(self): # Renamed for clarity
        """Helper to check if widget is in process of being destroyed."""
        try:
            # Accessing an internal attribute like _w can indicate widget state.
            # If it's gone, TclError is raised.
            self._w 
            return False 
        except tkinter.TclError:
            return True


# Removed PyQt6 based SimulatorController, assuming it's in controller.py
# class SimulatorController:
# ...

# Removed PyQt6 based run_application function. 
# main.py will create SimulatorUI instance and run its run_async method.
# def run_application(simulator_controller):
# ...
