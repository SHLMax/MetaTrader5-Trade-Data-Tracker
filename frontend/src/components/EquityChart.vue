<template>
  <div ref="chartRef" class="chart"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as echarts from 'echarts';

const props = defineProps({
  data: {
    type: Array,
    required: true
  }
});

const chartRef = ref(null);
let chartInstance = null;

const initChart = () => {
  chartInstance = echarts.init(chartRef.value, 'dark', { renderer: 'svg' });
  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis'
    },
    grid: {
      top: 30,
      right: 20,
      bottom: 30,
      left: 60
    },
    xAxis: {
      type: 'category',
      data: props.data.map(item => item.date),
      axisLine: { lineStyle: { color: '#555' } },
      axisLabel: { color: '#aaa', fontSize: 10 },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLine: { show: false },
      axisLabel: { color: '#aaa', fontSize: 10 },
      splitLine: { lineStyle: { color: '#333' } }
    },
    series: [
      {
        name: '余额',
        type: 'line',
        data: props.data.map(item => item.balance),
        itemStyle: { color: '#00bcd4' },
        lineStyle: { width: 3 },
        symbol: 'none',
        smooth: true,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 188, 212, 0.4)' },
            { offset: 1, color: 'rgba(0, 188, 212, 0.05)' }
          ])
        }
      }
    ]
  };
  chartInstance.setOption(option);
};

watch(() => props.data, (newData) => {
  if (chartInstance && newData.length > 0) {
    chartInstance.setOption({
      xAxis: { data: newData.map(item => item.date) },
      series: [{ data: newData.map(item => item.balance) }]
    });
  }
}, { deep: true });

onMounted(() => {
  // Ensure DOM is ready, initialize mock or exact chart
  setTimeout(initChart, 50);
  window.addEventListener('resize', handleResize);
});

const handleResize = () => {
  if (chartInstance) chartInstance.resize();
};

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  if (chartInstance) chartInstance.dispose();
});
</script>

<style scoped>
.chart {
  width: 100%;
  height: 100%;
}
</style>
