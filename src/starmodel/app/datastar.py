import json
from typing import Any, List, Tuple
from starlette.requests import Request, QueryParams
from datastar_py.fastapi import DatastarResponse, ReadSignals, read_signals

async def is_datastar_request(request: Request) -> bool:
    """Check if the request is a Datastar request."""
    if "Datastar-Request" in request.headers:
        return True
    return False

def _dig(d: dict[str, Any], path: List[str]) -> dict[str, Any] | None:
    """Walk `d` following path segments; return the subtree or None."""
    cur: Any = d
    for seg in path:
        if not isinstance(cur, dict) or seg not in cur:
            return None
        cur = cur[seg]
    return cur if isinstance(cur, dict) else None


def _flatten_leaves(node: dict[str, Any]) -> List[Tuple[str, str]]:
    """Return every leaf key/value pair (depth-first)."""
    out: list[tuple[str, str]] = []
    for k, v in node.items():
        if isinstance(v, dict):
            out.extend(_flatten_leaves(v))
        else:
            out.append((k, str(v)))
    return out


def _pairs_from_query(qp: QueryParams) -> List[Tuple[str, str]]:
    """Dump all key/value pairs from (possibly duplicated) QueryParams."""
    pairs: list[tuple[str, str]] = []
    for key in qp.keys():
        for val in qp.getlist(key):
            pairs.append((key, val))
    return pairs

async def explode_datastar_params_in_request(request: Request, namespace: str) -> None:
    """
    Mutate `request` so that:

      ?datastar={...<namespace>: {...}}      -> becomes
      ?datastar=...&<namespace>=...&<leaves>...

    • `namespace` may contain dots (“Test.person.user”).
    • Values are appended, not overwritten.
    • Dict values are JSON-encoded because query strings can only hold text.
    """
    datastar = await read_signals(request)
    subtree = _dig(datastar, namespace.split("."))
    if subtree is None:
        return  # namespace not present – silently ignore

    extra: list[tuple[str, str]] = []
    extra.append((namespace, json.dumps(subtree)))      # whole subtree
    extra.extend(_flatten_leaves(subtree))              # every leaf key/val

    merged_pairs = _pairs_from_query(request.query_params) + extra
    new_qp       = QueryParams(merged_pairs)

    # Update the ASGI scope so *all* later consumers (FastAPI/Starlette) see it
    request.scope["query_string"] = str(new_qp).encode("latin-1")

    # Clear cached objects that Starlette keeps
    request._query_params = new_qp           # type: ignore[attr-defined]
    if hasattr(request, "_url"):
        request._url = None                  # force re-compute on next access
