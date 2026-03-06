<template>
  <div class="table-wrapper">
    <table>
      <thead>
        <tr>
          <th>日期</th>
          <th>总手数</th>
          <th>最小|大手数</th>
          <th>次数</th>
          <th>盈亏金额</th>
          <th>百分比%</th>
          <th>出入金</th>
          <th>余额</th>
          <th>最大浮亏金额</th>
          <th>最大浮亏比例</th>
          <th>最大浮盈金额</th>
          <th>最大浮盈比例</th>
          <th>最小|平均|最大持仓时间</th>
          <th>胜率</th>
          <th>盈亏比</th>
        </tr>
      </thead>
      
      <!-- Open Positions section -->
      <tbody class="positions-body" v-if="positionsData && positionsData.length > 0">
        <tr v-for="row in positionsData" :key="'pos-'+row.date" class="position-row">
          <td class="secondary">{{ row.date }} (持仓)</td>
          <td :class="colorClass(row.total_lots, true)">{{ row.total_lots.toFixed(2) }}</td>
          <td :class="colorClass(1, true)">{{ row.min_max_lots }}</td>
          <td :class="colorClass(row.trade_count, true)">{{ row.trade_count }}</td>
          <td :class="colorClass(row.pnl)">{{ isPositive(row.pnl) }}{{ row.pnl.toFixed(2) }}</td>
          <td :class="colorClass(row.pnl_percentage)">{{ isPositive(row.pnl_percentage) }}{{ (row.pnl_percentage * 100).toFixed(2) }} %</td>
          <td>{{ row.deposits_withdrawals }}</td>
          <td>{{ row.balance.toFixed(2) }}</td>
          <td :class="colorClass(row.max_floating_loss_amount)">{{ row.max_floating_loss_amount.toFixed(2) }}</td>
          <td :class="colorClass(row.max_floating_loss_percentage)">{{ (row.max_floating_loss_percentage * 100).toFixed(2) }} %</td>
          <td :class="colorClass(row.max_floating_profit_amount)">{{ row.max_floating_profit_amount.toFixed(2) }}</td>
          <td :class="colorClass(row.max_floating_profit_percentage)">{{ (row.max_floating_profit_percentage * 100).toFixed(2) }} %</td>
          <td>{{ row.min_avg_max_holding_time }}</td>
          <td>{{ row.win_rate.toFixed(2) }} %</td>
          <td>{{ row.profit_factor.toFixed(2) }}</td>
        </tr>
      </tbody>
      
      <!-- Blank separator if positions exist -->
      <tbody v-if="positionsData && positionsData.length > 0">
        <tr class="separator-row"><td colspan="15"></td></tr>
      </tbody>

      <!-- History Data section -->
      <tbody>
        <tr v-for="row in data" :key="'hist-'+row.date">
          <td class="secondary">{{ row.date }}</td>
          <td :class="colorClass(row.total_lots, true)">{{ row.total_lots.toFixed(2) }}</td>
          <td :class="colorClass(1, true)">{{ row.min_max_lots }}</td>
          <td :class="colorClass(row.trade_count, true)">{{ row.trade_count }}</td>
          <td :class="colorClass(row.pnl)">{{ isPositive(row.pnl) }}{{ row.pnl.toFixed(2) }}</td>
          <td :class="colorClass(row.pnl_percentage)">{{ isPositive(row.pnl_percentage) }}{{ (row.pnl_percentage * 100).toFixed(2) }} %</td>
          <td>{{ row.deposits_withdrawals }}</td>
          <td>{{ row.balance.toFixed(2) }}</td>
          <td :class="colorClass(row.max_floating_loss_amount)">{{ row.max_floating_loss_amount.toFixed(2) }}</td>
          <td :class="colorClass(row.max_floating_loss_percentage)">{{ (row.max_floating_loss_percentage * 100).toFixed(2) }} %</td>
          <td :class="colorClass(row.max_floating_profit_amount)">{{ row.max_floating_profit_amount.toFixed(2) }}</td>
          <td :class="colorClass(row.max_floating_profit_percentage)">{{ (row.max_floating_profit_percentage * 100).toFixed(2) }} %</td>
          <td>{{ row.min_avg_max_holding_time }}</td>
          <td>{{ row.win_rate.toFixed(2) }} %</td>
          <td>{{ row.profit_factor.toFixed(2) }}</td>
        </tr>
      </tbody>
      <tfoot v-if="summaryRow">
        <tr class="summary-row">
          <td class="secondary">总计</td>
          <td :class="colorClass(summaryRow.total_lots, true)">{{ summaryRow.total_lots.toFixed(2) }}</td>
          <td :class="colorClass(1, true)">{{ summaryRow.min_max_lots }}</td>
          <td :class="colorClass(summaryRow.trade_count, true)">{{ summaryRow.trade_count }}</td>
          <td :class="colorClass(summaryRow.pnl)">{{ isPositive(summaryRow.pnl) }}{{ summaryRow.pnl.toFixed(2) }}</td>
          <td :class="colorClass(summaryRow.pnl_percentage)">{{ isPositive(summaryRow.pnl_percentage) }}{{ (summaryRow.pnl_percentage * 100).toFixed(2) }} %</td>
          <td>{{ summaryRow.deposits_withdrawals.toFixed(2) }}</td>
          <td>{{ summaryRow.balance.toFixed(2) }}</td>
          <td :class="colorClass(summaryRow.max_floating_loss_amount)">{{ summaryRow.max_floating_loss_amount.toFixed(2) }}</td>
          <td :class="colorClass(summaryRow.max_floating_loss_percentage)">{{ (summaryRow.max_floating_loss_percentage * 100).toFixed(2) }} %</td>
          <td :class="colorClass(summaryRow.max_floating_profit_amount)">{{ summaryRow.max_floating_profit_amount.toFixed(2) }}</td>
          <td :class="colorClass(summaryRow.max_floating_profit_percentage)">{{ (summaryRow.max_floating_profit_percentage * 100).toFixed(2) }} %</td>
          <td>{{ summaryRow.min_avg_max_holding_time }}</td>
          <td>{{ summaryRow.win_rate.toFixed(2) }} %</td>
          <td>{{ summaryRow.profit_factor ? summaryRow.profit_factor.toFixed(2) : '-' }}</td>
        </tr>
      </tfoot>
    </table>
  </div>
</template>

<script setup>
const props = defineProps({
  data: {
    type: Array,
    required: true
  },
  positionsData: {
    type: Array,
    default: () => []
  },
  summaryRow: {
    type: Object,
    default: null
  }
});

// For values like Lot size, count, etc always red in the screenshot
const colorClass = (val, alwaysPositive = false) => {
  if (alwaysPositive) return 'positive';
  if (val > 0) return 'positive';
  if (val < 0) return 'negative';
  return '';
};

const isPositive = (val) => val >= 0 ? '+' : '';
</script>

<style scoped>
.table-wrapper {
  overflow-y: auto;
  overflow-x: auto;
  height: 100%;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
  color: #ccc;
  white-space: nowrap;
}

th {
  text-align: left;
  padding: 8px 12px;
  font-weight: 500;
  color: #fff;
  background-color: #242424;
  position: sticky;
  top: 0;
  z-index: 10;
  border-bottom: 1px solid var(--border-color);
  height: 35px; /* Hardcode height so we can offset the sticky row below it reliably */
  box-sizing: border-box;
}

td {
  padding: 6px 12px;
  border-bottom: 1px solid #2a2a2a;
}

tbody tr:hover {
  background-color: var(--surface-hover);
}

.position-row {
  font-weight: bold;
}

.position-row td {
  background-color: #1e282a; /* Solid opaque color tint to hide rows scrolling beneath it */
  position: sticky;
  top: 35px; /* Offset exactly by the header height */
  z-index: 9;
}

.separator-row td {
  padding: 2px 0;
  background-color: var(--surface-color);
  border-bottom: 2px solid #555;
}

.secondary {
  color: #aaa;
}

.positive {
  color: var(--positive-color);
}

.negative {
  color: var(--negative-color);
}

.summary-row {
  font-weight: bold;
}

.summary-row td {
  background-color: #242424; /* Apply background to cells to prevent transparent overlap */
  border-top: 2px solid #444;
  border-bottom: none;
  position: sticky;
  bottom: 0;
  z-index: 10;
}
</style>
