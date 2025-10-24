#!/usr/bin/env python3
"""
СКРИПТ ДЛЯ ПОЛНОГО СБРОСА И ПЕРЕЗАГРУЗКИ ДАННЫХ
"""

import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from monitor import RStylePairMonitor  # 🆕 ИМПОРТИРУЕМ НОВЫЙ КЛАСС

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def main():
    print("=" * 60)
    print("🔄 DATA RESET SCRIPT - COMPLETE HISTORICAL DATA RELOAD")
    print("=" * 60)
    
    try:
        monitor = RStylePairMonitor()  # 🆕 СОЗДАЕМ НОВЫЙ МОНИТОР
        print("📊 Starting complete data reset...")
        
        if monitor.complete_data_reset():
            print("✅ SUCCESS: Data reset completed successfully!")
            print("🎯 You can now run: python monitor.py")
            print("")
            print("📈 R-STYLE PAIR TRADING READY:")
            print("   - 4 trading pairs (1vs1)")
            print("   - ADF tests on 120/90/60 bars") 
            print("   - Z-score on 35-bar sliding window")
        else:
            print("❌ FAILED: Data reset failed!")
            
    except Exception as e:
        print(f"💥 ERROR: {e}")
    
    print("=" * 60)

if __name__ == "__main__":
    main()