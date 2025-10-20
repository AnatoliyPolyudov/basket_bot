# main.py
import logging import time import sys from datetime 
import datetime from config import config from exchange 
import exchange from basket_manager import 
basket_manager from signal_generator import 
signal_generator from position_manager import 
position_manager from telegram_notifier import telegram 
from utils import setup_logging class BasketTradingBot:
    def __init__(self): self.logger = setup_logging() 
        self.running = False
    def initialize(self): try: config.validate() 
            self.logger.info("Configuration validated") 
            if not basket_manager.build_basket():
                self.logger.error("Failed to build 
                initial basket") return False
            telegram.system_start() 
            self.logger.info("System initialized 
            successfully") return True
        except Exception as e: 
            self.logger.error(f"Initialization failed: 
            {e}") telegram.error_alert(f"Initialization 
            failed: {e}") return False
    def run(self): self.running = True 
        self.logger.info("Starting main trading loop") 
        iteration = 0 while self.running:
            try: iteration += 1 
                self._process_iteration(iteration) 
                time.sleep(config.REFRESH_INTERVAL)
            except KeyboardInterrupt: 
                self.logger.info("Received interrupt 
                signal, shutting down") break
            except Exception as e: 
                self.logger.error(f"Error in main loop: 
                {e}") 
                time.sleep(config.REFRESH_INTERVAL)
    def _process_iteration(self, iteration): 
        self._check_rebalance() z_score, ratio, mean, 
        std = 
        signal_generator.calculate_current_zscore() if 
        z_score is None:
            self.logger.warning("Failed to calculate 
            Z-score") return
        signal = signal_generator.generate_signal() 
        self._handle_signal(signal, z_score, ratio) 
        self._log_status(iteration, z_score, ratio, 
        signal)
    def _check_rebalance(self): if 
        basket_manager.should_rebalance():
            self.logger.info("Rebalancing basket...") 
            if basket_manager.build_basket():
                self.logger.info("Basket rebalanced 
                successfully")
            else: self.logger.error("Basket rebalance 
                failed")
    def _handle_signal(self, signal, z_score, ratio): 
        if signal == "NO_SIGNAL":
            return if signal in 
        ["SHORT_TARGET_LONG_BASKET", 
        "LONG_TARGET_SHORT_BASKET"]:
            if not position_manager.is_position_open(): 
                if 
                position_manager.open_position(signal, 
                z_score):
                    telegram.signal_alert(signal, 
                    z_score, ratio) 
                    self.logger.info(f"Position opened: 
                    {signal}")
        elif signal == "EXIT_POSITION": if 
            position_manager.is_position_open():
                position_info = 
                position_manager.get_position_info() 
                pnl = z_score - 
                position_info.get("entry_zscore", 0) if 
                position_manager.close_position():
                    telegram.position_closed(pnl, 
                    position_info.get("duration", "")) 
                    self.logger.info(f"Position closed 
                    with PnL: {pnl:.2f}bps")
        if signal_generator.is_stop_loss_triggered(): 
            if position_manager.is_position_open():
                self.logger.warning("Stop loss 
                triggered, closing position") 
                position_manager.close_position()
    def _log_status(self, iteration, z_score, ratio, 
    signal):
        if iteration % 10 == 0: position_status = 
            "OPEN" if 
            position_manager.is_position_open() else 
            "CLOSED" self.logger.info(
                f"Iteration: {iteration} | " f"Z-score: 
                {z_score:.2f} | " f"Ratio: {ratio:.6f} 
                | "
                f"Signal: {signal} | " f"Position: 
                {position_status}"
            ) def shutdown(self): self.running = False 
        self.logger.info("Shutting down bot...") if 
        position_manager.is_position_open():
            self.logger.info("Closing open positions 
            before shutdown") 
            position_manager.close_position()
def main(): bot = BasketTradingBot() if not 
    bot.initialize():
        sys.exit(1) try: bot.run() except Exception as 
    e:
        bot.logger.error(f"Fatal error: {e}") 
        telegram.error_alert(f"Fatal error: {e}")
    finally: bot.shutdown() if __name__ == "__main__": 
    main()
