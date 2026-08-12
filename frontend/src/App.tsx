import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AdminPage } from "./pages/admin/AdminPage";
import { BookingPage } from "./pages/BookingPage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { MyOrdersPage } from "./pages/MyOrdersPage";
import { OrderStatusPage } from "./pages/OrderStatusPage";
import { RegisterPage } from "./pages/RegisterPage";
import { TripDetailPage } from "./pages/TripDetailPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route path="trips/:id" element={<TripDetailPage />} />
        <Route path="trips/:id/book" element={<BookingPage />} />
        <Route path="orders/:id" element={<OrderStatusPage />} />
        <Route
          path="orders"
          element={
            <ProtectedRoute>
              <MyOrdersPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="admin/*"
          element={
            <ProtectedRoute adminOnly>
              <AdminPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<div className="state state--empty">Page not found.</div>} />
      </Route>
    </Routes>
  );
}
