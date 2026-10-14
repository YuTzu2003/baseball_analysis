import assert from "node:assert/strict";
import test from "node:test";
import { parse } from "zrender/lib/tool/color.js";

import { formatMetric, teamColor } from "../node_modules/.tmp/team-tests/teamPresentation.js";


test("formatMetric shows unavailable team rates as a dash", () => {
  assert.equal(formatMetric(null, "ERA"), "—");
  assert.equal(formatMetric(undefined, "OPS"), "—");
  assert.equal(formatMetric("", "AVG"), "—");
});

test("teamColor is stable and distinguishes historical team IDs", () => {
  assert.equal(teamColor("ACC"), teamColor("ACC"));
  assert.notEqual(teamColor("ACC"), teamColor("ABB"));
  assert.notEqual(teamColor("ABB"), teamColor("AFF"));
  assert.match(teamColor("ACC"), /^hsl\(\d+, 65%, 36%\)$/);
  assert.ok(parse(teamColor("ACC"), []));
});
