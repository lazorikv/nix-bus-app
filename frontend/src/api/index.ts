import { apiRequest } from "./client";
import type {
  Bus,
  City,
  Order,
  Page,
  Passenger,
  Trip,
  TripDetail,
  User,
} from "./types";

export const authApi = {
  register: (email: string, password: string) =>
    apiRequest<User>("/auth/register", { method: "POST", body: { email, password }, auth: false }),
  login: (email: string, password: string) =>
    apiRequest<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: { email, password },
      auth: false,
    }),
  me: () => apiRequest<User>("/auth/me"),
};

export const citiesApi = {
  list: () => apiRequest<City[]>("/cities", { auth: false }),
  create: (data: Omit<City, "id" | "created_at" | "updated_at">) =>
    apiRequest<City>("/cities", { method: "POST", body: data }),
  update: (id: number, data: Partial<City>) =>
    apiRequest<City>(`/cities/${id}`, { method: "PATCH", body: data }),
  remove: (id: number) => apiRequest<void>(`/cities/${id}`, { method: "DELETE" }),
};

export const busesApi = {
  list: () => apiRequest<Bus[]>("/buses"),
  create: (data: { color: string; seats_quantity: number; number_plate: string }) =>
    apiRequest<Bus>("/buses", { method: "POST", body: data }),
  update: (id: number, data: Partial<Bus>) =>
    apiRequest<Bus>(`/buses/${id}`, { method: "PATCH", body: data }),
  remove: (id: number) => apiRequest<void>(`/buses/${id}`, { method: "DELETE" }),
  uploadPhoto: (id: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiRequest<Bus>(`/buses/${id}/photo`, { method: "POST", body: form, isForm: true });
  },
};

export interface TripSearchParams {
  origin?: number;
  destination?: number;
  departure_date?: string;
  min_price?: number;
  max_price?: number;
  min_seats?: number;
  sort?: string;
  page?: number;
  page_size?: number;
}

export const tripsApi = {
  search: (params: TripSearchParams) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "" && v !== null) qs.append(k, String(v));
    });
    return apiRequest<Page<Trip>>(`/trips?${qs.toString()}`, { auth: false });
  },
  get: (id: number) => apiRequest<TripDetail>(`/trips/${id}`, { auth: false }),
  create: (data: {
    name: string;
    price: number;
    bus_id: number;
    route: { city_id: number; city_name: string; time: string; position: number }[];
  }) => apiRequest<Trip>("/trips", { method: "POST", body: data }),
  update: (id: number, data: Record<string, unknown>) =>
    apiRequest<Trip>(`/trips/${id}`, { method: "PATCH", body: data }),
  remove: (id: number) => apiRequest<void>(`/trips/${id}`, { method: "DELETE" }),
};

export const ordersApi = {
  create: (trip_id: number, passengers: Omit<Passenger, "ticket_price">[]) =>
    apiRequest<Order>("/orders", { method: "POST", body: { trip_id, passengers } }),
  list: (page = 1, page_size = 10) =>
    apiRequest<Page<Order>>(`/orders?page=${page}&page_size=${page_size}`),
  // Token sent when present (owner/admin), omitted for an anonymous guest
  // polling their own NULL-owner order — both flows are authorized server-side.
  get: (id: number) => apiRequest<Order>(`/orders/${id}`),
};

export const paymentApi = {
  simulate: (orderId: number, success: boolean) =>
    apiRequest<{ order_id: number; status: string; applied: boolean }>(
      `/payment/simulate/${orderId}?success=${success}`,
      { method: "POST", auth: false },
    ),
};
