# okx_basket_monitor.py
import ccxt
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('okx_basket_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OKXBasketMonitor:
    def __init__(self):
        # Инициализация OKX с фьючерсами
self.exchange = ccxt.okx({
            'sandbox': False,
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'}
        })        
        self.target = 'BTC-USDT-SWAP'
        self.basket_symbols = ['ETH-USDT-SWAP', 'BNB-USDT-SWAP', 'SOL-USDT-SWAP', 'XRP-USDT-SWAP']
        self.basket_weights = []
        self.historical_data = {}
        self.lookback_days = 30
        
    def fetch_historical_data(self):
        """Собираем исторические данные фьючерсов"""
        logger.info("Загрузка исторических данных с OKX...")
        
        for symbol in [self.target] + self.basket_symbols:
            try:
                # OKX требует правильный формат символов для фьючерсов
                since = self.exchange.parse8601(
                    (datetime.now() - pd.Timedelta(days=self.lookback_days)).isoformat()
                )
                
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol, 
                    '1d', 
                    since=since, 
                    limit=30
                )
                
                if not ohlcv:
                    logger.warning(f"Нет данных для {symbol}")
                    continue
                    
                closes = [candle[4] for candle in ohlcv]
                self.historical_data[symbol] = closes
                logger.info(f"Загружено {len(closes)} дней для {symbol}")
                
            except Exception as e:
                logger.error(f"Ошибка загрузки данных для {symbol}: {e}")
                continue
        
        # Проверяем, что есть достаточно данных
        valid_symbols = [s for s in [self.target] + self.basket_symbols 
                        if s in self.historical_data and len(self.historical_data[s]) > 10]
        
        if len(valid_symbols) < 3:  # Минимум target + 2 актива
            logger.error("Недостаточно данных для анализа")
            return False
            
        return True
    
    def calculate_basket_weights(self):
        """Рассчитываем веса на основе корреляций с BTC"""
        correlations = []
        valid_symbols = []
        
        for symbol in self.basket_symbols:
            if (symbol in self.historical_data and 
                self.target in self.historical_data and
                len(self.historical_data[self.target]) == len(self.historical_data[symbol])):
                
                corr = np.corrcoef(self.historical_data[self.target], 
                                 self.historical_data[symbol])[0, 1]
                
                if not np.isnan(corr):
                    correlations.append(corr)
                    valid_symbols.append(symbol)
                    logger.info(f"Корреляция BTC/{symbol}: {corr:.4f}")
        
        # Обновляем корзину только с валидными символами
        self.basket_symbols = valid_symbols
        
        if not correlations:
            logger.warning("Нет валидных корреляций, используем равные веса")
            self.basket_weights = np.ones(len(self.basket_symbols)) / len(self.basket_symbols)
            return
        
        # Веса пропорциональны корреляции (чем выше корреляция, тем больше вес)
        abs_correlations = np.abs(correlations)
        self.basket_weights = abs_correlations / sum(abs_correlations)
        
        logger.info("Рассчитаны веса корзины фьючерсов:")
        for i, symbol in enumerate(self.basket_symbols):
            logger.info(f"  {symbol}: {self.basket_weights[i]:.3f} (корр: {correlations[i]:.3f})")
    
    def get_current_prices(self):
        """Получаем текущие цены фьючерсов"""
        prices = {}
        try:
            all_symbols = [self.target] + self.basket_symbols
            tickers = self.exchange.fetch_tickers(all_symbols)
            
            for symbol in all_symbols:
                if symbol in tickers:
                    prices[symbol] = tickers[symbol]['last']
                else:
                    logger.warning(f"Нет данных для {symbol}")
                    
            return prices if len(prices) == len(all_symbols) else None
            
        except Exception as e:
            logger.error(f"Ошибка получения цен: {e}")
            return None
    
    def calculate_basket_price(self, prices):
        """Рассчитываем цену корзины фьючерсов"""
        basket_price = 0
        for i, symbol in enumerate(self.basket_symbols):
            if symbol in prices:
                basket_price += self.basket_weights[i] * prices[symbol]
        return basket_price
    
    def calculate_spread_series(self):
        """Рассчитываем исторические спреды для фьючерсов"""
        # Находим минимальную длину данных
        min_length = min([len(self.historical_data[s]) 
                         for s in [self.target] + self.basket_symbols 
                         if s in self.historical_data])
        
        if min_length < 10:
            logger.warning("Недостаточно исторических данных")
            return None
        
        target_prices = self.historical_data[self.target][-min_length:]
        
        basket_prices = []
        for i in range(min_length):
            basket_price = 0
            for j, symbol in enumerate(self.basket_symbols):
                basket_price += (self.basket_weights[j] * 
                               self.historical_data[symbol][-min_length:][i])
            basket_prices.append(basket_price)
        
        spreads = np.array(target_prices) / np.array(basket_prices)
        return spreads
    
    def calculate_current_zscore(self, current_prices):
        """Рассчитываем текущий Z-score для фьючерсов"""
        try:
            # Проверяем что все цены есть
            if not all(symbol in current_prices for symbol in [self.target] + self.basket_symbols):
                logger.warning("Не все цены доступны для расчета")
                return None, None, None
            
            # Текущий спред
            target_price = current_prices[self.target]
            basket_price = self.calculate_basket_price(current_prices)
            
            if basket_price == 0:
                logger.warning("Цена корзины равна 0")
                return None, None, None
                
            current_spread = target_price / basket_price
            
            # Исторические спреды
            spread_series = self.calculate_spread_series()
            if spread_series is None:
                return None, None, None
            
            spread_mean = np.mean(spread_series)
            spread_std = np.std(spread_series)
            
            if spread_std < 1e-10:
                logger.warning("Стандартное отклонение слишком мало")
                return None, None, None
            
            z_score = (current_spread - spread_mean) / spread_std
            
            return z_score, current_spread, (spread_mean, spread_std)
            
        except Exception as e:
            logger.error(f"Ошибка расчета Z-score: {e}")
            return None, None, None
    
    def get_trading_signal(self, z_score):
        """Генерируем торговый сигнал на основе Z-score"""
        if z_score is None:
            return "НЕТ ДАННЫХ"
        
        if z_score > 2.0:
            return "SHORT BTC / LONG BASKET"
        elif z_score < -2.0:
            return "LONG BTC / SHORT BASKET"  
        elif abs(z_score) < 0.5:
            return "EXIT POSITION"
        else:
            return "HOLD"
    
    def run_monitoring(self, interval_minutes=5):
        """Запускаем мониторинг фьючерсов"""
        logger.info("Запуск мониторинга Z-score корзины фьючерсов OKX...")
        
        # Инициализация
        if not self.fetch_historical_data():
            logger.error("Не удалось загрузить исторические данные")
            return
        
        self.calculate_basket_weights()
        
        if not self.basket_symbols:
            logger.error("Нет валидных символов для корзины")
            return
        
        logger.info(f"Мониторинг запущен. Корзина: {self.basket_symbols}")
        
        # Основной цикл мониторинга
        while True:
            try:
                current_prices = self.get_current_prices()
                if not current_prices:
                    logger.warning("Не удалось получить цены, повтор через 60 сек")
                    time.sleep(60)
                    continue
                
                z_score, current_spread, stats = self.calculate_current_zscore(current_prices)
                
                if z_score is not None:
                    spread_mean, spread_std = stats
                    signal = self.get_trading_signal(z_score)
                    
                    # Формируем отчет
                    report = f"""
=== OKX FUTURES BASKET MONITOR ===
Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
BTC-USDT-SWAP: ${current_prices[self.target]:.2f}
Цена корзины: ${self.calculate_basket_price(current_prices):.2f}
Спред (BTC/Корзина): {current_spread:.6f}
Среднее: {spread_mean:.6f} ± {spread_std:.6f}
Z-Score: {z_score:.4f}

Сигнал: {signal}

Уровни:
Z > +2.0: SHORT BTC / LONG BASKET
Z < -2.0: LONG BTC / SHORT BASKET  
|Z| < 0.5: EXIT POSITION

Статус: {"🟢 НОРМА" if abs(z_score) < 0.5 else "🟡 ВНИМАНИЕ" if abs(z_score) < 2.0 else "🔴 СИГНАЛ"}
"""
                    print(report)
                    
                    # Логируем сигналы
                    if abs(z_score) > 2.0:
                        logger.warning(f"ТОРГОВЫЙ СИГНАЛ! Z-score: {z_score:.4f} - {signal}")
                    
                else:
                    logger.warning("Не удалось рассчитать Z-score")
                
                logger.info(f"Ожидание {interval_minutes} минут...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("Мониторинг остановлен пользователем")
                break
            except Exception as e:
                logger.error(f"Ошибка в основном цикле: {e}")
                time.sleep(60)

def main():
    monitor = OKXBasketMonitor()
    
    try:
        monitor.run_monitoring(interval_minutes=5)
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
