const currentTeamColors: Record<string, string> = {
  ACN: "#b58d00",
  ADD: "#d86400",
  AJL: "#7b2d8e",
  AEO: "#005baa",
  AAA: "#d71920",
  AKP: "#247a37",
};

export function teamColor(teamId: string): string {
  if (currentTeamColors[teamId]) return currentTeamColors[teamId];
  let hash = 0;
  for (const character of teamId) hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
  return `hsl(${Math.round((hash * 137.508) % 360)}, 65%, 36%)`;
}

export function formatMetric(value: unknown, key: string): string {
  if (value == null || value === "") return "—";
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  if (["AVG", "OBP", "SLG", "OPS", "ISO", "win_pct"].includes(key))
    return number.toFixed(3).replace(/^0/, "");
  if (["ERA", "WHIP", "K_9", "BB_9", "HR_9"].includes(key)) return number.toFixed(2);
  if (["K_pct", "BB_pct"].includes(key)) return `${number.toFixed(1)}%`;
  return number.toLocaleString();
}
