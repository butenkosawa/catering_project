# SQL

- Structured Query Language
- IBM - 1970
- "sequel" or "S Q L"
- based on relational algebra
  - `AND`, `OR`, `XOR` operations with attributes values, etc
- SQL is declarative ("what to get," not "how to get it")

---

# SQL Keywods

## SELECT - query to get data

- `SELECT * from table WHERE id in (4,5,6);`
-
- `SELECT DISTINCT FROM table;`
-
- `SELECT * FROM table WHERE id BETWEEN 1 AND 10;`
-
- `SELECT * FROM table WHERE id>1 AND id<10;`
-
- `SELECT * FROM table WHERE name LIKE 'Da%'`
-
- `SELECT * FROM table WHERE name LIKE '657-268-____'`

---

# SQL Keywods

## ORDER BY - sorting/ordering

- `SELECT * from table ORDER BY id ASC`
- `SELECT * from table ORDER BY id DESC`

<br>

## GROUP BY - grouping data

- `SELECT id, COUNT(*) AS total FROM table GROUP BY id;`

<br>

## HAVING - filter for GROUP BY

- `SELECT id, name, SUM(amount) AS total FROM table GROUP BY id, name HAVING SUM(amount) > 1000;`

---

# SQL Keywods

## DROP - remove objects and assisiations

- `DROP TABLE users'` - remove the whole table
-
- `ALTER TABLE users DROP CONSTRAINT userFk` - remove the constraint with Foreign Key

<br>

## CHECK - constraint for restriction

- _can be used to create restrictions on the values that are allowed to appear in a column_
- `ALTER TABLE project ADD CONSTRAINT projectCheckDates CHECK (startDate < endDate);`

---

# Functions

- `SELECT MIN(hours) AS minHours FROM table WHERE id>7;`
-
- `SELECT MAX(hours) AS maxHours FROM table WHERE id>7;`
-
- `SELECT SUM(id) AS totalIds FROM table WHERE id>7;`
-
- `AVG` - calculates the numerical average (mean) of a specific column for those rows matching the criteria
-
- `STDEV` - standard deviation of the values in a numeric columnm

---

# Retrieve Information From Multiple Tables

## using subqueries

- NON CORRELATED subquery
  - `SELECT name FROM table_1 WHERE id IN (SELECT id FROM table_2 WHERE name LIKE 'Viewer%');`
-
- CORRELATED subquery
  - `SELECT e.name FROM employee as e WHERE salary > (SELECT AVG(salary) FROM employee WHERE departmentId=e.id);`

## JOINs

| Join Type    | Description                                     | Example                            |
| ------------ | ----------------------------------------------- | ---------------------------------- |
| `INNER JOIN` | Returns only **matching** rows                  | Orders with Customers              |
|              |                                                 |                                    |
|              |                                                 |                                    |
| `LEFT JOIN`  | Returns **all** from left + matching from right | All Customers, even without Orders |
|              |                                                 |                                    |
|              |                                                 |                                    |
| `RIGHT JOIN` | Returns **all** from right + matching from left | All Orders, even without Customers |
|              |                                                 |                                    |
|              |                                                 |                                    |
| `FULL JOIN`  | Returns **all** rows, even if there's no match  | Every record from both tables      |
|              |                                                 |                                    |
|              |                                                 |                                    |
| `CROSS JOIN` | Returns **every combination** of both tables    | All menu items + All ingredients   |

<br>

- `SELECT orders.id, users.name from orders LEFT JOIN users ON orders.user_id = users.id;`

---

# SQL Views

- SQL View is a virtual table, created by a DMBS-stored SELECTED statement
- combine access to data in multiple tables and even in other views

```sql
-- definition
CREATE view SalesDepartment AS
SELECT *
FROM employee
WHERE deptId = (SELECT deptId FROM department WHERE deptName = 'Sales');


-- usage
select empName from SalesDepartment;
```

---

# Data Modeling & the ER Model

- designing data models (E-R) (**_ENTITY Relationship Diagram_**)
- 1:1, 1:N, N:N

<br>

<br>

## 1:N (One-to-Many)

- Based on Foreign Key

`user_orders table`

| order_id                             | user_id   |
| ------------------------------------ | --------- |
| d5dbfb18-66cd-44fe-8480-9d88f135a9f7 | 1         |
| 17fe7574-791b-4907-b9bf-5faef9c14f8f | 2         |
| acd19487-68e7-4a0a-980e-39021e97d44c | 1 (again) |

<br>

<br>

## 1:1 (One-to-One)

- Restriction in Foreign Key

`users table`

| id  | profile_id |
| --- | ---------- |
| 1   | 12         |
| 2   | 13         |
| 3   | 12 (error) |

---

## N:N (Many-to-Many)

**Users** can place multiple **Orders**, and each order can include dishes from multiple Restaurants (via an order-restaurant junction table).

`users table`

| id  | name  |
| --- | ----- |
| 1   | John  |
| 2   | Marry |

`products table`

| id  | name   |
| --- | ------ |
| 1   | Cake   |
| 2   | Coffee |
| 3   | Salad  |

`orders table`

| id                                   | user_id |
| ------------------------------------ | ------- |
| ca1b5e55-3af1-4098-9b72-2629eb636c47 | 1       |
| f6f93a0d-2666-4657-9993-e0706cf9e53a | 2       |

`order_products table`

| id  | order_id                             | product_id | quantity |
| --- | ------------------------------------ | ---------- | -------- |
| 1   | ca1b5e55-3af1-4098-9b72-2629eb636c47 | 1          | 1        |
| 2   | ca1b5e55-3af1-4098-9b72-2629eb636c47 | 2          | 2        |
| 3   | f6f93a0d-2666-4657-9993-e0706cf9e53a | 2          | 1        |
| 4   | f6f93a0d-2666-4657-9993-e0706cf9e53a | 3          | 2        |

---

# PRACTICE

## Scenario:

- Imagine a simplified scenario where our **CATERING SERVICE** manages Orders, Dishes, and Users
- Then, we have the following tables:
  - `users`: `id`, `name`, `phone`, `role` (ADMIN, USER, SUPPORT)
  - `dishes`: `id`, `name`, `price`
  - `orders`: `id`, `user_id`, `date`, `total`, `status` (PENDING, PROCESSING, DELIVERED, CANCELLED)
  - `order_items` `id`, `order_id`, `dish_id`, `quantity`

`users`

| id  | name  | phone         | role    |
| --- | ----- | ------------- | ------- |
| 1   | admin | +380974438976 | ADMIN   |
| 2   | john  | +380974438987 | USER    |
| 3   | marry | +380971938981 | SUPPORT |

`dishes`

| id  | name   | price |
| --- | ------ | ----- |
| 1   | Coffee | 5$    |
| 2   | Soda   | 3$    |
| 3   | Salad  | 8$    |

`orders`

| id  | user_id | date       | total | status    |
| --- | ------- | ---------- | ----- | --------- |
| 1   | 2       | 30-06-2025 | 13$   | PENDING   |
| 1   | 2       | 30-05-2025 | 10$   | DELIVERED |

`order_items`

| id  | order_id | dish_id | quantity |
| --- | -------- | ------- | -------- |
| 1   | 1        | 1       | 1        |
| 2   | 1        | 3       | 1        |

