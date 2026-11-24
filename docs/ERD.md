# Implemented entity relationship diagram

Printable submission copy: [complete ER diagram PDF](submission/ER_Diagram.pdf), split into three landscape views for readability. It covers all 10 application tables, 62 columns and 12 foreign keys. PK/FK markers, nullable references and a cardinality legend are included.

The original proposal's junction tables and resource registry are implemented.
The diagram below corrects the source diagram's simplified relationship between
USER_ROLE and ROLE_PERMISSION: both refer to ROLE independently. Session and
security-event tables support authentication rather than application policy.

```mermaid
erDiagram
    APP_USER ||--o{ USER_ROLE : receives
    APP_USER ||--o{ USER_ROLE : assigns
    ROLE ||--o{ USER_ROLE : assigned_as
    ROLE ||--o{ ROLE_PERMISSION : contains
    PERMISSION ||--o{ ROLE_PERMISSION : grants
    APP_USER ||--o{ RESOURCE : owns
    APP_USER o|--o{ AUDIT_EVENT : requests
    RESOURCE o|--o{ AUDIT_EVENT : evaluated_for
    ROLE o|--o{ AUDIT_EVENT : matches
    APP_USER ||--o{ POLICY_CHANGE : administers
    APP_USER ||--o{ LOGIN_SESSION : authenticates
    APP_USER o|--o{ SECURITY_EVENT : identified_as
    APP_USER {
        int id PK
        varchar name
        varchar email UK
        text password_hash
        boolean active
        timestamptz created_at
        timestamptz updated_at
    }
    ROLE {
        int id PK
        varchar name UK
        varchar description
        varchar kind
        boolean active
    }
    PERMISSION {
        int id PK
        varchar action "unique with resource_type"
        varchar resource_type
    }
    USER_ROLE {
        int user_id PK,FK
        int role_id PK,FK
        int assigned_by FK
        timestamptz assigned_at
        boolean active
    }
    ROLE_PERMISSION {
        int role_id PK,FK
        int permission_id PK,FK
    }
    RESOURCE {
        int id PK
        varchar resource_type "unique with resource_key"
        varchar resource_key
        varchar name
        int owner_user_id FK
        boolean active
    }
    AUDIT_EVENT {
        uuid id PK
        int actor_user_id FK
        varchar actor_email "historical snapshot"
        varchar action
        int resource_id FK
        varchar resource_type "historical snapshot"
        varchar resource_key "historical snapshot or missing ID"
        varchar decision
        varchar reason_code
        int matching_role_id FK
        varchar matching_role_name "historical snapshot"
        uuid request_id "unique with actor_user_id"
        timestamptz occurred_at
    }
    POLICY_CHANGE {
        uuid id PK
        int actor_user_id FK
        varchar actor_email
        varchar target_type
        varchar target_id
        varchar operation
        jsonb details
        uuid request_id
        timestamptz occurred_at
    }
    LOGIN_SESSION {
        varchar token_hash PK
        int user_id FK
        varchar csrf_token
        timestamptz created_at
        timestamptz expires_at
    }
    SECURITY_EVENT {
        int id PK
        int actor_user_id FK
        varchar email
        varchar ip_hash
        varchar operation
        uuid request_id
        timestamptz occurred_at
    }
```

All live references use PostgreSQL foreign keys with default NO ACTION deletion
behavior. The application deactivates records and revokes assignments; it never
deletes a user, role, resource, or audit record. A policy target is a historical
identifier rather than a polymorphic foreign key: JSON details capture removed
mappings after their deletion. All ten tables and both views are represented in
the data dictionary.
