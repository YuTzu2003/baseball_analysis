<script setup lang="ts">
import * as THREE from 'three'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ZONE } from '../umpireGeometry'

type ViewPreset = 'plate' | 'inside' | 'outside'

const props = defineProps<{ pitch: { x: number; y: number; speed: number }; revealed: boolean; strike: boolean }>()
const emit = defineEmits<{ ready: [ready: boolean] }>()
const mount = ref<HTMLDivElement | null>(null)
const webglUnavailable = ref(false)
const viewPreset = ref<ViewPreset>('plate')
const zoneFrame = { left: 38.5, top: 49, width: 19, height: 18 }
const targetLeft = computed(() => zoneFrame.left + ((props.pitch.x - ZONE.left) / (ZONE.right - ZONE.left)) * zoneFrame.width)
const targetTop = computed(() => zoneFrame.top + ((props.pitch.y - ZONE.top) / (ZONE.bottom - ZONE.top)) * zoneFrame.height)

let renderer: THREE.WebGLRenderer | undefined
let scene: THREE.Scene | undefined
let camera: THREE.OrthographicCamera | undefined
let ball: THREE.Mesh<THREE.SphereGeometry, THREE.MeshStandardMaterial> | undefined
let landingMark: THREE.Mesh<THREE.CircleGeometry, THREE.MeshBasicMaterial> | undefined
let frame = 0
let startedAt = 0

function render() {
  if (renderer && scene && camera) renderer.render(scene, camera)
}

function applyCamera() {
  if (!camera) return
  // The Three.js layer uses screen coordinates so its ball lands exactly on the DOM strike zone.
  camera.position.set(0, 0, 10)
  camera.lookAt(0, 0, 0)
  render()
}

function setPreset(preset: ViewPreset) {
  viewPreset.value = preset
  applyCamera()
}

function animate(time: number) {
  if (!ball) return
  const progress = Math.min((time - startedAt) / 1500, 1)
  const flight = Math.min(progress / 0.78, 1)
  const endX = (targetLeft.value / 100) * 2 - 1
  const endY = 1 - (targetTop.value / 100) * 2
  // Start around the pitcher's release point, then grow toward the plate to convey depth.
  const startX = -0.03
  const startY = 0.04
  const breakX = Math.sin(flight * Math.PI) * (props.pitch.x - 0.5) * -0.18
  const arcY = Math.sin(flight * Math.PI) * 0.025
  const destinationX = startX + (endX - startX) * flight + breakX
  const destinationY = startY + (endY - startY) * flight + arcY
  // Carry the pitch just past its crossing point, then leave a small neutral landing mark.
  const pastZone = Math.max(0, (progress - 0.78) / 0.22)
  const direction = new THREE.Vector2(endX - startX, endY - startY).normalize()
  ball.position.set(destinationX + direction.x * pastZone * 0.22, destinationY + direction.y * pastZone * 0.22, 0.5)
  ball.visible = progress < 0.9
  ball.scale.setScalar(0.19 + flight * 0.39)
  if (landingMark) {
    landingMark.position.set(endX, endY, 0.35)
    landingMark.visible = progress >= 0.78
  }
  render()
  if (progress < 1) frame = requestAnimationFrame(animate)
  else emit('ready', true)
}

function restart() {
  cancelAnimationFrame(frame)
  emit('ready', false)
  if (!ball) {
    emit('ready', true)
    return
  }
  ball.material.color.set('#f5f5f4')
  ball.visible = true
  ball.position.set(-0.03, 0.04, 0.5)
  ball.scale.setScalar(0.19)
  if (landingMark) {
    landingMark.visible = false
    landingMark.material.color.set('#111111')
  }
  startedAt = performance.now()
  frame = requestAnimationFrame(animate)
}

function resize() {
  if (!mount.value || !renderer || !camera) return
  const width = mount.value.clientWidth
  const height = mount.value.clientHeight
  if (!width || !height) return
  renderer.setSize(width, height, false)
  camera.updateProjectionMatrix()
  render()
}

function build() {
  if (!mount.value) return
  try {
    scene = new THREE.Scene()
    scene.background = null
    camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 20)
    camera.position.set(0, 0, 10)
    camera.lookAt(0, 0, 0)
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
    renderer.setClearColor(0x000000, 0)
    renderer.domElement.style.pointerEvents = 'none'
    renderer.domElement.setAttribute('aria-label', '主審第一視角投球模擬')
    mount.value.replaceChildren(renderer.domElement)
    scene.add(new THREE.HemisphereLight('#ffffff', '#333333', 2.1))
    const light = new THREE.DirectionalLight('#ffffff', 2.2)
    light.position.set(-3, 6, 5)
    scene.add(light)

    ball = new THREE.Mesh(new THREE.SphereGeometry(0.037, 24, 16), new THREE.MeshStandardMaterial({ color: '#f5f5f4' }))
    scene.add(ball)
    landingMark = new THREE.Mesh(new THREE.CircleGeometry(0.035, 32), new THREE.MeshBasicMaterial({ color: '#111111', transparent: true, opacity: 0.58, depthWrite: false, side: THREE.DoubleSide }))
    landingMark.visible = false
    scene.add(landingMark)
    window.addEventListener('resize', resize)
    setPreset('plate')
    resize()
  } catch {
    webglUnavailable.value = true
    renderer?.dispose()
    renderer = undefined
    ball = undefined
  }
  restart()
}

function disposeScene() {
  cancelAnimationFrame(frame)
  scene?.traverse(object => {
    if (object instanceof THREE.Mesh || object instanceof THREE.Line || object instanceof THREE.LineSegments) {
      object.geometry.dispose()
      const materials = Array.isArray(object.material) ? object.material : [object.material]
      materials.forEach(material => material.dispose())
    }
  })
  renderer?.dispose()
  renderer = undefined
  ball = undefined
  landingMark = undefined
}

watch(() => props.pitch, () => { disposeScene(); build() })
watch(() => props.revealed, render)
onMounted(build)
onBeforeUnmount(() => { window.removeEventListener('resize', resize); disposeScene() })
</script>

<template>
  <div class="umpire-scene" aria-label="主審第一視角的打者與投球模擬">
    <div class="umpire-background" :class="`view-${viewPreset}`">
      <img src="/images/umpire-background.png" alt="主審第一視角的棒球場與打者背景" />
    </div>
    <div v-if="revealed" class="pitch-markup" :class="`view-${viewPreset}`" aria-label="答案用九宮格好球帶">
      <div class="pitch-strike-zone">
        <i v-for="line in 2" :key="`v${line}`" class="zone-divider vertical" :style="{ left: `${line * 33.333}%` }" />
        <i v-for="line in 2" :key="`h${line}`" class="zone-divider horizontal" :style="{ top: `${line * 33.333}%` }" />
      </div>
    </div>
    <div ref="mount" class="umpire-canvas-host" aria-hidden="true" />
    <div class="scene-view-tools" aria-label="切換觀看角度">
      <span>視角</span>
      <button type="button" :class="{ active: viewPreset === 'plate' }" @click="setPreset('plate')">正面</button>
      <button type="button" :class="{ active: viewPreset === 'inside' }" @click="setPreset('inside')">內角</button>
      <button type="button" :class="{ active: viewPreset === 'outside' }" @click="setPreset('outside')">外角</button>
      <small>切換視角查看場景</small>
    </div>
  </div>
  <p v-if="webglUnavailable" class="webgl-note">此瀏覽器無法顯示 3D，仍可用下方正面落點判讀。</p>
</template>
