import backtrader as bt

# Custom sizer to invest all available cash
class AllInSizer(bt.Sizer):
    def _getsizing(self, comminfo, cash, data, isbuy):
        if isbuy:
            # Calculate max shares affordable with available cash
            price = data.close[0]  # Current closing price
            # Account for commission if needed (optional)
            available_cash = self.broker.getcash()
            size = int((available_cash * 0.99) / price)  # Integer shares
            return size
        else:
            # Sell entire position
            return self.broker.getposition(data).size


# Custom Sizer: Buy a fixed dollar amount
class FixedValueSizer(bt.Sizer):
    params = (('value', 1000),)  # $1,000 per trade

    def _getsizing(self, comminfo, cash, data, isbuy):
        if isbuy:
            price = data.close[0]
            size = int(self.params.value / price)
            return size if size > 0 else 0
        return self.broker.getposition(data).size