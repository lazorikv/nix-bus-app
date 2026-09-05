"""Populate the database with realistic demo data.

Run locally:      python -m app.seed [--force] [--large]
Run in Docker:    docker compose exec backend python -m app.seed [--force] [--large]

Without --force the seeder is a no-op when cities already exist, so it is safe
to run on every startup. With --force it wipes domain data (cities, buses,
trips, orders) and reseeds; users are preserved and the admin/demo accounts are
ensured. Bus photos and paid-order tickets are uploaded to MinIO best-effort —
if object storage is unreachable the seeder still completes.

--large generates a much bigger, randomised dataset (many cities, buses, trips
across many routes/dates/prices, and orders in every status) so search,
filtering, sorting and pagination can be exercised end-to-end. It is
deterministic (fixed RNG seed) and implies --force.
"""

from __future__ import annotations

import io
import logging
import random
import sys
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.logging import configure_logging, log_event
from app.core.security import hash_password
from app.infrastructure.db.models import Bus, City, Order, OrderStatus, Trip, User, UserRole
from app.infrastructure.db.session import Base, SessionLocal, engine
from app.modules.orders.seats import SeatsService
from app.modules.payment.tickets import generate_and_store_ticket

logger = logging.getLogger("app.seed")

# Reference date for generating future departures (matches the demo timeline).
BASE = datetime(2026, 8, 1, 8, 0, 0)


CITIES = [
    ("Kyiv", 30.5234, 50.4501),
    ("Lviv", 24.0297, 49.8397),
    ("Odesa", 30.7233, 46.4825),
    ("Kharkiv", 36.2304, 49.9935),
    ("Dnipro", 35.0462, 48.4647),
    ("Vinnytsia", 28.4682, 49.2331),
    ("Warsaw", 21.0122, 52.2297),
    ("Krakow", 19.9450, 50.0647),
]

# Fixed bus specs as (color hex, seats, number plate). The hex renders the photo.
BUS_SPECS: list[tuple[str, int, str]] = [
    ("#e11d48", 40, "AA-1001-KA"),
    ("#2563eb", 32, "BC-2042-LV"),
    ("#16a34a", 50, "CE-3003-OD"),
    ("#f59e0b", 24, "KH-4004-KH"),
]


def _make_photo_png(hex_color: str) -> bytes:
    """Render a simple solid-color PNG to stand in for a real bus photo."""
    from PIL import Image

    rgb = tuple(int(hex_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    buf = io.BytesIO()
    Image.new("RGB", (640, 400), rgb).save(buf, format="PNG")
    return buf.getvalue()


def _ensure_user(db, email: str, password: str, role: UserRole) -> User:
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User(email=email, hashed_password=hash_password(password), role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _route(stop_specs: list[tuple[City, datetime]]) -> list[dict]:
    return [
        {
            "city_id": city.id,
            "city_name": city.name,
            "time": when.isoformat(),
            "position": i,
        }
        for i, (city, when) in enumerate(stop_specs)
    ]


def _passengers(names: list[tuple[str, str, int]], price: Decimal) -> list[dict]:
    return [
        {
            "first_name": fn,
            "last_name": ln,
            "email": f"{fn.lower()}.{ln.lower()}@example.com",
            "age": age,
            "ticket_price": str(price),
        }
        for fn, ln, age in names
    ]


def seed(force: bool = False, large: bool = False) -> None:
    Base.metadata.create_all(bind=engine)

    if large:
        force = True

    with SessionLocal() as db:
        existing = db.execute(select(City)).first()
        if existing and not force:
            log_event(logger, logging.INFO, "seed.skip", reason="cities already present")
            print("Data already present. Re-run with --force to wipe and reseed.")
            return

        if force:
            # Order matters due to FKs: orders -> trips -> buses/cities.
            db.query(Order).delete()
            db.query(Trip).delete()
            db.query(Bus).delete()
            db.query(City).delete()
            db.commit()
            log_event(logger, logging.INFO, "seed.wiped")

        # --- Users -------------------------------------------------------
        _ensure_user(db, "admin@busapp.com", "admin12345", UserRole.admin)
        demo_user = _ensure_user(db, "user@busapp.com", "user12345", UserRole.user)

        if large:
            _seed_large(db, demo_user)
            return

        # --- Cities ------------------------------------------------------
        cities: dict[str, City] = {}
        for name, lng, lat in CITIES:
            city = City(name=name, longitude=lng, latitude=lat)
            db.add(city)
            cities[name] = city
        db.commit()
        for c in cities.values():
            db.refresh(c)

        # --- Buses (with best-effort photos) -----------------------------
        buses: list[Bus] = []
        for color, seats, plate in BUS_SPECS:
            bus = Bus(color=color, seats_quantity=seats, number_plate=plate)
            db.add(bus)
            db.commit()
            db.refresh(bus)
            try:
                from app.modules.buses.photos import process_and_upload

                photo_key, thumb_key = process_and_upload("image/png", _make_photo_png(color))
                bus.photo_key = photo_key
                bus.thumbnail_key = thumb_key
                db.commit()
            except Exception as exc:  # noqa: BLE001
                log_event(logger, logging.WARNING, "seed.photo_failed", error=str(exc))
            buses.append(bus)

        # --- Trips: (name, price, bus, [(city, time), ...]) --------------
        trip_defs: list[tuple[str, Decimal, Bus, list[tuple[City, datetime]]]] = [
            (
                "Kyiv → Lviv Express",
                Decimal("28.50"),
                buses[0],
                [
                    (cities["Kyiv"], BASE),
                    (cities["Vinnytsia"], BASE + timedelta(hours=3)),
                    (cities["Lviv"], BASE + timedelta(hours=7)),
                ],
            ),
            (
                "Kyiv → Odesa Coastliner",
                Decimal("32.00"),
                buses[1],
                [
                    (cities["Kyiv"], BASE + timedelta(days=1)),
                    (cities["Odesa"], BASE + timedelta(days=1, hours=6)),
                ],
            ),
            (
                "Kharkiv → Dnipro Shuttle",
                Decimal("15.75"),
                buses[2],
                [
                    (cities["Kharkiv"], BASE + timedelta(days=2)),
                    (cities["Dnipro"], BASE + timedelta(days=2, hours=3)),
                ],
            ),
            (
                "Lviv → Krakow → Warsaw",
                Decimal("45.00"),
                buses[3],
                [
                    (cities["Lviv"], BASE + timedelta(days=3)),
                    (cities["Krakow"], BASE + timedelta(days=3, hours=4)),
                    (cities["Warsaw"], BASE + timedelta(days=3, hours=8)),
                ],
            ),
            (
                "Kyiv → Kharkiv Nightline",
                Decimal("22.00"),
                buses[0],
                [
                    (cities["Kyiv"], BASE + timedelta(days=4, hours=13)),
                    (cities["Kharkiv"], BASE + timedelta(days=4, hours=19)),
                ],
            ),
        ]

        trips: list[Trip] = []
        for name, price, bus, stops in trip_defs:
            trip = Trip(
                name=name,
                price=price,
                bus_id=bus.id,
                seats_left=bus.seats_quantity,
                route=_route(stops),
            )
            db.add(trip)
            db.commit()
            db.refresh(trip)
            trips.append(trip)

        # --- Orders in varied statuses -----------------------------------
        # 1) Paid order for the demo user (with a generated PDF ticket).
        _seed_order(
            db,
            trip=trips[0],
            user=demo_user,
            names=[("Ivan", "Petrenko", 34), ("Olena", "Petrenko", 31)],
            status=OrderStatus.paid,
        )
        # 2) Pending anonymous order.
        _seed_order(
            db,
            trip=trips[1],
            user=None,
            names=[("Guest", "Traveller", 27)],
            status=OrderStatus.pending,
        )
        # 3) Failed order (seats already restored -> not reserved).
        _seed_order(
            db,
            trip=trips[2],
            user=demo_user,
            names=[("Mykola", "Shevchuk", 45)],
            status=OrderStatus.failed,
        )

        log_event(
            logger,
            logging.INFO,
            "seed.done",
            cities=len(cities),
            buses=len(buses),
            trips=len(trips),
        )
        print(
            f"Seeded {len(cities)} cities, {len(buses)} buses, {len(trips)} trips, 3 orders.\n"
            "Admin login: admin@busapp.com / admin12345\n"
            "User  login: user@busapp.com  / user12345"
        )


def _seed_order(
    db,
    trip: Trip,
    user: User | None,
    names: list[tuple[str, str, int]],
    status: OrderStatus,
) -> None:
    seat_count = len(names)
    # Reserve seats for orders that hold them (pending/paid); a failed order
    # behaves as if seats were already restored.
    if status in (OrderStatus.pending, OrderStatus.paid):
        SeatsService(db).reserve(trip.id, seat_count)

    order = Order(
        trip_id=trip.id,
        user_id=user.id if user else None,
        status=status,
        price=trip.price * seat_count,
        passengers=_passengers(names, trip.price),
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    if status == OrderStatus.paid:
        try:
            order.ticket_pdf_key = generate_and_store_ticket(order, trip)
            db.commit()
        except Exception as exc:  # noqa: BLE001
            log_event(logger, logging.WARNING, "seed.ticket_failed", error=str(exc))


# --- Large randomised dataset (`--large`) -----------------------------------

# name, longitude, latitude
LARGE_CITIES: list[tuple[str, float, float]] = [
    ("Kyiv", 30.5234, 50.4501),
    ("Lviv", 24.0297, 49.8397),
    ("Odesa", 30.7233, 46.4825),
    ("Kharkiv", 36.2304, 49.9935),
    ("Dnipro", 35.0462, 48.4647),
    ("Vinnytsia", 28.4682, 49.2331),
    ("Zaporizhzhia", 35.1396, 47.8388),
    ("Ivano-Frankivsk", 24.7111, 48.9226),
    ("Ternopil", 25.5948, 49.5535),
    ("Chernivtsi", 25.9358, 48.2915),
    ("Poltava", 34.5514, 49.5883),
    ("Rivne", 26.2516, 50.6199),
    ("Uzhhorod", 22.2879, 48.6208),
    ("Warsaw", 21.0122, 52.2297),
    ("Krakow", 19.9450, 50.0647),
    ("Chisinau", 28.8575, 47.0105),
]

BUS_COLORS = [
    "#e11d48",
    "#2563eb",
    "#16a34a",
    "#f59e0b",
    "#7c3aed",
    "#0891b2",
    "#db2777",
    "#475569",
]
TRIP_SUFFIX = ["Express", "Coastliner", "Shuttle", "Nightline", "Intercity", "Direct", "Rapid"]
FIRST_NAMES = [
    "Ivan",
    "Olena",
    "Mykola",
    "Kateryna",
    "Andriy",
    "Sofia",
    "Petro",
    "Anna",
    "Taras",
    "Mariya",
    "Dmytro",
    "Yulia",
    "Oleh",
    "Iryna",
    "Serhiy",
    "Nadia",
]
LAST_NAMES = [
    "Petrenko",
    "Shevchenko",
    "Kovalenko",
    "Bondarenko",
    "Tkachuk",
    "Melnyk",
    "Boyko",
    "Kravets",
    "Oliynyk",
    "Marchenko",
    "Savchenko",
    "Rudenko",
]


def _seed_large(db, demo_user: User) -> None:
    """Generate a large, deterministic dataset for exercising the full app."""
    rng = random.Random(20260902)
    base = datetime(2026, 9, 3, 6, 0, 0)

    # --- Cities ------------------------------------------------------------
    cities: list[City] = []
    for name, lng, lat in LARGE_CITIES:
        city = City(name=name, longitude=lng, latitude=lat)
        db.add(city)
        cities.append(city)
    db.commit()
    for c in cities:
        db.refresh(c)

    # --- Buses (unique plates, best-effort photos) -------------------------
    n_buses = 30
    buses: list[Bus] = []
    for i in range(n_buses):
        color = rng.choice(BUS_COLORS)
        seats = rng.choice([24, 32, 40, 45, 50, 55])
        bus = Bus(color=color, seats_quantity=seats, number_plate=f"BX-{1000 + i}-UA")
        db.add(bus)
        db.commit()
        db.refresh(bus)
        try:
            from app.modules.buses.photos import process_and_upload

            photo_key, thumb_key = process_and_upload("image/png", _make_photo_png(color))
            bus.photo_key = photo_key
            bus.thumbnail_key = thumb_key
            db.commit()
        except Exception as exc:  # noqa: BLE001
            log_event(logger, logging.WARNING, "seed.photo_failed", error=str(exc))
        buses.append(bus)

    # --- Trips: many routes, dates, prices ---------------------------------
    n_trips = 220
    trips: list[Trip] = []
    for _ in range(n_trips):
        bus = rng.choice(buses)
        stop_cities = rng.sample(cities, rng.choice([2, 2, 2, 3, 3, 4]))
        depart = base + timedelta(
            days=rng.randint(0, 44), hours=rng.choice([5, 6, 7, 8, 9, 13, 15, 18, 21, 23])
        )
        stops: list[tuple[City, datetime]] = []
        when = depart
        for city in stop_cities:
            stops.append((city, when))
            when = when + timedelta(hours=rng.randint(2, 6))
        price = Decimal(str(rng.choice([12.5, 15, 18.75, 22, 25.5, 28, 32, 36.9, 40, 45, 52, 60])))
        name = f"{stop_cities[0].name} → {stop_cities[-1].name} {rng.choice(TRIP_SUFFIX)}"
        trip = Trip(
            name=name,
            price=price,
            bus_id=bus.id,
            seats_left=bus.seats_quantity,
            route=_route(stops),
        )
        db.add(trip)
        trips.append(trip)
    db.commit()
    for t in trips:
        db.refresh(t)

    # --- Extra customers so orders have varied owners ----------------------
    owners: list[User | None] = [demo_user]
    for i in range(15):
        owners.append(_ensure_user(db, f"traveller{i + 1}@example.com", "user12345", UserRole.user))

    # --- Orders in every status (paid/pending/failed, some anonymous) ------
    status_pool = [OrderStatus.paid] * 5 + [OrderStatus.pending] * 3 + [OrderStatus.failed] * 2
    counts = {"paid": 0, "pending": 0, "failed": 0}
    anonymous = 0
    n_orders = 150
    for _ in range(n_orders):
        trip = rng.choice(trips)
        owner = None if rng.random() < 0.25 else rng.choice(owners)
        n_pax = rng.randint(1, 4)
        names = [
            (rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES), rng.randint(6, 75))
            for _ in range(n_pax)
        ]
        status = rng.choice(status_pool)
        if status in (OrderStatus.pending, OrderStatus.paid) and not SeatsService(db).reserve(
            trip.id, n_pax
        ):
            # Trip sold out — record as a failed order that holds no seats.
            status = OrderStatus.failed

        order = Order(
            trip_id=trip.id,
            user_id=owner.id if owner else None,
            status=status,
            price=trip.price * n_pax,
            passengers=_passengers(names, trip.price),
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        if status == OrderStatus.paid:
            try:
                order.ticket_pdf_key = generate_and_store_ticket(order, trip)
                db.commit()
            except Exception as exc:  # noqa: BLE001
                log_event(logger, logging.WARNING, "seed.ticket_failed", error=str(exc))

        counts[status.value] += 1
        if owner is None:
            anonymous += 1

    log_event(
        logger,
        logging.INFO,
        "seed.done_large",
        cities=len(cities),
        buses=len(buses),
        trips=len(trips),
        orders=n_orders,
    )
    print(
        f"Seeded (large) {len(cities)} cities, {len(buses)} buses, {len(trips)} trips, "
        f"{n_orders} orders "
        f"(paid={counts['paid']}, pending={counts['pending']}, failed={counts['failed']}, "
        f"anonymous={anonymous}), {len(owners)} customers.\n"
        "Admin login: admin@busapp.com / admin12345\n"
        "User  login: user@busapp.com  / user12345"
    )


if __name__ == "__main__":
    configure_logging()
    seed(force="--force" in sys.argv, large="--large" in sys.argv)
