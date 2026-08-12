import { FormEvent, useRef, useState } from "react";
import { busesApi } from "../../api";
import { ApiError } from "../../api/client";
import type { Bus } from "../../api/types";
import { AsyncView } from "../../components/AsyncView";
import { useAsync } from "../../hooks/useAsync";

export function AdminBuses() {
  const { data, loading, error, reload } = useAsync(() => busesApi.list(), []);
  const [form, setForm] = useState({ color: "", seats_quantity: "", number_plate: "" });
  const [formError, setFormError] = useState<string | null>(null);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    try {
      await busesApi.create({
        color: form.color,
        seats_quantity: Number(form.seats_quantity),
        number_plate: form.number_plate,
      });
      setForm({ color: "", seats_quantity: "", number_plate: "" });
      reload();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not create bus");
    }
  }

  return (
    <div className="admin-section">
      <form className="card admin-form" onSubmit={onCreate}>
        <h3>Add bus</h3>
        <div className="admin-form__row">
          <input
            placeholder="Color"
            value={form.color}
            required
            onChange={(e) => setForm({ ...form, color: e.target.value })}
          />
          <input
            placeholder="Seats"
            type="number"
            min={0}
            value={form.seats_quantity}
            required
            onChange={(e) => setForm({ ...form, seats_quantity: e.target.value })}
          />
          <input
            placeholder="Number plate"
            value={form.number_plate}
            required
            onChange={(e) => setForm({ ...form, number_plate: e.target.value })}
          />
          <button className="btn btn--primary">Add</button>
        </div>
        {formError && <p className="form-error">{formError}</p>}
      </form>

      <AsyncView
        loading={loading}
        error={error}
        isEmpty={!!data && data.length === 0}
        emptyMessage="No buses yet."
        onRetry={reload}
      >
        <div className="bus-grid">
          {data?.map((bus) => (
            <BusRow key={bus.id} bus={bus} onChange={reload} />
          ))}
        </div>
      </AsyncView>
    </div>
  );
}

function BusRow({ bus, onChange }: { bus: Bus; onChange: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  async function onUpload(file: File) {
    setUploading(true);
    setUploadError(null);
    try {
      await busesApi.uploadPhoto(bus.id, file);
      onChange();
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function onDelete() {
    await busesApi.remove(bus.id);
    onChange();
  }

  return (
    <div className="card bus-card">
      <div className="bus-card__photo">
        {bus.thumbnail_url ? (
          <img src={bus.thumbnail_url} alt="Bus" />
        ) : (
          <div className="bus-card__photo--placeholder">No photo</div>
        )}
      </div>
      <div className="bus-card__body">
        <strong>{bus.number_plate}</strong>
        <span className="muted">
          {bus.color} · {bus.seats_quantity} seats
        </span>
        <div className="bus-card__actions">
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onUpload(f);
            }}
          />
          <button
            className="btn btn--sm"
            disabled={uploading}
            onClick={() => fileRef.current?.click()}
          >
            {uploading ? "Uploading…" : bus.photo_url ? "Replace photo" : "Upload photo"}
          </button>
          <button className="link-btn link-btn--danger" onClick={onDelete}>
            Delete
          </button>
        </div>
        {uploadError && <span className="field-error">{uploadError}</span>}
      </div>
    </div>
  );
}
