import * as THREE from 'three';
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { platePoint, ZONE } from '../umpireGeometry';
const props = defineProps();
const emit = defineEmits();
const mount = ref(null);
const arrived = ref(false);
const webglUnavailable = ref(false);
const svgX = computed(() => 20 + props.pitch.x * 200);
const svgY = computed(() => 20 + props.pitch.y * 200);
let renderer;
let scene;
let camera;
let ball;
let frame = 0;
let startedAt = 0;
function render() {
    if (renderer && scene && camera)
        renderer.render(scene, camera);
}
function animate(time) {
    if (!ball)
        return;
    const progress = Math.min((time - startedAt) / 1400, 1);
    const end = platePoint(props.pitch);
    const curve = Math.sin(progress * Math.PI) * 0.22;
    ball.position.set(end.x * progress, 2.65 + (end.y - 2.65) * progress + curve, -8 + progress * 8);
    render();
    if (progress < 1)
        frame = requestAnimationFrame(animate);
    else {
        arrived.value = true;
        emit('ready', true);
    }
}
function restart() {
    cancelAnimationFrame(frame);
    arrived.value = false;
    emit('ready', false);
    if (!ball) {
        // The readable front view remains usable if WebGL is disabled.
        arrived.value = true;
        emit('ready', true);
        return;
    }
    ball.material.color.set('#f5f5f4');
    ball.position.set(0, 2.65, -8);
    startedAt = performance.now();
    frame = requestAnimationFrame(animate);
}
function resize() {
    if (!mount.value || !renderer || !camera)
        return;
    const width = mount.value.clientWidth;
    if (!width)
        return;
    const height = Math.round(width * 0.62);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    render();
}
function build() {
    if (!mount.value)
        return;
    try {
        scene = new THREE.Scene();
        scene.background = new THREE.Color('#14201c');
        camera = new THREE.PerspectiveCamera(48, 1, 0.1, 30);
        camera.position.set(0, 2.65, 8);
        camera.lookAt(0, 2.65, 0);
        renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        mount.value.replaceChildren(renderer.domElement);
        scene.add(new THREE.HemisphereLight('#ffffff', '#385449', 2.2));
        const light = new THREE.DirectionalLight('#ffffff', 2);
        light.position.set(-3, 6, 5);
        scene.add(light);
        const top = platePoint({ x: 0.5, y: ZONE.top }).y;
        const bottom = platePoint({ x: 0.5, y: ZONE.bottom }).y;
        const left = platePoint({ x: ZONE.left, y: 0.5 }).x;
        const right = platePoint({ x: ZONE.right, y: 0.5 }).x;
        const zone = new THREE.BoxGeometry(right - left, top - bottom, 0.06);
        const fill = new THREE.Mesh(zone, new THREE.MeshBasicMaterial({ color: '#d8f7df', transparent: true, opacity: 0.08, depthWrite: false }));
        fill.position.set(0, (top + bottom) / 2, 0);
        scene.add(fill);
        const edges = new THREE.LineSegments(new THREE.EdgesGeometry(zone), new THREE.LineBasicMaterial({ color: '#a6f3c0' }));
        edges.position.copy(fill.position);
        scene.add(edges);
        const plate = new THREE.Mesh(new THREE.PlaneGeometry(2.2, 1.5), new THREE.MeshStandardMaterial({ color: '#e9efe9', side: THREE.DoubleSide }));
        plate.rotation.x = -Math.PI / 2;
        plate.position.set(0, 0.04, 0);
        scene.add(plate);
        const floor = new THREE.Mesh(new THREE.PlaneGeometry(20, 20), new THREE.MeshStandardMaterial({ color: '#263d33', side: THREE.DoubleSide }));
        floor.rotation.x = -Math.PI / 2;
        scene.add(floor);
        const destination = platePoint(props.pitch);
        const trail = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(0, 2.65, -8),
            new THREE.Vector3(destination.x * 0.55, 2.65 + (destination.y - 2.65) * 0.55 + 0.2, -3.6),
            new THREE.Vector3(destination.x, destination.y, 0),
        ]);
        const trajectory = new THREE.Line(trail, new THREE.LineBasicMaterial({ color: '#8daea1', transparent: true, opacity: 0.55 }));
        scene.add(trajectory);
        ball = new THREE.Mesh(new THREE.SphereGeometry(ZONE.ballRadius * 3.2, 24, 16), new THREE.MeshStandardMaterial({ color: '#f5f5f4' }));
        scene.add(ball);
        window.addEventListener('resize', resize);
        resize();
    }
    catch {
        webglUnavailable.value = true;
        renderer?.dispose();
        renderer = undefined;
        ball = undefined;
    }
    restart();
}
watch(() => props.pitch, () => {
    // The scene is recreated so the trajectory also points to the next pitch.
    cancelAnimationFrame(frame);
    if (scene)
        scene.traverse(object => {
            if (object instanceof THREE.Mesh || object instanceof THREE.Line || object instanceof THREE.LineSegments) {
                object.geometry.dispose();
                const materials = Array.isArray(object.material) ? object.material : [object.material];
                materials.forEach(material => material.dispose());
            }
        });
    renderer?.dispose();
    renderer = undefined;
    ball = undefined;
    window.removeEventListener('resize', resize);
    build();
});
watch(() => props.revealed, () => {
    if (ball && props.revealed)
        ball.material.color.set(props.strike ? '#42d994' : '#ff6b7c');
    render();
});
onMounted(build);
onBeforeUnmount(() => {
    cancelAnimationFrame(frame);
    window.removeEventListener('resize', resize);
    scene?.traverse(object => {
        if (object instanceof THREE.Mesh || object instanceof THREE.Line || object instanceof THREE.LineSegments) {
            object.geometry.dispose();
            const materials = Array.isArray(object.material) ? object.material : [object.material];
            materials.forEach(material => material.dispose());
        }
    });
    renderer?.dispose();
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "umpire-scene" },
    'aria-label': "從捕手視角觀看的 3D 投球與好球帶",
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div)({
    ref: "mount",
});
/** @type {typeof __VLS_ctx.mount} */ ;
if (__VLS_ctx.webglUnavailable) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
        ...{ class: "webgl-note" },
    });
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.aside, __VLS_intrinsicElements.aside)({
    ...{ class: "plate-reader" },
    'aria-label': "本壘正面判讀",
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
(__VLS_ctx.arrived ? '球已通過好球帶，請判決' : '球正飛向本壘');
__VLS_asFunctionalElement(__VLS_intrinsicElements.svg, __VLS_intrinsicElements.svg)({
    viewBox: "0 0 240 260",
    role: "img",
    'aria-label': "好球帶與球體進壘落點",
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.rect)({
    x: "46",
    y: "66",
    width: "148",
    height: "112",
    rx: "10",
    ...{ class: "expanded-zone" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.rect)({
    x: "56",
    y: "76",
    width: "128",
    height: "92",
    ...{ class: "strike-zone" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.path)({
    d: "M102 201 H138 L132 218 L120 229 L108 218 Z",
    ...{ class: "home-plate" },
});
if (__VLS_ctx.arrived) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.circle)({
        cx: (__VLS_ctx.svgX),
        cy: (__VLS_ctx.svgY),
        r: "10",
        ...{ class: (__VLS_ctx.revealed ? (__VLS_ctx.strike ? 'pitch-dot strike' : 'pitch-dot ball') : 'pitch-dot pending') },
    });
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.text, __VLS_intrinsicElements.text)({
    x: "120",
    y: "250",
    'text-anchor': "middle",
    ...{ class: (__VLS_ctx.revealed ? (__VLS_ctx.strike ? 'strike-text' : 'ball-text') : 'hint-text') },
});
(__VLS_ctx.revealed ? (__VLS_ctx.strike ? '好球' : '壞球') : __VLS_ctx.arrived ? '球已進壘，按 S 或 B' : '觀察球路中…');
__VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({});
/** @type {__VLS_StyleScopedClasses['umpire-scene']} */ ;
/** @type {__VLS_StyleScopedClasses['webgl-note']} */ ;
/** @type {__VLS_StyleScopedClasses['plate-reader']} */ ;
/** @type {__VLS_StyleScopedClasses['expanded-zone']} */ ;
/** @type {__VLS_StyleScopedClasses['strike-zone']} */ ;
/** @type {__VLS_StyleScopedClasses['home-plate']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            mount: mount,
            arrived: arrived,
            webglUnavailable: webglUnavailable,
            svgX: svgX,
            svgY: svgY,
        };
    },
    __typeEmits: {},
    __typeProps: {},
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    __typeEmits: {},
    __typeProps: {},
});
; /* PartiallyEnd: #4569/main.vue */
