# utils.py
from config import CAPITAL, RISK_PERCENT def 
calculate_position(entry_price, stop_loss_price):
    """ Calculate position size based on risk 
    management. """ risk_amount = CAPITAL * 
    (RISK_PERCENT / 100) price_diff = abs(entry_price - 
    stop_loss_price) if price_diff == 0:
        raise ValueError("Stop-loss cannot be zero") 
    size = risk_amount / price_diff position_info = (
        f"Capital: {CAPITAL} USDT\n" f"Risk: 
        {RISK_PERCENT}% = {risk_amount:.2f} USDT\n" 
        f"Position size: {size:.4f} units"
    ) print(position_info) return size, position_info
