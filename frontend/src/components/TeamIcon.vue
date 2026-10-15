<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ team?: string; teamId?: string; size?: 'sm' | 'md' }>(), {
  size: 'md',
})
const teamColors: Array<[string, string]> = [
  ['中信', 'team-icon-brothers'],
  ['統一', 'team-icon-lions'],
  ['富邦', 'team-icon-guardians'],
  ['樂天', 'team-icon-monkeys'],
  ['味全', 'team-icon-dragons'],
  ['台鋼', 'team-icon-hawks'],
]
const fallbackPalette = ['team-icon-amber', 'team-icon-blue', 'team-icon-red', 'team-icon-green', 'team-icon-purple', 'team-icon-slate']
const colorClass = computed(() => {
  const team = props.team ?? ''
  const matched = teamColors.find(([name]) => team.includes(name))
  if (matched) return matched[1]
  return fallbackPalette[[...(props.teamId ?? team ?? 'CPBL')].reduce((sum, char) => sum + char.charCodeAt(0), 0) % fallbackPalette.length]
})
</script>

<template>
  <span class="team-icon" :class="[colorClass, `team-icon-${size}`]" :title="team" aria-hidden="true">
    {{ (team ?? 'CPBL').slice(0, 1) }}
  </span>
</template>
