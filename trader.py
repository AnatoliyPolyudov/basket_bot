from observer import Observer
import logging
from datetime import datetime
import json
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class OKXBasketTrader(Observer):
    def __init__(self, paper_trading=True, max_exposure=1000, initial_balance=10000):
        self.paper_trading = paper_trading
        self.max_exposure = max_exposure
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.current_positions = {}
        self.position_history = []
        self.trading_enabled = True
        self.peak_equity = initial_balance
        
        self.performance_stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0,
            'max_drawdown': 0,
            'current_drawdown': 0,
            'best_trade': 0,
            'worst_trade': 0,
            'avg_trade_duration': 0
        }

    def update(self, data):
        """Автоматическая торговля по сигналам"""
        if not self.trading_enabled:
            return
            
        pairs_data = data.get('pairs_data', [])
        current_time = datetime.now()
        
        for pair_data in pairs_data:
            signal = pair_data.get("signal")
            pair_name = pair_data.get("pair_name")
            z_score = pair_data.get("z", 0)
            current_prices = {
                pair_data['asset_a']: pair_data.get('price_a', 0),
                pair_data['asset_b']: pair_data.get('price_b', 0)
            }
            
            # Обновляем плавающий PnL для открытых позиций
            if pair_name in self.current_positions:
                self.update_floating_pnl(pair_name, current_prices, current_time)
            
            # АВТОМАТИЧЕСКОЕ ЗАКРЫТИЕ
            if signal == "EXIT_POSITION" and pair_name in self.current_positions:
                self.close_position(signal, pair_name, f"Auto-close on exit signal (Z={z_score:.2f})", current_prices)
            
            # АВТОМАТИЧЕСКОЕ ОТКРЫТИЕ
            elif (signal and 
                  signal not in ["HOLD", "NO DATA", "NO TRADE - NOT STATIONARY", "EXIT_POSITION"] and
                  pair_name not in self.current_positions and
                  pair_data.get('adf_passed', False)):
                
                # Проверяем лимиты экспозиции
                if self.get_total_exposure() < self.max_exposure * 0.8:
                    self.open_position(signal, pair_name, z_score=z_score, current_prices=current_prices)

    def open_position(self, signal: str, pair_name: str, size=None, z_score=0, current_prices=None):
        """Открытие позиции с полным трекингом"""
        if size is None:
            size = min(self.max_exposure / 4, self.current_balance * 0.2)
        
        if pair_name in self.current_positions:
            logger.warning(f"⚠️ [PAPER] Position already open for {pair_name}")
            return False
        
        position = {
            'signal': signal,
            'size': size,
            'pair_name': pair_name,
            'entry_time': datetime.now(),
            'entry_z': z_score,
            'entry_prices': current_prices.copy() if current_prices else {},
            'current_prices': current_prices.copy() if current_prices else {},
            'floating_pnl': 0,
            'status': 'OPEN',
            'type': 'MANUAL' if 'MANUAL' in signal else 'AUTO',
            'max_floating_pnl': 0,
            'min_floating_pnl': 0
        }
        
        self.current_positions[pair_name] = position
        self.current_balance -= size

        trade_record = {
            'action': 'OPEN',
            'pair_name': pair_name,
            'signal': signal,
            'size': size,
            'entry_time': position['entry_time'],
            'entry_z': z_score,
            'type': position['type'],
            'timestamp': datetime.now().isoformat()
        }
        self.position_history.append(trade_record)
        
        logger.info(f"✅ [PAPER] OPENED: {pair_name} - {signal} | Size: ${size:.2f} | Z: {z_score:.2f}")
        return True

    def close_position(self, signal: str, pair_name: str, reason="Manual close", current_prices=None):
        """Закрытие позиции с расчетом PnL"""
        if pair_name not in self.current_positions:
            logger.warning(f"⚠️ [PAPER] No open position to close for {pair_name}")
            return False
        
        position = self.current_positions[pair_name]
        pnl = position['floating_pnl']
        self.current_balance += position['size'] + pnl
        
        close_record = {
            'action': 'CLOSE',
            'pair_name': pair_name,
            'original_signal': position['signal'],
            'close_signal': signal,
            'size': position['size'],
            'pnl': pnl,
            'pnl_percent': (pnl / position['size']) * 100 if position['size'] > 0 else 0,
            'entry_time': position['entry_time'],
            'exit_time': datetime.now(),
            'entry_z': position['entry_z'],
            'exit_reason': reason,
            'duration_minutes': round((datetime.now() - position['entry_time']).total_seconds() / 60, 1),
            'timestamp': datetime.now().isoformat()
        }
        
        self.position_history.append(close_record)
        self.update_performance_stats(close_record)
        del self.current_positions[pair_name]
        
        logger.info(f"✅ [PAPER] CLOSED: {pair_name} | PnL: ${pnl:.2f} | Reason: {reason}")
        return True

    def update_floating_pnl(self, pair_name: str, current_prices: dict, current_time: datetime):
        """Обновление плавающего PnL"""
        if pair_name not in self.current_positions:
            return
        
        position = self.current_positions[pair_name]
        position['current_prices'] = current_prices.copy()
        
        current_z = self.estimate_current_z(position, current_prices)
        if current_z is not None:
            z_distance_from_entry = abs(position['entry_z']) - abs(current_z)
            pnl = position['size'] * z_distance_from_entry * 0.05
            
            position['floating_pnl'] = pnl
            position['max_floating_pnl'] = max(position['max_floating_pnl'], pnl)
            position['min_floating_pnl'] = min(position['min_floating_pnl'], pnl)

    def estimate_current_z(self, position: dict, current_prices: dict) -> float:
        """Оценка текущего Z-score"""
        try:
            entry_prices = position['entry_prices']
            signal = position['signal']
            
            if "SHORT_" in signal and "LONG_" in signal:
                parts = signal.split('_')
                short_asset = parts[1] + "/USDT:USDT"
                long_asset = parts[3] + "/USDT:USDT"
                
                if short_asset in entry_prices and long_asset in entry_prices:
                    entry_short = entry_prices[short_asset]
                    entry_long = entry_prices[long_asset]
                    current_short = current_prices.get(short_asset, entry_short)
                    current_long = current_prices.get(long_asset, entry_long)
                    
                    entry_spread = entry_short / entry_long
                    current_spread = current_short / current_long
                    spread_change_pct = (current_spread - entry_spread) / entry_spread * 100
                    
                    if "SHORT" in signal.split('_')[0]:
                        return position['entry_z'] - abs(spread_change_pct) * 0.1
                    else:
                        return position['entry_z'] + abs(spread_change_pct) * 0.1
        except Exception as e:
            logger.warning(f"Error estimating Z-score: {e}")
        
        return position['entry_z'] * 0.95

    def update_performance_stats(self, close_record: dict):
        """Обновление статистики"""
        self.performance_stats['total_trades'] += 1
        pnl = close_record['pnl']
        self.performance_stats['total_pnl'] += pnl
        
        if pnl > 0:
            self.performance_stats['winning_trades'] += 1
            self.performance_stats['best_trade'] = max(self.performance_stats['best_trade'], pnl)
        elif pnl < 0:
            self.performance_stats['losing_trades'] += 1
            self.performance_stats['worst_trade'] = min(self.performance_stats['worst_trade'], pnl)
        
        closed_trades = [h for h in self.position_history if h['action'] == 'CLOSE']
        if closed_trades:
            durations = [trade['duration_minutes'] for trade in closed_trades]
            self.performance_stats['avg_trade_duration'] = sum(durations) / len(durations)

    def update_drawdown(self):
        """Обновление просадки"""
        current_equity = self.get_total_equity()
        self.peak_equity = max(self.peak_equity, current_equity)
        
        if self.peak_equity > 0:
            drawdown = (self.peak_equity - current_equity) / self.peak_equity * 100
            self.performance_stats['current_drawdown'] = drawdown
            self.performance_stats['max_drawdown'] = max(self.performance_stats['max_drawdown'], drawdown)

    def get_total_exposure(self) -> float:
        return sum(pos['size'] for pos in self.current_positions.values())

    def get_total_floating_pnl(self) -> float:
        return sum(pos['floating_pnl'] for pos in self.current_positions.values())

    def get_total_equity(self) -> float:
        return self.current_balance + self.get_total_floating_pnl()

    def get_trading_summary(self, current_prices_data=None):
        """Сводка с текущими Z-score"""
        self.update_drawdown()
        
        closed_trades = [h for h in self.position_history if h['action'] == 'CLOSE']
        total_closed_pnl = sum(trade.get('pnl', 0) for trade in closed_trades)
        
        win_rate = 0
        if self.performance_stats['total_trades'] > 0:
            win_rate = (self.performance_stats['winning_trades'] / self.performance_stats['total_trades']) * 100
        
        open_positions_details = []
        for pair_name, position in self.current_positions.items():
            current_z = None
            if current_prices_data:
                for pair_data in current_prices_data.get('pairs_data', []):
                    if pair_data.get('pair_name') == pair_name:
                        current_z = pair_data.get('z')
                        break
            
            if current_z is None:
                current_z = self.estimate_current_z(position, position.get('current_prices', {}))
            
            open_positions_details.append({
                'pair': pair_name,
                'signal': position['signal'],
                'size': position['size'],
                'entry_z': position['entry_z'],
                'current_z': current_z,
                'floating_pnl': position['floating_pnl'],
                'duration_minutes': round((datetime.now() - position['entry_time']).total_seconds() / 60, 1),
                'type': position['type']
            })
    
        return {
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'total_equity': self.get_total_equity(),
            'total_pnl': total_closed_pnl,
            'floating_pnl': self.get_total_floating_pnl(),
            'total_trades': self.performance_stats['total_trades'],
            'open_positions': len(self.current_positions),
            'open_positions_details': open_positions_details,
            'win_rate': win_rate,
            'max_drawdown': self.performance_stats['max_drawdown'],
            'current_drawdown': self.performance_stats['current_drawdown'],
            'best_trade': self.performance_stats['best_trade'],
            'worst_trade': self.performance_stats['worst_trade'],
            'avg_duration': self.performance_stats['avg_trade_duration'],
            'current_positions': list(self.current_positions.keys())
        }

    def get_open_positions(self):
        return self.current_positions

    def get_position_history(self, limit=10):
        return self.position_history[-limit:] if self.position_history else []

    def export_trading_log(self, filename=None):
        if not filename:
            filename = f"trading_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        log_data = {
            'export_time': datetime.now().isoformat(),
            'summary': self.get_trading_summary(),
            'performance_stats': self.performance_stats,
            'position_history': self.position_history,
            'current_positions': self.current_positions
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, default=str)
            logger.info(f"✅ Trading log exported to {filename}")
            return True
        except Exception as e:
            logger.error(f"❌ Error exporting log: {e}")
            return False

    def enable_trading(self):
        self.trading_enabled = True
        logger.info("✅ AUTO TRADING ENABLED")

    def disable_trading(self):
        self.trading_enabled = False
        logger.info("🚫 AUTO TRADING DISABLED")

    def close_all_positions(self, reason="Manual close all"):
        closed_count = 0
        for pair_name in list(self.current_positions.keys()):
            if self.close_position("CLOSE_ALL", pair_name, reason):
                closed_count += 1
        logger.info(f"✅ Closed {closed_count} positions")
        return closed_count