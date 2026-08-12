import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { citiesApi, tripsApi, type TripSearchParams } from "../api";
import type { Page, Trip } from "../api/types";
import { AsyncView } from "../components/AsyncView";
import { Pagination } from "../components/Pagination";
import { useAsync } from "../hooks/useAsync";

const PAGE_SIZE = 6;

export function HomePage() {
  const cities = useAsync(() => citiesApi.list(), []);
  const [params, setParams] = useState<TripSearchParams>({ sort: "price", page: 1 });
  const [result, setResult] = useState<Page<Trip> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  async function runSearch(next: TripSearchParams) {
    setLoading(true);
    setError(null);
    setSearched(true);
    try {
      const res = await tripsApi.search({ ...next, page_size: PAGE_SIZE });
      setResult(res);
      setParams(next);
    } catch (err: any) {
      setError(err?.message ?? "Search failed");
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    runSearch({ ...params, page: 1 });
  }

  function update<K extends keyof TripSearchParams>(key: K, value: TripSearchParams[K]) {
    setParams((p) => ({ ...p, [key]: value }));
  }

  return (
    <div className="stack">
      <section className="hero">
        <h1>Find your bus trip</h1>
        <p className="muted">Search routes, compare prices, and book in minutes.</p>
      </section>

      <form className="search-bar card" onSubmit={onSubmit}>
        <div className="search-grid">
          <label>
            From
            <select
              value={params.origin ?? ""}
              onChange={(e) => update("origin", e.target.value ? Number(e.target.value) : undefined)}
            >
              <option value="">Any city</option>
              {cities.data?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            To
            <select
              value={params.destination ?? ""}
              onChange={(e) =>
                update("destination", e.target.value ? Number(e.target.value) : undefined)
              }
            >
              <option value="">Any city</option>
              {cities.data?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Date
            <input
              type="date"
              value={params.departure_date ?? ""}
              onChange={(e) => update("departure_date", e.target.value || undefined)}
            />
          </label>
          <label>
            Sort by
            <select value={params.sort} onChange={(e) => update("sort", e.target.value)}>
              <option value="price">Price ↑</option>
              <option value="-price">Price ↓</option>
              <option value="-seats_left">Most seats</option>
              <option value="seats_left">Fewest seats</option>
            </select>
          </label>
          <label>
            Max price
            <input
              type="number"
              min={0}
              value={params.max_price ?? ""}
              onChange={(e) =>
                update("max_price", e.target.value ? Number(e.target.value) : undefined)
              }
            />
          </label>
          <label>
            Min seats
            <input
              type="number"
              min={0}
              value={params.min_seats ?? ""}
              onChange={(e) =>
                update("min_seats", e.target.value ? Number(e.target.value) : undefined)
              }
            />
          </label>
        </div>
        <button className="btn btn--primary" disabled={loading}>
          {loading ? "Searching…" : "Search trips"}
        </button>
      </form>

      {searched && (
        <AsyncView
          loading={loading}
          error={error}
          isEmpty={!!result && result.items.length === 0}
          emptyMessage="No trips match your search. Try widening the filters."
          onRetry={() => runSearch(params)}
        >
          <div className="results">
            <div className="results__count">{result?.total} trip(s) found</div>
            <div className="trip-grid">
              {result?.items.map((trip) => (
                <TripCard key={trip.id} trip={trip} />
              ))}
            </div>
            <Pagination
              page={result?.page ?? 1}
              pages={result?.pages ?? 1}
              onChange={(p) => runSearch({ ...params, page: p })}
            />
          </div>
        </AsyncView>
      )}
    </div>
  );
}

function TripCard({ trip }: { trip: Trip }) {
  const origin = trip.route[0];
  const destination = trip.route[trip.route.length - 1];
  return (
    <Link to={`/trips/${trip.id}`} className="trip-card">
      <div className="trip-card__photo">
        {trip.bus_thumbnail_url ? (
          <img src={trip.bus_thumbnail_url} alt="Bus" />
        ) : (
          <div className="trip-card__photo--placeholder">🚌</div>
        )}
      </div>
      <div className="trip-card__body">
        <h3>{trip.name}</h3>
        <p className="trip-card__route">
          {origin?.city_name} → {destination?.city_name}
        </p>
        <p className="muted trip-card__time">
          {new Date(origin?.time).toLocaleString()} —{" "}
          {new Date(destination?.time).toLocaleString()}
        </p>
        <div className="trip-card__footer">
          <span className="price">${trip.price}</span>
          <span className={`seats ${trip.seats_left === 0 ? "seats--none" : ""}`}>
            {trip.seats_left} seats left
          </span>
        </div>
      </div>
    </Link>
  );
}
