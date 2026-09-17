import { FormEvent, useState } from "react";
import { busesApi, citiesApi, tripsApi } from "../../api";
import { ApiError } from "../../api/client";
import type { Bus, City } from "../../api/types";
import { AsyncView } from "../../components/AsyncView";
import { useAsync } from "../../hooks/useAsync";

interface StopForm {
  city_id: string;
  time: string;
}

function validateStops(stops: StopForm[]): Record<number, string> {
  const errors: Record<number, string> = {};
  let prevTime: number | null = null;
  stops.forEach((s, i) => {
    if (!s.city_id || !s.time) {
      errors[i] = "City and time are required.";
      return;
    }
    const time = new Date(s.time).getTime();
    if (prevTime !== null && time <= prevTime) {
      errors[i] = "Must be after the previous stop's time.";
    } else {
      prevTime = time;
    }
  });
  return errors;
}

export function AdminTrips() {
  const cities = useAsync(() => citiesApi.list(), []);
  const buses = useAsync(() => busesApi.list(), []);
  const trips = useAsync(() => tripsApi.search({ page_size: 100 }), []);

  const [name, setName] = useState("");
  const [price, setPrice] = useState("");
  const [busId, setBusId] = useState("");
  const [stops, setStops] = useState<StopForm[]>([
    { city_id: "", time: "" },
    { city_id: "", time: "" },
  ]);
  const [formError, setFormError] = useState<string | null>(null);
  const [stopErrors, setStopErrors] = useState<Record<number, string>>({});
  const [routeError, setRouteError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function updateStop(i: number, field: keyof StopForm, value: string) {
    setStops((list) => list.map((s, idx) => (idx === i ? { ...s, [field]: value } : s)));
    setStopErrors((errs) => {
      if (!(i in errs)) return errs;
      const rest = { ...errs };
      delete rest[i];
      return rest;
    });
  }
  const addStop = () => setStops((l) => [...l, { city_id: "", time: "" }]);
  const removeStop = (i: number) =>
    setStops((l) => (l.length > 2 ? l.filter((_, idx) => idx !== i) : l));

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    setStopErrors({});
    setRouteError(null);

    const clientErrors = validateStops(stops);
    if (Object.keys(clientErrors).length > 0) {
      setFormError("Please fix the highlighted fields.");
      setStopErrors(clientErrors);
      return;
    }

    const cityMap = new Map((cities.data ?? []).map((c: City) => [String(c.id), c.name]));
    const route = stops.map((s, i) => ({
      city_id: Number(s.city_id),
      city_name: cityMap.get(s.city_id) ?? "",
      time: new Date(s.time).toISOString(),
      position: i,
    }));

    setSubmitting(true);
    try {
      await tripsApi.create({ name, price: Number(price), bus_id: Number(busId), route });
      setName("");
      setPrice("");
      setBusId("");
      setStops([
        { city_id: "", time: "" },
        { city_id: "", time: "" },
      ]);
      trips.reload();
    } catch (err) {
      if (err instanceof ApiError) {
        setFormError(err.message);
        if (err.fieldErrors.route) setRouteError(err.fieldErrors.route);
      } else {
        setFormError("Could not create trip");
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function onDelete(id: number) {
    await tripsApi.remove(id);
    trips.reload();
  }

  return (
    <div className="admin-section">
      <form className="card admin-form" onSubmit={onSubmit}>
        <h3>Create trip</h3>
        <div className="admin-form__row">
          <input placeholder="Name" value={name} required onChange={(e) => setName(e.target.value)} />
          <input
            placeholder="Price"
            type="number"
            step="0.01"
            min={0}
            value={price}
            required
            onChange={(e) => setPrice(e.target.value)}
          />
          <select value={busId} required onChange={(e) => setBusId(e.target.value)}>
            <option value="">Select bus…</option>
            {buses.data?.map((b: Bus) => (
              <option key={b.id} value={b.id}>
                {b.number_plate} ({b.seats_quantity} seats)
              </option>
            ))}
          </select>
        </div>

        <h4>Route builder</h4>
        <p className="muted">At least 2 stops, in chronological order.</p>
        {stops.map((s, i) => (
          <div className="route-builder__stop" key={i}>
            <span className="route-builder__pos">{i + 1}</span>
            <select
              value={s.city_id}
              required
              aria-invalid={!!stopErrors[i]}
              onChange={(e) => updateStop(i, "city_id", e.target.value)}
            >
              <option value="">City…</option>
              {cities.data?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            <input
              type="datetime-local"
              value={s.time}
              required
              aria-invalid={!!stopErrors[i]}
              onChange={(e) => updateStop(i, "time", e.target.value)}
            />
            {stops.length > 2 && (
              <button type="button" className="link-btn link-btn--danger" onClick={() => removeStop(i)}>
                ✕
              </button>
            )}
            {stopErrors[i] && <span className="field-error">{stopErrors[i]}</span>}
          </div>
        ))}
        <button type="button" className="btn btn--sm" onClick={addStop}>
          + Add stop
        </button>
        {routeError && <p className="field-error">{routeError}</p>}

        {formError && <p className="form-error">{formError}</p>}
        <button className="btn btn--primary" disabled={submitting}>
          {submitting ? "Creating…" : "Create trip"}
        </button>
      </form>

      <AsyncView
        loading={trips.loading}
        error={trips.error}
        isEmpty={!!trips.data && trips.data.items.length === 0}
        emptyMessage="No trips yet."
        onRetry={trips.reload}
      >
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Route</th>
              <th>Price</th>
              <th>Seats left</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {trips.data?.items.map((t) => (
              <tr key={t.id}>
                <td>{t.id}</td>
                <td>{t.name}</td>
                <td>
                  {t.route[0]?.city_name} → {t.route[t.route.length - 1]?.city_name}
                </td>
                <td>${t.price}</td>
                <td>{t.seats_left}</td>
                <td>
                  <button className="link-btn link-btn--danger" onClick={() => onDelete(t.id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </AsyncView>
    </div>
  );
}
