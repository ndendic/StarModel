from typing import TypeVar, Type

T = TypeVar('T')

def singleton(cls: Type[T]) -> Type[T]:
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance