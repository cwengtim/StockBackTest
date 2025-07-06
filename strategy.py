# Strategy
import backtrader as bt
from indicator import *


class BaseStrategy(bt.Strategy):
    def log(self, txt):
        dt = self.datas[0].datetime.date(0)
        print(f'{dt}: {txt}')

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'BUY EXECUTED: {order.executed.size} shares at ${order.executed.price:.2f}, '
                    f'Total Value: ${order.executed.value:.2f}, Commission: ${order.executed.comm:.2f}, '
                    f'Cash: ${self.broker.cash:.2f}'
                )
            elif order.issell():
                self.log(
                    f'SELL EXECUTED: {order.executed.size} shares at ${order.executed.price:.2f}, '
                    f'Total Value: ${abs(order.executed.size * order.executed.price):.2f}, Commission: ${order.executed.comm:.2f}, '
                    f'Cash: ${self.broker.cash:.2f}'
                )
            self.order = None


class SMACrossover(BaseStrategy):
    params = (('fast', 10), ('slow', 30),)

    def __init__(self):
        self.fast_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.fast
        )
        self.slow_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.slow
        )
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
        self.order = None

    def next(self):
        '''if self.order:
            return'''
        if not self.position:
            if self.crossover > 0:
                self.order = self.buy()
        elif self.crossover < 0:
            self.order = self.sell()


class MomentumStrategy(BaseStrategy):
    params = (
        ('fast_period', 10),
        ('slow_period', 50),
        ('size', 100),  # Fixed size for simplicity
    )

    def __init__(self):
        self.fast_sma = bt.indicators.SMA(self.data.close, period=self.params.fast_period)
        self.slow_sma = bt.indicators.SMA(self.data.close, period=self.params.slow_period)
        self.rsi = bt.indicators.RSI(self.data.close, period=14)
        self.order = None

    def next(self):
        if self.order:  # Check if an order is pending
            return

        # Check if we are in the market
        if not self.position:
            # Buy condition: Fast SMA > Slow SMA and RSI < 70
            if self.fast_sma > self.slow_sma and self.rsi < 50:
                self.order = self.buy()
                self.stop_price = self.data.close * 0.9  # 3% stop-loss
        else:
            # Sell condition: Fast SMA < Slow SMA or stop-loss hit
            if self.fast_sma < self.slow_sma or self.data.close < self.stop_price:
                self.order = self.sell()


class KDJStrategyOld(BaseStrategy):
    params = (
        ('k_period', 9),  # Period for K line
        ('d_period', 3),  # Period for D line
        ('slow_period', 3),  # Period for slow stochastic (D smoothing)
        ('buy_threshold', 40),  # K and D below 30 for buy
        ('sell_threshold', 60),  # K and D above 60 for sell
        ('stop_loss', 1),  # 10% stop loss
    )

    def __init__(self):
        # Initialize the Stochastic KDJ indicator
        self.kdj = bt.indicators.StochasticFull(
            period=self.params.k_period,
            period_dfast=self.params.d_period,
            period_dslow=self.params.slow_period
        )
        self.k_line = self.kdj.percD  # K line
        self.d_line = self.kdj.percDSlow  # D line
        self.order = None  # Track active orders
        self.buy_price = None  # Track buy price for stop-loss

    def next(self):
        offset = 0
        # If we have an open position
        if self.position:
            # Check for stop-loss (10% below buy price)
            if self.data.close[0] <= self.buy_price * (1 - self.params.stop_loss):
                print("s", self.data.close[0], self.buy_price)
                self.sell(size=self.position.size)
                self.order = None
                self.buy_price = None
                return

            # Sell condition: K and D above 60 and D crosses above K
            if (self.k_line[offset] > self.params.sell_threshold and
                    self.d_line[offset] > self.params.sell_threshold and
                    self.d_line[offset] > self.k_line[offset] and
                    self.d_line[offset - 1] <= self.k_line[offset - 1]):
                print("s", self.k_line[offset], self.d_line[offset], self.k_line[offset - 1], self.d_line[offset - 1])
                self.sell(size=self.position.size)
                self.order = None
                self.buy_price = None

        # If no position, check for buy signal
        else:
            # Buy condition: K and D below 30 and K crosses above D
            if (self.k_line[offset] < self.params.buy_threshold and
                    self.d_line[offset] < self.params.buy_threshold and
                    self.k_line[offset] > self.d_line[offset] and
                    self.k_line[offset - 1] <= self.d_line[offset - 1]):
                print("b", self.k_line[offset], self.d_line[offset], self.k_line[offset - 1], self.d_line[offset - 1])
                self.buy()
                self.buy_price = self.data.close[1]


class ElliottWaveStrategy(BaseStrategy):
    params = (
        ('short_ma_period', 10),  # Short-term SMA
        ('long_ma_period', 30),  # Long-term SMA
        ('rsi_period', 14),  # RSI period
        ('zigzag_percent', 5.0),  # ZigZag swing threshold (5%)
        ('rsi_overbought', 70),  # RSI sell threshold
        ('rsi_oversold', 30),  # RSI buy threshold
        ('stop_loss', 0.1),  # 10% stop loss
        ('peak_drop', 0.15),  # 30% drop from previous peak
    )

    def __init__(self):
        # Initialize indicators
        self.short_ma = bt.indicators.SMA(period=self.params.short_ma_period)
        self.long_ma = bt.indicators.SMA(period=self.params.long_ma_period)
        self.rsi = bt.indicators.RSI(period=self.params.rsi_period)
        self.zigzag = CustomZigZag(self.data.close, percent=self.params.zigzag_percent)
        self.order = None  # Track active orders
        self.buy_price = None  # Track buy price for stop-loss
        self.last_pivot = None  # Track last pivot type ('high' or 'low')
        self.last_pivot_price = None  # Track price at last pivot
        self.peak_price = None  # Track highest price since last buy

    def next(self):
        # Update peak price if in a position
        if self.position:
            if self.peak_price is None or self.data.close[0] > self.peak_price:
                self.peak_price = self.data.close[0]

        # Update pivot information from ZigZag
        if self.zigzag[0] != 0:  # New pivot detected
            if self.last_pivot_price is None:
                # Initial pivot
                self.last_pivot_price = self.zigzag[0]
                self.last_pivot = 'low'  # Assume first pivot is a low
            else:
                # Determine pivot type based on price comparison
                self.last_pivot = 'high' if self.zigzag[0] > self.last_pivot_price else 'low'
                self.last_pivot_price = self.zigzag[0]

        # If we have an open position
        if self.position:
            # Check for stop-loss (10% below buy price)
            if self.data.close[0] <= self.buy_price * (1 - self.params.stop_loss):
                self.sell(size=self.position.size)
                self.order = None
                self.buy_price = None
                self.peak_price = None
                return

            # Sell condition 1: Potential corrective wave (e.g., Wave A or C)
            if (self.short_ma[0] < self.long_ma[0] and
                    self.short_ma[-1] >= self.long_ma[-1] and
                    self.rsi[0] > self.params.rsi_overbought and
                    self.last_pivot == 'high'):
                self.sell(size=self.position.size)
                self.order = None
                self.buy_price = None
                self.peak_price = None
                return

            # Sell condition 2: Current price is 30% below previous peak
            if (self.peak_price is not None and
                    self.data.close[0] <= self.peak_price * (1 - self.params.peak_drop)):
                self.sell(size=self.position.size)
                self.order = None
                self.buy_price = None
                self.peak_price = None
                return

        # If no position, check for buy signal
        else:
            # Buy condition: Potential impulsive wave (e.g., Wave 3)
            if (self.short_ma[0] > self.long_ma[0] and
                    self.short_ma[-1] <= self.long_ma[-1] and
                    self.rsi[0] > self.params.rsi_oversold and
                    self.rsi[0] < self.params.rsi_overbought and
                    self.last_pivot == 'low'):
                self.buy()
                self.buy_price = self.data.close[0]
                self.peak_price = self.data.close[0]  # Initialize peak price


# KDJ Strategy
class KDJStrategy(BaseStrategy):
    params = (
        ('kdj_period', 9),  # KDJ period
        ('sma_period', 20),  # 50-day SMA
        ('stop_loss', 0.03),  # 2% stop-loss
        ('take_profit', 0.2),  # 4% take-profit (2:1 reward-to-risk)
        ('size', 100),  # Number of shares to trade
        ('buy_threshold', 50),  # K and D below 30 for buy
        ('sell_threshold', 50),  # K and D above 60 for sell
    )

    def __init__(self):
        # Indicators
        self.kdj = KDJ(self.data, period=self.p.kdj_period)
        self.sma = bt.indicators.SMA(self.data.close, period=self.p.sma_period)
        # Track orders and entry price
        self.order = None
        self.entry_price = None

    def next(self):
        # Skip if an order is pending
        if self.order:
            return

        # Check if we are in a position
        if not self.position:
            # Buy condition: %K crosses above %D below 20 and price > 50-day SMA
            #if (self.kdj.K[-1] < self.kdj.D[-1] and self.kdj.K[0] > self.kdj.D[0] and self.kdj.K[0] < self.p.buy_threshold and self.data.close[0] > self.sma[0]):
            if (self.kdj.K[0] > self.kdj.D[0] and self.kdj.K[0] < self.p.buy_threshold and self.data.close[0] > self.sma[0]):
                #print(self.data.close[0], self.sma[0], self.kdj.K[0], self.kdj.K[1])
                self.order = self.buy()
                self.entry_price = self.data.close[0]
                # Set stop-loss and take-profit
                self.stop_price = self.entry_price * (1 - self.p.stop_loss)
                self.profit_price = self.entry_price * (1 + self.p.take_profit)
                self.log(
                    f'BUY at {self.data.close[0]:.2f}, Stop: {self.stop_price:.2f}, Profit: {self.profit_price:.2f}')

        else:
            # Sell condition: %K crosses below %D above 80 or price hits stop-loss/take-profit
            '''if (self.kdj.K[-1] > self.kdj.D[-1] and
                self.kdj.K[0] < self.kdj.D[0] and
                self.kdj.K[0] > self.p.sell_threshold) or \
                    self.data.close[0] <= self.stop_price or \
                    self.data.close[0] >= self.profit_price:'''
            if self.data.close[0] <= self.stop_price or self.data.close[0] >= self.profit_price:
                self.order = self.sell()
                self.log(f'SELL at {self.data.close[0]:.2f}')

    def log(self, txt):
        dt = self.datas[0].datetime.date(0)
        print(f'{dt}: {txt}')


class MACDStrategy(BaseStrategy):
    params = (
        ('macd1', 12),  # Fast EMA period
        ('macd2', 26),  # Slow EMA period
        ('signal', 9),  # Signal line period
        ('size', 100),  # Number of shares to trade
    )

    def __init__(self):
        # Initialize MACD indicator
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params.macd1,
            period_me2=self.params.macd2,
            period_signal=self.params.signal
        )
        # Cross of MACD line and Signal line
        self.crossover = bt.indicators.CrossOver(self.macd.macd, self.macd.signal)
        # Track position
        self.order = None

    def next(self):
        # If an order is pending, don't place a new one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:
            # Buy condition: MACD crosses above Signal
            if self.crossover > 0:
                self.log(f'BUY CREATE at {self.data.close[0]:.2f}')
                self.order = self.buy(size=self.params.size)
        else:
            # Sell condition: MACD crosses below Signal
            if self.crossover < 0:
                self.log(f'SELL CREATE at {self.data.close[0]:.2f}')
                self.order = self.sell(size=self.params.size)

    def stop(self):
        # Log final portfolio value
        self.log(f'Final Portfolio Value: {self.broker.getvalue():.2f}')