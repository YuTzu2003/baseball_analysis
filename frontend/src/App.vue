<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import snapshot from "./data/cpbl-2024.json";
import MetricSpark from "./components/MetricSpark.vue";
import UmpireScene from "./components/UmpireScene.vue";
import UmpireReplay from "./components/UmpireReplay.vue";
import PlayerIcon from "./components/PlayerIcon.vue";
import TeamIcon from "./components/TeamIcon.vue";
import { teamColor, teamTextColor } from "./teamPresentation";
import { isStrike } from "./umpireGeometry";

type Batter = (typeof snapshot.batters)[number];
type Pitcher = (typeof snapshot.pitchers)[number];
type View = "home" | "players" | "profile" | "compare" | "teams" | "umpire";
type TeamSummary = {
  team_id: string;
  team: string;
  nickname: string | null;
  batting: Record<string, number | null>;
  pitching: Record<string, number | null>;
};
type StaticSeasonData = {
  batters: Record<string, unknown>[];
  pitchers: Record<string, unknown>[];
  standings: Record<string, unknown>[];
  team_summaries: TeamSummary[];
};
type Audience = "scout" | "coach" | "analyst" | "player";
type Pitch = { x: number; y: number; speed: number; label: string };
const views: Array<[View, string]> = [
  ["umpire", "鍵盤裁判"],
  ["home", "數據排行榜"],
  ["players", "球員資料庫"],
  ["compare", "選手比較"],
  ["teams", "球隊"],
];
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
  W: "勝投",
  L: "敗投",
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
const staticDataMode = import.meta.env.VITE_STATIC_DATA === "true";
let staticSeasonData: StaticSeasonData | null = null;
const first = ref(""),
  second = ref(""),
  history = ref<Record<string, unknown>[]>([]);
const profileKind = ref<"batters" | "pitchers">("batters"),
  profileId = ref(""),
  profileHistory = ref<Record<string, unknown>[]>([]),
  profileLeague = ref<Record<string, unknown>[]>([]);
const profileMetric = ref("OPS");
const showLeagueAverage = ref(true);
const selectedTeam = ref("");
const rosterRole = ref<"batters" | "pitchers">("batters");
const teamSummaries = ref<TeamSummary[]>([]);
const teamMetricGroup = ref<"batting" | "pitching">("batting");
const teamMetric = ref("OPS");
const teamComparisonMetrics = {
  batting: [
    { key: "AVG", label: "打擊率 AVG" },
    { key: "OBP", label: "上壘率 OBP" },
    { key: "SLG", label: "長打率 SLG" },
    { key: "OPS", label: "整體攻擊指數 OPS" },
    { key: "HR", label: "全壘打 HR" },
    { key: "RBI", label: "打點 RBI" },
  ],
  pitching: [
    { key: "ERA", label: "防禦率 ERA", lowerBetter: true },
    { key: "WHIP", label: "每局被上壘率 WHIP", lowerBetter: true },
    { key: "SO", label: "三振 SO" },
    { key: "SV", label: "救援成功 SV" },
  ],
} as const;
const routePath = (path: string) => (staticDataMode ? `#${path}` : path);
const currentRoutePath = () =>
  staticDataMode ? window.location.hash || "#/" : window.location.pathname;
const paths: Record<Exclude<View, "profile">, string> = {
  home: routePath("/"),
  players: routePath("/players"),
  compare: routePath("/"),
  teams: routePath("/teams"),
  umpire: routePath("/umpire"),
};
const navigationViews = computed(() => views.filter(([id]) => id !== "compare"));
const staticDataUrl = (path: string) => `${import.meta.env.BASE_URL}data/${path}`;
async function loadStaticData<T>(path: string): Promise<T> {
  const response = await fetch(staticDataUrl(path));
  if (!response.ok) throw Error(`Unable to load static data: ${path}`);
  return response.json() as Promise<T>;
}
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
  historyChartEl = ref<HTMLElement | null>(null),
  profileChartEl = ref<HTMLElement | null>(null),
  teamChartEl = ref<HTMLElement | null>(null);
let playerChart: import("echarts").ECharts | undefined;
let historyChart: import("echarts").ECharts | undefined;
let profileChart: import("echarts").ECharts | undefined;
let teamChart: import("echarts").ECharts | undefined;
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
      : Number((x as Pitcher).IP) >= minimum.value,
  ),
);
const sorted = computed(() =>
  [...qualified.value]
    .filter((x) => x[metric.value as keyof typeof x] != null)
    .sort(
      (a, b) =>
        metric.value === "ERA"
          ? Number(a[metric.value as keyof typeof a]) -
            Number(b[metric.value as keyof typeof b])
          : Number(b[metric.value as keyof typeof b]) -
            Number(a[metric.value as keyof typeof a]),
    ),
);
const batters = computed(() =>
  dataset.value.batters.filter((x) => Number(x.PA) >= minimum.value),
);
const firstPlayer = computed(
  () =>
    dataset.value.batters.find((x) => x.source_player_id === first.value) ??
    dataset.value.batters[0],
);
const secondPlayer = computed(
  () =>
    dataset.value.batters.find((x) => x.source_player_id === second.value) ??
    dataset.value.batters[0],
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
const compare = (x: Batter | undefined, key: string) =>
  x ? fmt(x[key as keyof Batter], key) : "—";
const rank = (x: Batter | undefined) => {
  if (!x) return "—";
  const p = batters.value.sort((a, b) => Number(b.OPS) - Number(a.OPS));
  const r = p.findIndex((y) => y.source_player_id === x.source_player_id) + 1;
  return r ? `${r} / ${p.length}` : "樣本不足";
};
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
const profileMetrics = computed(() =>
  profileKind.value === "batters" ? battingMetrics : pitchingMetrics,
);
const lowerIsBetter = computed(() =>
  ["ERA", "WHIP", "BB_9", "HR_9"].includes(profileMetric.value),
);
const profileMetricKey = computed(() => profileMetric.value.toLowerCase());
const profileSamples = computed(() =>
  profileHistory.value.map((row) => ({
    season: Number(row.season),
    qualified:
      profileKind.value === "batters"
        ? Number(row.pa) >= 100
        : Number(row.ip_outs) >= 150,
  })),
);
const hasInsufficientProfileSamples = computed(() =>
  profileSamples.value.some((row) => !row.qualified),
);
const profileComparison = computed(() => {
  const metric = profileMetricKey.value;
  const player = profileHistory.value
    .map((row) => ({ season: row.season, value: Number(row[metric]) }))
    .filter((row) => Number.isFinite(row.value));
  return player.map((row) => {
    const league = Number(
      profileLeague.value.find((avg) => avg.season === row.season)?.[metric],
    );
    if (!Number.isFinite(league))
      return { ...row, label: "無聯盟平均資料", tone: "muted" };
    if (row.value === league)
      return { ...row, label: "與聯盟平均相同", tone: "muted" };
    const below = row.value < league;
    const better = lowerIsBetter.value ? below : !below;
    const relation = below ? "低於" : "高於";
    return {
      ...row,
      label: `${relation}聯盟平均（${better ? "較佳" : "較差"}）`,
      tone: better ? "good" : "bad",
    };
  });
});
const career = computed(() => {
  const rows = profileHistory.value;
  const total = (key: string) =>
    rows.reduce((sum, row) => sum + (Number(row[key]) || 0), 0);
  if (profileKind.value === "batters") {
    const ab = total("ab");
    const pa = total("pa");
    const h = total("h");
    const bb = total("bb");
    return {
      items: [
        [
          "出賽數",
          total("g") ||
            rows.reduce((sum, row) => sum + (Number(raw(row).G) || 0), 0),
          "累計",
        ],
        ["PA", pa, "累計"],
        ["AB", ab, "累計"],
        ["H", h, "累計"],
        ["HR", total("hr"), "累計"],
        ["RBI", total("rbi"), "累計"],
        ["BB", bb, "累計"],
        ["SO", total("so"), "累計"],
        [
          "SB",
          rows.reduce((sum, row) => sum + (Number(raw(row).SB) || 0), 0),
          "累計",
        ],
        ["AVG", ab ? h / ab : null, "率"],
        ["OBP", pa ? (h + bb) / pa : null, "率"],
        [
          "SLG",
          ab
            ? rows.reduce((sum, row) => sum + (Number(raw(row).TB) || 0), 0) /
              ab
            : null,
          "率",
        ],
        [
          "OPS",
          pa
            ? (h + bb) / pa +
              rows.reduce((sum, row) => sum + (Number(raw(row).TB) || 0), 0) /
                ab
            : null,
          "率",
        ],
      ],
    };
  }
  const outs = total("ip_outs");
  const hits = rows.reduce((sum, row) => sum + (Number(raw(row).H) || 0), 0);
  return {
    items: [
      [
        "出賽數",
        total("g") ||
          rows.reduce((sum, row) => sum + (Number(raw(row).G) || 0), 0),
        "累計",
      ],
      ["IP", outs / 3, "累計"],
      ["W", total("w"), "累計"],
      ["L", total("l"), "累計"],
      ["SV", total("sv"), "累計"],
      ["SO", total("so"), "累計"],
      ["BB", total("bb"), "累計"],
      ["HR", total("hr"), "累計"],
      ["ERA", outs ? (total("er") * 27) / outs : null, "率"],
      ["WHIP", outs ? (hits + total("bb")) / (outs / 3) : null, "率"],
      ["K_9", outs ? (total("so") * 27) / outs : null, "率"],
    ],
  };
});
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
async function loadHistory() {
  if (!first.value) return;
  try {
    if (staticDataMode) {
      const payload = await loadStaticData<{ history: Record<string, unknown>[] }>(
        `players/batters/${encodeURIComponent(first.value)}.json`,
      );
      history.value = payload.history;
      return;
    }
    const r = await fetch(
      `/api/batters/player/${encodeURIComponent(first.value)}/history`,
    );
    history.value = r.ok ? await r.json() : [];
  } catch {
    history.value = [];
  }
}
async function loadTeamSummaries(season: number) {
  try {
    if (staticDataMode) {
      teamSummaries.value = staticSeasonData?.team_summaries ?? [];
      return;
    }
    const response = await fetch(`/api/teams/summary?season=${season}`);
    teamSummaries.value = response.ok ? await response.json() : [];
  } catch {
    teamSummaries.value = [];
  }
}
async function openProfile(kind: "batters" | "pitchers", id: string) {
  profileKind.value = kind;
  profileId.value = id;
  profileMetric.value = kind === "batters" ? "OPS" : "ERA";
  try {
    const payload: { history: Record<string, unknown>[]; league_averages: Record<string, unknown>[] } = staticDataMode
      ? await loadStaticData<{ history: Record<string, unknown>[]; league_averages: Record<string, unknown>[] }>(`players/${kind}/${encodeURIComponent(id)}.json`)
      : await (async () => {
          const r = await fetch(`/api/${kind}/player/${encodeURIComponent(id)}/analysis`);
          return r.ok ? r.json() : { history: [], league_averages: [] };
        })();
    profileHistory.value = payload.history ?? [];
    profileLeague.value = payload.league_averages ?? [];
  } catch {
    profileHistory.value = [];
    profileLeague.value = [];
  }
  active.value = "profile";
  await nextTick(drawCharts);
}
async function loadSeason() {
  try {
    const season = selectedSeason.value;
    if (staticDataMode) {
      const payload = await loadStaticData<StaticSeasonData>(`seasons/${season}.json`);
      staticSeasonData = payload;
      dataset.value = {
        season,
        batters: mapBatters(payload.batters),
        pitchers: mapPitchers(payload.pitchers),
        standings: payload.standings.map((x) => ({
          source_team_id: x.team_id,
          team: x.team,
          nickname: x.nickname,
          W: x.wins,
          L: x.losses,
          T: x.ties,
          win_pct: x.win_pct,
        })),
      } as typeof snapshot;
      first.value = dataset.value.batters[0]?.source_player_id ?? "";
      second.value = dataset.value.batters[1]?.source_player_id ?? "";
      dataStatus.value = "GitHub Pages 靜態資料";
      await loadHistory();
      await loadTeamSummaries(season);
      await nextTick(drawCharts);
      return;
    }
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
    first.value = dataset.value.batters[0]?.source_player_id ?? "";
    second.value = dataset.value.batters[1]?.source_player_id ?? "";
    dataStatus.value = "SQLite 本機資料庫";
    await loadHistory();
    await loadTeamSummaries(season);
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
          data: d.map((x) => ({
            value: Number(x[metric.value as keyof typeof x]),
            itemStyle: { color: teamColor(String(x.source_team_id)) },
          })),
          label: { show: true, position: "top", color: ink },
        },
      ],
    });
  }
  if (active.value === "profile" && profileChartEl.value) {
    profileChart?.dispose();
    profileChart = e.init(profileChartEl.value);
    const key = profileMetric.value.toLowerCase();
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
          name: "球員",
          type: "line",
          smooth: true,
          data: profileHistory.value.map((x) => x[key]),
          lineStyle: { color, width: 2 },
          itemStyle: { color },
        },
        {
          name: "聯盟平均",
          type: "line",
          smooth: true,
          data: profileHistory.value.map(
            (x) =>
              profileLeague.value.find((avg) => avg.season === x.season)?.[key],
          ),
          lineStyle: { color: "#9aa1a8", type: "dashed" },
          itemStyle: { color: "#9aa1a8" },
        },
      ],
    });
  }
  if (active.value === "teams" && teamChartEl.value) {
    teamChart?.dispose();
    teamChart = e.init(teamChartEl.value);
    const group = teamMetricGroup.value;
    const key = teamMetric.value;
    teamChart.setOption({
      grid: { left: 110, right: 42, top: 18, bottom: 32 },
      xAxis: { type: "value", axisLabel: { color: muted }, splitLine: { lineStyle: { color: rule } } },
      yAxis: { type: "category", data: teamSummaries.value.map((x) => x.nickname || x.team), axisLabel: { color: ink, fontWeight: 700 } },
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (value: number) => fmt(value, key) },
      series: [{
        type: "bar",
        barMaxWidth: 30,
        data: teamSummaries.value.map((x) => ({ value: x[group][key], itemStyle: { color: teamColor(x.team_id), borderRadius: [0, 4, 4, 0] } })),
        label: { show: true, position: "right", color: ink, formatter: ({ value }: { value: number }) => fmt(value, key) },
      }],
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
function switchTeamMetricGroup(group: "batting" | "pitching") {
  teamMetricGroup.value = group;
  teamMetric.value = group === "batting" ? "OPS" : "ERA";
}
function navigate(view: Exclude<View, "profile">) {
  active.value = view;
  window.history.pushState({}, "", paths[view]);
  void nextTick(drawCharts);
}
async function applyLocation() {
  const view = (Object.entries(paths).find(
    ([, path]) => path === currentRoutePath(),
  )?.[0] ?? "home") as Exclude<View, "profile">;
  active.value = view;
  await nextTick(drawCharts);
}
watch([active, metric, minimum, role, team, teamMetric, teamMetricGroup, teamSummaries], () => nextTick(drawCharts));
watch(active, (view) => {
  if (view !== "profile" && currentRoutePath() !== paths[view])
    window.history.pushState({}, "", paths[view]);
});
onMounted(() => {
  window.addEventListener("popstate", applyLocation);
  window.addEventListener("hashchange", applyLocation);
  void applyLocation();
});
onMounted(async () => {
  const saved = localStorage.getItem("cpbl-umpire-score");
  if (saved) score.value = JSON.parse(saved);
  loadPitchStats();
  window.addEventListener("keydown", keyboard);
  try {
    if (staticDataMode) {
      availableSeasons.value = await loadStaticData<number[]>("seasons.json");
      selectedSeason.value = availableSeasons.value[0] ?? snapshot.season;
      await loadSeason();
      return;
    }
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
  teamChart?.dispose();
  window.removeEventListener("keydown", keyboard);
  window.removeEventListener("popstate", applyLocation);
  window.removeEventListener("hashchange", applyLocation);
});
</script>

<template>
  <div class="analysis-shell">
    <header class="topbar">
      <div>
        <a class="brand" href="#">CPBL <span>ANALYSIS DESK</span></a>
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
      <aside class="side-rail">
        <nav>
          <button
            v-for="[id, label] in navigationViews"
            :key="id"
            :class="{ active: active === id }"
            @click="active = id"
          >
            {{ label }}
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
            <p class="eyebrow">
              CPBL OPENDATA · {{ dataset.season }} 球季 ·
              {{ availableSeasons.length }} 個年度資料
            </p>
            <h1>最新球季排行榜</h1>
            <p>點擊球員即可查看歷年數據趨勢；排名依各指標獨立計算。</p>
          </div>
          <h2 class="ranking-heading">打擊排行榜</h2>
          <div class="ranking-grid">
            <section
              v-for="board in battingBoards"
              :key="board.key"
              class="panel ranking-card"
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
                    @click="openProfile('batters', String(p.source_player_id))"
                  >
                    <TeamIcon
                      :team="String(p.team)"
                      :team-id="String(p.source_team_id)"
                      size="sm"
                    /><span
                      ><strong>{{ p.name }}</strong
                      ><small>{{ p.team }}</small></span
                    ><b>{{ fmt(p[board.key], board.key) }}</b>
                  </button>
                </li>
              </ol>
            </section>
          </div>
          <h2 class="ranking-heading">投球排行榜</h2>
          <div class="ranking-grid">
            <section
              v-for="board in pitchingBoards"
              :key="board.key"
              class="panel ranking-card"
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
                    @click="openProfile('pitchers', String(p.source_player_id))"
                  >
                    <TeamIcon
                      :team="String(p.team)"
                      :team-id="String(p.source_team_id)"
                      size="sm"
                    /><span
                      ><strong>{{ p.name }}</strong
                      ><small>{{ p.team }}</small></span
                    ><b>{{ fmt(p[board.key], board.key) }}</b>
                  </button>
                </li>
              </ol>
            </section>
          </div>
          <section class="panel standings-home">
            <div class="panel-header">
              <h2>球隊戰績</h2>
              <span>勝率</span>
            </div>
            <table class="table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>球隊</th>
                  <th>勝</th>
                  <th>敗</th>
                  <th>勝率</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(x, index) in [...dataset.standings].sort(
                    (a, b) => Number(b.win_pct) - Number(a.win_pct),
                  )"
                  :key="x.source_team_id"
                >
                  <td>{{ index + 1 }}</td>
                  <td>
                    <strong>{{ x.team }}</strong>
                  </td>
                  <td>{{ x.W }}</td>
                  <td>{{ x.L }}</td>
                  <td class="metric-good">{{ fmt(x.win_pct, "win_pct") }}</td>
                </tr>
              </tbody>
            </table>
          </section>
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
            ><label class="filter-minimum"
              ><span>{{ role === "batters" ? "最低打席數（PA）" : "最低投球局數（IP）" }}</span
              ><input
                v-model.number="minimum"
                class="form-control"
                type="number"
                min="0"
              /></label
            ><select v-model="metric" class="form-select">
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
            <p class="chart-note">顯示前 10 名；長條顏色代表所屬球隊。</p>
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
                    <button
                      class="player-link"
                      @click="openProfile(role, String(p.source_player_id))"
                    >
                      <PlayerIcon
                        :name="String(p.name)"
                        :team-id="String(p.source_team_id)"
                        :kind="role === 'batters' ? 'batter' : 'pitcher'"
                        size="sm"
                      /><strong>{{ p.name }}</strong>
                    </button>
                  </td>
                  <td>
                    <TeamIcon
                      :team="String(p.team)"
                      :team-id="String(p.source_team_id)"
                      size="sm"
                    />{{ p.team }}
                  </td>
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
        <section v-else-if="active === 'profile'" class="page">
          <div class="section-title">
            <div>
              <p class="eyebrow">PLAYER HISTORY</p>
              <h1>
                <PlayerIcon
                  :name="String(profileHistory[0]?.name ?? '')"
                  :team-id="String(profileHistory[0]?.team_id ?? '')"
                  :kind="profileKind === 'batters' ? 'batter' : 'pitcher'"
                />{{ profileHistory[0]?.name ?? "球員" }} 歷年分析
              </h1>
            </div>
            <button class="btn btn-outline-dark" @click="active = 'home'">
              返回排行榜
            </button>
          </div>
          <div class="profile-range">
            資料涵蓋 {{ profileHistory[0]?.season ?? "—" }}–{{
              profileHistory[profileHistory.length - 1]?.season ?? "—"
            }}
            球季 · 共 {{ profileHistory.length }} 年
          </div>
          <div class="career-grid">
            <article
              v-for="item in career.items"
              :key="String(item[0])"
              class="panel career-stat"
            >
              <small>{{ item[0] }} · {{ item[2] }}</small
              ><strong>{{ fmt(item[1], String(item[0])) }}</strong>
            </article>
          </div>
          <div v-if="!profileHistory.length" class="panel empty-state">
            找不到此球員的歷年資料，請更換球員或確認資料庫已匯入。
          </div>
          <div v-else class="panel chart-panel">
            <div class="panel-header">
              <div>
                <h2>歷年趨勢</h2>
                <span>虛線為該年度聯盟平均；ERA、WHIP 等指標越低越好</span>
              </div>
              <select
                v-model="profileMetric"
                class="form-select profile-metric"
                @change="drawCharts"
              >
                <option
                  v-for="(label, key) in profileMetrics"
                  :key="key"
                  :value="key"
                >
                  {{ label }}
                </option>
              </select>
            </div>
            <div ref="profileChartEl" class="chart" />
            <div class="profile-comparison">
              <span
                v-for="item in profileComparison"
                :key="String(item.season)"
                :class="`comparison-${item.tone}`"
                >{{ item.season }}：{{ item.label }}</span
              >
            </div>
          </div>
          <div
            v-if="profileKind === 'batters'"
            class="panel table-responsive history-table"
          >
            <table class="table">
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
                  v-for="x in profileHistory"
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
            <table class="table">
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
                  v-for="x in profileHistory"
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
        <section v-else-if="active === 'compare'" class="page">
          <div class="section-title">
            <div>
              <p class="eyebrow">PLAYER COMPARISON</p>
              <h1>選手比較</h1>
            </div>
            <p>上方是同球季比較；下方僅顯示左側選手的跨季趨勢。</p>
          </div>
          <div class="filter-bar compare-filter">
            <select v-model="first" class="form-select">
              <option
                v-for="p in batters"
                :key="p.source_player_id"
                :value="p.source_player_id"
              >
                {{ p.name }} · {{ p.team }}
              </option></select
            ><select v-model="second" class="form-select">
              <option
                v-for="p in batters"
                :key="p.source_player_id"
                :value="p.source_player_id"
              >
                {{ p.name }} · {{ p.team }}
              </option>
            </select>
          </div>
          <div class="compare-identity">
            <article>
              <span>左側選手</span><strong>{{ firstPlayer?.name }}</strong
              ><small>{{ firstPlayer?.team }} · {{ firstPlayer?.PA }} PA</small>
            </article>
            <b>VS</b>
            <article>
              <span>右側選手</span><strong>{{ secondPlayer?.name }}</strong
              ><small
                >{{ secondPlayer?.team }} · {{ secondPlayer?.PA }} PA</small
              >
            </article>
          </div>
          <div class="panel table-responsive">
            <table class="table compare-table">
              <thead>
                <tr>
                  <th>指標</th>
                  <th>{{ firstPlayer?.name }}</th>
                  <th>{{ secondPlayer?.name }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(_, key) in battingMetrics" :key="key">
                  <td>{{ battingMetrics[String(key)] }}</td>
                  <td>{{ compare(firstPlayer, String(key)) }}</td>
                  <td>{{ compare(secondPlayer, String(key)) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="panel chart-panel">
            <div class="panel-header">
              <h2>{{ firstPlayer?.name }} 的 OPS 歷年趨勢</h2>
              <span>{{ history.length }} 個球季</span>
            </div>
            <div ref="historyChartEl" class="chart" />
          </div>
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
          <section class="panel team-comparison">
            <div class="panel-header">
              <div>
                <p class="eyebrow">TEAM COMPARISON</p>
                <h2>球隊年度比較</h2>
              </div>
              <span>{{ dataset.season }} 年度</span>
            </div>
            <div class="team-comparison-toolbar">
              <div class="roster-tabs" role="tablist" aria-label="比較類型">
                <button :class="{ active: teamMetricGroup === 'batting' }" @click="switchTeamMetricGroup('batting')">打擊</button>
                <button :class="{ active: teamMetricGroup === 'pitching' }" @click="switchTeamMetricGroup('pitching')">投球</button>
              </div>
              <select v-model="teamMetric" class="form-select">
                <option v-for="item in teamComparisonMetrics[teamMetricGroup]" :key="item.key" :value="item.key">{{ item.label }}</option>
              </select>
            </div>
            <div v-if="teamSummaries.length" ref="teamChartEl" class="chart team-comparison-chart" />
            <p v-else class="comparison-empty">此年度尚無可供比較的球隊彙總資料。</p>
            <div v-if="teamSummaries.length" class="team-comparison-values">
              <div v-for="row in teamSummaries" :key="row.team_id">
                <span class="team-dot" :style="{ backgroundColor: teamColor(row.team_id) }" />
                <span>{{ row.nickname || row.team }}</span>
                <strong>{{ fmt(row[teamMetricGroup][teamMetric], teamMetric) }}</strong>
              </div>
            </div>
          </section>
          <div class="team-grid">
            <button
              v-for="x in dataset.standings"
              :key="x.source_team_id"
              class="team-card team-select"
              :class="{
                selected: x.source_team_id === selectedClub?.source_team_id,
              }"
              :style="{
                '--team-color': teamColor(String(x.source_team_id)),
                '--team-ink': teamTextColor(String(x.source_team_id)),
              }"
              @click="openTeam(String(x.source_team_id))"
            >
              <div>
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
              <PlayerIcon :team-id="String(p.source_team_id)" :kind="rosterRole === 'batters' ? 'batter' : 'pitcher'" size="lg" /><span class="role-label">{{
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
