import { Link, useParams } from "react-router-dom";
import { tripsApi } from "../api";
import { AsyncView } from "../components/AsyncView";
import { useAsync } from "../hooks/useAsync";

export function TripDetailPage() {
  const { id } = useParams();
  const tripId = Number(id);
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

            <h3>Route</h3>
            <ol className="route">
              {trip.route.map((stop) => (
                <li key={stop.position} className="route__stop">
                  <span className="route__city">{stop.city_name}</span>
                  <span className="muted">{new Date(stop.time).toLocaleString()}</span>
                </li>
              ))}
            </ol>

            {trip.seats_left > 0 ? (
              <Link to={`/trips/${trip.id}/book`} className="btn btn--primary btn--lg">
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
