import { FormEvent, useState } from "react";
import { citiesApi } from "../../api";
import { ApiError } from "../../api/client";
import { AsyncView } from "../../components/AsyncView";
import { useAsync } from "../../hooks/useAsync";

export function AdminCities() {
  const { data, loading, error, reload } = useAsync(() => citiesApi.list(), []);
  const [form, setForm] = useState({ name: "", longitude: "", latitude: "" });
  const [formError, setFormError] = useState<string | null>(null);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    try {
      await citiesApi.create({
        name: form.name,
        longitude: Number(form.longitude),
        latitude: Number(form.latitude),
      });
      setForm({ name: "", longitude: "", latitude: "" });
      reload();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not create city");
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
          <input
            placeholder="Name"
            value={form.name}
            required
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <input
            placeholder="Longitude"
            type="number"
            step="any"
            value={form.longitude}
            required
            onChange={(e) => setForm({ ...form, longitude: e.target.value })}
          />
          <input
            placeholder="Latitude"
            type="number"
            step="any"
            value={form.latitude}
            required
            onChange={(e) => setForm({ ...form, latitude: e.target.value })}
          />
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
