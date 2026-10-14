<script setup lang="ts">
import { computed } from 'vue'
import { ZONE } from '../umpireGeometry'

const props = defineProps<{ pitch: { x: number; y: number }; strike: boolean; revealed: boolean }>()
const svgX = computed(() => 78 + ((props.pitch.x - ZONE.left) / (ZONE.right - ZONE.left)) * 84)
const svgY = computed(() => 52 + ((props.pitch.y - ZONE.top) / (ZONE.bottom - ZONE.top)) * 136)
</script>

<template>
  <section class="umpire-replay" aria-label="判定回放">
    <div class="umpire-replay-heading">
      <strong>判定回放</strong>
      <small>{{ props.revealed ? '本球判定回放' : '作答後顯示判決' }}</small>
    </div>
    <svg viewBox="0 0 240 260" role="img" :aria-label="revealed ? '九宮格好球帶、球的落點與判定結果' : '九宮格好球帶與球的落點'">
      <rect x="70" y="42" width="100" height="156" rx="10" class="expanded-zone" />
      <rect x="78" y="52" width="84" height="136" class="strike-zone" />
      <path d="M106 52 V188 M134 52 V188 M78 97.33 H162 M78 142.67 H162" class="zone-grid" />
      <path d="M102 201 H138 L132 218 L120 229 L108 218 Z" class="home-plate" />
      <circle v-if="revealed" :cx="svgX" :cy="svgY" r="10" :class="strike ? 'pitch-dot strike' : 'pitch-dot ball'" />
      <text v-if="revealed" x="120" y="250" text-anchor="middle" :class="strike ? 'strike-text' : 'ball-text'">{{ strike ? '好球' : '壞球' }}</text>
    </svg>
    <div v-if="revealed" class="answer-chip" :class="strike ? 'answer-strike' : 'answer-ball'">{{ strike ? 'STRIKE 好球' : 'BALL 壞球' }}</div>
    <p v-if="revealed">球體與好球帶相交，依規則判定。</p>
    <p v-else>先觀察落點並完成判斷。</p>
  </section>
</template>
