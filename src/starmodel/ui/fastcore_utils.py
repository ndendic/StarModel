from typing import Iterable,Generator
from functools import partial
from fastcore.basics import risinstance


def is_iter(o):
    "Test whether `o` can be used in a `for` loop"
    #Rank 0 tensors in PyTorch are not really iterable
    return isinstance(o, (Iterable,Generator)) and getattr(o,'ndim',1)

def is_coll(o):
    "Test whether `o` is a collection (i.e. has a usable `len`)"
    #Rank 0 tensors in PyTorch do not have working `len`
    return hasattr(o, '__len__') and getattr(o,'ndim',1)

def is_array(x):
    "`True` if `x` supports `__array__` or `iloc`"
    return hasattr(x,'__array__') or hasattr(x,'iloc')

# %% ../nbs/01_basics.ipynb
def listify(o=None, *rest, use_list=False, match=None):
    "Convert `o` to a `list`"
    if rest: o = (o,)+rest
    if use_list: res = list(o)
    elif o is None: res = []
    elif isinstance(o, list): res = o
    elif isinstance(o, str) or isinstance(o, bytes) or is_array(o): res = [o]
    elif is_iter(o): res = list(o)
    else: res = [o]
    if match is not None:
        if is_coll(match): match = len(match)
        if len(res)==1: res = res*match
        else: assert len(res)==match, 'Match length mismatch'
    return res

def tuplify(o, use_list=False, match=None):
    "Make `o` a tuple"
    return tuple(listify(o, use_list=use_list, match=match))

def _risinstance(types, obj):
    if any(isinstance(t,str) for t in types):
        return any(t.__name__ in types for t in type(obj).__mro__)
    return isinstance(obj, types)

def risinstance(types, obj=None):
    "Curried `isinstance` but with args reversed"
    types = tuplify(types)
    if obj is None: return partial(_risinstance,types)
    return _risinstance(types, obj)
    
def partition(coll, f):
    "Partition a collection by a predicate"
    ts,fs = [],[]
    for o in coll: (fs,ts)[f(o)].append(o)
    if isinstance(coll,tuple):
        typ = type(coll)
        ts,fs = typ(ts),typ(fs)
    return ts,fs