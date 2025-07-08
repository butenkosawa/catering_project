# About Databases

- RDBMS - relations database management systems - tables:
  [
  ["id", "name", "last_name"],
  [1, "John", "Doe", '...'],
  [2, "Marry", "Black"],
  ]
- Non-RDBMS - non-relational database management systems
  - {...}

# Database Purposes

- storing data (persistance)
- providing an organizational structure of data
- providing a mechanism for querying, creating, modifying and deleting data (CRUD)
  - CRUDService, DALService, Repository

# Issues

1 Normal Form

| id  | name  | age | passport id      | address | product | price | order |
| --- | ----- | --- | ---------------- | ------- | ------- | ----- | ----- |
| 1   | John  | 45  | 388801           | NYC     | A, B    | 20$   | 33231 |
| 2   | Marry | 30  | 388802           | LA      | C       | 30$   | 33232 |
| 3   | Mark  | 40  | 388803           | NYC     | A       | 10$   | 33233 |
| 4   | John  | 45  | 388802 (mistake) | NYC     | C       | 30$   | 33234 |

Normalize

Users

| id  | name  | age | passport id | address |
| --- | ----- | --- | ----------- | ------- |
| 1   | John  | 20  | 388801      | NYC     |
| 2   | Marry | 30  | 388802      | LA      |
| 3   | Mark  | 40  | 388803      | NYC     |
| 4   | John  | 45  | 388802      | NYC     |

Products

| id  | product | price |
| --- | ------- | ----- |
| 1   | A       | 10$   |
| 2   | B       | 20$   |
| 3   | C       | 30$   |

Orders

| id  | user id | products |
| --- | ------- | -------- |
| 1   | 1       | 1, 2     |
| 2   | 2       | 3        |
| 3   | 3       | 2        |
| 4   | 1       | 3        |

# Glossary (RDBMS)

- `TABLE`, file, relation - is 2-demantional grid of data
- `COLUMN`, field, attribute - represent different ATTRIBUTES in `ENTITY`
- `ROW`, record, (tuple rarely) - represent INSTANCE of an `ENTITY`
- `NULL VALUE`, nothing, empty - represent the situation when there is no data in CELL (grid address space)

# What kind of problem do we solve in real world?

ISSUE

- customer could create MANY orders in the SYSTEM
- marketing department could include employees but and employee is related only to a single department

SOLUTION

- we have to store information somewhere
- we create structure for this data
- first iteration would be - having "a list of data" to represent in CSV

> RULE: PROBLEM IS NOT ABOUT HOW DO WE STORE INFORMATION
> PROBLEM IS WHAT IS HAPPEN TO THE INFORMATION

# RDBMS

stores information in TABLES. Each information theme (or business concept) has its own table

- customers, projects, managers, orders, ...

ISSUE: how to gather data from different tables?
SOLUTION: JOIN data from different tables

## about Database System

- USERS - real people
  - use 'database application' to keep track of information
  - use different interfaces to enter, read, delete and query data
  - produce reports, ...
- DATABASE APPLICATION - Python client, Table Plus, ...
- DATABASE MANAGEMENT SYSTEM - software, that exposes the dastabase itself (postgresql, mysql)
- DATABASE (DB)
  - self-describing collection of related records
    - knows about its structure (described in METADATA)
  - tables within a RDB are related to each other in some way

call hierarchy: user -> database application -> DBMS -> DB

### Database Contents

- user data
- metadata
- indexes, and overhead data
- application metadata

### About RDBMS

- manage and control database activities
- creates, process, administrate the database

functions of RDMBS:

- create database
- create tables
- create suporting structures
- read data from database
- modify database data (insert, update, delete)
- enforce rules (to regulate and control)
- control concurrency
- provide security (additional layer to secure the data and connection)
- perform backup and data recovery

### Integrity Constraitns


## Relational Model

TOPICS
- how relations differ from non-relational tables
- entity, keys, foreign keys, other
- keys:
    - foreign keys
    - surrogate keys
- functional dependencies
- normalization


### characteristics of a RELATION

- rows are instances
- columns are attributes
- cells - single value
- all values in the same column has the same KIND (data type)
- each column has UNIQUE name
- the order of columns and rows is NOT important
- 2 rows CAN NOT be identical (if you have similar ids for records)

### what is ENTITY?

- is something of importance to a user or organization that needs to be represented in the database
- represents the theme, topic, or business concept
- in the RELATIONAL MODEL ENTITIES are restricted to things that can be represented using a single table


### what are KEYS?

a key is ONE (or MORE) columns of relations whose values are used to identify the row.

1. UNIQUE KEY - data values is unique for each row
    - Candidate Key
    - Composite Key
        - compose 2 or more columns for the uniqness
        - John -> NYC -> XXXYYY
            - XXXYYY
            - departure_time
    - Primary Key
    - Surrogate Key (ID)
2. NONUNIQUE KEY - data values can be shared among several rows
    - Foreign Key
