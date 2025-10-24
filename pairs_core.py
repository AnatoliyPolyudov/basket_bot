# pairs_core.py - ДИНАМИЧЕСКИЙ ТОП ПАР С OKX
import ccxt
import pandas as pd
import numpy as np
from statsmodels.tsa.stattools import adfuller
from scipy.stats import zscore
import logging
from typing import List, Dict, Optional
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PairAnalyzer:
    def __init__(self, n_pairs: int = 30):
        self.exchange = ccxt.okx({
            "enableRateLimit": True,
            "options": {"defaultType": "swap"}
        })
        self.n_pairs = n_pairs
        self.pairs = self.get_dynamic_top_pairs(n_pairs)
        
    def get_dynamic_top_pairs(self, n_pairs: int) -> List[Dict]:
        """Динамически получает топ пар по объему с OKX"""
        try:
            print(f"📊 Fetching top {n_pairs} pairs from OKX...")
            
            # Получаем все рынки
            markets = self.exchange.load_markets()
            
            # Фильтруем USDT пары спот-маркет
            usdt_pairs = [
                symbol for symbol in markets 
                if symbol.endswith('/USDT:USDT') and markets[symbol]['active']
            ]
            
            print(f"📈 Found {len(usdt_pairs)} active USDT pairs")
            
            # Получаем объемы для топ пар (лимитируем запросы)
            top_symbols = []
            batch_size = 20
            
            for i in range(0, min(100, len(usdt_pairs)), batch_size):
                batch = usdt_pairs[i:i + batch_size]
                try:
                    tickers = self.exchange.fetch_tickers(batch)
                    
                    # Сортируем по объему (baseVolume)
                    batch_volumes = []
                    for symbol in batch:
                        if symbol in tickers and tickers[symbol].get('baseVolume'):
                            volume = tickers[symbol]['baseVolume']
                            batch_volumes.append((symbol, volume))
                    
                    # Добавляем топ из батча
                    batch_volumes.sort(key=lambda x: x[1], reverse=True)
                    top_symbols.extend([s[0] for s in batch_volumes[:10]])
                    
                    time.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    print(f"⚠️ Error fetching batch: {e}")
                    continue
            
            # Берем топ N символов по объему
            top_symbols = list(dict.fromkeys(top_symbols))[:n_pairs * 2]  # Берем в 2 раза больше для создания пар
            
            print(f"🎯 Top {len(top_symbols)} symbols by volume: {[s.split('/')[0] for s in top_symbols[:10]]}...")
            
            # Создаем пары из топ символов
            pairs = []
            max_pairs_per_symbol = 3  # Максимум пар на один символ
            
            for i, symbol_a in enumerate(top_symbols):
                symbol_a_name = symbol_a.split('/')[0]
                pairs_added = 0
                
                for j, symbol_b in enumerate(top_symbols[i+1:], i+1):
                    if pairs_added >= max_pairs_per_symbol:
                        break
                        
                    symbol_b_name = symbol_b.split('/')[0]
                    
                    # Пропускаем пары с одинаковой базой
                    if symbol_a_name != symbol_b_name:
                        pairs.append({
                            'asset_a': symbol_a,
                            'asset_b': symbol_b,
                            'name': f"{symbol_a_name}_{symbol_b_name}",
                            'base_volume_a': self.get_symbol_volume(symbol_a),
                            'base_volume_b': self.get_symbol_volume(symbol_b)
                        })
                        pairs_added += 1
                
                if len(pairs) >= n_pairs:
                    break
            
            # Сортируем пары по совокупному объему
            pairs.sort(key=lambda x: (x.get('base_volume_a', 0) + x.get('base_volume_b', 0)), reverse=True)
            pairs = pairs[:n_pairs]
            
            print(f"✅ Created {len(pairs)} trading pairs")
            print(f"📋 Sample pairs: {[p['name'] for p in pairs[:5]]}...")
            
            return pairs
            
        except Exception as e:
            print(f"❌ Error fetching dynamic pairs: {e}")
            return self.get_fallback_pairs(n_pairs)
    
    def get_symbol_volume(self, symbol: str) -> float:
        """Получает объем для символа"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker.get('baseVolume', 0)
        except:
            return 0
    
    def get_fallback_pairs(self, n_pairs: int) -> List[Dict]:
        """Резервные пары если не удалось получить динамические"""
        print("🔄 Using fallback pair list...")
        
        fallback_symbols = [
            "BTC/USDT:USDT", "ETH/USDT:USDT", "BNB/USDT:USDT", "SOL/USDT:USDT",
            "XRP/USDT:USDT", "ADA/USDT:USDT", "AVAX/USDT:USDT", "DOT/USDT:USDT",
            "LINK/USDT:USDT", "LTC/USDT:USDT", "ATOM/USDT:USDT", "DOGE/USDT:USDT",
            "MATIC/USDT:USDT", "TRX/USDT:USDT", "XLM/USDT:USDT", "BCH/USDT:USDT",
            "FIL/USDT:USDT", "ETC/USDT:USDT", "EOS/USDT:USDT", "AAVE/USDT:USDT"
        ]
        
        pairs = []
        for i in range(min(10, len(fallback_symbols))):
            for j in range(i + 1, min(i + 6, len(fallback_symbols))):
                asset_a = fallback_symbols[i]
                asset_b = fallback_symbols[j]
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
            all_prices = {}
            
            # Разбиваем на батчи чтобы избежать лимитов
            batch_size = 10
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                try:
                    tickers = self.exchange.fetch_tickers(batch)
                    for symbol in batch:
                        if symbol in tickers and tickers[symbol].get('last'):
                            all_prices[symbol] = tickers[symbol]['last']
                    time.sleep(0.3)
                except Exception as e:
                    logger.warning(f"Batch price error: {e}")
            
            return all_prices
        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
            return None

    # Остальные методы остаются без изменений
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
            adf_passed = adf_stat < -2.0
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
