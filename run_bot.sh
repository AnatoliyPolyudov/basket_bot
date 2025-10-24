#!/bin/bash

# 🎯 BASKET BOT MANAGEMENT SCRIPT
# Управление статистическим арбитраж ботом с авто-парами

BOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BOT_DIR"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}📊 $1${NC}"
}

case "$1" in
    start|start-auto)
        PRESET="${2:-auto_top_30}"
        echo -e "${GREEN}🚀 STARTING BOT WITH PRESET: $PRESET${NC}"
        
        # Проверяем есть ли Python и зависимости
        if ! command -v python &> /dev/null; then
            print_error "Python not found!"
            exit 1
        fi
        
        # Проверяем есть ли файлы
        if [ ! -f "monitor.py" ]; then
            print_error "monitor.py not found!"
            exit 1
        fi
        
        # Запускаем бота
        python monitor.py --preset "$PRESET"
        ;;
    
    start-default)
        print_info "STARTING BOT WITH DEFAULT PRESET"
        python monitor.py
        ;;
    
    stop)
        print_warning "STOPPING BOT..."
        if pgrep -f "python monitor.py" > /dev/null; then
            pkill -f "python monitor.py"
            sleep 2
            if pgrep -f "python monitor.py" > /dev/null; then
                print_error "Failed to stop bot gracefully, forcing..."
                pkill -9 -f "python monitor.py"
            fi
            print_status "Bot stopped"
        else
            print_warning "Bot is not running"
        fi
        ;;
    
    restart|reload)
        PRESET="${2:-auto_top_30}"
        print_info "RESTARTING BOT WITH PRESET: $PRESET"
        
        # Останавливаем бота
        if pgrep -f "python monitor.py" > /dev/null; then
            pkill -f "python monitor.py"
            sleep 3
        fi
        
        # Запускаем заново
        python monitor.py --preset "$PRESET"
        ;;
    
    status)
        print_info "BOT STATUS:"
        if pgrep -f "python monitor.py" > /dev/null; then
            print_status "Bot is RUNNING"
            echo "Active processes:"
            ps aux | grep "python monitor.py" | grep -v grep | while read line; do
                echo "   📝 $line"
            done
            
            # Пытаемся получить информацию о пресете
            PRESET_INFO=$(ps aux | grep "python monitor.py" | grep -o "preset [a-zA-Z0-9_]*" | head -1)
            if [ ! -z "$PRESET_INFO" ]; then
                echo "   🎯 Using: $PRESET_INFO"
            fi
        else
            print_error "Bot is STOPPED"
        fi
        ;;
    
    test)
        print_info "TESTING ALL PRESETS..."
        python monitor.py --test
        ;;
    
    test-preset)
        if [ -z "$2" ]; then
            print_error "Usage: $0 test-preset <preset_name>"
            echo "   Available presets: auto_top_30, auto_top_20, auto_top_15, auto_btc_focused, top_10_btc_pairs"
            exit 1
        fi
        print_info "TESTING PRESET: $2"
        python monitor.py --preset "$2" --test
        ;;
    
    reset-data)
        print_warning "RESETTING HISTORICAL DATA..."
        python reset_data.py
        ;;
    
    edit-pairs)
        print_info "EDITING PAIRS CONFIG..."
        if command -v nano &> /dev/null; then
            nano pairs_config.py
        elif command -v vim &> /dev/null; then
            vim pairs_config.py
        else
            vi pairs_config.py
        fi
        ;;
    
    view-pairs)
        print_info "VIEWING ALL PAIRS CONFIG:"
        python -c "
try:
    from pairs_config import get_all_presets
    presets = get_all_presets()
    for preset_name, pairs in presets.items():
        print(f'\n🎯 {preset_name.upper()} ({len(pairs)} pairs):')
        for i, pair in enumerate(pairs[:10], 1):  # Показываем первые 10
            print(f'   {i:2d}. {pair[\"name\"]}: {pair[\"asset_a\"]} / {pair[\"asset_b\"]}')
        if len(pairs) > 10:
            print(f'   ... and {len(pairs) - 10} more pairs')
except Exception as e:
    print(f'❌ Error: {e}')
"
        ;;
    
    show-top30)
        print_info "CURRENT TOP-30 PAIRS FROM EXCHANGE:"
        python -c "
try:
    from pairs_config import get_current_top_30_pairs
    pairs = get_current_top_30_pairs()
    print(f'🎯 TOP-30 TRADING PAIRS (live from exchange):')
    for i, pair in enumerate(pairs, 1):
        print(f'{i:2d}. {pair[\"name\"]:15} | {pair[\"type\"]:10} | {pair[\"asset_a\"]} / {pair[\"asset_b\"]}')
except Exception as e:
    print(f'❌ Error loading pairs: {e}')
"
        ;;
    
    show-symbols)
        print_info "TOP SYMBOLS FROM EXCHANGE:"
        python -c "
try:
    from pairs_config import get_top_symbols_from_exchange
    symbols = get_top_symbols_from_exchange(20)
    print(f'📈 TOP-20 SYMBOLS BY VOLUME:')
    for i, symbol in enumerate(symbols, 1):
        print(f'{i:2d}. {symbol}')
except Exception as e:
    print(f'❌ Error: {e}')
"
        ;;
    
    refresh-pairs|update-pairs)
        print_info "REFRESHING PAIRS FROM EXCHANGE..."
        python -c "
try:
    from pairs_config import refresh_presets
    presets = refresh_presets()
    print('✅ Presets refreshed from exchange!')
    for name, pairs in presets.items():
        if name.startswith('auto_'):
            print(f'📊 {name}: {len(pairs)} pairs')
except Exception as e:
    print(f'❌ Error refreshing pairs: {e}')
"
        ;;
    
    add-pair)
        if [ -z "$2" ] || [ -z "$3" ]; then
            print_error "Usage: $0 add-pair <asset_a> <asset_b> [preset]"
            echo "   Example: $0 add-pair BTC/USDT:USDT SOL/USDT:USDT auto_top_30"
            exit 1
        fi
        ASSET_A="$2"
        ASSET_B="$3"
        PRESET="${4:-auto_top_30}"
        PAIR_NAME="${ASSET_A%%/*}_${ASSET_B%%/*}"
        
        print_info "ADDING PAIR: $PAIR_NAME ($ASSET_A / $ASSET_B) to preset: $PRESET"
        
        python -c "
import json
try:
    # Читаем текущую конфигурацию
    with open('pairs_config.py', 'r') as f:
        content = f.read()
    
    # Извлекаем MANUAL_PRESETS
    exec(content)
    
    new_pair = {
        'asset_a': '$ASSET_A',
        'asset_b': '$ASSET_B', 
        'name': '$PAIR_NAME'
    }
    
    if '$PRESET' in MANUAL_PRESETS:
        # Проверяем нет ли уже такой пары
        for pair in MANUAL_PRESETS['$PRESET']:
            if pair['name'] == '$PAIR_NAME':
                print('❌ Pair already exists!')
                exit(1)
        
        MANUAL_PRESETS['$PRESET'].append(new_pair)
        print('✅ Pair added successfully to manual preset!')
    else:
        print('❌ Preset not found in manual presets!')
        print('   Available manual presets:', list(MANUAL_PRESETS.keys()))
        exit(1)
    
    # Сохраняем обратно в файл
    with open('pairs_config.py', 'w') as f:
        f.write('''#!/usr/bin/env python3
\\\"\\\"\\\"
КОНФИГУРАЦИЯ ТОРГОВЫХ ПАР - АВТОМАТИЧЕСКАЯ ЗАГРУЗКА ТОП-30
\\\"\\\"\\\"

import ccxt
import json
from typing import List, Dict

def get_top_symbols_from_exchange(limit=30):
    # ... (остальные функции остаются без изменений)
    pass

def get_fallback_symbols():
    # ... (остальные функции остаются без изменений)
    pass

def generate_top_30_pairs(symbols: List[str]):
    # ... (остальные функции остаются без изменений)
    pass

def get_current_top_30_pairs():
    # ... (остальные функции остаются без изменений)
    pass

# РУЧНЫЕ ПРЕСЕТЫ
MANUAL_PRESETS = %s

def get_all_presets():
    auto_pairs = get_current_top_30_pairs()
    return {**MANUAL_PRESETS, **{
        \"auto_top_30\": auto_pairs,
        \"auto_top_20\": auto_pairs[:20],
        \"auto_top_15\": auto_pairs[:15],
        \"auto_btc_focused\": [p for p in auto_pairs if p[\"asset_a\"] == \"BTC/USDT:USDT\"][:15],
    }}

PAIR_PRESETS = get_all_presets()
AVAILABLE_SYMBOLS = get_top_symbols_from_exchange(30) or get_fallback_symbols()

def get_preset(preset_name):
    all_presets = get_all_presets()
    return all_presets.get(preset_name, [])

def list_available_presets():
    return list(get_all_presets().keys())

def refresh_presets():
    global PAIR_PRESETS, AVAILABLE_SYMBOLS
    PAIR_PRESETS = get_all_presets()
    AVAILABLE_SYMBOLS = get_top_symbols_from_exchange(30) or get_fallback_symbols()
    return PAIR_PRESETS
''' % (json.dumps(MANUAL_PRESETS, indent=4)))
    
except Exception as e:
    print(f'❌ Error: {e}')
    exit(1)
"
        ;;
    
    logs)
        print_info "VIEWING BOT LOGS:"
        if pgrep -f "python monitor.py" > /dev/null; then
            if [ -f "nohup.out" ]; then
                tail -f nohup.out
            else
                print_warning "No log file found. Bot might be running in foreground."
                echo "Current output:"
                ps aux | grep "python monitor.py" | grep -v grep
            fi
        else
            print_error "Bot is not running"
        fi
        ;;
    
    quick-restart)
        print_info "QUICK RESTART - STOP & START AUTO TOP-30"
        ./run_bot.sh stop
        sleep 2
        ./run_bot.sh start-auto
        ;;
    
    deploy)
        print_info "FULL DEPLOY - REFRESH PAIRS & RESTART"
        ./run_bot.sh refresh-pairs
        sleep 2
        ./run_bot.sh quick-restart
        ;;
    
    help|--help|-h|*)
        echo -e "${GREEN}🎯 BASKET BOT MANAGEMENT COMMANDS:${NC}"
        echo ""
        echo -e "${BLUE}🚀 START COMMANDS:${NC}"
        echo "  $0 start-auto           - Start with auto top-30 pairs (recommended)"
        echo "  $0 start [preset]       - Start with specific preset"
        echo "  $0 start-default        - Start with default preset"
        echo ""
        echo -e "${YELLOW}🛑 STOP/RESTART COMMANDS:${NC}"
        echo "  $0 stop                 - Stop bot"
        echo "  $0 restart [preset]     - Restart with preset"
        echo "  $0 quick-restart        - Quick stop & start auto top-30"
        echo "  $0 reload               - Alias for restart"
        echo ""
        echo -e "${GREEN}📊 STATUS & INFO COMMANDS:${NC}"
        echo "  $0 status               - Check bot status"
        echo "  $0 show-top30           - Show current top-30 pairs"
        echo "  $0 show-symbols         - Show top symbols from exchange"
        echo "  $0 view-pairs           - View all pairs config"
        echo "  $0 logs                 - View bot logs"
        echo ""
        echo -e "${BLUE}⚙️  CONFIG COMMANDS:${NC}"
        echo "  $0 refresh-pairs        - Refresh pairs from exchange"
        echo "  $0 edit-pairs           - Edit pairs config"
        echo "  $0 add-pair <a> <b> [p] - Add new trading pair"
        echo "  $0 reset-data           - Reset historical data"
        echo ""
        echo -e "${YELLOW}🧪 TEST COMMANDS:${NC}"
        echo "  $0 test                 - Test all presets"
        echo "  $0 test-preset <name>   - Test specific preset"
        echo ""
        echo -e "${GREEN}🚀 DEPLOY COMMANDS:${NC}"
        echo "  $0 deploy               - Full deploy: refresh pairs & restart"
        echo ""
        echo -e "${BLUE}📋 AVAILABLE PRESETS:${NC}"
        echo "  auto_top_30, auto_top_20, auto_top_15, auto_btc_focused"
        echo "  top_10_btc_pairs (manual)"
        echo ""
        echo -e "${YELLOW}💡 QUICK USAGE:${NC}"
        echo "  ./run_bot.sh start-auto          # 🚀 Start with auto pairs"
        echo "  ./run_bot.sh quick-restart       # 🔄 Quick restart"
        echo "  ./run_bot.sh deploy              # 🚀 Full deploy"
        ;;
esac