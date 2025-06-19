from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, Generator, List, Optional, Type, Union, get_args, get_origin
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import func, or_
from sqlmodel import Session, SQLModel, create_engine, select

from .base import EntityPersistenceBackend


class SQLModelBackend(EntityPersistenceBackend):

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, url: str = "sqlite:///starmodel.db", echo: bool = False):
        if not self._initialized:
            # Initialize data storage
            self._expiry: Dict[str, float] = {}
            SQLModelBackend._initialized = True
            
            # Initialize parent class for cleanup functionality
            super().__init__()
            self.engine = create_engine(url, echo=echo)
            
            # NOTE: Table creation moved to configure_app() to ensure proper initialization order
            # Tables must be created AFTER all SQLEntity models are imported/defined
            
            # Register this backend for global cleanup management
            from . import register_backend
            register_backend(self)
            
            # TODO: Start automatic cleanup by default
            # self.start_cleanup()


    def init_db(self) -> None:
        SQLModel.metadata.create_all(self.engine)


    def get_session(self) -> Generator[Session, None, None]:
        with Session(self.engine) as session:
            yield session


    def schema(self) -> str:
        inspector = sa.inspect(self.engine)
        res = ""
        for table_name in inspector.get_table_names():
            res += f"Table: {table_name}\n"
            pk_cols = inspector.get_pk_constraint(table_name)["constrained_columns"]
            for column in inspector.get_columns(table_name):
                pk_marker = "*" if column["name"] in pk_cols else "-"
                res += f"  {pk_marker} {column['name']}: {column['type']}\n"
        return res


    def all_records(self, model: Type[SQLModel]) -> List[SQLModel]:
        with Session(self.engine) as session:
            statement = select(model)
            results = session.exec(statement).all()
            return results

    def filter(
        self,
        model: Type[SQLModel],
        sorting_field: Optional[str] = None,
        sort_direction: str = "asc",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        as_dict: bool = False,
        fields: Optional[List[str]] = None,
        exact_match: bool = True,
        **kwargs
    ) -> List[Dict[str, Any]]:
        with Session(self.engine) as session:
            # Validate that all filter fields exist in the model
            invalid_fields = [field for field in kwargs.keys() if field not in model.__fields__]
            if invalid_fields:
                raise ValueError(f"Invalid fields for filtering: {', '.join(invalid_fields)}")

            # Build the base query
            if fields:
                query = select(*[getattr(model, field) for field in fields])
            else:
                query = select(model)

            # Add filters for each kwarg
            for field, value in kwargs.items():
                if value is None:
                    query = query.filter(getattr(model, field).is_(None))
                    continue

                field_type = model.__fields__[field].annotation
                # Get the underlying type if it's Optional
                if get_origin(field_type) is Union:
                    # Optional[T] is actually Union[T, None]
                    field_type = next((t for t in get_args(field_type) if t is not type(None)), str)

                if not exact_match and isinstance(value, str):
                    query = query.filter(getattr(model, field).ilike(f"%{value}%"))
                else:
                    # Handle different field types
                    if field_type in (str, Optional[str]):
                        if exact_match:
                            query = query.filter(getattr(model, field) == value)
                        else:
                            query = query.filter(getattr(model, field).ilike(f"%{value}%"))
                    
                    elif field_type in (int, float, Decimal, bool, Optional[int], Optional[float], Optional[Decimal], Optional[bool]):
                        query = query.filter(getattr(model, field) == value)
                    
                    elif field_type in (datetime, date, Optional[datetime], Optional[date]):
                        # Handle date/datetime range queries
                        if isinstance(value, (list, tuple)) and len(value) == 2:
                            start, end = value
                            query = query.filter(
                                getattr(model, field).between(start, end)
                            )
                        else:
                            query = query.filter(getattr(model, field) == value)
                    elif field_type is UUID:
                        # Handle UUID fields, converting string to UUID if needed
                        if isinstance(value, str):
                            try:
                                value = UUID(value)
                            except ValueError:
                                raise ValueError(f"Invalid UUID format for field {field}: {value}")
                        query = query.filter(getattr(model, field) == value)
                    
                    elif isinstance(value, (list, tuple)):
                        # Handle IN queries for lists
                        query = query.filter(getattr(model, field).in_(value))
                    
                    else:
                        # Default to exact match for unknown types
                        query = query.filter(getattr(model, field) == value)

            # Add sorting
            if sorting_field:
                if sorting_field in model.__fields__:
                    order_field = getattr(model, sorting_field)
                    query = query.order_by(
                        order_field.desc()
                        if sort_direction.lower() == "desc"
                        else order_field
                    )
                else:
                    raise ValueError(
                        f"Sorting field '{sorting_field}' does not exist in the model."
                    )
            else:
                query = query.order_by(model.id)

            # Add pagination
            if limit is not None:
                query = query.limit(limit)

            if offset is not None:
                query = query.offset(offset)

            results = session.exec(query).all()

            if as_dict:
                return [result.dict() for result in results]
            return results

    def search(
        self,
        model: Type[SQLModel],
        search_value: Optional[str] = None,
        sorting_field: Optional[str] = None,
        sort_direction: str = "asc",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        as_dict: bool = False,
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        with Session(self.engine) as session:
            if fields:
                query = select(*[getattr(model, field) for field in fields])
            else:
                query = select(model)

            if search_value:
                string_fields = [
                    k for k, v in model.__fields__.items() if v.annotation is str
                ]
                if string_fields:
                    conditions = [
                        getattr(model, field).ilike(f"%{search_value}%")
                        for field in string_fields
                    ]
                    query = query.filter(or_(*conditions))

            if sorting_field:
                if sorting_field in model.__fields__:
                    order_field = getattr(model, sorting_field)
                    query = query.order_by(
                        order_field.desc()
                        if sort_direction.lower() == "desc"
                        else order_field
                    )
                else:
                    raise ValueError(
                        f"Sorting field '{sorting_field}' does not exist in the model."
                    )
            else:
                query = query.order_by(model.id)

            if limit is not None:
                query = query.limit(limit)

            if offset is not None:
                query = query.offset(offset)

            results = session.exec(query).all()

            if as_dict:
                dict_results = [result._asdict() for result in results]
                return dict_results
            else:
                return results


    def load_entity_sync(self, model: Type[SQLModel], id: Any, alt_key: str = None) -> Optional[SQLModel]:
        with Session(self.engine) as session:
            if alt_key:
                stmt = select(model).where(getattr(model, alt_key) == id)
                result = session.exec(stmt).first()
            else:
                result = session.get(model, id)
            return result
        
    def exists_sync(self, model: Type[SQLModel], id: Any, alt_key: str = None) -> bool:
        with Session(self.engine) as session:
            if alt_key:
                stmt = select(model).where(getattr(model, alt_key) == id)
                result = session.exec(stmt).first()
            else:
                result = session.get(model, id)
            return result

    def cleanup_expired_sync(self) -> int:
        # TODO: Implement cleanup logic
        return 0

    def update_record(self, model: Type[SQLModel], id: Any, data: Dict[str, Any]) -> Dict[str, Any]:
        with Session(self.engine) as session:
            record = session.get(model, id)
            if not record:
                raise Exception(f"Record with id {id} not found")
            for key, value in data.items():
                setattr(record, key, value)
            session.add(record)
            session.commit()
            session.refresh(record)
            return record.model_dump()


    def delete_entity_sync(self, record: SQLModel) -> None:
        with Session(self.engine) as session:
            record = session.get(type(record), record.id)
            if record:
                session.delete(record)
                session.commit()


    def save_entity_sync(self, record: SQLModel, ttl: Optional[int] = None) -> SQLModel:
        data = record.model_dump()
        model = type(record)
        with Session(self.engine) as session:
            if "id" in data:
                db_record = session.get(model, data["id"])
                if db_record:
                    for key, value in data.items():
                        setattr(db_record, key, value)
                else:
                    db_record = model(**data)
            else:
                db_record = model(**data)

            session.add(db_record)
            session.commit()
            session.refresh(db_record)

            return db_record


    def bulk_insert(self, model: Type[SQLModel], data: List[Dict[str, Any]]) -> List[SQLModel]:
        with Session(self.engine) as session:
            records = [model(**item) for item in data]
            session.add_all(records)
            session.commit()
            for record in records:
                session.refresh(record)
            return records


    def bulk_update(self, model: Type[SQLModel], data: List[Dict[str, Any]]) -> List[SQLModel]:
        with Session(self.engine) as session:
            records = []
            for item in data:
                if "id" in item:
                    record = session.get(model, item["id"])
                    if record:
                        for key, value in item.items():
                            setattr(record, key, value)
                        records.append(record)
            session.add_all(records)
            session.commit()
            for record in records:
                session.refresh(record)
            return records


    def count_records(self, model: Type[SQLModel]) -> int:
        with Session(self.engine) as session:
            return session.exec(select(func.count()).select_from(model)).one()