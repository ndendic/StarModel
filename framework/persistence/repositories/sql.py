"""
SQL Repository - FastSQLModel Integration Repository

🗃️ SQL Database Repository:
This module provides a repository implementation for SQL databases using
FastSQLModel, enabling relational database persistence while maintaining
the clean repository interface and supporting transactions.

Key Features:
- FastSQLModel integration with clean repository interface
- SQL transaction support with proper isolation
- Query translation from repository filters to SQL
- Batch operations for performance
- Connection pooling and optimization
- Migration and schema management
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Type, Union, AsyncIterator
from datetime import datetime
import json
from dataclasses import dataclass
import uuid

# SQL and FastSQLModel imports
try:
    from sqlalchemy import create_engine, text, select, delete, update, and_, or_, desc, asc
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.exc import SQLAlchemyError, IntegrityError
    from fastsqlmodel import BaseTable, FastSQLModel
    SQL_AVAILABLE = True
except ImportError:
    # Graceful fallback when SQL dependencies are not available
    SQL_AVAILABLE = False
    BaseTable = object
    FastSQLModel = object
    AsyncSession = object
    SQLAlchemyError = Exception
    IntegrityError = Exception

from .interface import (
    EntityRepository, QueryFilter, QueryOptions, QueryResult, QueryOperator,
    SortDirection, TransactionContext
)

logger = logging.getLogger(__name__)

@dataclass
class SQLConnectionConfig:
    """SQL database connection configuration"""
    database_url: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False
    connect_args: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.connect_args is None:
            self.connect_args = {}

class SQLTransactionContext(TransactionContext):
    """SQL-specific transaction context"""
    
    def __init__(self, transaction_id: str, session: AsyncSession, isolation_level: str = "READ_COMMITTED"):
        super().__init__(transaction_id, isolation_level)
        self.session = session
        self.savepoints: List[str] = []
    
    async def create_savepoint(self, name: str):
        """Create a savepoint within the transaction"""
        await self.session.execute(text(f"SAVEPOINT {name}"))
        self.savepoints.append(name)
    
    async def rollback_to_savepoint(self, name: str):
        """Rollback to a specific savepoint"""
        await self.session.execute(text(f"ROLLBACK TO SAVEPOINT {name}"))
        # Remove savepoints created after this one
        if name in self.savepoints:
            index = self.savepoints.index(name)
            self.savepoints = self.savepoints[:index + 1]

class SQLRepository(EntityRepository):
    """
    SQL repository implementation using FastSQLModel.
    
    Provides SQL database persistence while maintaining the clean
    repository interface for entity operations.
    """
    
    def __init__(self, config: SQLConnectionConfig):
        if not SQL_AVAILABLE:
            raise ImportError("SQL dependencies not available. Please install fastsqlmodel and sqlalchemy[asyncio]")
        
        self.config = config
        self.engine = create_async_engine(
            config.database_url,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_timeout=config.pool_timeout,
            pool_recycle=config.pool_recycle,
            echo=config.echo,
            connect_args=config.connect_args
        )
        
        # Create async session factory
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Metrics tracking
        self.metrics = {
            'queries_executed': 0,
            'transactions_started': 0,
            'transactions_committed': 0,
            'transactions_rolled_back': 0,
            'entities_saved': 0,
            'entities_loaded': 0,
            'entities_deleted': 0,
            'batch_operations': 0,
            'query_time_total_ms': 0.0
        }
        
        # Active transactions
        self.active_transactions: Dict[str, SQLTransactionContext] = {}
    
    def _is_sql_entity(self, entity_class: Type) -> bool:
        """Check if entity class is a SQL entity (inherits from BaseTable)"""
        return hasattr(entity_class, '__table__') and issubclass(entity_class, BaseTable)
    
    def _get_session(self, context: Optional[TransactionContext] = None) -> AsyncSession:
        """Get database session from context or create new one"""
        if context and isinstance(context, SQLTransactionContext):
            return context.session
        else:
            # Return new session for non-transactional operations
            return self.session_factory()
    
    async def save(self, entity, context: Optional[TransactionContext] = None) -> str:
        """Save an entity to the SQL database"""
        if not self._is_sql_entity(type(entity)):
            raise ValueError(f"Entity {type(entity).__name__} is not a SQL entity (must inherit from BaseTable)")
        
        session = self._get_session(context)
        start_time = datetime.now()
        
        try:
            # Check if entity already exists (has an ID)
            if hasattr(entity, 'id') and entity.id:
                # Update existing entity
                session.add(entity)
                await session.merge(entity)
            else:
                # Create new entity
                if not hasattr(entity, 'id') or not entity.id:
                    entity.id = str(uuid.uuid4())
                session.add(entity)
            
            # Commit if not in transaction context
            if not context:
                await session.commit()
            
            self.metrics['entities_saved'] += 1
            self.metrics['queries_executed'] += 1
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self.metrics['query_time_total_ms'] += execution_time
            
            return entity.id
            
        except Exception as e:
            if not context:
                await session.rollback()
            logger.error(f"Error saving entity {type(entity).__name__}: {e}")
            raise
        finally:
            if not context:
                await session.close()
    
    async def load(self, entity_class: Type, entity_id: str, 
                   context: Optional[TransactionContext] = None) -> Optional[Any]:
        """Load an entity by ID from SQL database"""
        if not self._is_sql_entity(entity_class):
            raise ValueError(f"Entity {entity_class.__name__} is not a SQL entity (must inherit from BaseTable)")
        
        session = self._get_session(context)
        start_time = datetime.now()
        
        try:
            # Build select query
            stmt = select(entity_class).where(entity_class.id == entity_id)
            result = await session.execute(stmt)
            entity = result.scalar_one_or_none()
            
            self.metrics['entities_loaded'] += 1
            self.metrics['queries_executed'] += 1
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self.metrics['query_time_total_ms'] += execution_time
            
            return entity
            
        except Exception as e:
            logger.error(f"Error loading entity {entity_class.__name__} with ID {entity_id}: {e}")
            raise
        finally:
            if not context:
                await session.close()
    
    async def delete(self, entity_class: Type, entity_id: str,
                     context: Optional[TransactionContext] = None) -> bool:
        """Delete an entity by ID from SQL database"""
        if not self._is_sql_entity(entity_class):
            raise ValueError(f"Entity {entity_class.__name__} is not a SQL entity (must inherit from BaseTable)")
        
        session = self._get_session(context)
        start_time = datetime.now()
        
        try:
            # Build delete query
            stmt = delete(entity_class).where(entity_class.id == entity_id)
            result = await session.execute(stmt)
            
            # Commit if not in transaction context
            if not context:
                await session.commit()
            
            deleted = result.rowcount > 0
            if deleted:
                self.metrics['entities_deleted'] += 1
            
            self.metrics['queries_executed'] += 1
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self.metrics['query_time_total_ms'] += execution_time
            
            return deleted
            
        except Exception as e:
            if not context:
                await session.rollback()
            logger.error(f"Error deleting entity {entity_class.__name__} with ID {entity_id}: {e}")
            raise
        finally:
            if not context:
                await session.close()
    
    async def exists(self, entity_class: Type, entity_id: str,
                     context: Optional[TransactionContext] = None) -> bool:
        """Check if an entity exists in SQL database"""
        if not self._is_sql_entity(entity_class):
            raise ValueError(f"Entity {entity_class.__name__} is not a SQL entity (must inherit from BaseTable)")
        
        session = self._get_session(context)
        start_time = datetime.now()
        
        try:
            # Build exists query
            stmt = select(entity_class.id).where(entity_class.id == entity_id)
            result = await session.execute(stmt)
            exists = result.scalar_one_or_none() is not None
            
            self.metrics['queries_executed'] += 1
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self.metrics['query_time_total_ms'] += execution_time
            
            return exists
            
        except Exception as e:
            logger.error(f"Error checking existence of entity {entity_class.__name__} with ID {entity_id}: {e}")
            raise
        finally:
            if not context:
                await session.close()
    
    def _build_where_clause(self, entity_class: Type, filters: List[QueryFilter]):
        """Build SQLAlchemy where clause from repository filters"""
        if not filters:
            return None
        
        conditions = []
        
        for filter_condition in filters:
            field_attr = getattr(entity_class, filter_condition.field, None)
            if not field_attr:
                continue
            
            if filter_condition.operator == QueryOperator.EQUALS:
                conditions.append(field_attr == filter_condition.value)
            elif filter_condition.operator == QueryOperator.NOT_EQUALS:
                conditions.append(field_attr != filter_condition.value)
            elif filter_condition.operator == QueryOperator.GREATER_THAN:
                conditions.append(field_attr > filter_condition.value)
            elif filter_condition.operator == QueryOperator.GREATER_THAN_OR_EQUAL:
                conditions.append(field_attr >= filter_condition.value)
            elif filter_condition.operator == QueryOperator.LESS_THAN:
                conditions.append(field_attr < filter_condition.value)
            elif filter_condition.operator == QueryOperator.LESS_THAN_OR_EQUAL:
                conditions.append(field_attr <= filter_condition.value)
            elif filter_condition.operator == QueryOperator.IN:
                conditions.append(field_attr.in_(filter_condition.value))
            elif filter_condition.operator == QueryOperator.NOT_IN:
                conditions.append(~field_attr.in_(filter_condition.value))
            elif filter_condition.operator == QueryOperator.CONTAINS:
                conditions.append(field_attr.contains(filter_condition.value))
            elif filter_condition.operator == QueryOperator.STARTS_WITH:
                conditions.append(field_attr.startswith(filter_condition.value))
            elif filter_condition.operator == QueryOperator.ENDS_WITH:
                conditions.append(field_attr.endswith(filter_condition.value))
            elif filter_condition.operator == QueryOperator.IS_NULL:
                conditions.append(field_attr.is_(None))
            elif filter_condition.operator == QueryOperator.IS_NOT_NULL:
                conditions.append(field_attr.is_not(None))
        
        return and_(*conditions) if len(conditions) > 1 else conditions[0] if conditions else None
    
    def _build_order_clause(self, entity_class: Type, sort_criteria):
        """Build SQLAlchemy order clause from repository sort criteria"""
        if not sort_criteria:
            return []
        
        order_clauses = []
        
        for sort_item in sort_criteria:
            field_attr = getattr(entity_class, sort_item.field, None)
            if field_attr:
                if sort_item.direction == SortDirection.DESC:
                    order_clauses.append(desc(field_attr))
                else:
                    order_clauses.append(asc(field_attr))
        
        return order_clauses
    
    async def query(self, entity_class: Type, options: QueryOptions,
                    context: Optional[TransactionContext] = None) -> QueryResult:
        """Query entities with filtering and sorting from SQL database"""
        if not self._is_sql_entity(entity_class):
            raise ValueError(f"Entity {entity_class.__name__} is not a SQL entity (must inherit from BaseTable)")
        
        session = self._get_session(context)
        start_time = datetime.now()
        
        try:
            # Build base select query
            stmt = select(entity_class)
            
            # Add where clause
            where_clause = self._build_where_clause(entity_class, options.filters)
            if where_clause is not None:
                stmt = stmt.where(where_clause)
            
            # Add order by clause
            order_clauses = self._build_order_clause(entity_class, options.sort_by)
            if order_clauses:
                stmt = stmt.order_by(*order_clauses)
            
            # Add pagination
            if options.offset > 0:
                stmt = stmt.offset(options.offset)
            if options.limit:
                stmt = stmt.limit(options.limit)
            
            # Execute query
            result = await session.execute(stmt)
            entities = result.scalars().all()
            
            # Get total count if requested
            total_count = None
            if options.include_count:
                count_stmt = select(entity_class)
                if where_clause is not None:
                    count_stmt = count_stmt.where(where_clause)
                
                count_result = await session.execute(count_stmt)
                total_count = len(count_result.scalars().all())
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self.metrics['queries_executed'] += 1
            self.metrics['query_time_total_ms'] += execution_time
            
            return QueryResult(
                entities=list(entities),
                total_count=total_count,
                has_more=options.limit and len(entities) == options.limit,
                query_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"Error querying entities {entity_class.__name__}: {e}")
            raise
        finally:
            if not context:
                await session.close()
    
    async def count(self, entity_class: Type, filters: Optional[List[QueryFilter]] = None,
                    context: Optional[TransactionContext] = None) -> int:
        """Count entities matching filters in SQL database"""
        if not self._is_sql_entity(entity_class):
            raise ValueError(f"Entity {entity_class.__name__} is not a SQL entity (must inherit from BaseTable)")
        
        session = self._get_session(context)
        start_time = datetime.now()
        
        try:
            # Build count query
            stmt = select(entity_class)
            
            # Add where clause
            if filters:
                where_clause = self._build_where_clause(entity_class, filters)
                if where_clause is not None:
                    stmt = stmt.where(where_clause)
            
            # Execute count query
            result = await session.execute(stmt)
            count = len(result.scalars().all())
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self.metrics['queries_executed'] += 1
            self.metrics['query_time_total_ms'] += execution_time
            
            return count
            
        except Exception as e:
            logger.error(f"Error counting entities {entity_class.__name__}: {e}")
            raise
        finally:
            if not context:
                await session.close()
    
    async def save_batch(self, entities: List, 
                         context: Optional[TransactionContext] = None) -> List[str]:
        """Save multiple entities in a batch to SQL database"""
        if not entities:
            return []
        
        entity_class = type(entities[0])
        if not self._is_sql_entity(entity_class):
            raise ValueError(f"Entity {entity_class.__name__} is not a SQL entity (must inherit from BaseTable)")
        
        session = self._get_session(context)
        start_time = datetime.now()
        
        try:
            entity_ids = []
            
            for entity in entities:
                # Ensure entity has an ID
                if not hasattr(entity, 'id') or not entity.id:
                    entity.id = str(uuid.uuid4())
                
                entity_ids.append(entity.id)
                session.add(entity)
            
            # Commit if not in transaction context
            if not context:
                await session.commit()
            
            self.metrics['entities_saved'] += len(entities)
            self.metrics['batch_operations'] += 1
            self.metrics['queries_executed'] += 1
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self.metrics['query_time_total_ms'] += execution_time
            
            return entity_ids
            
        except Exception as e:
            if not context:
                await session.rollback()
            logger.error(f"Error saving entity batch: {e}")
            raise
        finally:
            if not context:
                await session.close()
    
    async def load_batch(self, entity_class: Type, entity_ids: List[str],
                         context: Optional[TransactionContext] = None) -> List[Optional[Any]]:
        """Load multiple entities by ID from SQL database"""
        if not entity_ids:
            return []
        
        if not self._is_sql_entity(entity_class):
            raise ValueError(f"Entity {entity_class.__name__} is not a SQL entity (must inherit from BaseTable)")
        
        session = self._get_session(context)
        start_time = datetime.now()
        
        try:
            # Build batch select query
            stmt = select(entity_class).where(entity_class.id.in_(entity_ids))
            result = await session.execute(stmt)
            entities_dict = {entity.id: entity for entity in result.scalars().all()}
            
            # Return entities in the same order as requested IDs
            entities = [entities_dict.get(entity_id) for entity_id in entity_ids]
            
            self.metrics['entities_loaded'] += len([e for e in entities if e])
            self.metrics['batch_operations'] += 1
            self.metrics['queries_executed'] += 1
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self.metrics['query_time_total_ms'] += execution_time
            
            return entities
            
        except Exception as e:
            logger.error(f"Error loading entity batch: {e}")
            raise
        finally:
            if not context:
                await session.close()
    
    async def delete_batch(self, entity_class: Type, entity_ids: List[str],
                           context: Optional[TransactionContext] = None) -> int:
        """Delete multiple entities by ID from SQL database"""
        if not entity_ids:
            return 0
        
        if not self._is_sql_entity(entity_class):
            raise ValueError(f"Entity {entity_class.__name__} is not a SQL entity (must inherit from BaseTable)")
        
        session = self._get_session(context)
        start_time = datetime.now()
        
        try:
            # Build batch delete query
            stmt = delete(entity_class).where(entity_class.id.in_(entity_ids))
            result = await session.execute(stmt)
            
            # Commit if not in transaction context
            if not context:
                await session.commit()
            
            deleted_count = result.rowcount
            self.metrics['entities_deleted'] += deleted_count
            self.metrics['batch_operations'] += 1
            self.metrics['queries_executed'] += 1
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self.metrics['query_time_total_ms'] += execution_time
            
            return deleted_count
            
        except Exception as e:
            if not context:
                await session.rollback()
            logger.error(f"Error deleting entity batch: {e}")
            raise
        finally:
            if not context:
                await session.close()
    
    async def begin_transaction(self, isolation_level: str = "READ_COMMITTED") -> SQLTransactionContext:
        """Begin a new SQL transaction"""
        session = self.session_factory()
        transaction_id = str(uuid.uuid4())
        
        try:
            # Set isolation level
            if isolation_level != "READ_COMMITTED":
                await session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"))
            
            # Begin transaction
            await session.begin()
            
            context = SQLTransactionContext(transaction_id, session, isolation_level)
            context.is_active = True
            context.started_at = datetime.now()
            
            self.active_transactions[transaction_id] = context
            self.metrics['transactions_started'] += 1
            
            return context
            
        except Exception as e:
            await session.rollback()
            await session.close()
            logger.error(f"Error beginning transaction: {e}")
            raise
    
    async def commit_transaction(self, context: SQLTransactionContext):
        """Commit a SQL transaction"""
        if not context.is_active:
            raise ValueError("Transaction is not active")
        
        try:
            await context.session.commit()
            context.is_committed = True
            context.is_active = False
            context.committed_at = datetime.now()
            
            self.metrics['transactions_committed'] += 1
            
        except Exception as e:
            await context.session.rollback()
            logger.error(f"Error committing transaction {context.transaction_id}: {e}")
            raise
        finally:
            await context.session.close()
            if context.transaction_id in self.active_transactions:
                del self.active_transactions[context.transaction_id]
    
    async def rollback_transaction(self, context: SQLTransactionContext):
        """Rollback a SQL transaction"""
        if not context.is_active:
            return  # Already rolled back or committed
        
        try:
            await context.session.rollback()
            context.is_rolled_back = True
            context.is_active = False
            
            self.metrics['transactions_rolled_back'] += 1
            
        except Exception as e:
            logger.error(f"Error rolling back transaction {context.transaction_id}: {e}")
        finally:
            await context.session.close()
            if context.transaction_id in self.active_transactions:
                del self.active_transactions[context.transaction_id]
    
    async def cleanup_expired(self, entity_class: Type, before: datetime) -> int:
        """Clean up expired entities from SQL database"""
        if not self._is_sql_entity(entity_class):
            raise ValueError(f"Entity {entity_class.__name__} is not a SQL entity (must inherit from BaseTable)")
        
        # This assumes entities have a created_at or updated_at field
        # Implementations may need to customize this based on their schema
        session = self.session_factory()
        
        try:
            # Try to find a timestamp field
            timestamp_field = None
            for field_name in ['created_at', 'updated_at', 'timestamp']:
                if hasattr(entity_class, field_name):
                    timestamp_field = getattr(entity_class, field_name)
                    break
            
            if not timestamp_field:
                logger.warning(f"No timestamp field found for cleanup in {entity_class.__name__}")
                return 0
            
            # Build delete query for expired entities
            stmt = delete(entity_class).where(timestamp_field < before)
            result = await session.execute(stmt)
            await session.commit()
            
            cleaned_count = result.rowcount
            logger.info(f"Cleaned up {cleaned_count} expired {entity_class.__name__} entities")
            
            return cleaned_count
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error cleaning up expired entities: {e}")
            raise
        finally:
            await session.close()
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get SQL repository performance metrics"""
        avg_query_time = (
            self.metrics['query_time_total_ms'] / self.metrics['queries_executed']
            if self.metrics['queries_executed'] > 0 else 0
        )
        
        return {
            **self.metrics,
            'average_query_time_ms': avg_query_time,
            'active_transactions': len(self.active_transactions),
            'connection_pool_size': self.config.pool_size,
            'database_url': self.config.database_url.split('@')[-1] if '@' in self.config.database_url else self.config.database_url
        }
    
    async def initialize_schema(self, entity_classes: List[Type]):
        """Initialize database schema for entity classes"""
        if not SQL_AVAILABLE:
            raise ImportError("SQL dependencies not available")
        
        try:
            # Import FastSQLModel's create_all equivalent
            from fastsqlmodel import create_tables
            
            # Create tables for all SQL entities
            sql_entities = [cls for cls in entity_classes if self._is_sql_entity(cls)]
            
            if sql_entities:
                await create_tables(self.engine, sql_entities)
                logger.info(f"Created tables for {len(sql_entities)} SQL entities")
            
        except Exception as e:
            logger.error(f"Error initializing schema: {e}")
            raise
    
    async def close(self):
        """Close the SQL repository and cleanup resources"""
        # Rollback any active transactions
        for context in list(self.active_transactions.values()):
            await self.rollback_transaction(context)
        
        # Close the engine
        await self.engine.dispose()
        
        logger.info("SQL repository closed")

# Helper functions
def create_sqlite_repository(database_path: str = ":memory:", **kwargs) -> SQLRepository:
    """Create a SQLite repository"""
    config = SQLConnectionConfig(
        database_url=f"sqlite+aiosqlite:///{database_path}",
        **kwargs
    )
    return SQLRepository(config)

def create_postgresql_repository(
    host: str = "localhost", 
    port: int = 5432, 
    database: str = "starmodel", 
    username: str = "postgres", 
    password: str = "",
    **kwargs
) -> SQLRepository:
    """Create a PostgreSQL repository"""
    config = SQLConnectionConfig(
        database_url=f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{database}",
        **kwargs
    )
    return SQLRepository(config)

def create_mysql_repository(
    host: str = "localhost", 
    port: int = 3306, 
    database: str = "starmodel", 
    username: str = "root", 
    password: str = "",
    **kwargs
) -> SQLRepository:
    """Create a MySQL repository"""
    config = SQLConnectionConfig(
        database_url=f"mysql+aiomysql://{username}:{password}@{host}:{port}/{database}",
        **kwargs
    )
    return SQLRepository(config)

# Export main components
__all__ = [
    "SQLRepository", "SQLConnectionConfig", "SQLTransactionContext",
    "create_sqlite_repository", "create_postgresql_repository", "create_mysql_repository"
]