import asyncio
import websockets
import json
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import pytz
import psutil
import os

# Target WebSocket endpoint in FastAPI
WS_URI = "ws://127.0.0.1:8000/ws/mt5"

def find_mt5_terminals():
    """Scan running processes for MT5 terminal executables and return their paths."""
    terminals = set()
    for proc in psutil.process_iter(['name', 'exe']):
        try:
            name = proc.info['name']
            if name and name.lower() in ('terminal64.exe', 'terminal.exe'):
                exe_path = proc.info['exe']
                if exe_path and os.path.exists(exe_path):
                    terminals.add(exe_path)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return list(terminals)


def aggregate_by_period(df, period_name, date_format_func, account_id):
    summaries = []
    
    if df.empty:
        return []
        
    df_period = df.copy()
    df_period['period_date'] = date_format_func(df_period['time'])
    
    all_periods = sorted(df_period['period_date'].unique())
    
    # An account always starts at zero before any deposits.
    # The balance at any point is the cumulative sum of all deposits and profits.
    running_balance = 0.0
    
    for period_date_str in all_periods:
        group = df_period[df_period['period_date'] == period_date_str]
        
        closes_group = group[group['entry'].isin([1, 2, 3])]
        deposits_group = group[group['type'] == 2]
        
        trade_count = len(closes_group)
        if trade_count > 0:
            total_lots = closes_group['volume'].sum()
            min_lot = closes_group['volume'].min()
            max_lot = closes_group['volume'].max()
            
            winning_trades = len(closes_group[closes_group['profit'] > 0])
            win_rate = (winning_trades / trade_count) * 100 if trade_count > 0 else 0
            
            gross_profit = closes_group[closes_group['profit'] > 0]['profit'].sum()
            gross_loss = abs(closes_group[closes_group['profit'] < 0]['profit'].sum())
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0)
        else:
            total_lots = 0.0
            min_lot = 0.0
            max_lot = 0.0
            win_rate = 0.0
            profit_factor = 0.0

        # PnL includes EVERY deal in the period (Entry IN commissions, Swap interest, Entry OUT profits, etc) EXCLUDING deposits
        non_deposits_group = group[group['type'] != 2]
        pnl = non_deposits_group['profit'].sum() + non_deposits_group['commission'].sum() + non_deposits_group['swap'].sum()

        daily_deposits = deposits_group['profit'].sum() if not deposits_group.empty else 0.0
        
        # Balance forward
        running_balance += pnl + daily_deposits
        
        pnl_percentage = pnl / running_balance if running_balance > 0 else 0
        
        summary = {
            "account_id": account_id,
            "timeframe": period_name,
            "date": period_date_str,
            "total_lots": round(total_lots, 2),
            "min_max_lots": f"{min_lot:.2f} | {max_lot:.2f}" if trade_count > 0 else "0.00 | 0.00",
            "trade_count": int(trade_count),
            "pnl": round(pnl, 2),
            "pnl_percentage": round(pnl_percentage, 4),
            "deposits_withdrawals": round(daily_deposits, 2),
            "balance": round(running_balance, 2),
            "max_floating_loss_amount": 0.0,
            "max_floating_loss_percentage": 0.0,
            "max_floating_profit_amount": 0.0,
            "max_floating_profit_percentage": 0.0,
            "min_avg_max_holding_time": "00:00:00 | 00:00:00 | 00:00:00",
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2)
        }
        summaries.append(summary)
        
    return summaries

def get_all_summaries(terminal_path=None):
    """Extracts historical deals from MT5 and groups by multiple timeframes."""
    if terminal_path:
        if not mt5.initialize(terminal_path):
            return [], ""
    else:
        if not mt5.initialize():
            return [], ""

    account_info = mt5.account_info()
    account_id = str(account_info.login) if account_info else "unknown"

    timezone = pytz.timezone("Etc/UTC")
    utc_from = datetime(2020, 1, 1, tzinfo=timezone)
    utc_to = datetime.now(timezone)
    
    deals = mt5.history_deals_get(utc_from, utc_to)
    if deals is None or len(deals) == 0:
        mt5.shutdown()
        return [], account_id

    df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    all_summaries = []
    
    # 1. Daily
    all_summaries.extend(aggregate_by_period(df, "日", lambda s: s.dt.strftime('%Y.%m.%d'), account_id))
    
    # 2. Weekly (ISO Year-Week)
    all_summaries.extend(aggregate_by_period(df, "周", lambda s: s.dt.strftime('%G-W%V'), account_id))
    
    # 3. Monthly
    all_summaries.extend(aggregate_by_period(df, "月", lambda s: s.dt.strftime('%Y.%m'), account_id))
    
    # 4. Quarterly
    all_summaries.extend(aggregate_by_period(df, "季", lambda s: s.dt.to_period('Q').dt.strftime('%Y-Q%q'), account_id))
    
    # 5. Yearly
    all_summaries.extend(aggregate_by_period(df, "年", lambda s: s.dt.strftime('%Y'), account_id))
    
    mt5.shutdown()
    return all_summaries, account_id


def get_open_positions(terminal_path=None):
    """Extracts currently open positions from MT5 and aggregates them matching daily summary."""
    if terminal_path:
        if not mt5.initialize(terminal_path):
            return [], "", "", ""
    else:
        if not mt5.initialize():
            return [], "", "", ""
    
    account_info = mt5.account_info()
    account_id = str(account_info.login) if account_info else "unknown"
    account_name = account_info.name if account_info else ""
    broker = account_info.server if account_info else ""
    balance = account_info.balance if account_info else 0.0

    positions = mt5.positions_get()
    if positions is None or len(positions) == 0:
        mt5.shutdown()
        return [], account_id, account_name, broker
        
    trade_count = len(positions)
    volumes = [p.volume for p in positions]
    total_lots = sum(volumes)
    min_lot = min(volumes)
    max_lot = max(volumes)
    
    # We sum profit, swap, and commission to get total floating PnL
    floating_pnl = sum([p.profit for p in positions])
    try:
        floating_pnl += sum([p.swap for p in positions])
        floating_pnl += sum([getattr(p, 'commission', 0.0) for p in positions])
    except Exception:
        pass

    pnl_percentage = (floating_pnl / balance) if balance > 0 else 0.0

    summary = {
        "account_id": account_id,
        "date": "持仓",
        "total_lots": round(total_lots, 2),
        "min_max_lots": f"{min_lot:.2f} | {max_lot:.2f}",
        "trade_count": int(trade_count),
        "pnl": round(floating_pnl, 2),
        "pnl_percentage": round(pnl_percentage, 4),
        "deposits_withdrawals": 0.0,
        "balance": round(balance, 2),
        "max_floating_loss_amount": 0.0,
        "max_floating_loss_percentage": 0.0,
        "max_floating_profit_amount": 0.0,
        "max_floating_profit_percentage": 0.0,
        "min_avg_max_holding_time": "00:00:00 | 00:00:00 | 00:00:00",
        "win_rate": 0,
        "profit_factor": 0
    }

    mt5.shutdown()
    return [summary], account_id, account_name, broker


def get_deals_count(terminal_path=None):
    """Get total deals count for a specific terminal."""
    if terminal_path:
        if not mt5.initialize(terminal_path):
            return -1, ""
    else:
        if not mt5.initialize():
            return -1, ""
    
    account_info = mt5.account_info()
    account_id = str(account_info.login) if account_info else "unknown"

    timezone = pytz.timezone("Etc/UTC")
    utc_from = datetime(2020, 1, 1, tzinfo=timezone)
    utc_to = datetime.now(timezone)
    count = mt5.history_deals_total(utc_from, utc_to)
    
    mt5.shutdown()
    return count, account_id


async def stream_mt5_data():
    """Connecting to FastAPI and sending the extracted MT5 data from all terminals."""
    # Track deals count per account
    last_deals_count = {}  # {account_id: count}

    while True:
        try:
               async with websockets.connect(WS_URI, ping_interval=20, ping_timeout=20) as websocket:
                print("Connected to FastAPI WebSocket.")
                
                # Background task to drain the socket so server pings are answered
                async def consume_pings():
                    try:
                        while True:
                            await websocket.recv()
                    except asyncio.CancelledError:
                        pass
                    except Exception:
                        pass
                        
                reader_task = asyncio.create_task(consume_pings())
                
                try:
                    while True:
                        # Discover all running MT5 terminals
                        terminals = find_mt5_terminals()
                    if not terminals:
                        print("No MT5 terminals found. Retrying in 5s...")
                        await asyncio.sleep(5)
                        continue
                    
                    for terminal_path in terminals:
                        try:
                            # 1. Open Positions
                            positions, account_id, account_name, broker = get_open_positions(terminal_path)
                            
                            await asyncio.wait_for(
                                websocket.send(json.dumps({
                                    "type": "OPEN_POSITIONS_UPDATE",
                                    "data": positions,
                                    "account_id": account_id,
                                    "account_name": account_name,
                                    "broker": broker
                                })),
                                timeout=10.0
                            )
                            print(f"[{account_id}] Sent {len(positions)} open positions")

                            # 2. History Summaries (Only update when deals change)
                            current_count, _ = get_deals_count(terminal_path)
                            prev_count = last_deals_count.get(account_id, -1)
                            
                            if current_count != prev_count:
                                print(f"[{account_id}] History deals changed: {prev_count} -> {current_count}. Updating summaries...")
                                summaries, _ = get_all_summaries(terminal_path)
                                
                                if summaries:
                                    for summary in summaries:
                                        message = {
                                            "type": "DAILY_SUMMARY_UPDATE",
                                            "data": summary
                                        }
                                        await asyncio.wait_for(
                                            websocket.send(json.dumps(message)),
                                            timeout=10.0
                                        )
                                
                                last_deals_count[account_id] = current_count
                        except (websockets.exceptions.ConnectionClosed, websockets.exceptions.ConnectionClosedError) as e:
                            print(f"[{account_id}] Connection Closed: {e}")
                            raise e  # Let the outer handler reconnect
                        except asyncio.TimeoutError:
                            print(f"[{account_id}] WebSocket send timeout! Forcing reconnect.")
                            raise websockets.exceptions.ConnectionClosedError(None, None)
                        except Exception as e:
                            print(f"Error processing terminal {terminal_path}: {e}")
                    
                    await asyncio.sleep(2)
                finally:
                    reader_task.cancel()
                    
        except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosed):
            print("WebSocket disconnected, reconnecting in 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Connection failed: {e}. Retrying in 5s...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(stream_mt5_data())
