import { FormEvent, useState } from "react";
import { citiesApi } from "../../api";
import { ApiError } from "../../api/client";
import { AsyncView } from "../../components/AsyncView";
import { useAsync } from "../../hooks/useAsync";

function validateCoordinates(longitude: number, latitude: number): Record<string, string> {
  const errors: Record<string, string> = {};
  if (Number.isNaN(longitude) || longitude < -180 || longitude > 180) {
    errors.longitude = "Longitude must be between -180 and 180.";
  }
  if (Number.isNaN(latitude) || latitude < -90 || latitude > 90) {
    errors.latitude = "Latitude must be between -90 and 90.";
  }
  return errors;
}

export function AdminCities() {
  const { data, loading, error, reload } = useAsync(() => citiesApi.list(), []);
  const [form, setForm] = useState({ name: "", longitude: "", latitude: "" });
  const [formError, setFormError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    setFieldErrors({});

    const longitude = Number(form.longitude);
    const latitude = Number(form.latitude);
    const clientErrors = validateCoordinates(longitude, latitude);
    if (Object.keys(clientErrors).length > 0) {
      setFormError("Please fix the highlighted fields.");
      setFieldErrors(clientErrors);
      return;
    }

    try {
      await citiesApi.create({ name: form.name, longitude, latitude });
      setForm({ name: "", longitude: "", latitude: "" });
      reload();
    } catch (err) {
      if (err instanceof ApiError) {
        setFormError(err.message);
        setFieldErrors(err.fieldErrors);
      } else {
        setFormError("Could not create city");
      }
    }
  }

  async function onDelete(id: number) {
    await citiesApi.remove(id);
    reload();
  }

  return (
    <div className="admin-section">
      <form className="card admin-form" onSubmit={onCreate}>
        <h3>Add city</h3>
        <div className="admin-form__row">
          <div className="admin-form__field">
            <input
              placeholder="Name"
              value={form.name}
              required
              aria-invalid={!!fieldErrors.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
            {fieldErrors.name && <span className="field-error">{fieldErrors.name}</span>}
          </div>
          <div className="admin-form__field">
            <input
              placeholder="Longitude"
              type="number"
              step="any"
              value={form.longitude}
              required
              aria-invalid={!!fieldErrors.longitude}
              onChange={(e) => setForm({ ...form, longitude: e.target.value })}
            />
            {fieldErrors.longitude && <span className="field-error">{fieldErrors.longitude}</span>}
          </div>
          <div className="admin-form__field">
            <input
              placeholder="Latitude"
              type="number"
              step="any"
              value={form.latitude}
              required
              aria-invalid={!!fieldErrors.latitude}
              onChange={(e) => setForm({ ...form, latitude: e.target.value })}
            />
            {fieldErrors.latitude && <span className="field-error">{fieldErrors.latitude}</span>}
          </div>
          <button className="btn btn--primary">Add</button>
        </div>
        {formError && <p className="form-error">{formError}</p>}
      </form>

      <AsyncView
        loading={loading}
        error={error}
        isEmpty={!!data && data.length === 0}
        emptyMessage="No cities yet."
        onRetry={reload}
      >
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Lng</th>
              <th>Lat</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {data?.map((c) => (
              <tr key={c.id}>
                <td>{c.id}</td>
                <td>{c.name}</td>
                <td>{c.longitude}</td>
                <td>{c.latitude}</td>
                <td>
                  <button className="link-btn link-btn--danger" onClick={() => onDelete(c.id)}>
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
