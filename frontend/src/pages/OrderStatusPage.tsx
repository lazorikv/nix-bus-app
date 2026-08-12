import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ordersApi, paymentApi } from "../api";
import type { Order } from "../api/types";
import { AsyncView } from "../components/AsyncView";
import { StatusBadge } from "../components/StatusBadge";

export function OrderStatusPage() {
  const { id } = useParams();
  const orderId = Number(id);
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [paying, setPaying] = useState(false);
  const [polling, setPolling] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval>>();

  const load = useCallback(async () => {
    try {
      const o = await ordersApi.get(orderId);
      setOrder(o);
      setError(null);
      return o;
    } catch (e: any) {
      setError(e?.message ?? "Could not load order");
      return null;
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    load();
  }, [load]);

  // Poll while the order is pending (mock gateway resolves it out-of-band).
  useEffect(() => {
    if (order?.status === "pending" && polling) {
      timer.current = setInterval(async () => {
        const o = await load();
        if (o && o.status !== "pending") setPolling(false);
      }, 1500);
      return () => clearInterval(timer.current);
    }
  }, [order?.status, polling, load]);

  async function pay(success: boolean) {
    setPaying(true);
    try {
      await paymentApi.simulate(orderId, success);
      setPolling(true);
      await load();
    } finally {
      setPaying(false);
    }
  }

  return (
    <AsyncView loading={loading} error={error} onRetry={load}>
      {order && (
        <div className="card card--narrow order-status">
          <h1>Order #{order.id}</h1>
          <p className="order-status__badge">
            <StatusBadge status={order.status} /> {polling && <span className="muted">· checking…</span>}
          </p>
          <p className="summary__row">
            <span>Total</span>
            <span>${order.price}</span>
          </p>
          <p className="summary__row">
            <span>Passengers</span>
            <span>{order.passengers.length}</span>
          </p>

          {order.status === "pending" && (
            <div className="mock-pay">
              <h3>Mock payment</h3>
              <p className="muted">Simulate a payment gateway callback:</p>
              <div className="mock-pay__actions">
                <button className="btn btn--primary" disabled={paying} onClick={() => pay(true)}>
                  Pay (success)
                </button>
                <button className="btn" disabled={paying} onClick={() => pay(false)}>
                  Fail payment
                </button>
              </div>
            </div>
          )}

          {order.status === "paid" && (
            <div className="state state--success">
              <p>🎉 Payment confirmed! Your booking is complete.</p>
              {order.ticket_pdf_url && (
                <a
                  className="btn btn--primary"
                  href={order.ticket_pdf_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Download ticket (PDF)
                </a>
              )}
            </div>
          )}

          {order.status === "failed" && (
            <div className="state state--error">
              <p>Payment failed. Your seats were released.</p>
              <Link className="btn" to={`/trips/${order.trip_id}`}>
                Back to trip
              </Link>
            </div>
          )}
        </div>
      )}
    </AsyncView>
  );
}
