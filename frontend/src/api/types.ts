export type Role = "admin" | "user";
export type OrderStatus = "pending" | "paid" | "failed";

export interface User {
  id: number;
  email: string;
  role: Role;
}

export interface City {
  id: number;
  name: string;
  longitude: number;
  latitude: number;
  created_at: string;
  updated_at: string;
}

export interface Bus {
  id: number;
  color: string;
  seats_quantity: number;
  number_plate: string;
  photo_url: string | null;
  thumbnail_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface RouteStop {
  city_id: number;
  city_name: string;
  time: string;
  position: number;
}

export interface Trip {
  id: number;
  name: string;
  price: string;
  bus_id: number;
  seats_left: number;
  route: RouteStop[];
  bus_thumbnail_url?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TripDetail extends Trip {
  bus: Bus | null;
}

export interface Passenger {
  first_name: string;
  last_name: string;
  email: string;
  age: number;
  ticket_price?: string;
}

export interface Order {
  id: number;
  trip_id: number;
  user_id: number | null;
  status: OrderStatus;
  price: string;
  passengers: Passenger[];
  ticket_pdf_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
