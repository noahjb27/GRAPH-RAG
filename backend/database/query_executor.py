"""
Query executor for safe Cypher query execution
"""

import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from .neo4j_client import Neo4jClient, Neo4jQueryResult

@dataclass
class QueryValidationResult:
    """Result of query validation"""
    is_valid: bool
    issues: List[str]
    is_read_only: bool
    estimated_complexity: int  # 1-5 scale

class QueryExecutor:
    """Executes and validates Cypher queries safely"""
    
    def __init__(self, neo4j_client: Neo4jClient):
        self.client = neo4j_client
        
        # Patterns for dangerous operations
        self.dangerous_patterns = [
            r'\bDELETE\b',
            r'\bREMOVE\b', 
            r'\bSET\b.*=\s*null',
            r'\bDROP\b',
            r'\bCREATE\s+(?!.*\bWHERE\b)',  # CREATE without WHERE can be dangerous
            r'\bMERGE\b',
            r'\bDETACH\s+DELETE\b'
        ]
        
        # Patterns for expensive operations
        self.expensive_patterns = [
            r'\bMATCH\s*\([^)]*\)\s*-\s*\[[^]]*\]\s*-\s*\([^)]*\)',  # Patterns without WHERE
            r'\bMATCH\s*\([^)]*\)(?!\s*WHERE)',  # MATCH without WHERE
            r'\bCOLLECT\s*\(',  # COLLECT can be expensive
            r'\bUNWIND\b.*\bUNWIND\b',  # Nested UNWIND
        ]
    
    def validate_query(self, query: str) -> QueryValidationResult:
        """Validate Cypher query for safety and performance"""
        
        issues = []
        is_read_only = True
        complexity = 1
        
        query_upper = query.upper()
        
        # Check for dangerous operations
        for pattern in self.dangerous_patterns:
            if re.search(pattern, query_upper, re.IGNORECASE):
                issues.append(f"Potentially dangerous operation detected: {pattern}")
                is_read_only = False
        
        # Check for expensive operations
        for pattern in self.expensive_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                issues.append(f"Potentially expensive operation: {pattern}")
                complexity += 1
        
        # Check for proper LIMIT usage on complex queries
        if 'MATCH' in query_upper and 'LIMIT' not in query_upper:
            if any(word in query_upper for word in ['COLLECT', 'COUNT', 'UNWIND']):
                issues.append("Consider adding LIMIT clause for performance")
                complexity += 1
        
        # Estimate complexity based on query structure
        if query_upper.count('MATCH') > 2:
            complexity += 1
        if query_upper.count('WITH') > 1:
            complexity += 1
        if any(word in query_upper for word in ['SHORTESTPATH', 'ALLSHORTESTPATHS']):
            complexity += 2
            
        complexity = min(complexity, 5)  # Cap at 5
        
        return QueryValidationResult(
            is_valid=len(issues) == 0 or all('dangerous' not in issue for issue in issues),
            issues=issues,
            is_read_only=is_read_only,
            estimated_complexity=complexity
        )
    
    async def execute_query_safely(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        max_complexity: int = 4,
        allow_write: bool = False
    ) -> Neo4jQueryResult:
        """Execute query with safety checks"""
        
        # Validate query first
        validation = self.validate_query(query)
        
        # Check if query is too complex
        if validation.estimated_complexity > max_complexity:
            result = Neo4jQueryResult(
                records=[],
                summary={},
                execution_time_seconds=0.0,
                query=query,
                parameters=parameters or {},
                timestamp=datetime.now(),
                success=False,
                error_message=f"Query complexity ({validation.estimated_complexity}) exceeds maximum ({max_complexity})"
            )
            return result
        
        # Check if write operations are allowed
        if not validation.is_read_only and not allow_write:
            result = Neo4jQueryResult(
                records=[],
                summary={},
                execution_time_seconds=0.0,
                query=query,
                parameters=parameters or {},
                timestamp=datetime.now(),
                success=False,
                error_message="Write operations not permitted"
            )
            return result
        
        # Execute the query
        if validation.is_read_only:
            return await self.client.execute_read_query(query, parameters)
        else:
            return await self.client.execute_query(query, parameters)
    
    def add_safety_limits(self, query: str, default_limit: int = 1000) -> str:
        """Add LIMIT clause to query if not present"""
        
        query_upper = query.upper().strip()
        
        # Don't add LIMIT if query already has one
        if 'LIMIT' in query_upper:
            return query
            
        # Don't add LIMIT to certain query types
        skip_limit_patterns = [
            r'\bCOUNT\s*\(',
            r'\bSUM\s*\(',
            r'\bAVG\s*\(',
            r'\bMIN\s*\(',
            r'\bMAX\s*\(',
            r'\bRETURN\s+count\s*\(',
        ]
        
        for pattern in skip_limit_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return query
        
        # Add LIMIT to the end
        return f"{query.rstrip()} LIMIT {default_limit}"
    
    def optimize_query(self, query: str) -> str:
        """Apply basic optimizations to the query"""
        
        optimized = query
        
        # Add LIMIT if missing (for safety)
        optimized = self.add_safety_limits(optimized)
        
        # Could add more optimizations here:
        # - Index hints
        # - Query rewriting
        # - Parameter suggestions
        
        return optimized 