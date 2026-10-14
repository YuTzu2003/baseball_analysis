export type PitchLocation = { x: number; y: number }

// Normalized catcher's-view coordinates. Y grows downward.
// A taller, narrower zone matching the reference umpire view.
export const ZONE = { left: 0.30, right: 0.70, top: 0.18, bottom: 0.82, ballRadius: 0.05 } as const

export function isStrike(pitch: PitchLocation): boolean {
  const nearestX = Math.max(ZONE.left, Math.min(pitch.x, ZONE.right))
  const nearestY = Math.max(ZONE.top, Math.min(pitch.y, ZONE.bottom))
  return Math.hypot(pitch.x - nearestX, pitch.y - nearestY) <= ZONE.ballRadius
}

// One normalized unit equals 3.2 scene units. The 3D sphere therefore
// touches the same border that the strike calculation uses.
export function platePoint(pitch: PitchLocation) {
  // Keep the zone around a real batter's knees-to-chest height, not above the head.
  return { x: (pitch.x - 0.5) * 3.2, y: 0.25 + (1 - pitch.y) * 2.4 }
}
