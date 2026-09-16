import type { RouteStop } from "../api/types";

export interface Segment {
  origin: RouteStop;
  destination: RouteStop;
}

/**
 * Resolve the boarding/drop-off stops for an optionally selected segment,
 * defaulting each end to the trip's first / last stop. Returns null when the
 * route is empty or the selected ids are not a valid forward segment, letting
 * callers fall back to the whole trip.
 */
export function resolveSegment(
  route: RouteStop[],
  fromId?: number,
  toId?: number,
): Segment | null {
  if (route.length === 0) return null;
  const originIdx = fromId != null ? route.findIndex((s) => s.city_id === fromId) : 0;
  const destIdx = toId != null ? route.findIndex((s) => s.city_id === toId) : route.length - 1;
  if (originIdx < 0 || destIdx < 0 || originIdx >= destIdx) return null;
  return { origin: route[originIdx], destination: route[destIdx] };
}
