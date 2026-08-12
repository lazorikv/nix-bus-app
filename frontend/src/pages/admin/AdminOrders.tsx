import { useState } from "react";
import { Link } from "react-router-dom";
import { ordersApi } from "../../api";
import { AsyncView } from "../../components/AsyncView";
import { Pagination } from "../../components/Pagination";
import { StatusBadge } from "../../components/StatusBadge";
import { useAsync } from "../../hooks/useAsync";

export function AdminOrders() {
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useAsync(() => ordersApi.list(page, 15), [page]);

  return (
    <div className="admin-section">
      <AsyncView
        loading={loading}
        error={error}
        isEmpty={!!data && data.items.length === 0}
        emptyMessage="No orders yet."
        onRetry={reload}
      >
        <table className="table">
          <thead>
            <tr>
              <th>#</th>
              <th>Trip</th>
              <th>User</th>
              <th>Passengers</th>
              <th>Total</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((o) => (
              <tr key={o.id}>
                <td>{o.id}</td>
                <td>#{o.trip_id}</td>
                <td>{o.user_id ?? <em className="muted">anonymous</em>}</td>
                <td>{o.passengers.length}</td>
                <td>${o.price}</td>
                <td>
                  <StatusBadge status={o.status} />
                </td>
                <td>
                  <Link className="link-btn" to={`/orders/${o.id}`}>
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <Pagination page={data?.page ?? 1} pages={data?.pages ?? 1} onChange={setPage} />
      </AsyncView>
    </div>
  );
}
