<script setup lang="ts">
defineProps<{ label: string; value: string | number; detail: string; tone?: 'green' | 'blue' | 'ink' }>()
</script>

<template>
  <article class="metric-spark" :class="`tone-${tone ?? 'ink'}`">
    <span>{{ label }}</span><strong>{{ value }}</strong><small>{{ detail }}</small>
  </article>
</template>
