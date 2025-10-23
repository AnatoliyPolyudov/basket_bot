#!/usr/bin/env python3
"""
СКРИПТ ДЛЯ ПОЛНОГО СБРОСА И ПЕРЕЗАГРУЗКИ ДАННЫХ
"""

import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from monitor import SimpleBasketMonitor

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
        monitor = SimpleBasketMonitor()
        print("📊 Starting complete data reset...")
        
        if monitor.complete_data_reset():
            print("✅ SUCCESS: Data reset completed successfully!")
            print("🎯 You can now run: python monitor.py")
            print("")
            print("📈 Expected results after reset:")
            print("   - Z-score: ±0.5 to ±2.0 (normal range)")
            print("   - Accurate trading signals")
        else:
            print("❌ FAILED: Data reset failed!")
            
    except Exception as e:
        print(f"💥 ERROR: {e}")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
