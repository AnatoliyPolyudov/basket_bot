# trader.py

from observer import Observer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OKXBasketTrader(Observer):
    def __init__(self, paper_trading=True, max_exposure=1000):
        """
        paper_trading: True — не ставит реальные ордера, только выводит в консоль.
        max_exposure: максимальная сумма на одну позицию в USDT.
        """
        self.paper_trading = paper_trading
        self.max_exposure = max_exposure
        self.current_positions = {}  # {'BTC/USDT': qty, 'ETH/USDT': qty, ...}

    def update(self, data):
        """
        Метод Observer: вызывается при каждом новом сигнале от монитора.
        """
        signal = data.get("signal")
        if not signal:
            return
        self.execute_signal(signal, data)

    def execute_signal(self, signal, data):
        """
        Выполняет действия в зависимости от сигнала.
        """
        prices = self._extract_prices(data)
        if prices is None:
            logger.warning("No valid prices in data")
            return

        if self.paper_trading:
            logger.info(f"[PAPER TRADING] Received signal: {signal}")

        # --- LONG BTC / SHORT BASKET ---
        if signal == "LONG BTC / SHORT BASKET":
            self._open_long_btc_short_basket(prices)

        # --- SHORT BTC / LONG BASKET ---
        elif signal == "SHORT BTC / LONG BASKET":
            self._open_short_btc_long_basket(prices)

        # --- EXIT POSITION ---
        elif signal == "EXIT POSITION":
            self._close_all_positions()

        # --- HOLD ---
        elif signal == "HOLD":
            logger.info("[PAPER TRADING] Holding current positions — no changes.")

    def _extract_prices(self, data):
        """Извлекает цены из данных сигнала."""
        try:
            basket_symbols = data["basket_symbols"]
            basket_weights = data["basket_weights"]
            basket_price = data["basket_price"]
            target_price = data["target_price"]
            return {
                "BTC/USDT": float(target_price),
                "basket_symbols": basket_symbols,
                "basket_weights": basket_weights,
                "basket_price": float(basket_price),
            }
        except KeyError:
            return None

    def _open_long_btc_short_basket(self, prices):
        btc_qty = self.max_exposure / prices["BTC/USDT"]
        logger.info(f"[LONG] Open LONG BTC ({btc_qty:.4f} BTC at {prices['BTC/USDT']:.2f} USDT)")

        for s, w in zip(prices["basket_symbols"], prices["basket_weights"]):
            exposure = self.max_exposure * w
            symbol_price = prices["basket_price"] / sum(prices["basket_weights"])
            qty = exposure / symbol_price
            logger.info(f"[SHORT] Open SHORT {s} ({qty:.4f} units for {exposure:.2f} USDT)")

        self.current_positions["BTC/USDT"] = btc_qty
        logger.info("[PORTFOLIO] Updated positions after LONG BTC / SHORT BASKET")

    def _open_short_btc_long_basket(self, prices):
        btc_qty = self.max_exposure / prices["BTC/USDT"]
        logger.info(f"[SHORT] Open SHORT BTC ({btc_qty:.4f} BTC at {prices['BTC/USDT']:.2f} USDT)")

        for s, w in zip(prices["basket_symbols"], prices["basket_weights"]):
            exposure = self.max_exposure * w
            symbol_price = prices["basket_price"] / sum(prices["basket_weights"])
            qty = exposure / symbol_price
            logger.info(f"[LONG] Open LONG {s} ({qty:.4f} units for {exposure:.2f} USDT)")

        self.current_positions["BTC/USDT"] = -btc_qty
        logger.info("[PORTFOLIO] Updated positions after SHORT BTC / LONG BASKET")

    def _close_all_positions(self):
        if not self.current_positions:
            logger.info("[PAPER TRADING] No open positions to close.")
            return

        logger.info("[PAPER TRADING] Closing all positions...")
        for symbol, qty in self.current_positions.items():
            logger.info(f"  Closing {symbol}: {qty:+.4f} units")
        self.current_positions.clear()
        logger.info("[PORTFOLIO] All positions closed.")
