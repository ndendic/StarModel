from dataclasses import dataclass
from datetime import date
from inspect import Parameter, get_annotations
from types import GenericAlias, UnionType
from types import SimpleNamespace as ns
from typing import (
    List,
    Union,
    get_args,
    get_origin,
)
from warnings import warn

from fastcore.basics import (
    camel2words,
    first,
    listify,
    noop,
    snake2camel,
    str2bool,
    str2date,
    str2int,
)
from fastcore.xtras import dict2obj, is_namedtuple
from starlette.applications import Starlette
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException
from starlette.requests import FormData, Request



empty = Parameter.empty
def _mk_list(t, v): return [t(o) for o in listify(v)]

def snake2hyphens(s:str):
    "Convert `s` from snake case to hyphenated and capitalised"
    s = snake2camel(s)
    return camel2words(s, '-')


htmx_hdrs = dict(
    boosted="HX-Boosted",
    current_url="HX-Current-URL",
    history_restore_request="HX-History-Restore-Request",
    prompt="HX-Prompt",
    request="HX-Request",
    target="HX-Target",
    trigger_name="HX-Trigger-Name",
    trigger="HX-Trigger")

@dataclass
class HtmxHeaders:
    boosted:str|None=None; current_url:str|None=None; history_restore_request:str|None=None; prompt:str|None=None
    request:str|None=None; target:str|None=None; trigger_name:str|None=None; trigger:str|None=None
    def __bool__(self): return any(hasattr(self,o) for o in htmx_hdrs)

def _get_htmx(h):
    res = {k:h.get(v.lower(), None) for k,v in htmx_hdrs.items()}
    return HtmxHeaders(**res)


async def parse_form(req: Request) -> FormData:
    "Starlette errors on empty multipart forms, so this checks for that situation"
    ctype = req.headers.get("Content-Type", "")
    if ctype=='application/json': return await req.json()
    if not ctype.startswith("multipart/form-data"): return await req.form()
    try: boundary = ctype.split("boundary=")[1].strip()
    except IndexError: raise HTTPException(400, "Invalid form-data: no boundary")
    min_len = len(boundary) + 6
    clen = int(req.headers.get("Content-Length", "0"))
    if clen <= min_len: return FormData()
    return await req.form()

def _annotations(anno):
    "Same as `get_annotations`, but also works on namedtuples"
    if is_namedtuple(anno): return {o:str for o in anno._fields}
    return get_annotations(anno)

def _is_body(anno): return issubclass(anno, (dict,ns)) or _annotations(anno)


def _formitem(form, k):
    "Return single item `k` from `form` if len 1, otherwise return list"
    if isinstance(form, dict): return form.get(k)
    o = form.getlist(k)
    return o[0] if len(o) == 1 else o if o else None

def _form_arg(k, v, d):
    "Get type by accessing key `k` from `d`, and use to cast `v`"
    if v is None: return
    if not isinstance(v, (str,list,tuple)): return v
    # This is the type we want to cast `v` to
    anno = d.get(k, None)
    if not anno: return v
    return _fix_anno(anno, v)

def form2dict(form: FormData) -> dict:
    "Convert starlette form data to a dict"
    if isinstance(form, dict): return form
    return {k: _formitem(form, k) for k in form}

async def _from_body(req, p):
    anno = p.annotation
    # Get the fields and types of type `anno`, if available
    d = _annotations(anno)
    data = form2dict(await parse_form(req))
    if req.query_params: data = {**data, **dict(req.query_params)}
    cargs = {k: _form_arg(k, v, d) for k, v in data.items() if not d or k in d}
    return anno(**cargs)


async def _find_p(req, arg:str, p:Parameter):
    "In `req` find param named `arg` of type in `p` (`arg` is ignored for body types)"
    anno = p.annotation
    # If there's an annotation of special types, return object of that type
    # GenericAlias is a type of typing for iterators like list[int] that is not a class
    if isinstance(anno, type) and not isinstance(anno, GenericAlias):
        if issubclass(anno, Request): return req
        if issubclass(anno, HtmxHeaders): return _get_htmx(req.headers)
        if issubclass(anno, Starlette): return req.scope['app']
        if _is_body(anno) and 'session'.startswith(arg.lower()): return req.scope.get('session', {})
        if _is_body(anno): return await _from_body(req, p)
    # If there's no annotation, check for special names
    if anno is empty:
        if 'request'.startswith(arg.lower()): return req
        if 'session'.startswith(arg.lower()): return req.scope.get('session', {})
        if arg.lower()=='scope': return dict2obj(req.scope)
        if arg.lower()=='auth': return req.scope.get('auth', None)
        if arg.lower()=='htmx': return _get_htmx(req.headers)
        if arg.lower()=='app': return req.scope['app']
        if arg.lower()=='body': return (await req.body()).decode()
        if arg.lower() in ('hdrs','ftrs','bodykw','htmlkw'): return getattr(req, arg.lower())
        if arg!='resp': warn(f"`{arg} has no type annotation and is not a recognised special name, so is ignored.")
        return None
    # Look through path, cookies, headers, query, and body in that order
    res = req.path_params.get(arg, None)
    if res in (empty,None): res = req.cookies.get(arg, None)
    if res in (empty,None): res = req.headers.get(snake2hyphens(arg), None)
    if res in (empty,None): res = req.query_params.getlist(arg)
    if res==[]: res = None
    if res in (empty,None): res = _formitem(await parse_form(req), arg)
    # Raise 400 error if the param does not include a default
    if (res in (empty,None)) and p.default is empty: raise HTTPException(400, f"Missing required field: {arg}")
    # If we have a default, return that if we have no value
    if res in (empty,None): res = p.default
    # We can cast str and list[str] to types; otherwise just return what we have
    if anno is empty: return res
    try: return _fix_anno(anno, res)
    except ValueError: raise HTTPException(404, req.url.path) from None

def _fix_anno(t, o):
    "Create appropriate callable type for casting a `str` to type `t` (or first type in `t` if union)"
    origin = get_origin(t)
    if origin is Union or origin is UnionType or origin in (list,List):
        t = first(o for o in get_args(t) if o!=type(None))
    d = {bool: str2bool, int: str2int, date: str2date, UploadFile: noop}
    res = d.get(t, t)
    if origin in (list,List): return _mk_list(res, o)
    if not isinstance(o, (str,list,tuple)): return o
    return res(o[-1]) if isinstance(o,(list,tuple)) else res(o)