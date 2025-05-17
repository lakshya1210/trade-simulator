# Cryptocurrency Trade Simulator

A high-performance trade simulator that uses real-time market data to estimate transaction costs and market impact for cryptocurrency trading.

## Features

- Real-time L2 orderbook data streaming from OKX
- Estimation of slippage, fees, and market impact
- Implementation of Almgren-Chriss market impact model
- Regression models for prediction
- Interactive UI with input parameters and real-time results

## Setup

1. Create a virtual environment:
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```
pip install -r requirements.txt
```

3. Run the application:
```
python src/main.py
```

## Note

You will need to use a VPN to access OKX for market data streaming. No account creation is required.

## Components

- WebSocket Client: Connects to exchange API for real-time L2 orderbook data
- Orderbook Processor: Manages and processes the orderbook data
- Market Impact Model: Implements Almgren-Chriss model
- Regression Models: For slippage and maker/taker proportion prediction
- UI: PyQt6-based interface with input and output panels
