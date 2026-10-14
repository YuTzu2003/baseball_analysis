<script setup lang="ts">
import {computed,nextTick,onBeforeUnmount,onMounted,ref,watch,} from "vue";
import snapshot from "./data/cpbl-2024.json";
import MetricSpark from "./components/MetricSpark.vue";
import UmpireScene from "./components/UmpireScene.vue";
import UmpireReplay from "./components/UmpireReplay.vue";
import { isStrike } from "./umpireGeometry";

type Batter = (typeof snapshot.batters)[number];
type Pitcher = (typeof snapshot.pitchers)[number];
type View = "home" | "players" | "profile" | "teams" | "umpire" | "rankings";
type Audience = "scout" | "coach" | "analyst" | "player";
type Pitch = { x: number; y: number; speed: number; label: string };
const views: Array<[View, string]> = [
  ["umpire", "鍵盤裁判"],
  ["home", "數據排行榜"],
  ["players", "球員資料庫"],
  ["teams", "球隊"],
];
const navLabels: Record<View, string> = { home: "數據首頁", players: "球員數據", profile: "球員檔案", teams: "球隊名單", umpire: "裁判挑戰", rankings: "完整排行榜" };
const navIcons: Record<View, string> = { home: "▦", players: "●", profile: "●", teams: "◆", umpire: "◉", rankings: "#" };
const audiences: Array<[Audience, string, string]> = [
  ["scout", "球探", "工具、樣本與相對位置"],
  ["coach", "教練", "人選與球隊脈絡"],
  ["analyst", "技術員", "指標口徑與資料限制"],
  ["player", "球員", "同年度定位與生涯趨勢"],
];
const battingMetrics: Record<string, string> = {
  OPS: "OPS",
  AVG: "AVG",
  OBP: "OBP",
  SLG: "SLG",
  HR: "全壘打",
  RBI: "打點",
  H: "安打",
  K_pct: "K%",
  BB_pct: "BB%",
  ISO: "ISO",
};
const pitchingMetrics: Record<string, string> = {
  ERA: "ERA",
  WHIP: "WHIP",
  SO: "三振",
  K_9: "K/9",
  BB_9: "BB/9",
  HR_9: "HR/9",
  SV: "救援成功",
};
const dataset = ref({
  ...snapshot,
  batters: [...snapshot.batters],
  pitchers: [...snapshot.pitchers],
  standings: [...snapshot.standings],
});
const active = ref<View>("umpire"),
  audience = ref<Audience>("scout"),
  role = ref<"batters" | "pitchers">("batters"),
  team = ref("全部"),
  metric = ref("OPS"),
  minimum = ref(100);
const selectedSeason = ref(snapshot.season),
  availableSeasons = ref<number[]>([snapshot.season]),
  dataStatus = ref("讀取本機資料庫");
const profileKind = ref<"batters" | "pitchers">("batters"),
  profileId = ref(""),
  profileHistory = ref<Record<string, unknown>[]>([]);
const profileMetric = ref("");
const profileSeasonRows = computed(() => {
  const rows = profileHistory.value.filter((row) => Number(row.season) === selectedSeason.value);
  return rows.length ? rows : profileHistory.value;
});
const selectedTeam = ref("");
const rosterRole = ref<"batters" | "pitchers">("batters");
const score = ref({
    correct: 0,
    total: 0,
    strikeMiss: 0,
    ballMiss: 0,
    streak: 0,
  }),
  pitchIndex = ref(0),
  judgement = ref<"S" | "B" | null>(null),
  pitchReady = ref(false);
const pitchStats = ref<Record<string, { total: number; correct: number }>>({});
const playerChartEl = ref<HTMLElement | null>(null),
  profileChartEl = ref<HTMLElement | null>(null);
let playerChart: import("echarts").ECharts | undefined;
let profileChart: import("echarts").ECharts | undefined;
const paths: Record<Exclude<View, "profile">, string> = {
  home: "/",
  players: "/players",
  teams: "/teams",
  umpire: "/umpire",
  rankings: "/rankings",
};
function navigate(view: Exclude<View, "profile">) {
  active.value = view;
  window.history.pushState({}, "", paths[view]);
  nextTick(drawCharts);
}
function navigateProfile(kind: "batters" | "pitchers", id: string, metric = "") {
  window.history.pushState(
    {},
    "",
    `/players/${kind}/${encodeURIComponent(id)}${metric ? `?metric=${encodeURIComponent(metric)}` : ""}`,
  );
}
function openRanking(kind: "batters" | "pitchers", metric: string, ascending = false) {
  rankingKind.value = kind;
  rankingMetric.value = metric;
  rankingAscending.value = ascending;
  active.value = "rankings";
  window.history.pushState({}, "", `/rankings?kind=${kind}&metric=${encodeURIComponent(metric)}&ascending=${ascending}`);
}
async function applyLocation() {
  const match = window.location.pathname.match(
    /^\/players\/(batters|pitchers)\/([^/]+)$/,
  );
  if (match) {
    await openProfile(
      match[1] as "batters" | "pitchers",
      decodeURIComponent(match[2]),
      false,
      new URLSearchParams(window.location.search).get("metric") ?? "",
    );
    return;
  }
  if (window.location.pathname === "/rankings") {
    const params = new URLSearchParams(window.location.search);
    rankingKind.value = params.get("kind") === "pitchers" ? "pitchers" : "batters";
    rankingMetric.value = params.get("metric") ?? (rankingKind.value === "batters" ? "OPS" : "ERA");
    rankingAscending.value = params.get("ascending") === "true";
    active.value = "rankings";
    return;
  }
  const view = (Object.entries(paths).find(
    ([, path]) => path === window.location.pathname,
  )?.[0] ?? "home") as Exclude<View, "profile">;
  active.value = view;
  await nextTick(drawCharts);
}
const pitches: Pitch[] = [
  { x: 0.5, y: 0.46, speed: 142, label: "四縫線" },
  { x: 0.12, y: 0.45, speed: 148, label: "四縫線" },
  { x: 0.87, y: 0.66, speed: 133, label: "變速球" },
  { x: 0.49, y: 0.2, speed: 151, label: "四縫線" },
  { x: 0.3, y: 0.72, speed: 126, label: "曲球" },
  { x: 0.7, y: 0.37, speed: 145, label: "滑球" },
  { x: -0.03, y: 0.52, speed: 139, label: "卡特球" },
  { x: 0.54, y: 0.85, speed: 122, label: "曲球" },
];
const teams = computed(() => [
  "全部",
  ...new Set(dataset.value.batters.map((x) => x.team)),
]);
const players = computed(() =>
  (dataset.value[role.value] as Array<Batter | Pitcher>).filter(
    (x) => team.value === "全部" || x.team === team.value,
  ),
);
const metrics = computed(() =>
  role.value === "batters" ? battingMetrics : pitchingMetrics,
);
const qualified = computed(() =>
  players.value.filter((x) =>
    role.value === "batters"
      ? Number((x as Batter).PA) >= minimum.value
      : Number((x as Pitcher).IP) >= minimum.value / 50,
  ),
);
const sorted = computed(() =>
  [...qualified.value]
    .filter((x) => x[metric.value as keyof typeof x] != null)
    .sort(
      (a, b) =>
        Number(b[metric.value as keyof typeof b]) -
        Number(a[metric.value as keyof typeof a]),
    ),
);
const selectedPitch = computed(
  () => pitches[pitchIndex.value % pitches.length],
);
const pitchTypeAccuracy = computed(() =>
  [...new Set(pitches.map((pitch) => pitch.label))].map((label) => {
    const stats = pitchStats.value[label] ?? { total: 0, correct: 0 };
    return {
      label,
      ...stats,
      accuracy: stats.total
        ? Math.round((stats.correct / stats.total) * 100)
        : null,
    };
  }),
);
const strike = computed(() => isStrike(selectedPitch.value));
const leaders = computed(() =>
  [...dataset.value.batters]
    .filter((x) => Number(x.PA) >= minimum.value)
    .sort((a, b) => Number(b.OPS) - Number(a.OPS))
    .slice(0, 5),
);
const pitcherLeaders = computed(() =>
  [...dataset.value.pitchers]
    .filter((x) => Number(x.IP) >= 50)
    .sort((a, b) => Number(a.ERA) - Number(b.ERA))
    .slice(0, 5),
);
const battingBoards = [
  { key: "OPS", label: "OPS", sample: "最低 100 PA" },
  { key: "AVG", label: "打擊率", sample: "最低 100 PA" },
  { key: "HR", label: "全壘打", sample: "累積數據" },
  { key: "RBI", label: "打點", sample: "累積數據" },
] as const;
const pitchingBoards = [
  { key: "ERA", label: "防禦率", sample: "最低 50 IP", ascending: true },
  { key: "WHIP", label: "WHIP", sample: "最低 50 IP", ascending: true },
  { key: "SO", label: "三振", sample: "累積數據", ascending: false },
  { key: "SV", label: "救援成功", sample: "累積數據", ascending: false },
] as const;
const leaderTeam = computed(
  () =>
    [...dataset.value.standings].sort(
      (a, b) => Number(b.win_pct) - Number(a.win_pct),
    )[0],
);
const activeNews = ref(0);
const homeNews = computed(() => [
  { label: "打擊焦點", highlight: leaders.value[0]?.name ?? "—", title: "暫居 OPS 領先", detail: leaders.value[0] ? `${leaders.value[0].team} · OPS ${fmt(leaders.value[0].OPS, "OPS")}` : "尚無符合資格的打者資料", kind: "batters" as const, id: String(leaders.value[0]?.source_player_id ?? "") },
  { label: "投球焦點", highlight: pitcherLeaders.value[0]?.name ?? "—", title: "防禦率最佳", detail: pitcherLeaders.value[0] ? `${pitcherLeaders.value[0].team} · ERA ${fmt(pitcherLeaders.value[0].ERA, "ERA")}` : "尚無符合資格的投手資料", kind: "pitchers" as const, id: String(pitcherLeaders.value[0]?.source_player_id ?? "") },
  { label: "戰績焦點", highlight: leaderTeam.value?.team ?? "—", title: "位居聯盟第一", detail: leaderTeam.value ? `${leaderTeam.value.W} 勝 · ${leaderTeam.value.L} 敗 · 勝率 ${fmt(leaderTeam.value.win_pct, "win_pct")}` : "尚無戰績資料", kind: "teams" as const, id: String(leaderTeam.value?.source_team_id ?? "") },
]);
const currentNews = computed(() => homeNews.value[activeNews.value] ?? homeNews.value[0]);
function selectNews(index: number) { activeNews.value = index; }
function openNews() { if (!currentNews.value?.id) return; if (currentNews.value.kind === "teams") openTeam(currentNews.value.id); else void openProfile(currentNews.value.kind, currentNews.value.id); }
const selectedClub = computed(
  () =>
    dataset.value.standings.find(
      (x) => x.source_team_id === selectedTeam.value,
    ) ?? dataset.value.standings[0],
);
const clubBatters = computed(() =>
  dataset.value.batters
    .filter((x) => x.source_team_id === selectedClub.value?.source_team_id)
    .sort((a, b) => Number(b.OPS) - Number(a.OPS)),
);
const clubPitchers = computed(() =>
  dataset.value.pitchers
    .filter((x) => x.source_team_id === selectedClub.value?.source_team_id)
    .sort((a, b) => Number(a.ERA) - Number(b.ERA)),
);
const rosterRows = computed(() =>
  rosterRole.value === "batters" ? clubBatters.value : clubPitchers.value,
);
const fmt = (value: unknown, key: string) => {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  if (["AVG", "OBP", "SLG", "OPS", "ISO", "win_pct"].includes(key))
    return n.toFixed(3).replace(/^0/, "");
  if (["ERA", "WHIP", "K_9", "BB_9", "HR_9"].includes(key)) return n.toFixed(2);
  if (["K_pct", "BB_pct"].includes(key)) return `${n.toFixed(1)}%`;
  return n.toLocaleString();
};
const initials = (value: unknown) => String(value ?? "").trim().slice(0, 2) || "CP";
const topBatters = (key: keyof Batter) =>
  [...dataset.value.batters]
    .filter((x) => key === "HR" || key === "RBI" || Number(x.PA) >= 100)
    .sort((a, b) => Number(b[key]) - Number(a[key]))
    .slice(0, 5);
const topPitchers = (key: keyof Pitcher, ascending = false) =>
  [...dataset.value.pitchers]
    .filter((x) => key === "SO" || key === "SV" || Number(x.IP) >= 50)
    .sort((a, b) =>
      ascending
        ? Number(a[key]) - Number(b[key])
        : Number(b[key]) - Number(a[key]),
    )
    .slice(0, 5);
const rankingKind = ref<"batters" | "pitchers">("batters");
const rankingMetric = ref("OPS");
const rankingAscending = ref(false);
const rankedBatters = (key: keyof Batter) => [...dataset.value.batters].filter((x) => key === "HR" || key === "RBI" || Number(x.PA) >= 100).sort((a, b) => Number(b[key]) - Number(a[key]));
const rankedPitchers = (key: keyof Pitcher, ascending = false) => [...dataset.value.pitchers].filter((x) => key === "SO" || key === "SV" || Number(x.IP) >= 50).sort((a, b) => ascending ? Number(a[key]) - Number(b[key]) : Number(b[key]) - Number(a[key]));
const battingRankingRows = computed(() => rankedBatters(rankingMetric.value as keyof Batter).slice(0, 30));
const pitchingRankingRows = computed(() => rankedPitchers(rankingMetric.value as keyof Pitcher, rankingAscending.value).slice(0, 30));
const fullRankingRows = computed(() => (rankingKind.value === "batters" ? rankedBatters(rankingMetric.value as keyof Batter) : rankedPitchers(rankingMetric.value as keyof Pitcher, rankingAscending.value)).slice(0, 30));
const fullRankingLabel = computed(() => rankingKind.value === "batters" ? battingMetrics[rankingMetric.value] : pitchingMetrics[rankingMetric.value]);
function rankingValue(player: Batter | Pitcher) { return fmt(player[rankingMetric.value as keyof typeof player], rankingMetric.value); }
function raw(row: Record<string, unknown>) {
  try {
    return JSON.parse(String(row.raw_json ?? "{}")) as Record<string, unknown>;
  } catch {
    return {};
  }
}
function mapBatters(rows: Record<string, unknown>[]) {
  return rows.map((row) => {
    const x = raw(row);
    return {
      source_player_id: row.player_id,
      source_team_id: row.team_id,
      name: row.name,
      team: row.team,
      PA: row.pa,
      AB: row.ab,
      H: row.h,
      HR: row.hr,
      RBI: row.rbi,
      BB: row.bb,
      SO: row.so,
      SB: row.sb,
      AVG: row.avg,
      OBP: row.obp,
      SLG: row.slg,
      OPS: row.ops,
      K_pct: row.k_pct,
      BB_pct: row.bb_pct,
      ISO: row.iso,
      G: x.G ?? 0,
      R: x.R ?? 0,
      TB: x.TB ?? 0,
    } as unknown as Batter;
  });
}
function mapPitchers(rows: Record<string, unknown>[]) {
  return rows.map((row) => {
    const x = raw(row);
    return {
      source_player_id: row.player_id,
      source_team_id: row.team_id,
      name: row.name,
      team: row.team,
      IP: Number(row.ip_outs) / 3,
      W: row.w,
      L: row.l,
      SV: row.sv,
      HLD: row.hld,
      SO: row.so,
      BB: row.bb,
      HR: row.hr,
      ER: row.er,
      ERA: row.era,
      WHIP: row.whip,
      K_pct: row.k_pct,
      BB_pct: row.bb_pct,
      K_9: row.k_9,
      BB_9: row.bb_9,
      HR_9: row.hr_9,
      G: x.G ?? 0,
    } as unknown as Pitcher;
  });
}
async function openProfile(
  kind: "batters" | "pitchers",
  id: string,
  updateUrl = true,
  metric = "",
) {
  profileKind.value = kind;
  profileId.value = id;
  profileMetric.value = metric;
  try {
    const r = await fetch(
      `/api/${kind}/player/${encodeURIComponent(id)}/history`,
    );
    profileHistory.value = r.ok ? await r.json() : [];
  } catch {
    profileHistory.value = [];
  }
  active.value = "profile";
  if (updateUrl) navigateProfile(kind, id, metric);
  await nextTick(drawCharts);
}
async function loadSeason() {
  try {
    const season = selectedSeason.value;
    const [b, p, s] = await Promise.all([
      fetch(`/api/batters?season=${season}`),
      fetch(`/api/pitchers?season=${season}`),
      fetch(`/api/standings?season=${season}`),
    ]);
    if (!b.ok || !p.ok || !s.ok) throw Error();
    dataset.value = {
      season,
      batters: mapBatters(await b.json()),
      pitchers: mapPitchers(await p.json()),
      standings: (await s.json()).map((x: Record<string, unknown>) => ({
        source_team_id: x.team_id,
        team: x.team,
        nickname: x.nickname,
        W: x.wins,
        L: x.losses,
        T: x.ties,
        win_pct: x.win_pct,
      })),
    } as typeof snapshot;
    dataStatus.value = "SQLite 本機資料庫";
    await nextTick(drawCharts);
  } catch {
    dataStatus.value = "使用內建快照";
  }
}
async function drawCharts() {
  const e = await import("echarts");
  const ink = "#343a40";
  const muted = "#68717c";
  const rule = "#e5e7e9";
  const accent = "#b67d1c";
  if (active.value === "players" && playerChartEl.value) {
    playerChart?.dispose();
    playerChart = e.init(playerChartEl.value);
    const d = sorted.value.slice(0, 10);
    playerChart.setOption({
      grid: { left: 42, right: 18, top: 20, bottom: 55 },
      xAxis: {
        type: "category",
        data: d.map((x) => x.name),
        axisLabel: { rotate: 35, color: muted },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: muted },
        splitLine: { lineStyle: { color: rule } },
      },
      tooltip: { trigger: "axis" },
      series: [
        {
          type: "bar",
          data: d.map((x) => Number(x[metric.value as keyof typeof x])),
          itemStyle: { color: accent },
        },
      ],
    });
  }
  if (active.value === "profile" && profileChartEl.value) {
    profileChart?.dispose();
    profileChart = e.init(profileChartEl.value);
    const key = profileKind.value === "batters" ? "ops" : "era";
    const color = profileKind.value === "batters" ? accent : ink;
    profileChart.setOption({
      grid: { left: 42, right: 18, top: 20, bottom: 36 },
      xAxis: {
        type: "category",
        data: profileHistory.value.map((x) => String(x.season)),
        axisLabel: { color: muted },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: muted },
        splitLine: { lineStyle: { color: rule } },
      },
      tooltip: { trigger: "axis" },
      series: [
        {
          type: "line",
          smooth: true,
          data: profileHistory.value.map((x) => x[key]),
          lineStyle: { color, width: 2 },
          itemStyle: { color },
        },
      ],
    });
  }
}
function answer(value: "S" | "B") {
  if (judgement.value || !pitchReady.value) return;
  judgement.value = value;
  const right = (value === "S") === strike.value;
  score.value = {
    total: score.value.total + 1,
    correct: score.value.correct + Number(right),
    streak: right ? score.value.streak + 1 : 0,
    strikeMiss: score.value.strikeMiss + Number(!right && strike.value),
    ballMiss: score.value.ballMiss + Number(!right && !strike.value),
  };
  localStorage.setItem("cpbl-umpire-score", JSON.stringify(score.value));
  const label = selectedPitch.value.label;
  const previous = pitchStats.value[label] ?? { total: 0, correct: 0 };
  pitchStats.value = {
    ...pitchStats.value,
    [label]: {
      total: previous.total + 1,
      correct: previous.correct + Number(right),
    },
  };
  localStorage.setItem(
    "cpbl-umpire-pitch-stats",
    JSON.stringify(pitchStats.value),
  );
}
function loadPitchStats() {
  try {
    const saved = JSON.parse(
      localStorage.getItem("cpbl-umpire-pitch-stats") ?? "{}",
    ) as Record<string, { total: number; correct: number }>;
    pitchStats.value = Object.fromEntries(
      Object.entries(saved).filter(
        ([, stats]) =>
          Number.isFinite(stats?.total) &&
          Number.isFinite(stats?.correct) &&
          stats.total >= 0 &&
          stats.correct >= 0 &&
          stats.correct <= stats.total,
      ),
    );
  } catch {
    pitchStats.value = {};
  }
}
function nextPitch() {
  pitchReady.value = false;
  judgement.value = null;
  pitchIndex.value++;
}
function keyboard(e: KeyboardEvent) {
  if (active.value !== "umpire") return;
  if (e.key.toLowerCase() === "s") answer("S");
  if (e.key.toLowerCase() === "b") answer("B");
  if (e.key === "Enter" && judgement.value) nextPitch();
}
function switchRole(x: "batters" | "pitchers") {
  role.value = x;
  metric.value = x === "batters" ? "OPS" : "ERA";
}
function openTeam(teamId: string) {
  selectedTeam.value = teamId;
  rosterRole.value = "batters";
  navigate("teams");
}
watch([active, metric, minimum, role, team], () => nextTick(drawCharts));
watch(active, (view) => {
  if (view !== "profile" && window.location.pathname !== paths[view])
    window.history.pushState({}, "", paths[view]);
});
onMounted(() => {
  window.addEventListener("popstate", applyLocation);
  void applyLocation();
});
onMounted(async () => {
  const saved = localStorage.getItem("cpbl-umpire-score");
  if (saved) score.value = JSON.parse(saved);
  loadPitchStats();
  window.addEventListener("keydown", keyboard);
  try {
    const r = await fetch("/api/seasons");
    if (r.ok) {
      availableSeasons.value = await r.json();
      selectedSeason.value = availableSeasons.value[0] ?? snapshot.season;
      await loadSeason();
    }
  } catch {
    dataStatus.value = "使用內建快照";
  }
  nextTick(drawCharts);
});
onBeforeUnmount(() => {
  playerChart?.dispose();
  profileChart?.dispose();
  window.removeEventListener("keydown", keyboard);
  window.removeEventListener("popstate", applyLocation);
});
</script>

<template>
  <div class="analysis-shell">
    <header class="topbar">
      <div>
        <a class="brand" href="#">Baseball Analysis</a>
        <div class="season-control">
          <small>{{ dataStatus }}</small
          ><select
            v-model.number="selectedSeason"
            class="form-select form-select-sm"
            @change="loadSeason"
          >
            <option v-for="year in availableSeasons" :key="year" :value="year">
              {{ year }} 球季
            </option>
          </select>
        </div>
      </div>
    </header>
    <div class="workbench">
      <aside class="side-rail shadow-sm">
        <nav>
          <button
            v-for="[id] in views"
            :key="id"
            :class="{ active: active === id }"
            @click="active = id"
          >
            <span class="nav-icon" aria-hidden="true">{{ navIcons[id] }}</span><span>{{ navLabels[id] }}</span>
          </button>
        </nav>
        <div class="rail-note">
          <small>資料模式</small><strong>本機 SQLite</strong
          ><span>年度彙總資料</span>
        </div>
      </aside>
      <main class="desk-main">
        <section v-if="active === 'home'" class="page">
          <div class="home-title">
            <h1>最新球季排行榜</h1>
          </div>
          <section class="home-briefing shadow-sm" aria-label="數據焦點">
            <div class="briefing-standings">
              <div class="briefing-standings-header"><span>球隊戰績</span><b>{{ dataset.season }}</b></div>
              <ol>
                <li v-for="(club, index) in [...dataset.standings].sort((a, b) => Number(b.win_pct) - Number(a.win_pct))" :key="club.source_team_id">
                  <em>{{ index + 1 }}</em><span class="team-avatar">{{ initials(club.nickname || club.team) }}</span><strong>{{ club.team }}</strong><small>{{ club.W }} 勝 {{ club.L }} 敗</small><b>{{ fmt(club.win_pct, 'win_pct') }}</b>
                </li>
              </ol>
            </div>
            <div class="briefing-copy">
              <p>{{ currentNews?.label }}</p>
              <h2><span>{{ currentNews?.highlight }}</span>{{ currentNews?.title }}</h2>
              <span>{{ currentNews?.detail }}</span>
              <button class="briefing-link" @click="openNews">查看完整數據 <span aria-hidden="true">→</span></button>
            </div>
            <div class="briefing-tabs" role="tablist" aria-label="切換數據焦點">
              <button v-for="(item, index) in homeNews" :key="item.label" :class="{ active: activeNews === index }" :aria-label="`顯示${item.label}`" :aria-selected="activeNews === index" role="tab" @click="selectNews(index)"></button>
            </div>
          </section>
          <h2 class="ranking-heading">打擊排行榜</h2>
          <div class="ranking-grid">
            <section
              v-for="board in battingBoards"
              :key="board.key"
              class="panel ranking-card shadow-sm"
            >
              <div class="panel-header">
                <h2>{{ board.label }}</h2>
                <span>{{ board.sample }}</span>
              </div>
              <ol>
                <li
                  v-for="p in topBatters(board.key)"
                  :key="p.source_player_id"
                >
                  <button
                    @click="openProfile('batters', String(p.source_player_id), true, board.key)"
                  >
                    <span class="ranking-player"><i class="player-avatar">{{ initials(p.name) }}</i><span><strong>{{ p.name }}</strong><small>{{ p.team }}</small></span></span><b>{{ fmt(p[board.key], board.key) }}</b>
                  </button>
                </li>
              </ol>
              <button class="ranking-more btn btn-outline-success btn-sm" @click="openRanking('batters', board.key)">查看完整排行榜</button>
            </section>
          </div>
          <h2 class="ranking-heading">投球排行榜</h2>
          <div class="ranking-grid">
            <section
              v-for="board in pitchingBoards"
              :key="board.key"
              class="panel ranking-card shadow-sm"
            >
              <div class="panel-header">
                <h2>{{ board.label }}</h2>
                <span>{{ board.sample }}</span>
              </div>
              <ol>
                <li
                  v-for="p in topPitchers(board.key, Boolean(board.ascending))"
                  :key="p.source_player_id"
                >
                  <button
                    @click="openProfile('pitchers', String(p.source_player_id), true, board.key)"
                  >
                    <span class="ranking-player"><i class="player-avatar">{{ initials(p.name) }}</i><span><strong>{{ p.name }}</strong><small>{{ p.team }}</small></span></span><b>{{ fmt(p[board.key], board.key) }}</b>
                  </button>
                </li>
              </ol>
              <button class="ranking-more btn btn-outline-success btn-sm" @click="openRanking('pitchers', board.key, Boolean(board.ascending))">查看完整排行榜</button>
            </section>
          </div>
        </section>
        <section v-else-if="active === 'players'" class="page">
          <div class="section-title">
            <div>
              <p class="eyebrow">PLAYER DATABASE</p>
              <h1>球員資料庫</h1>
            </div>
            <p>先固定球隊、類型與樣本量。排行與圖表會一起更新。</p>
          </div>
          <div class="filter-bar">
            <div class="btn-group">
              <button
                class="btn"
                :class="role === 'batters' ? 'btn-dark' : 'btn-outline-dark'"
                @click="switchRole('batters')"
              >
                打者</button
              ><button
                class="btn"
                :class="role === 'pitchers' ? 'btn-dark' : 'btn-outline-dark'"
                @click="switchRole('pitchers')"
              >
                投手
              </button>
            </div>
            <select v-model="team" class="form-select">
              <option v-for="x in teams" :key="x">{{ x }}</option></select
            ><input
              v-model.number="minimum"
              class="form-control"
              type="number"
              min="0"
            /><select v-model="metric" class="form-select">
              <option v-for="(label, key) in metrics" :key="key" :value="key">
                {{ label }}
              </option>
            </select>
          </div>
          <div class="panel chart-panel">
            <div class="panel-header">
              <h2>{{ metrics[metric] }} 前十名</h2>
              <span>{{ qualified.length }} 位符合樣本量</span>
            </div>
            <div ref="playerChartEl" class="chart" />
          </div>
          <div class="panel table-panel table-responsive">
            <table class="table table-hover">
              <thead>
                <tr>
                  <th>球員</th>
                  <th>球隊</th>
                  <th>{{ role === "batters" ? "PA" : "IP" }}</th>
                  <th v-for="(label, key) in metrics" :key="key">
                    {{ label }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="p in sorted"
                  :key="`${p.source_player_id}-${p.source_team_id}`"
                >
                  <td>
                    <strong>{{ p.name }}</strong>
                  </td>
                  <td>{{ p.team }}</td>
                  <td>
                    {{
                      role === "batters"
                        ? (p as Batter).PA
                        : fmt((p as Pitcher).IP, "IP")
                    }}
                  </td>
                  <td v-for="(_, key) in metrics" :key="key">
                    {{ fmt(p[key as keyof typeof p], String(key)) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
        <section v-else-if="active === 'profile'" class="page profile-page">
          <div class="section-title">
            <div>
              <p class="eyebrow">PLAYER SEASON</p>
              <h1>{{ profileHistory[0]?.name ?? "球員" }} · {{ selectedSeason }} 球季數據</h1>
            </div>
            <button class="btn btn-outline-dark" @click="active = 'home'">
              返回排行榜
            </button>
          </div>
          <div class="panel chart-panel">
            <div class="panel-header">
              <h2>{{ profileKind === "batters" ? "OPS" : "ERA" }} 年度走勢</h2>
              <span>{{ profileHistory.length }} 個球季</span>
            </div>
            <div ref="profileChartEl" class="chart" />
          </div>
          <div
            v-if="profileKind === 'batters'"
            class="panel table-responsive history-table"
          >
            <table class="table" :class="`highlight-${profileMetric}`">
              <thead>
                <tr>
                  <th>球季</th>
                  <th>球隊</th>
                  <th>PA</th>
                  <th>AB</th>
                  <th>H</th>
                  <th>HR</th>
                  <th>RBI</th>
                  <th>BB</th>
                  <th>SO</th>
                  <th>AVG</th>
                  <th>OBP</th>
                  <th>SLG</th>
                  <th>OPS</th>
                  <th>K%</th>
                  <th>BB%</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="x in profileSeasonRows"
                  :key="`${x.season}-${x.team_id}`"
                >
                  <td>{{ x.season }}</td>
                  <td>{{ x.team }}</td>
                  <td>{{ x.pa }}</td>
                  <td>{{ x.ab }}</td>
                  <td>{{ x.h }}</td>
                  <td>{{ x.hr }}</td>
                  <td>{{ x.rbi }}</td>
                  <td>{{ x.bb }}</td>
                  <td>{{ x.so }}</td>
                  <td>{{ fmt(x.avg, "AVG") }}</td>
                  <td>{{ fmt(x.obp, "OBP") }}</td>
                  <td>{{ fmt(x.slg, "SLG") }}</td>
                  <td class="metric-good">{{ fmt(x.ops, "OPS") }}</td>
                  <td>{{ fmt(x.k_pct, "K_pct") }}</td>
                  <td>{{ fmt(x.bb_pct, "BB_pct") }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="panel table-responsive history-table">
            <table class="table" :class="`highlight-${profileMetric}`">
              <thead>
                <tr>
                  <th>球季</th>
                  <th>球隊</th>
                  <th>IP</th>
                  <th>W</th>
                  <th>L</th>
                  <th>SV</th>
                  <th>HLD</th>
                  <th>SO</th>
                  <th>BB</th>
                  <th>HR</th>
                  <th>ERA</th>
                  <th>WHIP</th>
                  <th>K/9</th>
                  <th>BB/9</th>
                  <th>HR/9</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="x in profileSeasonRows"
                  :key="`${x.season}-${x.team_id}`"
                >
                  <td>{{ x.season }}</td>
                  <td>{{ x.team }}</td>
                  <td>{{ fmt(Number(x.ip_outs) / 3, "IP") }}</td>
                  <td>{{ x.w }}</td>
                  <td>{{ x.l }}</td>
                  <td>{{ x.sv }}</td>
                  <td>{{ x.hld }}</td>
                  <td>{{ x.so }}</td>
                  <td>{{ x.bb }}</td>
                  <td>{{ x.hr }}</td>
                  <td class="metric-good">{{ fmt(x.era, "ERA") }}</td>
                  <td>{{ fmt(x.whip, "WHIP") }}</td>
                  <td>{{ fmt(x.k_9, "K_9") }}</td>
                  <td>{{ fmt(x.bb_9, "BB_9") }}</td>
                  <td>{{ fmt(x.hr_9, "HR_9") }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
        <section v-else-if="active === 'rankings'" class="page full-ranking-page">
          <div class="section-title">
            <div><p class="eyebrow">FULL LEADERBOARD</p><h1>{{ fullRankingLabel }} 完整排行榜</h1></div>
            <button class="btn btn-outline-dark" @click="navigate('home')">返回首頁</button>
          </div>
          <section class="panel full-ranking-panel">
            <div class="panel-header"><h2>{{ rankingKind === 'batters' ? '打擊' : '投球' }} · {{ fullRankingLabel }}</h2><span>{{ fullRankingRows.length }} 位合資格球員</span></div>
            <div v-if="rankingKind === 'batters'" class="table-responsive"><table class="table full-ranking-table" :class="`highlight-${rankingMetric}`"><thead><tr><th>#</th><th>球員</th><th>球隊</th><th>PA</th><th>AB</th><th>H</th><th>HR</th><th>RBI</th><th>BB</th><th>SO</th><th>AVG</th><th>OBP</th><th>SLG</th><th>OPS</th><th>K%</th><th>BB%</th></tr></thead><tbody><tr v-for="(player, index) in battingRankingRows" :key="player.source_player_id"><td>{{ index + 1 }}</td><td><button @click="openProfile('batters', String(player.source_player_id), true, rankingMetric)">{{ player.name }}</button></td><td>{{ player.team }}</td><td>{{ player.PA }}</td><td>{{ player.AB }}</td><td>{{ player.H }}</td><td>{{ player.HR }}</td><td>{{ player.RBI }}</td><td>{{ player.BB }}</td><td>{{ player.SO }}</td><td>{{ fmt(player.AVG, 'AVG') }}</td><td>{{ fmt(player.OBP, 'OBP') }}</td><td>{{ fmt(player.SLG, 'SLG') }}</td><td>{{ fmt(player.OPS, 'OPS') }}</td><td>{{ fmt(player.K_pct, 'K_pct') }}</td><td>{{ fmt(player.BB_pct, 'BB_pct') }}</td></tr></tbody></table></div>
            <div v-else class="table-responsive"><table class="table full-ranking-table" :class="`highlight-${rankingMetric}`"><thead><tr><th>#</th><th>球員</th><th>球隊</th><th>IP</th><th>W</th><th>L</th><th>SV</th><th>HLD</th><th>SO</th><th>BB</th><th>HR</th><th>ERA</th><th>WHIP</th><th>K/9</th><th>BB/9</th><th>HR/9</th></tr></thead><tbody><tr v-for="(player, index) in pitchingRankingRows" :key="player.source_player_id"><td>{{ index + 1 }}</td><td><button @click="openProfile('pitchers', String(player.source_player_id), true, rankingMetric)">{{ player.name }}</button></td><td>{{ player.team }}</td><td>{{ fmt(player.IP, 'IP') }}</td><td>{{ player.W }}</td><td>{{ player.L }}</td><td>{{ player.SV }}</td><td>{{ player.HLD }}</td><td>{{ player.SO }}</td><td>{{ player.BB }}</td><td>{{ player.HR }}</td><td>{{ fmt(player.ERA, 'ERA') }}</td><td>{{ fmt(player.WHIP, 'WHIP') }}</td><td>{{ fmt(player.K_9, 'K_9') }}</td><td>{{ fmt(player.BB_9, 'BB_9') }}</td><td>{{ fmt(player.HR_9, 'HR_9') }}</td></tr></tbody></table></div>
          </section>
        </section>
        <section v-else-if="active === 'teams'" class="page">
          <div class="section-title">
            <div>
              <p class="eyebrow">TEAM ROSTER</p>
              <h1>球隊名單</h1>
            </div>
            <p>
              選擇年度與球隊後，以角色卡片瀏覽登錄選手；點擊卡片開啟完整歷年成績。
            </p>
          </div>
          <div class="team-grid">
            <button
              v-for="x in dataset.standings"
              :key="x.source_team_id"
              class="team-card team-select"
              :class="{
                selected: x.source_team_id === selectedClub?.source_team_id,
              }"
              @click="openTeam(String(x.source_team_id))"
            >
              <div>
                <span class="team-avatar team-avatar-large">{{ initials(x.nickname || x.team) }}</span>
                <span>{{ x.nickname || "CPBL" }}</span>
                <h2>{{ x.team }}</h2>
              </div>
              <strong>{{ fmt(x.win_pct, "win_pct") }}</strong>
              <p>{{ x.W }} 勝 · {{ x.L }} 敗 · {{ x.T }} 和</p>
            </button>
          </div>
          <div class="roster-title">
            <div>
              <p class="eyebrow">
                {{ selectedClub?.nickname || "CPBL" }} ·
                {{ dataset.season }} 年度
              </p>
              <h2>{{ selectedClub?.team }} 球員名單</h2>
            </div>
            <span
              >{{ clubBatters.length }} 位打者 ·
              {{ clubPitchers.length }} 位投手</span
            >
          </div>
          <div class="roster-tabs" role="tablist">
            <button
              :class="{ active: rosterRole === 'batters' }"
              @click="rosterRole = 'batters'"
            >
              打者</button
            ><button
              :class="{ active: rosterRole === 'pitchers' }"
              @click="rosterRole = 'pitchers'"
            >
              投手
            </button>
          </div>
          <div class="player-card-grid">
            <button
              v-for="p in rosterRows"
              :key="p.source_player_id"
              class="player-card"
              @click="openProfile(rosterRole, String(p.source_player_id))"
            >
              <span class="player-avatar player-avatar-large">{{ initials(p.name) }}</span><span class="role-label">{{
                rosterRole === "batters" ? "打者" : "投手"
              }}</span
              ><strong>{{ p.name }}</strong
              ><small>{{ p.team }}</small>
              <div v-if="rosterRole === 'batters'" class="card-stat">
                <b>{{ fmt((p as Batter).OPS, "OPS") }}</b
                ><span>OPS · {{ (p as Batter).PA }} PA</span>
              </div>
              <div v-else class="card-stat">
                <b>{{ fmt((p as Pitcher).ERA, "ERA") }}</b
                ><span>ERA · {{ fmt((p as Pitcher).IP, "IP") }} IP</span>
              </div>
            </button>
          </div>
        </section>
        <section v-else class="page umpire-page">
          <div class="section-title">
            <div><h1>鍵盤裁判</h1></div>
            <p>
              先看投球飛過本壘，再判好球判壞球；作答後按
              <kbd>Enter</kbd> 下一球。
            </p>
          </div>
          <div class="umpire-layout">
            <div class="scene-panel">
              <UmpireScene
                :pitch="selectedPitch"
                :revealed="Boolean(judgement)"
                :strike="strike"
                @ready="pitchReady = $event"
              />
              <div class="scene-meta">
                <span
                  >{{ selectedPitch.label }} ·
                  {{ selectedPitch.speed }} km/h</span
                ><span>判定平面：本壘前緣</span>
              </div>
              <div class="umpire-actions">
                <button
                  class="btn btn-outline-light"
                  :disabled="!!judgement || !pitchReady"
                  @click="answer('S')"
                >
                  S · 好球</button
                ><button
                  class="btn btn-outline-light"
                  :disabled="!!judgement || !pitchReady"
                  @click="answer('B')"
                >
                  B · 壞球</button
                ><button
                  v-if="judgement"
                  class="btn btn-success"
                  @click="nextPitch"
                >
                  Enter · 下一球
                </button>
              </div>
              <p
                class="result-line"
                :class="
                  judgement
                    ? (judgement === 'S') === strike
                      ? 'right'
                      : 'wrong'
                    : 'neutral'
                "
              >
                {{
                  judgement
                    ? ((judgement === "S") === strike
                        ? "判定正確。"
                        : "判定錯誤。") + `這球是${strike ? "好球" : "壞球"}。`
                    : pitchReady
                      ? "球已進壘，請依正面落點判決。"
                      : "投球飛行中…"
                }}
              </p>
            </div>
            <aside class="score-panel">
              <p class="eyebrow">YOUR CALLS</p>
              <h2>本輪判決</h2>
              <dl>
                <div>
                  <dt>題數</dt>
                  <dd>{{ score.total }}</dd>
                </div>
                <div>
                  <dt>正確率</dt>
                  <dd>
                    {{
                      score.total
                        ? Math.round((score.correct / score.total) * 100)
                        : 0
                    }}%
                  </dd>
                </div>
                <div>
                  <dt>好球判壞</dt>
                  <dd>{{ score.strikeMiss }}</dd>
                </div>
                <div>
                  <dt>壞球判好</dt>
                  <dd>{{ score.ballMiss }}</dd>
                </div>
                <div>
                  <dt>連續答對</dt>
                  <dd>{{ score.streak }}</dd>
                </div>
              </dl>
              <div class="rule-box">
                <strong>幾何判定</strong>
                <p>3D 球體與回放圖使用同一落點；球體碰到好球帶就判好球。</p>
              </div>
              <section class="pitch-accuracy">
                <div class="pitch-accuracy-heading">
                  <strong>各球種判決率</strong><small>僅統計已作答球次</small>
                </div>
                <div
                  v-for="item in pitchTypeAccuracy"
                  :key="item.label"
                  class="pitch-accuracy-row"
                >
                  <span>{{ item.label }}</span
                  ><span>{{ item.total }} 球</span
                  ><strong>{{
                    item.accuracy === null ? "—" : `${item.accuracy}%`
                  }}</strong>
                </div>
              </section>
              <UmpireReplay
                :pitch="selectedPitch"
                :strike="judgement ? strike : false"
                :revealed="Boolean(judgement)"
              />
            </aside>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<style>
:root{--ui-font:"PingFang TC","Microsoft JhengHei","Noto Sans TC",system-ui,sans-serif;font-family:var(--ui-font)}
body,button,input,select,textarea{font-family:var(--ui-font);font-size:16px;line-height:1.6}.desk-main{font-size:16px}.side-rail button{font-size:15px}.season-control small,.rail-note small,.rail-note span,.eyebrow,.panel-header span{font-size:12px}.table{font-size:15px}.table th{font-size:12px}.ranking-card li small,.team-card span,.team-card p,.player-card>small,.card-stat span{font-size:13px}.filter-bar .form-control,.filter-bar .form-select,.season-control select{font-size:15px}
.team-card .team-avatar{display:grid;color:var(--avatar-ink)}
.ranking-card li .player-avatar{margin-right:0}
.briefing-standings{display:none}.home-briefing{display:block;min-height:0;margin-bottom:34px}.home-briefing .briefing-copy{min-height:238px;padding:clamp(28px,4vw,48px);background:var(--system-paper);border-left:5px solid var(--green)}.home-briefing .briefing-copy h2{max-width:760px}.briefing-tabs{right:32px;bottom:28px}
.topbar{height:84px;box-shadow:0 4px 20px color-mix(in srgb,var(--ink) 6%,transparent)}.topbar>div{max-width:none;padding:0 38px}.brand{display:grid;gap:1px;font-size:24px;font-weight:900;letter-spacing:-.035em;line-height:1;color:var(--ink)}.brand span{margin:0;font-size:11px;letter-spacing:.16em;color:var(--green)}.workbench{max-width:none;grid-template-columns:232px minmax(0,1fr);min-height:calc(100vh - 84px)}.side-rail{padding:26px 14px;border-right:1px solid var(--line);box-shadow:10px 0 28px color-mix(in srgb,var(--ink) 3%,transparent);z-index:1}.side-rail nav{gap:8px}.side-rail button{display:grid;grid-template-columns:30px minmax(0,1fr);align-items:center;gap:8px;padding:13px 14px;border-radius:10px;font-size:16px;font-weight:700;color:var(--ink)}.side-rail button .nav-icon{display:grid;place-items:center;width:26px;height:26px;border-radius:7px;background:var(--avatar-surface);color:var(--avatar-ink);font-size:14px}.side-rail button.active,.side-rail button:hover{background:var(--avatar-surface)!important;color:var(--ink)!important}.side-rail button.active .nav-icon,.side-rail button:hover .nav-icon{background:var(--green);color:var(--system-paper)}.rail-note{padding:20px 10px 0}.rail-note small,.rail-note span{font-size:12px}.rail-note strong{font-size:14px}.desk-main{padding:48px clamp(28px,5vw,88px) 88px;background:var(--system-paper)}.page{max-width:1280px}.standings-home{margin-top:42px;padding:30px}.standings-home .table{font-size:16px}.standings-home td:nth-child(2){display:flex;align-items:center;gap:10px}.standings-home .team-avatar{width:34px;height:34px;font-size:12px}.standings-home .panel-header{margin-bottom:12px}
@media(max-width:850px){.topbar{height:72px}.topbar>div{padding:0 20px}.brand{font-size:21px}.workbench{grid-template-columns:1fr;min-height:calc(100vh - 72px)}.side-rail{padding:10px 14px;box-shadow:none}.side-rail nav{gap:6px}.side-rail button{grid-template-columns:26px auto;padding:10px 12px;font-size:14px}.side-rail button .nav-icon{width:22px;height:22px;font-size:12px}.desk-main{padding:30px 20px 60px}.home-briefing .briefing-copy{padding:28px 24px 56px}.briefing-tabs{left:24px;right:auto;bottom:22px}}
.home-briefing{background:var(--dark);box-shadow:0 24px 52px color-mix(in srgb,var(--dark) 26%,transparent)}.home-briefing .briefing-copy{background:linear-gradient(120deg,var(--dark),color-mix(in srgb,var(--dark) 82%,var(--green)));border-left:5px solid var(--green);color:var(--system-paper)}.home-briefing .briefing-copy>p{color:color-mix(in srgb,var(--system-paper) 66%,var(--green));font-size:13px}.home-briefing .briefing-copy h2{color:var(--system-paper);font-size:clamp(32px,4vw,54px);max-width:820px}.home-briefing .briefing-copy>span{color:color-mix(in srgb,var(--system-paper) 68%,transparent);font-size:17px}.home-briefing .briefing-link{color:var(--system-paper);padding-bottom:4px;border-bottom:1px solid color-mix(in srgb,var(--system-paper) 38%,transparent)}.home-briefing .briefing-link:hover,.home-briefing .briefing-link:focus-visible{color:var(--system-paper);border-bottom-color:var(--system-paper);text-decoration:none}.home-briefing .briefing-tabs button{background:color-mix(in srgb,var(--system-paper) 30%,transparent)}.home-briefing .briefing-tabs button.active{background:var(--system-paper)}
.home-briefing .briefing-copy h2 span{display:block;color:color-mix(in srgb,var(--green) 62%,var(--system-paper));font-size:.72em;letter-spacing:-.04em}.ranking-more{width:100%;margin-top:10px;padding:10px 0;border:0;border-top:1px solid var(--line);background:transparent;color:var(--green);font-weight:800;font-size:14px}.ranking-more:hover,.ranking-more:focus-visible{color:var(--ink);text-decoration:underline}.ranking-more:focus-visible{outline:2px solid var(--green);outline-offset:3px}
.ranking-card .panel-header h2,.standings-home .panel-header h2{display:inline-flex;align-items:center;min-height:34px;padding:5px 11px;border-radius:7px;background:var(--green);color:var(--system-paper);font-size:18px;letter-spacing:.01em}.ranking-grid .ranking-card:nth-child(2) .panel-header h2{background:var(--blue)}.ranking-grid .ranking-card:nth-child(3) .panel-header h2{background:var(--dark)}.ranking-grid .ranking-card:nth-child(4) .panel-header h2{background:color-mix(in srgb,var(--green) 72%,var(--blue))}.standings-home .panel-header h2{background:var(--dark);font-size:20px}.ranking-card .panel-header{align-items:center}
.ranking-card .panel-header,.standings-home .panel-header{align-items:center;margin:-4px -4px 14px;padding:10px 12px;border:0;border-radius:9px;background:var(--avatar-surface);box-shadow:0 6px 14px color-mix(in srgb,var(--green) 10%,transparent)}.ranking-card .panel-header h2,.standings-home .panel-header h2,.ranking-grid .ranking-card:nth-child(2) .panel-header h2,.ranking-grid .ranking-card:nth-child(3) .panel-header h2,.ranking-grid .ranking-card:nth-child(4) .panel-header h2{min-height:30px;padding:4px 10px;background:var(--green);font-size:16px;color:var(--system-paper)}.standings-home .panel-header h2{font-size:17px}.ranking-card .panel-header span,.standings-home .panel-header span{font-size:12px;color:var(--ink)!important}
.full-ranking-page{max-width:980px}.full-ranking-page .section-title{align-items:end}.full-ranking-panel{padding:26px}.full-ranking-panel .panel-header{padding-bottom:16px;border-bottom:1px solid var(--line)}.full-ranking-panel .panel-header h2{font-size:20px}.full-ranking-panel ol{list-style:none;margin:0;padding:0}.full-ranking-panel li{display:grid;grid-template-columns:42px 40px minmax(0,1fr) auto;align-items:center;gap:12px;padding:13px 6px;border-bottom:1px solid var(--line)}.full-ranking-panel li:last-child{border-bottom:0}.ranking-place{font-weight:800;color:var(--muted);text-align:center}.full-ranking-panel li>button{display:grid;gap:1px;min-width:0;padding:0;border:0;background:transparent;text-align:left;color:var(--ink)}.full-ranking-panel li>button strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:16px}.full-ranking-panel li>button small{color:var(--muted);font-size:13px}.full-ranking-panel li>b{font-size:18px;color:var(--green)}.full-ranking-panel li:hover{background:var(--avatar-surface)}.full-ranking-panel li>button:hover strong,.full-ranking-panel li>button:focus-visible strong{color:var(--green);text-decoration:underline}.full-ranking-panel li>button:focus-visible{outline:2px solid var(--green);outline-offset:4px}@media(max-width:560px){.full-ranking-panel{padding:18px}.full-ranking-panel li{grid-template-columns:30px 34px minmax(0,1fr) auto;gap:8px}.full-ranking-panel li>b{font-size:16px}}
.history-table{--metric-highlight:color-mix(in srgb,var(--ink) 7%,var(--system-paper))}.history-table .highlight-AVG :is(th:nth-child(10),td:nth-child(10)),.history-table .highlight-OPS :is(th:nth-child(13),td:nth-child(13)),.history-table .highlight-HR :is(th:nth-child(6),td:nth-child(6)),.history-table .highlight-RBI :is(th:nth-child(7),td:nth-child(7)),.history-table .highlight-SO :is(th:nth-child(8),td:nth-child(8)),.history-table .highlight-SV :is(th:nth-child(6),td:nth-child(6)),.history-table .highlight-ERA :is(th:nth-child(11),td:nth-child(11)),.history-table .highlight-WHIP :is(th:nth-child(12),td:nth-child(12)){background:var(--metric-highlight);font-weight:800}.history-table .highlight-AVG th,.history-table .highlight-OPS th,.history-table .highlight-HR th,.history-table .highlight-RBI th,.history-table .highlight-SO th,.history-table .highlight-SV th,.history-table .highlight-ERA th,.history-table .highlight-WHIP th{color:var(--ink)}
.full-ranking-panel,.profile-page .panel{box-shadow:none!important;border:1px solid var(--line)!important}.full-ranking-table{--metric-highlight:color-mix(in srgb,var(--ink) 7%,var(--system-paper));font-size:14px}.full-ranking-table td,.full-ranking-table th{padding:.72rem .5rem}.full-ranking-table td:nth-child(2) button{padding:0;border:0;background:transparent;color:var(--ink);font-weight:800;white-space:nowrap}.full-ranking-table td:nth-child(2) button:hover,.full-ranking-table td:nth-child(2) button:focus-visible{color:var(--green);text-decoration:underline}.full-ranking-table td:nth-child(2) button:focus-visible{outline:2px solid var(--green);outline-offset:3px}.full-ranking-table.highlight-AVG :is(th:nth-child(11),td:nth-child(11)),.full-ranking-table.highlight-OPS :is(th:nth-child(14),td:nth-child(14)),.full-ranking-table.highlight-HR :is(th:nth-child(7),td:nth-child(7)),.full-ranking-table.highlight-RBI :is(th:nth-child(8),td:nth-child(8)),.full-ranking-table.highlight-SO :is(th:nth-child(9),td:nth-child(9)),.full-ranking-table.highlight-SV :is(th:nth-child(7),td:nth-child(7)),.full-ranking-table.highlight-ERA :is(th:nth-child(12),td:nth-child(12)),.full-ranking-table.highlight-WHIP :is(th:nth-child(13),td:nth-child(13)){background:var(--metric-highlight);font-weight:800}
:root{--bs-primary:var(--green);--bs-success:var(--green);--bs-body-bg:color-mix(in srgb,var(--blue) 4%,var(--system-paper));--bs-body-color:var(--ink);--bs-border-color:var(--line);--bs-table-striped-bg:color-mix(in srgb,var(--blue) 5%,var(--system-paper));--bs-table-hover-bg:color-mix(in srgb,var(--green) 9%,var(--system-paper))}.desk-main{background:var(--bs-body-bg)}.home-title{padding:clamp(22px,3vw,36px);border:1px solid color-mix(in srgb,var(--blue) 18%,var(--line));border-left:5px solid var(--blue);border-radius:14px;background:color-mix(in srgb,var(--blue) 6%,var(--system-paper));box-shadow:0 10px 24px color-mix(in srgb,var(--blue) 8%,transparent)}.home-title .home-eyebrow{width:max-content;padding:6px 10px;font-size:11px;letter-spacing:.11em}.ranking-card{border-top:3px solid var(--bs-success)!important}.ranking-card.shadow-sm{box-shadow:0 10px 24px color-mix(in srgb,var(--green) 8%,transparent)!important}.standings-home{border-top:3px solid var(--blue)!important}.table-striped>tbody>tr:nth-of-type(odd)>*{--bs-table-accent-bg:var(--bs-table-striped-bg)}.table-hover>tbody>tr:hover>*{--bs-table-accent-bg:var(--bs-table-hover-bg)}.ranking-more.btn{margin-top:12px;border-width:1px;font-weight:800}.ranking-more.btn:hover{background:var(--bs-success);color:var(--system-paper);text-decoration:none}
/* Adobe palette: #00010D · #435946 · #D9981E · #BFBFBF · #F2AD85 */
:root{--palette-ink:#00010D;--palette-green:#435946;--palette-amber:#D9981E;--palette-gray:#BFBFBF;--palette-peach:#F2AD85;--ink:var(--palette-ink);--green:var(--palette-green);--blue:var(--palette-amber);--line:color-mix(in srgb,var(--palette-gray) 58%,var(--system-paper));--muted:color-mix(in srgb,var(--palette-ink) 56%,var(--system-paper));--bs-primary:var(--palette-green);--bs-success:var(--palette-green);--bs-warning:var(--palette-amber);--bs-body-bg:var(--system-paper);--bs-body-color:var(--palette-ink);--bs-border-color:var(--line);--bs-table-striped-bg:color-mix(in srgb,var(--palette-gray) 15%,var(--system-paper));--bs-table-hover-bg:color-mix(in srgb,var(--palette-peach) 25%,var(--system-paper));--avatar-surface:color-mix(in srgb,var(--palette-peach) 38%,var(--system-paper));--avatar-ink:var(--palette-green)}.desk-main{background:var(--system-paper)}.topbar{border-bottom-color:var(--line);box-shadow:none}.side-rail{box-shadow:none}.brand{color:var(--palette-ink)}.brand span{color:var(--palette-green)}.side-rail button .nav-icon{background:var(--avatar-surface);color:var(--palette-green)}.side-rail button.active,.side-rail button:hover{background:color-mix(in srgb,var(--palette-peach) 25%,var(--system-paper))!important}.side-rail button.active .nav-icon,.side-rail button:hover .nav-icon{background:var(--palette-green);color:var(--system-paper)}.home-title{background:var(--system-paper);border-color:var(--line);border-left-color:var(--palette-amber);box-shadow:none}.home-title .home-eyebrow{background:var(--palette-green)!important;color:var(--system-paper)}.home-briefing{background:var(--palette-ink);box-shadow:none}.home-briefing .briefing-copy{background:linear-gradient(120deg,var(--palette-ink),var(--palette-green));border-left-color:var(--palette-amber)}.home-briefing .briefing-copy h2 span{color:var(--palette-peach)}.home-briefing .briefing-copy>p{color:var(--palette-amber)}.home-briefing .briefing-tabs button.active{background:var(--palette-amber)}.ranking-card,.standings-home{border-top-color:var(--palette-amber)!important}.ranking-card.shadow-sm{box-shadow:none!important}.ranking-card .panel-header,.standings-home .panel-header{background:color-mix(in srgb,var(--palette-peach) 20%,var(--system-paper));box-shadow:none}.ranking-card .panel-header h2,.standings-home .panel-header h2{background:var(--palette-green)}.ranking-more.btn{border-color:var(--palette-green);color:var(--palette-green)}.ranking-more.btn:hover,.ranking-more.btn:focus-visible{background:var(--palette-green);border-color:var(--palette-green);color:var(--system-paper)}.table-striped>tbody>tr:nth-of-type(odd)>*{--bs-table-accent-bg:var(--bs-table-striped-bg)}.table-hover>tbody>tr:hover>*{--bs-table-accent-bg:var(--bs-table-hover-bg)}
/* Rankings: replace the peach header fill with a neutral, full-width header bar. */
.ranking-card .panel-header,
.standings-home .panel-header {
  background: #BFBFBF;
  box-shadow: 0 5px 14px rgb(0 1 13 / 12%);
}
.ranking-card .panel-header h2,
.standings-home .panel-header h2 {
  background: #435946;
  color: #00010D;
}
.ranking-card .panel-header span,
.standings-home .panel-header span { color: #00010D !important; }

/* Primary standings live at the top of the dashboard. */
.side-rail.shadow-sm { box-shadow: var(--bs-box-shadow-sm) !important; }
.side-rail button { font-size: 18px; }
.home-briefing.shadow-sm { box-shadow: var(--bs-box-shadow-sm) !important; }
.home-briefing {
  display: grid;
  grid-template-columns: minmax(330px, 0.9fr) minmax(0, 1.1fr);
  background: #fff;
}
.briefing-standings {
  display: block;
  margin: 16px;
  padding: 20px 24px;
  background: #fff;
  color: #00010D;
  border: 1px solid #BFBFBF;
  border-radius: 8px;
}
.briefing-standings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 2px solid #435946;
  color: #00010D;
}
.briefing-standings-header span { font-size: 19px; font-weight: 800; }
.briefing-standings-header b { color: #00010D; }
.briefing-standings ol { margin: 10px 0 0; padding: 0; list-style: none; }
.briefing-standings li {
  display: grid;
  grid-template-columns: 20px 32px minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 8px;
  padding: 9px 0;
  border-bottom: 1px solid #BFBFBF;
  color: #00010D;
}
.briefing-standings li:last-child { border-bottom: 0; }
.briefing-standings em, .briefing-standings small { color: #00010D; font-style: normal; }
.briefing-standings strong, .briefing-standings b { color: #00010D; }
.briefing-standings .team-avatar { background: #F2AD85; color: #00010D; }

/* Every ranking category uses the same title treatment. */
.ranking-card .panel-header h2,
.standings-home .panel-header h2,
.ranking-grid .ranking-card:nth-child(2) .panel-header h2,
.ranking-grid .ranking-card:nth-child(3) .panel-header h2,
.ranking-grid .ranking-card:nth-child(4) .panel-header h2 {
  min-height: 32px;
  padding: 5px 11px;
  background: #00010D !important;
  color: #fff !important;
  border-radius: 6px;
  font-size: 16px;
  line-height: 1.35;
}

@media (max-width: 850px) {
  .side-rail button { font-size: 16px; }
  .home-briefing { grid-template-columns: 1fr; }
  .briefing-standings { border: 1px solid #BFBFBF; }
}
</style>
