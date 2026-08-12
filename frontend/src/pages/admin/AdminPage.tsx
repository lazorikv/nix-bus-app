import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { AdminBuses } from "./AdminBuses";
import { AdminCities } from "./AdminCities";
import { AdminOrders } from "./AdminOrders";
import { AdminTrips } from "./AdminTrips";

export function AdminPage() {
  return (
    <div className="stack">
      <h1>Admin panel</h1>
      <nav className="tabs">
        <NavLink to="/admin/cities">Cities</NavLink>
        <NavLink to="/admin/buses">Buses</NavLink>
        <NavLink to="/admin/trips">Trips</NavLink>
        <NavLink to="/admin/orders">Orders</NavLink>
      </nav>
      <Routes>
        <Route index element={<Navigate to="cities" replace />} />
        <Route path="cities" element={<AdminCities />} />
        <Route path="buses" element={<AdminBuses />} />
        <Route path="trips" element={<AdminTrips />} />
        <Route path="orders" element={<AdminOrders />} />
      </Routes>
    </div>
  );
}
