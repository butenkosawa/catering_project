# Project Setup

> Ensure that you have `pipenv` insatlled on your system.
>
> `pipx install pipenv`

```shell
pipenv shell  &&  pipenv sync

# load test data into your database
python manage.py loaddata fixtures/dump.json

# dump database data to the JSON file
python manage.py dumpdata --natural-primary --natural-foregin --indent 2> tmp/dump.json

```

<br>

<br>

---

# IDEA

- Users Management
  - user registration (username, email, password, delivery address, phone)
  - user profile management
  - user roles management (admin, manager, customer, driver)
- Authentication / Authorization
  - JWT (JSON Web Token) for secure token authentication
- Menu and Dishes Management
  - admin can add, edit, delete dishes
  - V2, display dishes recommendations, based on user's orders
- Orders Management
  - Scheduling Orders (based on datetime and address)
  - Order status is updating ia a background
    - PROCESSING
    - ON THE WAY
    - CANCELLD
    - DELIVERED
  - V2, Track courier on the Map
- Payment System
  - ...
- Communication & Feedback
  - V2, Support System
  - V2, Communication with driver, after order is ON THE WAY
  - Rate: stars for restaurants and drivers after order is DELIVERED
- Notifications
  - ## Notify after order is DELIVERED

# BACKLOG FOR "KANBAN" TICKETS

- USERS MANAGEMENT (CRUD for `/users`) - EPIC
  - Endpoints to implement
    - User STORY (from Jira)
      - `HTTP POST /users` - create user -> `201 User`, [CUSTOMER, DRIVER]
      - `HTTP PUT /users` - update user information -> `200 User`, [ALL]
      - `HTTP GET /users` - update user information -> `200 User`, [ALL]
      - `HTTP DELETE /users` - delete user from system -> `204 null`, [CUSTOMER, DRIVER]
      - `HTTP POST /users/password/forgot` -> [KEY[UUID]]
      - `HTTP GET /users/password/reset?key={UUID}`
  - Roles:
    - `ADMIN`
    - `MANAGER`
    - `DRIVER`
    - `CUSTOMER`
- AUTHORIZATION
  - `HTTP POST /token` - create access token -> `200 Token` [ALL]
- DISHES MANAGEMENT
  - Endopints (CRUD)
    - `HTTP POST /dishes` - create a new dish [ADMIN, MANAGER]
    - `HTTP GET /dishes` - list of all dishes [ADMIN, MANAGER, CUSTOMER]
    - `HTTP GET /dishes/<ID>` - get a concrete DISH [ADMIN, MANAGER, CUSTOMER]
    - `HTTP PUT /dishes/<ID>` - update a concrete DISH [ADMIN, MANAGER]
    - `HTTP DELETE /dishes/<ID>` - delete a concrete DISH [ADMIN, MANAGER]
  - Refresh data from restaurant
    - as a separate `Thread(daemon=True)`
  - Show recommendations (V2)
- ORDERS MANAGEMENT
  - Endopints (CRUD)
    - `HTTP POST /orders` - create a new order [CUSTOMER]
      - request body: `{ dishes: DishOrder[] }`
    - `HTTP GET /orderes` - list of all orders [ADMIN, MANAGER]
    - `HTTP GET /orderes/<ID>` - get a concrete order [ADMIN, MANAGER, CUSTOMER]
    - `HTTP PUT /orderes/<ID>` - update a concrete order [ADMIN, MANAGER, CUSTOMER]
    - `HTTP PATCH /orderes/<ID>` - partially update a concrete order [ADMIN, MANAGER, CUSTOMER]
    - `HTTP DELETE /orderes/<ID>` - delete a concrete order [ADMIN, MANAGER]
    - `HTTP POST /orders/<ID>/reorder` - reorder order [CUSTOMER]
      - create a brand new order in the system

# PROJECT DECISIONS

- Package Managers
  - brew
  - apt
  - apt-get
  - yum
  - choco
- Virtualenv management tools
  - `virtualenv`
  - `pipenv`
  - `poetry`
  - `uv`
- Virtualization
  - Machine
  - `chown`
  - `chroot`
  - `namespaces` + `cgroups`
  - Virtual Machines (Type 2)
    - Virtual Box
    - VMWare Workstation
    - Parallels
  - Virtual Machines (Type 1)
    - Huper-V
      - Guest OS
    - KVM
- Containers
  - Docker

# DJANGO

- 2003, 2005 release
- Django Software Foundation
- All-in (ORM, Admin Panel, DTL)
- Stable
- Secutiry
- no Async ORM

Alternatives

- FastAPI (Starlette-based)
  - pydantic
  - SQLAlchemy (allows async)
- Flask
  - pydantic
  - SQLAlchemy (allows async)
- Laravel, Express, Ruby on Rails, Spring Boot, Symphony


## Basics about Web

- CLI -> Web. Difference?
  - in CLI - User works in Terminal
  - in Web - HTTP Request
  - in CLI we use `input()`
    - COMMANDS
  - in Web we use `HTTP ENDPOINT / HTTP PATH / URL / ...`
    - HTTP CLIENT
- To implement Web interaction
  - HTTP Server (Django)

# REST API Building Blocks

- API Endpoints (Presentation Layer)
  - Understand the CLIENT
  - Resources Consistent System
  - Errors Handling
    - 1.x.x - ...
    - 2.x.x - SUCCESS
    - 3.x.x - REDIRECTS
    - 4.x.x - USER ERRORS
    - 5.x.x - SERVER ERRORS
- Application Structure (Operational, Domain, Infrastructure)
  - Vertical Structure vs Horizontal Structure
    - Vertical - feature-first
      - users
        - endpoints
        - structures
        - model (business logic)
      - orders
        - endpoints
        - structures
        - model (business logic)
      - delivery
        - endpoints
        - structures
        - model (business logic)
    - Horizontal - function-first
      - endpoints
        - users
        - orders
        - delivery
      - structures
        - users
        - orders
        - delivery
      - model (business logic)
        - users
        - orders
        - delivery
- Project Configuration
  - Environment Variables via `.env`
- Dependencies Management
  - `pipenv`
- Code Delivery and Code Quality
  - CI/CD (Github Action)

## Django and DRF

- What is REST API with DRF
  - Stateless
  - Resources-based (nouns)
  - HTTP Methods (...) (verbs)
  - Status Code (aka lables)
- Files Structure
  - `config/`
  - `core/`
  - `users/`
  - `orders/`
  - `delivery/`
  - `.env`
  - `Pipfile`
- DRF Concepts
  - Routes & URLs - for endpoints declaration
  - Views (CBV, FBV)
    - ViewSet - deinfe resource root
    - Custom `@action` for custom endpoints
  - Serializers
    - Data validation & data transformation
    - User for all input/output structures
  - Permissions and Authorization layer
