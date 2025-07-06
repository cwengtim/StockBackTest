import backtrader as bt
import yfinance as yf
import pandas as pd
import os
from strategy import *
from sizer import *


def get_data(ticker='1810.HK', start='2024-01-01', end='2025-05-20'):
    # Check if CSV exists
    file = f"data/{ticker}_{start.replace('-', '')}_{end.replace('-', '')}.pkl"
    if os.path.exists(file):
        print(f"Loading data from {file}")
        _data = pd.read_pickle(file)
    else:
        print(f"Downloading data for {ticker} from yfinance")
        _data = yf.download(ticker, start=start, end=end)
        _data.to_pickle(file)
        print(f"Saved data to {file}")

    # Flatten MultiIndex columns if present
    if isinstance(_data.columns, pd.MultiIndex):
        _data.columns = [col[0] for col in _data.columns]

    # Rename columns for Backtrader
    _data = _data.rename(columns={
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume',
        'Adj Close': 'adj_close'
    })

    # Ensure datetime index and clean data
    _data.index = pd.to_datetime(_data.index)
    _data = _data.dropna()
    _data = _data[['open', 'high', 'low', 'close', 'volume']]
    return _data





# Set up Cerebro
cerebro = bt.Cerebro()
# Load or download data
stocks = ['9988.HK']
for stock in stocks:
    data = get_data(ticker=stock, start='2023-01-01', end='2025-07-05')
    data_feed = bt.feeds.PandasData(dataname=data, name=stock)
    cerebro.adddata(data_feed)
#cerebro.addstrategy(MomentumStrategy)
#cerebro.addstrategy(SMACrossover)
cerebro.addstrategy(MACDStrategy)
#cerebro.addstrategy(KDJStrategy)
#cerebro.addstrategy(ElliottWaveStrategy)
cerebro.broker.setcash(10000.0)
cerebro.broker.setcommission(commission=0.001)
cerebro.addsizer(AllInSizer)
#cerebro.addsizer(bt.sizers.PercentSizer, percents=90)
#cerebro.addsizer(FixedValueSizer, value=1000)
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

# Run backtest
print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
results = cerebro.run()
print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

# Print analyzer results
sharpe = results[0].analyzers.sharpe.get_analysis()
drawdown = results[0].analyzers.drawdown.get_analysis()
returns = results[0].analyzers.returns.get_analysis()
#print(f"Sharpe Ratio: {sharpe.get('sharperatio', 'N/A'):.2f}")
#print(f"Max Drawdown: {drawdown.get('max', {}).get('drawdown', 'N/A'):.2f}%")
print(f"Total Return: {returns.get('rtot', 'N/A') * 100:.2f}%")

# Plot
cerebro.plot()
