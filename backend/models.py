from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class TradeModel(BaseModel):
    ticket: int
    symbol: str
    type: int # 0 for buy, 1 for sell, etc.
    volume: float
    open_time: datetime
    close_time: datetime
    open_price: float
    close_price: float
    profit: float
    commission: float = 0.0
    swap: float = 0.0
    
class DailySummaryModel(BaseModel):
    account_id: str = ""
    timeframe: str = "日" # Daily, Weekly, Monthly, Quarterly, Yearly
    date: str # YYYY-MM-DD
    total_lots: float
    min_max_lots: str
    trade_count: int
    pnl: float
    pnl_percentage: float
    deposits_withdrawals: float
    balance: float
    max_floating_loss_amount: float
    max_floating_loss_percentage: float
    max_floating_profit_amount: float
    max_floating_profit_percentage: float
    min_avg_max_holding_time: str
    win_rate: float
    profit_factor: float # profit to loss ratio
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "date": "2021-02-24",
                "total_lots": 0.23,
                "min_max_lots": "0.01 | 0.03",
                "trade_count": 16,
                "pnl": 21.92,
                "pnl_percentage": 0.02,
                "deposits_withdrawals": 0,
                "balance": 100521.15,
                "max_floating_loss_amount": -9.10,
                "max_floating_loss_percentage": -0.01,
                "max_floating_profit_amount": 0.91,
                "max_floating_profit_percentage": 0.0,
                "min_avg_max_holding_time": "0:50:35 | 2:40:04 | 5:39:59",
                "win_rate": 68.75,
                "profit_factor": 0.52
            }
        }
