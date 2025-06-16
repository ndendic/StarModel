Below is a **targeted checklist** that maps the *current* code in `src/starmodel/` to the new **app-layer responsibilities** we just defined (Dispatcher + UoW + Bus).
Nothing here forces a rewrite—think of it as “where to copy-paste / move 20–40 lines” so the layers stay clean.

---

## 1. Dispatcher (new `starmodel/app/dispatcher.py`)

| You already have                                                                | Keep / move                                                                            | Why                                                                               |
| ------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `@event` decorator stores `SignalMeta` + registers route **inside** `events.py` | **Keep metadata only**, move **route registration & call binding** into the dispatcher | The dispatcher—not the decorator—decides *how* a request turns into an event call |
| `State.get_route_handler` (or similar private helper)                           | Move logic into `dispatcher.route_for(state_cls, event_info)`                          | Keeps HTTP wiring in app layer                                                    |
| `inspect.signature.bind_partial` bits you wrote in last refactor                | Leave in dispatcher (`_bind_args()`)                                                   | Pure application concern                                                          |

**Skeleton**

```python
# starmodel/app/dispatcher.py
def call_event(state_cls, event_name, request) -> tuple[Any, dict]:
    info = state_cls.events[event_name]
    state = state_cls.get(request)
    bound = info.signature.bind_partial(state, **request.query_params)
    new_state = info.fn(*bound.args, **bound.kwargs)
    cmd_record = {
        "entity": f"{state_cls.__name__}:{state.id}",
        "event": event_name,
        "args": bound.arguments | {"id": state.id},
        "actor": request.user.id if hasattr(request, "user") else None,
        "ts": datetime.utcnow().isoformat(),
    }
    return new_state, cmd_record
```

Then the FastHTML router adapter just:

```python
async def handler(request):
    new_state, cmd = dispatcher.call_event(MyState, "increment", request)
    await app_uow.commit(new_state, cmd)
    return DatastarResponse(...)
```

---

## 2. Unit-of-Work (new `starmodel/app/uow.py`)

You probably **commit directly in `State.save()`** today.
Refactor that commit into a `UoW` so you can add transactions later:

```python
class UnitOfWork:
    def __init__(self, repo, bus):
        self.repo, self.bus, self._events = repo, bus, []

    def collect(self, event_dict):          # called by repo on state change
        self._events.append(event_dict)

    async def commit(self, state, cmd_record):
        self.repo.save(state)
        self.collect(cmd_record)
        # commit DB / Redis transactions here
        for e in self._events:
            await self.bus.publish(e)
```

👉 **Update** `State.save()` to **just** `repo.save()`—no direct EventBus push.

---

## 3. EventBus (new `starmodel/app/bus.py`)

Right now Datastar responses are created inline in route handlers.
Extract a minimal bus:

```python
class InProcessBus:
    def __init__(self):
        self._subs: list[Callable[[dict], Awaitable[None]]] = []

    def subscribe(self, fn): self._subs.append(fn)

    async def publish(self, event: dict):
        for fn in self._subs:
            await fn(event)
```

### Hook Datastar

```python
from starmodel.adapters.sse import datastar_push

bus.subscribe(datastar_push)   # datastar_push formats & yields SSE
```

Later you can register more subscribers (WebSocket, task queue).

---

## 4. Repo split (move persistence glue out of `state.py`)

* `state.py` still defines `auto_persist`, but **remove** direct usage of `memory_persistence` inside `State.get()`—delegate to `repo = PersistenceManager.for_class(cls)`.
* Create `starmodel/adapters/persistence/memory.py` (you already have) **unchanged**.
* Add a micro-“manager” in `adapters/persistence/__init__.py` that picks the right repo based on `state_cls.model_config["store"]`.

---

## 5. FastHTML router adapter update

*Stop registering routes inside `@event`.*
Create `starmodel/adapters/web_fasthtml.py`:

```python
def include_state(router, state_cls):
    for name, info in state_cls.events.items():
        path = f"/{state_cls.__name__.lower()}/{name}"
        async def fn(request, _n=name):
            new_state, cmd = dispatcher.call_event(state_cls, _n, request)
            await uow.commit(new_state, cmd)
            return cmd_to_response(cmd, new_state)
        router.add_api_route(path, fn, methods=["POST", "GET"])
```

`cmd_to_response` chooses DatastarResponse vs normal Redirect based on request headers.

---

## 6. Refactor check-list in repo

1. **events.py** – strip route creation, leave metadata only.
2. **state.py** – replace inline memory cache with `PersistenceManager`.
3. **New files**:

   * `app/dispatcher.py`
   * `app/uow.py`
   * `app/bus.py`
   * `adapters/web_fasthtml.py`
4. **bootstrap.py** – wire:

   ```python
   bus = InProcessBus()
   repo_manager = PersistenceManager(default_backends)
   uow  = UnitOfWork(repo_manager, bus)
   app  = create_fasthtml_app(uow, bus, repo_manager)
   ```

---

### Immediate compile errors you’ll hit

| Symptom                             | Quick fix                                                                                   |
| ----------------------------------- | ------------------------------------------------------------------------------------------- |
| `AttributeError: events`            | In class `SignalModelMeta` add `cls.events = iter_state_events(cls)` during class creation. |
| Duplicate routes after reload       | Check `if path in {r.path for r in router.routes}` before adding.                           |
| `repo.save()` missing in-memory TTL | Move TTL logic from old `MemoryStatePersistence.save_state_sync` into `MemoryRepo.save()`.  |

That’s it—you now have a clear **app layer** without changing any `@event` authoring style. Tackle the bullet-points one file at a time and tests should still pass; then you can add Redis or SQL repos behind the same `PersistenceManager`.
