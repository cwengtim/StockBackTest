import backtrader as bt

class DirectionalChangeInd(bt.Indicator):
    lines = ('tops', 'bottoms',)
    params = (('sigma', 5),)
    plotinfo = dict(subplot=False, plotlinelabels=True)
    plotlines = dict(tops=dict(marker='$\u21E9$', markersize=10.0, color='black', fillstyle='full'),
                     bottoms=dict(marker='$\u21E7$', markersize=10.0, color='black', fillstyle='full'))

    def __init__(self):
        self.addminperiod(2)
        self.up_zig = True  # Last extreme is a bottom. Next is a top.
        self.tmp_max = None
        self.tmp_min = None

    def prenext(self):
        self.tmp_max = self.data.high[0]
        self.tmp_min = self.data.low[0]

    def next(self):

        if self.up_zig:  # Last extreme is a bottom
            if self.data.high[0] > self.tmp_max:
                # New high, update
                self.tmp_max = self.data.high[0]
            elif self.data.close[0] < self.tmp_max - self.tmp_max * self.params.sigma / 1000:
                # Price retraced by sigma %. Top confirmed, record it
                self.l.tops[0] = self.tmp_max
                # print('#1', self.l.tops[0])
                # Setup for next bottom
                self.up_zig = False
                self.tmp_min = self.data.low[0]
        else:  # Last extreme is a top
            if self.data.low[0] < self.tmp_min:
                # New low, update
                self.tmp_min = self.data.low[0]
            elif self.data.close[0] > self.tmp_min + self.tmp_min * self.params.sigma / 1000:
                # Price retraced by sigma %. Bottom confirmed, record it
                self.l.bottoms[0] = self.tmp_min
                # print('#2', self.l.bottoms[0])
                # Setup for next top
                self.up_zig = True
                self.tmp_max = self.data.high[0]


class CustomZigZag(bt.Indicator):
    lines = ('zigzag',)
    params = (('percent', 5.0),)  # Percentage threshold for swing

    def __init__(self):
        self.last_pivot_price = None
        self.last_pivot_type = None  # 'high' or 'low'
        self.last_pivot_idx = 0

    def next(self):
        if self.last_pivot_price is None:
            # Initialize with first price
            self.last_pivot_price = self.data[0]
            self.last_pivot_type = 'low'
            self.lines.zigzag[0] = self.data[0]
            return

        price = self.data[0]
        percent_change = abs((price - self.last_pivot_price) / self.last_pivot_price) * 100

        if self.last_pivot_type == 'low':
            if price >= self.last_pivot_price * (1 + self.params.percent / 100):
                # New high pivot
                self.lines.zigzag[0] = price
                self.last_pivot_price = price
                self.last_pivot_type = 'high'
                self.last_pivot_idx = len(self.data) - 1
            else:
                self.lines.zigzag[0] = 0  # No new pivot
        else:  # Last pivot is high
            if price <= self.last_pivot_price * (1 - self.params.percent / 100):
                # New low pivot
                self.lines.zigzag[0] = price
                self.last_pivot_price = price
                self.last_pivot_type = 'low'
                self.last_pivot_idx = len(self.data) - 1
            else:
                self.lines.zigzag[0] = 0  # No new pivot


class KDJ(bt.Indicator):
    lines = ('K', 'D', 'J')
    params = (
        ('period', 14),  # Lookback period for high/low
        ('period_d', 3),  # Period for %D smoothing
        ('period_j', 3),  # Period for %J calculation
    )

    def __init__(self):
        # Calculate %K
        highest = bt.indicators.Highest(self.data.high, period=self.p.period)
        lowest = bt.indicators.Lowest(self.data.low, period=self.p.period)
        rsv = 100 * (self.data.close - lowest) / (highest - lowest)
        self.lines.K = bt.indicators.SMA(rsv, period=self.p.period_d)
        # Calculate %D
        self.lines.D = bt.indicators.SMA(self.lines.K, period=self.p.period_j)
        # Calculate %J
        self.lines.J = 3 * self.lines.K - 2 * self.lines.D