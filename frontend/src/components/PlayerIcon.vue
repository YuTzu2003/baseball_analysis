<script setup lang="ts">
import { computed } from 'vue'
import { teamColor } from '../teamPresentation'

const props = withDefaults(defineProps<{ kind?: 'batter' | 'pitcher'; size?: 'sm' | 'md' | 'lg'; teamId?: string }>(), {
  kind: 'batter',
  size: 'md',
})
const backgroundColor = computed(() => props.teamId ? teamColor(props.teamId) : '#5b5b5b')
</script>

<template>
  <span class="player-icon" :class="`player-icon-${size}`" :style="{ backgroundColor }" aria-hidden="true">
    <span class="player-icon-head" />
    <span class="player-icon-body" />
  </span>
</template>

<style scoped>
.player-icon{--icon-size:40px;position:relative;display:inline-block;flex:0 0 auto;width:var(--icon-size);height:var(--icon-size);overflow:hidden;border:2px solid #111;border-radius:50%;background:#5b5b5b}.player-icon-sm{--icon-size:28px}.player-icon-lg{--icon-size:112px}.player-icon-head,.player-icon-body{position:absolute;left:50%;display:block;background:#fff;transform:translateX(-50%)}.player-icon-head{top:20%;width:31%;height:31%;border-radius:50%}.player-icon-body{bottom:-9%;width:75%;height:52%;border-radius:50% 50% 0 0}
</style>
