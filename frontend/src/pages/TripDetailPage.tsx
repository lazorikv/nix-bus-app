import { Link, useParams, useSearchParams } from "react-router-dom";
import { tripsApi } from "../api";
import { AsyncView } from "../components/AsyncView";
import { useAsync } from "../hooks/useAsync";
import { resolveSegment } from "../lib/segment";

export function TripDetailPage() {
  const { id } = useParams();
  const tripId = Number(id);
  const [searchParams] = useSearchParams();
  const from = searchParams.get("from") ? Number(searchParams.get("from")) : undefined;
  const to = searchParams.get("to") ? Number(searchParams.get("to")) : undefined;
  const bookQuery = searchParams.toString() ? `?${searchParams.toString()}` : "";
  const { data: trip, loading, error, reload } = useAsync(() => tripsApi.get(tripId), [tripId]);

  return (
    <AsyncView loading={loading} error={error} onRetry={reload}>
      {trip && (
        <div className="detail">
          <div className="detail__media card">
            {trip.bus?.photo_url ? (
              <img src={trip.bus.photo_url} alt="Bus" className="detail__photo" />
            ) : (
              <div className="detail__photo detail__photo--placeholder">🚌</div>
            )}
            {trip.bus && (
              <div className="detail__bus">
                <span>Bus {trip.bus.number_plate}</span>
                <span className="muted">
                  {trip.bus.color}, {trip.bus.seats_quantity} seats
                </span>
              </div>
            )}
          </div>

          <div className="detail__info card">
            <h1>{trip.name}</h1>
            <div className="detail__meta">
              <span className="price price--lg">${trip.price}</span>
              <span className={`seats ${trip.seats_left === 0 ? "seats--none" : ""}`}>
                {trip.seats_left} seats left
              </span>
            </div>

            {(() => {
              const seg = resolveSegment(trip.route, from, to);
              return seg && (from != null || to != null) ? (
                <p className="segment-note">
                  Your trip: <strong>{seg.origin.city_name}</strong> →{" "}
                  <strong>{seg.destination.city_name}</strong>
                </p>
              ) : null;
            })()}

            <h3>Route</h3>
            <ol className="route">
              {trip.route.map((stop) => {
                const isBoarding = from != null ? stop.city_id === from : stop.position === 0;
                const isDropoff =
                  to != null
                    ? stop.city_id === to
                    : stop.position === trip.route.length - 1;
                const mark = isBoarding ? " (board)" : isDropoff ? " (get off)" : "";
                return (
                  <li
                    key={stop.position}
                    className={`route__stop${mark ? " route__stop--active" : ""}`}
                  >
                    <span className="route__city">
                      {stop.city_name}
                      {mark && <span className="route__mark">{mark}</span>}
                    </span>
                    <span className="muted">{new Date(stop.time).toLocaleString()}</span>
                  </li>
                );
              })}
            </ol>

            {trip.seats_left > 0 ? (
              <Link to={`/trips/${trip.id}/book${bookQuery}`} className="btn btn--primary btn--lg">
                Book now
              </Link>
            ) : (
              <button className="btn btn--lg" disabled>
                Sold out
              </button>
            )}
          </div>
        </div>
      )}
    </AsyncView>
  );
}
