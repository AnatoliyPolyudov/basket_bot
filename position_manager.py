import logging from typing import Dict, Optional from 
datetime import datetime from config import config from 
exchange import exchange class PositionManager:
    def __init__(self): self.logger = 
        logging.getLogger(__name__) 
        self.current_position = None self.entry_time = 
        None self.entry_zscore = 0.0
        
    def open_position(self, signal_type: str, z_score: 
    float) -> bool:
        if self.current_position is not None: 
            self.logger.warning("Position already open, 
            cannot open new position") return False
            
        try: self._set_leverage()
            
            if signal_type == 
            "SHORT_TARGET_LONG_BASKET":
                success = 
                self._open_short_target_long_basket()
            elif signal_type == 
            "LONG_TARGET_SHORT_BASKET":
                success = 
                self._open_long_target_short_basket()
            else: self.logger.error(f"Invalid signal 
                type: {signal_type}") return False
                
            if success: self.current_position = 
                signal_type self.entry_time = 
                datetime.utcnow() self.entry_zscore = 
                z_score self.logger.info(f"Position 
                opened: {signal_type} at Z-score: 
                {z_score:.2f}") return True
            else: return False
                
        except Exception as e: 
            self.logger.error(f"Error opening position: 
            {e}") return False
    def close_position(self) -> bool: if 
        self.current_position is None:
            self.logger.warning("No position to close") 
            return True
            
        try: success = True
            
            success &= 
            exchange.close_position(config.TARGET_PAIR)
            
            from basket_manager import basket_manager 
            basket_symbols, _ = 
            basket_manager.get_basket_info() for symbol 
            in basket_symbols:
                success &= 
                exchange.close_position(symbol)
                
            if success: self.logger.info("All positions 
                closed successfully") 
                self.current_position = None 
                self.entry_time = None 
                self.entry_zscore = 0.0 return True
            else: self.logger.error("Failed to close 
                some positions") return False
                
        except Exception as e: 
            self.logger.error(f"Error closing position: 
            {e}") return False
    def _set_leverage(self) -> None: try: 
            exchange.set_leverage(config.TARGET_PAIR, 
            config.LEVERAGE)
            
            from basket_manager import basket_manager 
            basket_symbols, _ = 
            basket_manager.get_basket_info() for symbol 
            in basket_symbols:
                exchange.set_leverage(symbol, 
                config.LEVERAGE)
                
        except Exception as e: 
            self.logger.warning(f"Error setting 
            leverage: {e}")
    def _open_short_target_long_basket(self) -> bool: 
        try:
            success = True
            
            success &= 
            self._place_order(config.TARGET_PAIR, 
            'sell', config.MAX_POSITION_SIZE)
            
            from basket_manager import basket_manager 
            basket_symbols, basket_weights = 
            basket_manager.get_basket_info()
            
            for i, symbol in enumerate(basket_symbols): 
                weight = basket_weights[i] if weight > 
                0:
                    size = config.MAX_POSITION_SIZE * 
                    abs(weight) success &= 
                    self._place_order(symbol, 'buy', 
                    size)
                else: size = config.MAX_POSITION_SIZE * 
                    abs(weight) success &= 
                    self._place_order(symbol, 'sell', 
                    size)
                    
            return success
            
        except Exception as e: 
            self.logger.error(f"Error opening short 
            target long basket: {e}") return False
    def _open_long_target_short_basket(self) -> bool: 
        try:
            success = True
            
            success &= 
            self._place_order(config.TARGET_PAIR, 
            'buy', config.MAX_POSITION_SIZE)
            
            from basket_manager import basket_manager 
            basket_symbols, basket_weights = 
            basket_manager.get_basket_info()
            
            for i, symbol in enumerate(basket_symbols): 
                weight = basket_weights[i] if weight > 
                0:
                    size = config.MAX_POSITION_SIZE * 
                    abs(weight) success &= 
                    self._place_order(symbol, 'sell', 
                    size)
                else: size = config.MAX_POSITION_SIZE * 
                    abs(weight) success &= 
                    self._place_order(symbol, 'buy', 
                    size)
                    
            return success
            
        except Exception as e: 
            self.logger.error(f"Error opening long 
            target short basket: {e}") return False
    def _place_order(self, symbol: str, side: str, 
    size: float) -> bool:
        try: order = exchange.create_order( 
                symbol=symbol, order_type='market', 
                side=side, amount=size
            ) return order is not None and 'id' in 
            order
        except Exception as e: 
            self.logger.error(f"Error placing order for 
            {symbol}: {e}") return False
    def get_position_info(self) -> Dict: if 
        self.current_position is None:
            return {}
            
        duration = "" if self.entry_time: duration = 
            str(datetime.utcnow() - self.entry_time)
            
        return { 'type': self.current_position, 
            'entry_time': self.entry_time, 
            'entry_zscore': self.entry_zscore, 
            'duration': duration
        }
    def is_position_open(self) -> bool: return 
        self.current_position is not None
# Global position manager instance
position_manager = PositionManager()
