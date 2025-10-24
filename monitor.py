===== monitor.py =====

# ... остальной код без изменений ...

    def run(self, interval_minutes=1):
        """Основной цикл мониторинга для всех пар"""
        logger.info("🚀 Starting R-STYLE PAIR MONITOR...")
        logger.info(f"🎯 Monitoring {len(self.trading_pairs)} trading pairs")
        logger.info(f"🎯 {len(self.all_symbols)} unique symbols")
        logger.info(f"🎯 ADF Lookbacks: {self.adf_lookbacks} bars")
        logger.info(f"🎯 Z-score Window: {self.window_bars} bars")
        logger.info(f"🎯 R-STYLE THRESHOLDS: ENTER ±1.0, EXIT ±0.5")
        
        logger.info("🔥 PERFORMING COMPLETE DATA RESET BEFORE START...")
        if not self.complete_data_reset():
            logger.error("❌ CRITICAL: Complete data reset failed")
            return
            
        consecutive_bad_data = 0
        
        while True:
            try:
                prices = self.get_current_prices()
                if not prices:
                    consecutive_bad_data += 1
                    if consecutive_bad_data >= 3:
                        logger.error("🚨 Too many consecutive price errors, restarting...")
                        self.complete_data_reset()
                        consecutive_bad_data = 0
                    time.sleep(60)
                    continue
                
                consecutive_bad_data = 0
                current_time = datetime.utcnow().strftime('%H:%M:%S')
                
                # 🎯 ОБРАБАТЫВАЕМ КАЖДУЮ ПАРУ НЕЗАВИСИМО
                all_pair_data = []
                active_pairs_count = 0
                trading_signals_count = 0
                
                for pair in self.trading_pairs:
                    # Пропускаем пары без данных
                    if not self.pair_states[pair["name"]]['data_loaded']:
                        continue
                        
                    # Расчет Z-score и ADF для пары
                    z, spread, stats = self.calculate_zscore_for_pair(pair, prices)
                    historical_spread = self.get_pair_historical_spread(pair)
                    is_stationary = self.calculate_adf_test(historical_spread) if historical_spread is not None else False
                    
                    signal = self.trading_signal_for_pair(z, is_stationary, pair["name"])
                    
                    # Обновляем состояние пары
                    self.pair_states[pair["name"]]['adf_passed'] = is_stationary
                    self.pair_states[pair["name"]]['current_signal'] = signal
                    
                    if is_stationary:
                        active_pairs_count += 1
                    if signal not in ["HOLD", "NO DATA", "NO TRADE - NOT STATIONARY"]:
                        trading_signals_count += 1
                    
                    # Логирование только для пар с данными и сигналами
                    if z is not None and is_stationary:
                        adf_status = "STATIONARY"
                        status = "🚨 ABNORMAL" if abs(z) > 3.0 else "✅ NORMAL"
                        
                        if signal != "HOLD":
                            # 🆕 БЕЗОПАСНОЕ ФОРМАТИРОВАНИЕ - ИСПРАВЛЕННАЯ ЧАСТЬ
                            try:
                                # Преобразуем z в float для безопасного форматирования
                                z_float = float(z)
                                logger.info(f"[{current_time}] {pair['name']}: Z={z_float:.2f} {status} | {signal}")
                            except (ValueError, TypeError, Exception) as format_error:
                                # Если возникает ошибка форматирования, используем безопасный вывод
                                logger.info(f"[{current_time}] {pair['name']}: Z={z} {status} | {signal}")
                    
                    # Собираем данные для уведомлений
                    pair_data = {
                        "pair_name": pair["name"],
                        "asset_a": pair["asset_a"],
                        "asset_b": pair["asset_b"], 
                        "price_a": prices.get(pair["asset_a"], 0),
                        "price_b": prices.get(pair["asset_b"], 0),
                        "spread": spread if spread else 0,
                        "z": z if z else 0,
                        "signal": signal,
                        "adf_passed": is_stationary
                    }
                    all_pair_data.append(pair_data)
                
                # Сводка по итерации
                logger.info(f"📊 [{current_time}] Active: {active_pairs_count}/{len(self.trading_pairs)} | Signals: {trading_signals_count}")
                
                # Уведомляем наблюдателей
                report_data = {
                    "time": datetime.utcnow(),
                    "pairs_data": all_pair_data,
                    "total_pairs": len(self.trading_pairs),
                    "active_pairs": active_pairs_count,
                    "trading_signals": trading_signals_count
                }
                
                # 🆕 СОХРАНЯЕМ ТЕКУЩИЕ ДАННЫЕ ДЛЯ TELEGRAM
                self.current_report_data = report_data
                
                self.notify(report_data)
                
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("🛑 Monitoring stopped by user")
                break
            except Exception as e:
                logger.warning(f"❌ Error in main loop: {e}")
                time.sleep(60)

# ... остальной код без изменений ...