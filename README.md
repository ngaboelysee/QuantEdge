
QuantumEdge-Trading
Repository navigation
Code
Issues
Pull requests
Agents
A forex trading algorithm project built with FastAPI and yfinance.

0 stars
0 forks
0 watching
1 branch
0 tags
Activity
Public repository
ngaboelysee
ngaboelysee
4 months ago
Name	
__pycache__
4 months ago
frontend
4 months ago
README.md
4 months ago
app.py
4 months ago
Repository files navigation
README
QuantumEdge AI Trading System
QuantumEdge is a full-stack quantitative trading intelligence platform designed to analyze forex and gold markets using ensemble-based market models inspired by institutional hedge fund strategies.

The platform combines trend analysis, volatility forecasting, mean reversion systems, confidence scoring, and risk evaluation into a unified trading dashboard capable of generating real-time trade intelligence.

This project was built from scratch as a self-directed exploration of:

quantitative finance
algorithmic trading
backend engineering
frontend systems
API architecture
financial data analysis
Features
Quantitative Trading Engine
Multi-model ensemble analysis system
Trend-following logic
Mean reversion analysis
Volatility-based risk modeling
Confidence scoring algorithm
Dynamic trade ranking
Trade Intelligence
Users can:

View top-ranked live trading opportunities
Submit their own trades for evaluation
Receive directional agreement/disagreement analysis
View confidence scores and risk levels instantly
Portfolio Management
Account balance input
Risk tolerance selection
Dynamic trade filtering based on user risk profile
Real-Time Dashboard
Interactive trading interface
Institutional-style UI
Live market trade cards
FastAPI-powered backend communication
Dynamic frontend updates using JavaScript
Technologies Used
Backend
Python
FastAPI
Pandas
NumPy
yFinance
Frontend
HTML
CSS
JavaScript
System Architecture
Frontend Dashboard
⬇
JavaScript API Layer
⬇
FastAPI Backend
⬇
Quantitative Ensemble Models
⬇
Yahoo Finance Market Data

Example Trade Output
Pair	Direction	Confidence	Risk
EURJPY	BUY	76.83%	LOW
GBPJPY	BUY	76.83%	LOW
GOLD	BUY	74.96%	MEDIUM
Quantitative Models
The trading engine combines multiple independent market models:

Trend Model
Uses moving average analysis to identify directional market momentum.

Mean Reversion Model
Uses RSI-based analysis to detect overbought and oversold conditions.

Volatility Model
Evaluates market stability and adjusts risk exposure accordingly.

Ensemble Engine
Combines all model outputs into a unified confidence-weighted trading decision.

Future Improvements
Machine learning prediction layer
Reinforcement learning strategies
Broker API integration
Live websocket market feeds
Portfolio optimization engine
Position sizing algorithms
Real-time analytics and charting
Historical backtesting framework
Motivation
I built QuantumEdge to explore how quantitative finance and software engineering can combine into intelligent market analysis systems similar to those used by modern trading firms and hedge funds.

This project helped me gain hands-on experience with:

financial systems
full-stack development
API integration
quantitative modeling
real-time data pipelines
frontend/backend architecture
Disclaimer
This project is intended for educational and research purposes only and should not be considered financial advice.
