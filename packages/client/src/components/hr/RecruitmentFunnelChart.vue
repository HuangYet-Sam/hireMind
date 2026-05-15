<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { FunnelChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import type { PipelineStage } from '@/api/hr/analytics'

use([FunnelChart, TitleComponent, TooltipComponent, GridComponent, CanvasRenderer])

const props = defineProps<{
  data: PipelineStage[]
}>()

const option = computed(() => ({
  tooltip: {
    trigger: 'item',
    formatter: '{b}: {c}',
  },
  series: [{
    type: 'funnel',
    left: '10%',
    top: 20,
    bottom: 20,
    width: '80%',
    min: 0,
    max: props.data.length ? Math.max(...props.data.map(d => d.count)) : 100,
    minSize: '0%',
    maxSize: '100%',
    sort: 'descending',
    gap: 2,
    label: {
      show: true,
      position: 'inside',
      formatter: '{b}: {c}',
      fontSize: 13,
    },
    data: props.data.map(d => ({
      name: d.stage,
      value: d.count,
    })),
    itemStyle: {
      borderColor: '#fff',
      borderWidth: 1,
    },
  }],
}))
</script>

<template>
  <VChart :option="option" autoresize style="height: 320px;" />
</template>
