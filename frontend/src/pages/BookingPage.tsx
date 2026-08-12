import { FormEvent, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ordersApi, tripsApi } from "../api";
import { ApiError } from "../api/client";
import { AsyncView } from "../components/AsyncView";
import { useAsync } from "../hooks/useAsync";

interface PassengerForm {
  first_name: string;
  last_name: string;
  email: string;
  age: string;
}

const emptyPassenger = (): PassengerForm => ({ first_name: "", last_name: "", email: "", age: "" });

export function BookingPage() {
  const { id } = useParams();
  const tripId = Number(id);
  const navigate = useNavigate();
  const { data: trip, loading, error, reload } = useAsync(() => tripsApi.get(tripId), [tripId]);

  const [passengers, setPassengers] = useState<PassengerForm[]>([emptyPassenger()]);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function updatePassenger(i: number, field: keyof PassengerForm, value: string) {
    setPassengers((list) => list.map((p, idx) => (idx === i ? { ...p, [field]: value } : p)));
  }

  function addPassenger() {
    setPassengers((list) => [...list, emptyPassenger()]);
  }

  function removePassenger(i: number) {
    setPassengers((list) => (list.length > 1 ? list.filter((_, idx) => idx !== i) : list));
  }

  function validate(): string | null {
    for (const [i, p] of passengers.entries()) {
      if (!p.first_name.trim() || !p.last_name.trim()) return `Passenger ${i + 1}: name is required.`;
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(p.email)) return `Passenger ${i + 1}: valid email required.`;
      const age = Number(p.age);
      if (!p.age || Number.isNaN(age) || age < 0 || age > 150)
        return `Passenger ${i + 1}: age must be 0–150.`;
    }
    return null;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const err = validate();
    if (err) {
      setFormError(err);
      return;
    }
    setFormError(null);
    setSubmitting(true);
    try {
      const order = await ordersApi.create(
        tripId,
        passengers.map((p) => ({
          first_name: p.first_name.trim(),
          last_name: p.last_name.trim(),
          email: p.email.trim(),
          age: Number(p.age),
        })),
      );
      navigate(`/orders/${order.id}`);
    } catch (e) {
      setFormError(e instanceof ApiError ? e.message : "Could not create order");
    } finally {
      setSubmitting(false);
    }
  }

  const total = trip ? (Number(trip.price) * passengers.length).toFixed(2) : "0.00";

  return (
    <AsyncView loading={loading} error={error} onRetry={reload}>
      {trip && (
        <div className="booking">
          <form className="card booking__form" onSubmit={onSubmit}>
            <h1>Passengers</h1>
            {passengers.map((p, i) => (
              <fieldset key={i} className="passenger">
                <legend>
                  Passenger {i + 1}
                  {passengers.length > 1 && (
                    <button
                      type="button"
                      className="link-btn"
                      onClick={() => removePassenger(i)}
                    >
                      Remove
                    </button>
                  )}
                </legend>
                <div className="passenger__grid">
                  <input
                    placeholder="First name"
                    value={p.first_name}
                    onChange={(e) => updatePassenger(i, "first_name", e.target.value)}
                  />
                  <input
                    placeholder="Last name"
                    value={p.last_name}
                    onChange={(e) => updatePassenger(i, "last_name", e.target.value)}
                  />
                  <input
                    placeholder="Email"
                    type="email"
                    value={p.email}
                    onChange={(e) => updatePassenger(i, "email", e.target.value)}
                  />
                  <input
                    placeholder="Age"
                    type="number"
                    min={0}
                    value={p.age}
                    onChange={(e) => updatePassenger(i, "age", e.target.value)}
                  />
                </div>
              </fieldset>
            ))}
            <button type="button" className="btn btn--sm" onClick={addPassenger}>
              + Add passenger
            </button>
            {formError && <p className="form-error">{formError}</p>}
          </form>

          <aside className="card booking__summary">
            <h2>Order summary</h2>
            <p className="summary__row">
              <span>Trip</span>
              <span>{trip.name}</span>
            </p>
            <p className="summary__row">
              <span>Price / seat</span>
              <span>${trip.price}</span>
            </p>
            <p className="summary__row">
              <span>Passengers</span>
              <span>{passengers.length}</span>
            </p>
            <p className="summary__row summary__total">
              <span>Total</span>
              <span>${total}</span>
            </p>
            <button className="btn btn--primary btn--lg" onClick={onSubmit} disabled={submitting}>
              {submitting ? "Creating order…" : "Continue to payment"}
            </button>
            <p className="muted">Seats are reserved when you create the order.</p>
          </aside>
        </div>
      )}
    </AsyncView>
  );
}
