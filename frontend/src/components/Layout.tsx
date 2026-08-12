import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand">
          🚌 BusApp
        </Link>
        <nav className="nav">
          <NavLink to="/" end>
            Search
          </NavLink>
          {user && <NavLink to="/orders">My orders</NavLink>}
          {user?.role === "admin" && <NavLink to="/admin">Admin</NavLink>}
        </nav>
        <div className="topbar__spacer" />
        <div className="auth-actions">
          {user ? (
            <>
              <span className="user-chip">
                {user.email} <em>({user.role})</em>
              </span>
              <button
                className="btn btn--sm"
                onClick={() => {
                  logout();
                  navigate("/");
                }}
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className="btn btn--sm">
                Login
              </NavLink>
              <NavLink to="/register" className="btn btn--sm btn--primary">
                Register
              </NavLink>
            </>
          )}
        </div>
      </header>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
