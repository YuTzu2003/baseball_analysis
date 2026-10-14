export type PitchLocation = { x: number; y: number }

// Normalized catcher's-view coordinates. Y grows downward.
export const ZONE = { left: 0.18, right: 0.82, top: 0.28, bottom: 0.74, ballRadius: 0.05 } as const

export function isStrike(pitch: PitchLocation): boolean {
  const nearestX = Math.max(ZONE.left, Math.min(pitch.x, ZONE.right))
  const nearestY = Math.max(ZONE.top, Math.min(pitch.y, ZONE.bottom))
  return Math.hypot(pitch.x - nearestX, pitch.y - nearestY) <= ZONE.ballRadius
}

// One normalized unit equals 3.2 scene units. The 3D sphere therefore
// touches the same border that the strike calculation uses.
export function platePoint(pitch: PitchLocation) {
  return { x: (pitch.x - 0.5) * 3.2, y: 1.1 + (1 - pitch.y) * 3.2 }
}
