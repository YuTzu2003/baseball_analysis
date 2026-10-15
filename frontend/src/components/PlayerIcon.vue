<script setup lang="ts">
withDefaults(defineProps<{ name?: string; kind?: 'batter' | 'pitcher'; size?: 'sm' | 'md' }>(), {
  kind: 'batter',
  size: 'md',
})
</script>

<template>
  <span class="player-icon" :class="[`player-icon-${kind}`, `player-icon-${size}`]" aria-hidden="true">
    <span>{{ kind === 'pitcher' ? 'P' : (name?.slice(0, 1) ?? '球') }}</span>
  </span>
</template>
