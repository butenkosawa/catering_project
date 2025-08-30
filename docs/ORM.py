from dataclasses import dataclass
from datetime import date
from pprint import pprint as print

import psycopg

connection_payload = {
    "dbname": "catering",
    "user": "parfeniukink",
    "password": "pass",
    "host": "localhost",
    "port": 5432,
}


class DatabaseConnection:
    def __enter__(self):
        self.conn = psycopg.connect(**connection_payload)
        self.cur = self.conn.cursor()

        return self

    def __exit__(self, exc_type, *_):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()

        self.cur.close()
        self.conn.close()

    def query(self, sql: str, params: tuple | None = None):
        self.cur.execute(sql, params or ())
        return self.cur.fetchall()


@dataclass
class User:
    name: str
    phone: str
    role: str
    id: int | None = None

    @classmethod
    def all(cls) -> list["User"]:
        """return all the users from `users` table."""

        with DatabaseConnection() as db:
            rows = db.query("SELECT name, phone, role, id FROM users")
            return [cls(*row) for row in rows]

    @classmethod
    def filter(cls, **filters) -> list["User"]:
        """return filtered users from `users` table."""

        keys = filters.keys()
        conditions = " AND ".join([f"{key} = %s" for key in keys])
        values = tuple(filters.values())

        with DatabaseConnection() as db:
            rows = db.query(
                f"SELECT name, phone, role, id FROM users WHERE {conditions}",
                values,
            )
            return [cls(*row) for row in rows]

    @classmethod
    def get(cls, **filters) -> "User":
        """return filtered users from `users` table."""

        keys = filters.keys()
        conditions = " AND ".join([f"{key} = %s" for key in keys])
        values = tuple(filters.values())

        with DatabaseConnection() as db:
            rows = db.query(
                f"SELECT name, phone, role, id FROM users WHERE {conditions}",
                values,
            )
            name, phone, role, id = rows[0]

            return cls(id=id, name=name, phone=phone, role=role)

    def create(self) -> "User":
        with DatabaseConnection() as db:
            db.cur.execute(
                "INSERT INTO users (name, phone, role) VALUES (%s, %s, %s) RETURNING id",
                (self.name, self.phone, self.role),
            )
            # NOTE: actually bad practice to mutate `self` instance from here

            self.id = db.cur.fetchone()[0]

            return self

    def update(self, **payload) -> "User | None":
        fields = ", ".join([f"{key} = %s" for key in payload])
        values = tuple(payload.values())

        # ensure id exists
        if self.id is None:
            raise ValueError("Can not update user without ID")

        with DatabaseConnection() as db:
            db.cur.execute(
                f"UPDATE users SET {fields} WHERE id = %s RETURNING id, name, phone, role",
                (*values, self.id),
            )

            row = db.cur.fetchone()

        if not row:
            return None
        else:
            _, name, phone, role = row
            self.name = name
            self.phone = phone
            self.role = role

            return self

    @classmethod
    def delete(cls, id: int) -> bool:
        with DatabaseConnection() as db:
            db.cur.execute("DELETE FROM users WHERE id = %s RETURNING id", (id,))
            return db.cur.fetchone() is not None


@dataclass
class Dish:
    name: str
    price: float
    id: int | None = None

    @classmethod
    def all(cls) -> list["Dish"]:
        with DatabaseConnection() as db:
            rows = db.query("SELECT name, price, id FROM dishes")
            return [cls(*row) for row in rows]

    @classmethod
    def filter(cls, **filters) -> list["Dish"]:
        keys = filters.keys()
        conditions = " AND ".join([f"{key} = %s" for key in keys])
        values = tuple(filters.values())

        with DatabaseConnection() as db:
            rows = db.query(
                f"SELECT name, price, id FROM dishes WHERE {conditions}",
                values,
            )
            return [cls(*row) for row in rows]

    @classmethod
    def get(cls, **filters) -> "Dish":
        keys = filters.keys()
        conditions = " AND ".join([f"{key} = %s" for key in keys])
        values = tuple(filters.values())

        with DatabaseConnection() as db:
            rows = db.query(
                f"SELECT name, price, id FROM dishes WHERE {conditions}",
                values,
            )
            name, price, id = rows[0]
            return cls(name=name, price=price, id=id)

    def create(self) -> "Dish":
        with DatabaseConnection() as db:
            db.cur.execute(
                "INSERT INTO dishes (name, price) VALUES (%s, %s) RETURNING id",
                (self.name, self.price),
            )
            self.id = db.cur.fetchone()[0]
        return self

    def update(self, **payload) -> "Dish | None":
        fields = ", ".join([f"{key} = %s" for key in payload])
        values = tuple(payload.values())
        if self.id is None:
            raise ValueError("Can not update dish without ID")
        with DatabaseConnection() as db:
            db.cur.execute(
                f"UPDATE dishes SET {fields} WHERE id = %s RETURNING id, name, price",
                (*values, self.id),
            )
            row = db.cur.fetchone()
        if not row:
            return None
        else:
            _, name, price = row
            self.name, self.price = name, price
            return self

    @classmethod
    def delete(cls, id: int) -> bool:
        with DatabaseConnection() as db:
            db.cur.execute("DELETE FROM dishes WHERE id = %s RETURNING id", (id,))
            return db.cur.fetchone() is not None


@dataclass
class Order:
    date: date
    total: float
    status: str
    user_id: int
    id: int | None = None

    @classmethod
    def all(cls) -> list["Order"]:
        with DatabaseConnection() as db:
            rows = db.query("SELECT date, total, status, user_id, id FROM orders")
            return [cls(*row) for row in rows]

    @classmethod
    def filter(cls, **filters) -> list["Order"]:
        keys = filters.keys()
        conditions = " AND ".join([f"{key} = %s" for key in keys])
        values = tuple(filters.values())

        with DatabaseConnection() as db:
            rows = db.query(
                f"SELECT date, total, status, user_id, id FROM orders WHERE {conditions}",
                values,
            )
            return [cls(*row) for row in rows]

    @classmethod
    def get(cls, **filters) -> "Order":
        keys = filters.keys()
        conditions = " AND ".join([f"{key} = %s" for key in keys])
        values = tuple(filters.values())

        with DatabaseConnection() as db:
            rows = db.query(
                f"SELECT date, total, status, user_id, id FROM orders WHERE {conditions}",
                values,
            )
            date_val, total, status, user_id, id = rows[0]
            return cls(
                date=date_val, total=total, status=status, user_id=user_id, id=id
            )

    def create(self) -> "Order":
        with DatabaseConnection() as db:
            db.cur.execute(
                "INSERT INTO orders (date, total, status, user_id) VALUES (%s, %s, %s, %s) RETURNING id",
                (self.date, self.total, self.status, self.user_id),
            )
            self.id = db.cur.fetchone()[0]
        return self

    def update(self, **payload) -> "Order | None":
        fields = ", ".join([f"{key} = %s" for key in payload])
        values = tuple(payload.values())
        if self.id is None:
            raise ValueError("Can not update order without ID")
        with DatabaseConnection() as db:
            db.cur.execute(
                f"UPDATE orders SET {fields} WHERE id = %s RETURNING id, date, total, status, user_id",
                (*values, self.id),
            )
            row = db.cur.fetchone()
        if not row:
            return None
        else:
            _, date_val, total, status, user_id = row
            self.date, self.total, self.status, self.user_id = (
                date_val,
                total,
                status,
                user_id,
            )
            return self

    @classmethod
    def delete(cls, id: int) -> bool:
        with DatabaseConnection() as db:
            db.cur.execute("DELETE FROM orders WHERE id = %s RETURNING id", (id,))
            return db.cur.fetchone() is not None


# SELECT ALL USERS FROM USERS TABLE
# ---------------------------------------
# users = User.all()
# print(users)

# FILTER USERS
# ---------------------------------------
# users: list[User] = User.filter(role="USER", id=1)
# print(users)

# RETRIEVE USER
# ---------------------------------------
# user: User = User.get(id=2)
# print(user)

# CREATE USER
# ---------------------------------------
# mark = User(name="Mark", phone="+380973334478", role="USER")
# print(f"Before creation {mark}")

# mark.create()
# print(f"After creation {mark}")


# UPDATE USER
# ---------------------------------------
# mark = User.get(name="Mark")
# mark.update(role="ADMIN")
# print(mark)

# DELETE USER
# ---------------------------------------
# User.delete(id=3)
# print(User.all())


print(Dish.all())
