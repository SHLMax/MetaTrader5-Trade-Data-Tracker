<template>
  <div class="dashboard">
    <div class="header">
      <div class="header-controls">
        <select v-model="selectedAccount" class="account-select">
          <option v-for="acc in accounts" :key="acc" :value="acc">{{ accountLabel(acc) }}</option>
        </select>
        <div class="tabs">
          <button v-for="tab in tabs" :key="tab" @click="activeTab = tab" :class="{ active: activeTab === tab }">
            {{ tab }}
          </button>
        </div>
      </div>
    </div>
    <div class="chart-container">
      <EquityChart :data="chartData" />
    </div>
    <div class="tables-container">
      <div class="table-container">
        <TradeTable :data="filteredTableData" :positionsData="filteredPositionsData" :summaryRow="computedSummary" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import axios from 'axios';
import EquityChart from './components/EquityChart.vue';
import TradeTable from './components/TradeTable.vue';

const API_HOST = window.location.hostname;
const API_BASE = `http://${API_HOST}:8000`;
const WS_BASE = `ws://${API_HOST}:8000`;

const allTableData = ref([]);
const positionsData = ref([]);
const accounts = ref([]);
const selectedAccount = ref('');
const accountMeta = ref({});  // { account_id: { name, broker } }

const accountLabel = (acc) => {
  const meta = accountMeta.value[acc];
  if (meta && meta.name) {
    return `${acc} - ${meta.name} (${meta.broker || ''})`;
  }
  return acc;
};

const tabs = ['日', '周', '月', '季', '年'];
const activeTab = ref('日');

const filteredTableData = computed(() => {
  return allTableData.value.filter(d => 
    (d.timeframe || '日') === activeTab.value && 
    (d.account_id || '') === selectedAccount.value
  );
});

const filteredPositionsData = computed(() => {
  return positionsData.value.filter(d => (d.account_id || '') === selectedAccount.value);
});

const computedSummary = computed(() => {
  const data = filteredTableData.value;
  if (!data || data.length === 0) return null;

  let total_lots = 0;
  let min_lot = Infinity;
  let max_lot = -Infinity;
  let trade_count = 0;
  let pnl = 0;
  let deposits_withdrawals = 0;
  let winning_trades = 0;
  let gross_profit = 0;
  let gross_loss = 0;

  data.forEach(row => {
    total_lots += row.total_lots;
    trade_count += row.trade_count;
    pnl += row.pnl;
    deposits_withdrawals += row.deposits_withdrawals;
    
    // Parse min/max lots from string "0.01 | 0.05"
    const lotsParts = row.min_max_lots.split('|').map(s => parseFloat(s.trim()));
    if (lotsParts.length === 2 && !isNaN(lotsParts[0])) {
      min_lot = Math.min(min_lot, lotsParts[0]);
      max_lot = Math.max(max_lot, lotsParts[1]);
    }

    // Recover winning trades
    winning_trades += Math.round((row.win_rate / 100) * row.trade_count);
    
    // Recover approximate gross profit/loss
    // profit_factor = GP / GL
    // pnl = GP - GL
    // GP = GL * PF  =>  pnl = GL * PF - GL = GL * (PF - 1)
    if (row.profit_factor > 0 && row.profit_factor !== 1) {
      const gl = Math.abs(row.pnl / (row.profit_factor - 1));
      const gp = gl * row.profit_factor;
      gross_loss += gl;
      gross_profit += gp;
    } else if (row.pnl > 0) {
      gross_profit += row.pnl; // only profit
    } else if (row.pnl < 0) {
      gross_loss += Math.abs(row.pnl); // only loss
    }
  });

  const latestRow = data[0]; // array is sorted descending
  const pnl_percentage = deposits_withdrawals > 0 ? (pnl / deposits_withdrawals) : 0;
  const win_rate = trade_count > 0 ? (winning_trades / trade_count) * 100 : 0;
  const profit_factor = gross_loss > 0 ? (gross_profit / gross_loss) : (gross_profit > 0 ? gross_profit : 0);

  return {
    date: '总计',
    total_lots: total_lots,
    min_max_lots: `${min_lot === Infinity ? 0 : min_lot.toFixed(2)} | ${max_lot === -Infinity ? 0 : max_lot.toFixed(2)}`,
    trade_count: trade_count,
    pnl: pnl,
    pnl_percentage: pnl_percentage,
    deposits_withdrawals: deposits_withdrawals,
    balance: latestRow.balance,
    max_floating_loss_amount: 0.0,
    max_floating_loss_percentage: 0.0,
    max_floating_profit_amount: 0.0,
    max_floating_profit_percentage: 0.0,
    min_avg_max_holding_time: '00:00:00 | 00:00:00 | 00:00:00',
    win_rate: win_rate,
    profit_factor: profit_factor
  };
});

const chartData = computed(() => {
  return [...filteredTableData.value].reverse().map(item => ({
    date: item.date,
    balance: item.balance
  }));
});

const fetchData = async () => {
  try {
    // Fetch accounts first
    const accResponse = await axios.get(`${API_BASE}/api/accounts`);
    if (accResponse.data && accResponse.data.length > 0) {
      accounts.value = accResponse.data;
      if (!selectedAccount.value) {
        selectedAccount.value = accResponse.data[0];
      }
    }
    
    // Fetch all history
    const response = await axios.get(`${API_BASE}/api/history`);
    if (response.data && response.data.length > 0) {
      allTableData.value = response.data;
    }
  } catch (error) {
    console.error("Error fetching data. Waiting for Real-Time data...", error);
  }
};

const setupWebSocket = () => {
  const ws = new WebSocket(`${WS_BASE}/ws/mt5`);
  
  ws.onopen = () => {
    console.log("Connected to Real-Time Data Stream");
  };
  
  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.event === 'update' && msg.data) {
        // Handle incoming summary
        const newSummary = msg.data;
        const timeframe = newSummary.timeframe || '日';
        const accountId = newSummary.account_id || '';
        
        // Add account to list if new
        if (accountId && !accounts.value.includes(accountId)) {
          accounts.value.push(accountId);
          if (!selectedAccount.value) {
            selectedAccount.value = accountId;
          }
        }
        
        const existsIndex = allTableData.value.findIndex(d => 
          d.date === newSummary.date && 
          (d.timeframe || '日') === timeframe &&
          (d.account_id || '') === accountId
        );
        
        if (existsIndex >= 0) {
          allTableData.value[existsIndex] = newSummary; // Update existing
        } else {
          allTableData.value.push(newSummary); // Add new
          allTableData.value.sort((a, b) => b.date.localeCompare(a.date)); // Keep sorted desc
        }
      } else if (msg.event === 'positions' && msg.data) {
        // Handle incoming open positions — replace for the specific account
        const accountId = msg.account_id || '';
        const accountName = msg.account_name || '';
        const broker = msg.broker || '';
        
        if (accountId && !accounts.value.includes(accountId)) {
          accounts.value.push(accountId);
          if (!selectedAccount.value) {
            selectedAccount.value = accountId;
          }
        }
        
        // Store account metadata
        if (accountId) {
          accountMeta.value[accountId] = { name: accountName, broker: broker };
        }
        
        // Remove old positions for this account, add new ones
        positionsData.value = positionsData.value.filter(d => (d.account_id || '') !== accountId);
        positionsData.value.push(...msg.data);
      }
    } catch (err) {
      console.error("Error parsing WS message:", err);
    }
  };
  
  ws.onclose = () => {
    console.log("WebSocket disconnected, reconnecting in 5s...");
    setTimeout(setupWebSocket, 5000);
  };
};

onMounted(() => {
  fetchData();
  setupWebSocket();
});
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: var(--surface-color);
  box-sizing: border-box;
}

.header {
  padding: 10px 20px;
  border-bottom: 5px solid var(--background-color);
  background-color: #1e1e1e;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 20px;
}

.account-select {
  background-color: #2a2a2a;
  border: 1px solid #333;
  color: #ccc;
  padding: 6px 12px;
  border-radius: 4px;
  font-family: inherit;
  font-size: 0.85rem;
  cursor: pointer;
  outline: none;
  min-width: 140px;
}

.account-select:hover {
  background-color: #3a3a3a;
}

.account-select:focus {
  border-color: var(--accent-color);
}

.tabs {
  display: flex;
  gap: 10px;
}

.tabs button {
  background-color: #2a2a2a;
  border: 1px solid #333;
  color: #ccc;
  padding: 6px 16px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.tabs button:hover {
  background-color: #3a3a3a;
}

.tabs button.active {
  background-color: #4a4a4a;
  color: #fff;
  border-color: #555;
}

.chart-container {
  flex: 0 0 300px; /* Fixed height for chart match screenshot proportion */
  width: 100%;
  border-bottom: 5px solid var(--background-color);
}

.tables-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.table-container {
  flex: 1;
  overflow: hidden;
}
</style>
