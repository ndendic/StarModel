**StarModel Project Manifest – Extended Edition (v 2025‑06‑16)**

---

\## 🌟 Philosophy & North‑Star Goals

> **“Write an Entity once → get database, API, and live UI for free.”**

StarModel is a Python‑first, *entity‑centric* web framework. We merge the instant‑CRUD magic of Django Admin & Frappe with the real‑time feel of LiveView/HTMX—all in **pure Python** and **without front‑end build tooling**.

\### Guiding Principles

1. **Entity First** – Data **and** behavior live together in a single class; developers declare `@event` methods, not controllers.
2. **Opinionated On‑Ramp, Pluggable Runway** – FastHTML + MonsterUI + SQLite get you an MVP in minutes; every layer can be swapped via adapters.
3. **Progressive Disclosure** – Hello‑world in < 30 lines; advanced teams can override routing, persistence, UI, or background tasks without rewrites.
4. **Clean‑Architecture Core** – Domain logic is isolated from web, DB, or JS; ports‑and‑adapters keep tech choices swappable.
5. **Hybrid Persistence** – Each Entity chooses its own store: in‑memory, Redis, SQL, browser storage, or any custom backend.

---

\## 🏛️ Core Architecture (Top‑Down)

```
 ┌────────────── PRESENTATION (adapters) ───────────────┐
 │ FastHTML routes │ REST / GraphQL (opt) │ CLI │ …     │
 └────────────┬────────────┬────────────┬───────────────┘
              │            │            │
   🔄 Datastar / SSE / WS  │            │
              ▼            ▼            ▼
 ┌──────────────────────────────────────────────────────┐
 │              APPLICATION SERVICE LAYER               │
 │  • Event dispatcher  • Unit‑of‑Work  • EventBus      │
 └────────────┬────────────┬────────────┬───────────────┘
              │ emits DomainEvents│            │
              ▼            ▼            ▼
 ┌──────────────────────────────────────────────────────┐
 │                 DOMAIN  (Entities)                   │
 │  • Entity (Pydantic/SQLModel)  • @event methods      │
 │  • Value objects  • pure domain services             │
 └────────────┬────────────┬────────────┬───────────────┘
              │            │            │
              ▼            ▼            ▼
 ┌─────────────── INFRASTRUCTURE ADAPTERS ──────────────┐
 │ MemoryRepo │ RedisRepo │ SQLRepo (FastSQLModel) │ …  │
 └──────────────────────────────────────────────────────┘
```

\### Key Patterns & How They Map

| Pattern / Concept                            | Why we use it                                            | Where it lives                      |
| -------------------------------------------- | -------------------------------------------------------- | ----------------------------------- |
| **Entity = immutable snapshot** (`evolve()`) | Simpler diffing, undo/redo, concurrency‑safe             | `starmodel.core.entity`             |
| \`\`\*\* decorator\*\* (plain function)      | Zero boilerplate; runtime metadata → same DX as your PoC | `starmodel.core.events`             |
| **Synthetic Command Record**                 | Allows queueing/replay: `{entity, event, args}`          | Dispatcher serialises automatically |
| **Unit‑of‑Work**                             | One commit/rollback; flush DomainEvents                  | `starmodel.app.uow`                 |
| **Pluggable EventBus**                       | SSE fan‑out, WebSocket, AMQP, etc.                       | `starmodel.app.bus`                 |
| **Repository adapters**                      | Memory, Redis, SQLModel, etc. via interface              | `starmodel.adapters.persistence.*`  |

> **Note:** Frames stay identical if we later add dataclass‑commands—the dispatcher just bypasses `inspect`.

---

\## 🔧 Default Stack (v0.1)

| Layer       | Default Choice                          | How to Swap                                  |
| ----------- | --------------------------------------- | -------------------------------------------- |
| Web Engine  | **FastHTML** (Starlette core)           | Any ASGI via router adapter                  |
| UI Kit      | **MonsterUI** (Tailwind components)     | Other FastHTML kit or React via REST adapter |
| ORM / Table | **SQLModel + BaseTable** (FastSQLModel) | Tortoise / PonyORM / custom SQLAlchemy       |
| DB Engine   | **SQLite**                              | Postgres, MySQL via URL or alt repo          |
| Cache       | **Server Memory**                       | Redis via `RedisStatePersistence`            |
| Realtime    | **Datastar (SSE)**                      | WebSocket plugin (Phase 4)                   |
| Auth        | **FastHTML‑Auth simple**                | OAuth, AzureAD plugin                        |
| CLI         | `starmodel`: `init`, `run`              | New commands via entry‑point plugins         |

\### Per‑Entity Persistence Examples

```python
class Cart(Entity):
    items: list[Item] = []
    model_config = {"store": StateStore.SERVER_REDIS, "ttl": 7200}

# SQL‑backed (inherits BaseTable for full‑relational storage)
class BlogPost(Entity, BaseTable, table=True):
    title: str
    body: str
    model_config = {"store": StateStore.CUSTOM, "auto_persist": True}
```

---

\## 🛤️ Development Roadmap

| Phase                        | Deliverables                                                                 | Exit Test                                        |
| ---------------------------- | ---------------------------------------------------------------------------- | ------------------------------------------------ |
| **P0 Spike**                 | `@event` API + Memory repo + Datastar live counter                           | Two tabs show counter sync                       |
| **P1 MVP Core**              | Immutable Entity + Dispatcher w/ `inspect` + CLI `init/run` + MonsterUI CRUD | `starmodel init demo` → CRUD works live          |
| **P2 Pluggable Persistence** | Redis repo; SQLModel adapter; CLI `migrate`; registry                        | Hybrid Redis+SQL sample passes tests             |
| **P3 Plugin Framework**      | Entry‑point loader; Admin UI alpha; Auth plugin                              | Third‑party plugin adds route w/out core changes |
| **P4 Prod Harden**           | Task queue; WebSocket option; health/metrics                                 | 3‑node docker‑compose sync demo                  |
| **P5 Visual Builder**        | Metadata entity creator; drag‑drop UI                                        | Non‑dev adds `Event` entity via browser          |

---

\## 🔑 Persistence Layer

| Adapter              | Use‑case                 | Key Details                         |
| -------------------- | ------------------------ | ----------------------------------- |
| Memory               | Dev, ephemeral           | TTL cleanup task                    |
| Redis                | Cross‑node session/state | JSON keys `starmodel:{class}:{id}`  |
| SQLModel (BaseTable) | Durable data             | Alembic migrations via FastSQLModel |
| Client Session/Local | Pure UI state            | Stored in browser via Datastar      |
| Custom               | Anything else            | Implement `StatePersistenceBackend` |

> **Rule:** Domain code never imports adapters—it asks `PersistenceManager`.

---

\## 🔌 Extension Points

* Persistence Adapters — `entry_points="starmodel.persistence"`
* UI Skins — implement `UIAdapter`
* Auth Providers — startup hook + middleware
* CLI Commands — auto‑register under `starmodel.cli_commands`
* Admin Panels / Dash Tiles — slot‑based injector

---

## 📂 Recommended Project Layout

Below is the **canonical on‑disk layout** produced by `starmodel init myapp`. The structure mirrors our layered architecture and keeps StarModel code separate from application code.

```
myapp/
├─ pyproject.toml        # Project metadata – lists starmodel dependency
├─ .env                  # Local env vars (DATABASE_URL, REDIS_URL)
├─ app/
│  ├─ __init__.py        # Auto‑imports FastHTML app instance
│  ├─ entities.py        # Small projects keep all entities here
│  ├─ views.py           # Optional: custom FastHTML pages
│  ├─ plugins/           # Drop‑in Python packages (admin, auth)
│  │   └─ __init__.py
│  ├─ settings.py        # Overrides: default_store, theme, etc.
│  └─ main.py            # `create_app()` factory – used by CLI
├─ migrations/           # Alembic scripts (`starmodel migrate`)
├─ static/               # Tailwind CSS build or uploads
├─ templates/            # Optional Jinja/FastHTML templates
├─ tests/                # pytest modules – default Memory backend
└─ README.md
```

**Design Rationale**

* Entities stay in *pure Python* – no separate schema files.
* No front‑end build step: MonsterUI CSS via CDN; Tailwind build optional.
* *main.py* wires adapters once, e.g.:

  ```python
  from starmodel.bootstrap import create_fasthtml_app
  from app.entities import Product, Cart
  app = create_fasthtml_app(states=[Product, Cart])
  ```
* Anything in `plugins/` can expose entry‑points (`starmodel.plugins`) to extend routes, CLI, or UI.

---

## 📂 StarModel Library Package Layout

```
starmodel/
├─ core/
│   ├─ entity.py          # Immutable Entity + evolve()
│   ├─ events.py          # @event decorator & metadata helpers
│   └─ typing.py          # Protocols / utility generics
├─ app/
│   ├─ dispatcher.py      # Binds request → event
│   ├─ uow.py             # Unit‑of‑Work / transaction hub
│   └─ bus.py             # EventBus interface + default impl
├─ adapters/
│   ├─ fasthtml.py    # Auto‑router for FastHTML
│   ├─ ui_monster.py      # MonsterUI rendering helpers
│   └─ persistence/
│        ├─ memory.py
│        ├─ redis.py
│        └─ sqlmodel.py   # FastSQLModel integration
├─ cli/
│   ├─ __init__.py        # Typer CLI
│   └─ commands/
│        ├─ init.py  run.py  migrate.py  plugin.py
├─ plugins/__init__.py    # Loader utilities
└─ bootstrap.py           # create_fasthtml_app helper
```

*Domain code never imports from **\`\`** – maintaining clean separation.*

---

## 🚀 CLI Snapshot

```
$ starmodel init shop
✔ Project scaffolded (FastHTML + MonsterUI + SQLite)
$ cd shop && starmodel run
🔧 http://127.0.0.1:8000 (auto‑reload)
```

Upcoming:

```
$ starmodel migrate   # Alembic
$ starmodel plugin add redis-cache
```

---

\## 📈 KPI Targets (Dev → Prod)

| KPI                     | P1     | P2     | P4     |
| ----------------------- | ------ | ------ | ------ |
| Boot‑to‑CRUD time       | ≤5 min | ≤3 min | ≤2 min |
| Lines for Todo app      | <50    | <50    | <50    |
| RPS single node (list)  | 1k     | 1k     | 2k     |
| End‑to‑end test runtime | <30 s  | <45 s  | <60 s  |

---

\## ✨ Final Statement StarModel marries **rapid prototyping** with **long‑term viability**. Define an Entity, decorate behavior with `@event`, and watch your app come alive with live HTML, real‑time sync, and swappable persistence.

**Entity‑first · decorator‑driven · adapter‑powered · pure Python.**
