# pairs_core.py - Упрощенная логика анализа пар
import ccxt
import pandas as pd
import numpy as np
from statsmodels.tsa.stattools import adfuller
from scipy.stats import zscore
import logging
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PairAnalyzer:
    def __init__(self):
        self.exchange = ccxt.okx({
            "enableRateLimit": True,
            "options": {"defaultType": "swap"}
        })
        self.pairs = self.get_top_pairs(30)
        
    def get_top_pairs(self, n_pairs: int) -> List[Dict]:
        """Топ пар для мониторинга"""
        top_symbols = [
            "BTC/USDT:USDT", "ETH/USDT:USDT", "BNB/USDT:USDT", "SOL/USDT:USDT",
            "XRP/USDT:USDT", "ADA/USDT:USDT", "AVAX/USDT:USDT", "DOT/USDT:USDT",
            "LINK/USDT:USDT", "LTC/USDT:USDT", "ATOM/USDT:USDT", "DOGE/USDT:USDT",
            "MATIC/USDT:USDT", "TRX/USDT:USDT", "XLM/USDT:USDT", "BCH/USDT:USDT",
            "FIL/USDT:USDT", "ETC/USDT:USDT", "EOS/USDT:USDT", "AAVE/USDT:USDT"
        ]
        
        # Создаем пары BTC/ETH, BTC/BNB, ETH/BNB и т.д.
        pairs = []
        for i in range(min(10, len(top_symbols))):
            for j in range(i + 1, min(i + 6, len(top_symbols))):
                asset_a = top_symbols[i]
                asset_b = top_symbols[j]
                name_a = asset_a.split('/')[0]
                name_b = asset_b.split('/')[0]
                
                pairs.append({
                    'asset_a': asset_a,
                    'asset_b': asset_b,
                    'name': f"{name_a}_{name_b}"
                })
                
                if len(pairs) >= n_pairs:
                    return pairs
        return pairs
    
    def get_current_prices(self) -> Optional[Dict]:
        """Текущие цены для всех символов"""
        try:
            symbols = list(set([p['asset_a'] for p in self.pairs] + [p['asset_b'] for p in self.pairs]))
            tickers = self.exchange.fetch_tickers(symbols)
            return {symbol: ticker['last'] for symbol, ticker in tickers.items() if ticker.get('last')}
        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
            return None
    
    def calculate_spread(self, pair: Dict, prices: Dict) -> Optional[float]:
        """Расчет спреда между парой"""
        try:
            price_a = prices.get(pair['asset_a'])
            price_b = prices.get(pair['asset_b'])
            if price_a and price_b and price_b > 0:
                return price_a / price_b
        except Exception as e:
            logger.error(f"Error calculating spread for {pair['name']}: {e}")
        return None
    
    def analyze_pair(self, pair: Dict, prices: Dict, historical_data: List[float]) -> Dict:
        """Полный анализ одной пары"""
        current_spread = self.calculate_spread(pair, prices)
        if not current_spread or not historical_data:
            return {
                'pair_name': pair['name'],
                'signal': 'NO_DATA',
                'z_score': None,
                'adf_passed': False,
                'current_spread': current_spread
            }
        
        # ADF тест (готовой функцией)
        if len(historical_data) >= 60:
            adf_stat = adfuller(historical_data, maxlag=1)[0]
            adf_passed = adf_stat < -2.0  # Упрощенный критерий
        else:
            adf_passed = False
        
        # Z-score (готовой функцией)
        if len(historical_data) >= 20:
            z_scores = zscore(historical_data, ddof=1)
            current_z = z_scores[-1] if not np.isnan(z_scores[-1]) else None
        else:
            current_z = None
        
        # Генерация сигнала
        signal = self.generate_signal(current_z, adf_passed, pair['name'])
        
        return {
            'pair_name': pair['name'],
            'signal': signal,
            'z_score': current_z,
            'adf_passed': adf_passed,
            'current_spread': current_spread,
            'price_a': prices.get(pair['asset_a']),
            'price_b': prices.get(pair['asset_b'])
        }
    
    def generate_signal(self, z_score: Optional[float], adf_passed: bool, pair_name: str) -> str:
        """Генерация торгового сигнала"""
        if z_score is None or not adf_passed:
            return "NO_DATA"
        
        if z_score > 1.0:
            return f"SHORT_{pair_name.split('_')[0]}_LONG_{pair_name.split('_')[1]}"
        elif z_score < -1.0:
            return f"LONG_{pair_name.split('_')[0]}_SHORT_{pair_name.split('_')[1]}"
        elif abs(z_score) < 0.5:
            return "EXIT_POSITION"
        else:
            return "HOLD"
    
    def get_analysis_report(self) -> Dict:
        """Полный отчет по всем парам"""
        prices = self.get_current_prices()
        if not prices:
            return {'error': 'Failed to fetch prices'}
        
        report = {
            'timestamp': pd.Timestamp.now(),
            'pairs_data': [],
            'total_pairs': len(self.pairs),
            'active_pairs': 0,
            'trading_signals': 0
        }
        
        for pair in self.pairs:
            # В реальной реализации здесь была бы историческая data
            # Для демо используем случайные данные
            historical_data = np.random.normal(1.0, 0.1, 100).tolist()
            
            pair_analysis = self.analyze_pair(pair, prices, historical_data)
            report['pairs_data'].append(pair_analysis)
            
            if pair_analysis['adf_passed']:
                report['active_pairs'] += 1
            if pair_analysis['signal'] not in ['HOLD', 'NO_DATA']:
                report['trading_signals'] += 1
        
        return report
