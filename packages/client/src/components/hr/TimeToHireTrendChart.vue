<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, GridComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import type { TimeToHirePeriod } from '@/api/hr/analytics'

use([LineChart, TitleComponent, TooltipComponent, GridComponent, LegendComponent, CanvasRenderer])

const props = defineProps<{
  data: TimeToHirePeriod[]
}>()

const option = computed(() => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'cross' },
  },
  legend: {
    data: ['平均天数', '招聘数'],
    bottom: 0,
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: 40,
    top: 20,
    containLabel: true,
  },
  xAxis: {
    type: 'category',
    data: props.data.map(d => d.period),
    boundaryGap: false,
  },
  yAxis: [
    {
      type: 'value',
      name: '天数',
      position: 'left',
    },
    {
      type: 'value',
      name: '数量',
      position: 'right',
    },
  ],
  series: [
    {
      name: '平均天数',
      type: 'line',
      smooth: true,
      data: props.data.map(d => d.avg_days),
      areaStyle: { opacity: 0.15 },
      yAxisIndex: 0,
    },
    {
      name: '招聘数',
      type: 'line',
      smooth: true,
      data: props.data.map(d => d.count),
      yAxisIndex: 1,
    },
  ],
}))
</script>

<template>
  <VChart :option="option" autoresize style="height: 320px;" />
</template>
