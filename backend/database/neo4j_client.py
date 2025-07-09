"""
Neo4j database client for historical Berlin transport network
"""

import asyncio
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import time
from neo4j import AsyncGraphDatabase, AsyncSession
from ..config import settings

@dataclass
class Neo4jQueryResult:
    """Result of a Neo4j query execution"""
    
    records: List[Dict[str, Any]]
    summary: Dict[str, Any]
    execution_time_seconds: float
    query: str
    parameters: Dict[str, Any]
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    
    @property
    def record_count(self) -> int:
        """Number of records returned"""
        return len(self.records)
    
    @property
    def is_empty(self) -> bool:
        """Check if result is empty"""
        return len(self.records) == 0

class Neo4jClient:
    """Async Neo4j client for the historical Berlin transport database"""
    
    def __init__(self):
        self.uri = settings.neo4j_uri
        self.username = settings.neo4j_username
        self.password = settings.neo4j_password
        self.database = settings.neo4j_database
        self.driver = None
        self._connection_pool_size = 10
        self._max_transaction_retry_time = 30
        
    async def connect(self):
        """Establish connection to Neo4j database"""
        if self.driver is None:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password),
                max_connection_pool_size=self._connection_pool_size,
                max_transaction_retry_time=self._max_transaction_retry_time
            )
        
        # Test connection
        try:
            await self.driver.verify_connectivity()
            print(f"Successfully connected to Neo4j database: {self.database}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Neo4j: {e}")
    
    async def close(self):
        """Close Neo4j database connection"""
        if self.driver:
            await self.driver.close()
            self.driver = None
    
    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> Neo4jQueryResult:
        """Execute a single Cypher query"""
        
        if not self.driver:
            await self.connect()
        
        start_time = time.time()
        parameters = parameters or {}
        
        try:
            async with self.driver.session(database=self.database) as session:
                result = await session.run(query, parameters)
                records = []
                
                # Process all records
                async for record in result:
                    # Convert neo4j Record to dict
                    record_dict = {}
                    for key in record.keys():
                        value = record[key]
                        # Convert neo4j types to Python types
                        if hasattr(value, '_properties'):
                            # Node or Relationship
                            record_dict[key] = dict(value._properties)
                        else:
                            record_dict[key] = value
                    records.append(record_dict)
                
                # Get query summary
                summary = await result.consume()
                execution_time = time.time() - start_time
                
                return Neo4jQueryResult(
                    records=records,
                    summary={
                        "result_available_after": summary.result_available_after,
                        "result_consumed_after": summary.result_consumed_after,
                        "query_type": summary.query_type,
                        "counters": {
                            "nodes_created": summary.counters.nodes_created,
                            "nodes_deleted": summary.counters.nodes_deleted,
                            "relationships_created": summary.counters.relationships_created,
                            "relationships_deleted": summary.counters.relationships_deleted,
                            "properties_set": summary.counters.properties_set,
                            "labels_added": summary.counters.labels_added,
                            "labels_removed": summary.counters.labels_removed,
                            "indexes_added": summary.counters.indexes_added,
                            "indexes_removed": summary.counters.indexes_removed,
                            "constraints_added": summary.counters.constraints_added,
                            "constraints_removed": summary.counters.constraints_removed
                        } if summary.counters else {}
                    },
                    execution_time_seconds=execution_time,
                    query=query,
                    parameters=parameters,
                    timestamp=datetime.now(),
                    success=True
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            return Neo4jQueryResult(
                records=[],
                summary={},
                execution_time_seconds=execution_time,
                query=query,
                parameters=parameters,
                timestamp=datetime.now(),
                success=False,
                error_message=str(e)
            )
    
    async def execute_read_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Neo4jQueryResult:
        """Execute a read-only query (optimized for read replicas)"""
        
        if not self.driver:
            await self.connect()
        
        start_time = time.time()
        parameters = parameters or {}
        
        try:
            async with self.driver.session(
                database=self.database,
                default_access_mode="READ"
            ) as session:
                result = await session.run(query, parameters)
                records = []
                
                async for record in result:
                    record_dict = {}
                    for key in record.keys():
                        value = record[key]
                        if hasattr(value, '_properties'):
                            record_dict[key] = dict(value._properties)
                        else:
                            record_dict[key] = value
                    records.append(record_dict)
                
                summary = await result.consume()
                execution_time = time.time() - start_time
                
                return Neo4jQueryResult(
                    records=records,
                    summary={
                        "result_available_after": summary.result_available_after,
                        "result_consumed_after": summary.result_consumed_after,
                        "query_type": summary.query_type,
                        "counters": {
                            "nodes_created": summary.counters.nodes_created,
                            "nodes_deleted": summary.counters.nodes_deleted,
                            "relationships_created": summary.counters.relationships_created,
                            "relationships_deleted": summary.counters.relationships_deleted,
                            "properties_set": summary.counters.properties_set,
                            "labels_added": summary.counters.labels_added,
                            "labels_removed": summary.counters.labels_removed,
                            "indexes_added": summary.counters.indexes_added,
                            "indexes_removed": summary.counters.indexes_removed,
                            "constraints_added": summary.counters.constraints_added,
                            "constraints_removed": summary.counters.constraints_removed
                        } if summary.counters else {}
                    },
                    execution_time_seconds=execution_time,
                    query=query,
                    parameters=parameters,
                    timestamp=datetime.now(),
                    success=True
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            return Neo4jQueryResult(
                records=[],
                summary={},
                execution_time_seconds=execution_time,
                query=query,
                parameters=parameters,
                timestamp=datetime.now(),
                success=False,
                error_message=str(e)
            )
    
    async def test_connection(self) -> bool:
        """Test database connectivity"""
        try:
            result = await self.execute_read_query("RETURN 1 as test")
            return result.success and len(result.records) == 1
        except Exception:
            return False
    
    async def get_database_info(self) -> Dict[str, Any]:
        """Get basic database information"""
        queries = {
            "node_count": "MATCH (n) RETURN count(n) as count",
            "relationship_count": "MATCH ()-[r]->() RETURN count(r) as count",
            "labels": "CALL db.labels() YIELD label RETURN collect(label) as labels",
            "relationship_types": "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) as types",
            "available_years": "MATCH (y:Year) RETURN collect(y.year) as years ORDER BY y.year"
        }
        
        info = {}
        for key, query in queries.items():
            try:
                result = await self.execute_read_query(query)
                if result.success and result.records:
                    if key in ["node_count", "relationship_count"]:
                        info[key] = result.records[0]["count"]
                    elif key == "labels":
                        info[key] = result.records[0]["labels"]
                    elif key == "relationship_types":
                        info[key] = result.records[0]["types"]
                    elif key == "available_years":
                        info[key] = sorted(result.records[0]["years"])
                else:
                    info[key] = None
            except Exception as e:
                info[key] = f"Error: {e}"
        
        return info
    
    def __del__(self):
        """Cleanup on deletion"""
        if self.driver:
            # Can't await in __del__, so we'll just close synchronously if needed
            pass

# Global database client instance
neo4j_client = Neo4jClient() 