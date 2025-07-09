"""
Direct Cypher Pipeline - Schema-aware Cypher generation from natural language
Priority 1 implementation with multi-LLM support
"""

import time
import json
from typing import Optional, Dict, Any, List
from .base_pipeline import BasePipeline, PipelineResult
from ..llm_clients.client_factory import create_llm_client
from ..database.neo4j_client import neo4j_client
from ..database.schema_analyzer import SchemaAnalyzer
from ..database.query_executor import QueryExecutor
from ..config import settings

class DirectCypherPipeline(BasePipeline):
    """
    Direct Cypher generation pipeline using schema-aware prompting
    
    Process:
    1. Analyze user question and graph schema
    2. Generate Cypher query using LLM 
    3. Execute query against Neo4j
    4. Generate natural language answer from results
    """
    
    def __init__(self):
        super().__init__(
            name="Direct Cypher",
            description="Schema-aware Cypher generation from natural language"
        )
        
        self.schema_analyzer = SchemaAnalyzer(neo4j_client)
        self.query_executor = QueryExecutor(neo4j_client)
        self._schema_cache = None
        
    async def process_query(
        self,
        question: str,
        llm_provider: str = "mistral",
        **kwargs
    ) -> PipelineResult:
        """Process a natural language question using Direct Cypher approach"""
        
        start_time = time.time()
        
        try:
            # Step 1: Get LLM client
            llm_client = create_llm_client(llm_provider)
            if not llm_client:
                return PipelineResult(
                    answer="",
                    approach=self.name,
                    llm_provider=llm_provider,
                    execution_time_seconds=time.time() - start_time,
                    success=False,
                    error_message=f"LLM provider {llm_provider} not available",
                    error_stage="llm_client_init"
                )
            
            # Step 2: Analyze question and prepare schema context
            schema_context = await self._get_schema_context()
            
            # Step 3: Generate Cypher query
            cypher_response = await self._generate_cypher_query(
                question, schema_context, llm_client
            )
            
            if not cypher_response or not cypher_response.text.strip():
                return PipelineResult(
                    answer="",
                    approach=self.name,
                    llm_provider=llm_provider,
                    execution_time_seconds=time.time() - start_time,
                    success=False,
                    error_message="Failed to generate Cypher query",
                    error_stage="cypher_generation",
                    llm_response=cypher_response
                )
            
            # Step 4: Execute Cypher query
            cypher_query = self._extract_cypher_from_response(cypher_response.text)
            
            query_result = await self.query_executor.execute_query_safely(
                cypher_query,
                max_complexity=4,
                allow_write=False
            )
            
            if not query_result.success:
                return PipelineResult(
                    answer="",
                    approach=self.name,
                    llm_provider=llm_provider,
                    execution_time_seconds=time.time() - start_time,
                    success=False,
                    error_message=query_result.error_message,
                    error_stage="cypher_execution",
                    generated_cypher=cypher_query,
                    llm_response=cypher_response
                )
            
            # Step 5: Generate natural language answer from results
            answer_response = await self._generate_answer_from_results(
                question, cypher_query, query_result.records, llm_client
            )
            
            execution_time = time.time() - start_time
            
            result = PipelineResult(
                answer=answer_response.text if answer_response and answer_response.text.strip() else "Unable to generate answer",
                approach=self.name,
                llm_provider=llm_provider,
                execution_time_seconds=execution_time,
                success=bool(answer_response and answer_response.text.strip()),
                generated_cypher=cypher_query,
                cypher_results=query_result.records,
                llm_response=answer_response,
                metadata={
                    "cypher_generation_response": cypher_response.text,
                    "query_execution_time": query_result.execution_time_seconds,
                    "records_returned": len(query_result.records)
                }
            )
            
            self.update_stats(result)
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            result = PipelineResult(
                answer="",
                approach=self.name,
                llm_provider=llm_provider,
                execution_time_seconds=execution_time,
                success=False,
                error_message=str(e),
                error_stage="unknown"
            )
            self.update_stats(result)
            return result
    
    async def _get_schema_context(self) -> str:
        """Get schema context for Cypher generation"""
        
        if self._schema_cache is None:
            self._schema_cache = await self.schema_analyzer.get_schema_for_cypher_generation()
        
        return self._schema_cache
    
    async def _generate_cypher_query(
        self,
        question: str,
        schema_context: str,
        llm_client
    ):
        """Generate Cypher query from natural language question"""
        
        system_prompt = self._get_cypher_generation_system_prompt()
        
        user_prompt = f"""
Based on the following Neo4j graph schema, generate a Cypher query to answer this question:

QUESTION: {question}

GRAPH SCHEMA:
{schema_context}

IMPORTANT GUIDELINES:
1. Return ONLY the Cypher query, no additional text
2. Use proper node labels and relationship types from the schema
3. Include appropriate WHERE clauses for filtering
4. Add LIMIT clauses for performance (default: LIMIT 100)
5. For temporal queries, use the Year nodes and :IN_YEAR relationships
6. CRITICAL: Year nodes use the year property, e.g., (y:Year {{year: 1964}}) NOT {{value: 1964}}
7. For geographic queries, use HistoricalOrtsteil and HistoricalBezirk nodes
8. Remember the political timeline: 1946-1960 (unified) vs 1961+ (east/west division)

Generate the Cypher query:
"""
        
        return await llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=settings.cypher_generation_temperature,
            max_tokens=500
        )
    
    def _get_cypher_generation_system_prompt(self) -> str:
        """Get system prompt for Cypher generation"""
        
        return """You are an expert Neo4j Cypher query generator for a historical Berlin transport network database (1946-1989).

Your task is to convert natural language questions into precise Cypher queries that leverage the temporal and spatial modeling of the database.

Key principles:
- Focus on accuracy and specificity
- Use temporal filtering with Year nodes when time periods are mentioned
- Respect the political geography (east_west property) and administrative hierarchy
- Apply appropriate aggregations and ordering
- Always include reasonable LIMIT clauses for performance
- Return only the Cypher query, no explanations

You understand:
- Transport types: tram, u-bahn, s-bahn, autobus, ferry, oberleitungsbus
- Political divisions: unified (1946-1960), east/west (1961+)
- Administrative hierarchy: Station → HistoricalOrtsteil → HistoricalBezirk
- Temporal modeling: entities linked to specific Year nodes
- Line evolution: some lines changed types over time

Generate clean, efficient Cypher queries that directly answer the question."""
    
    def _extract_cypher_from_response(self, response_text: str) -> str:
        """Extract Cypher query from LLM response"""
        
        # Remove common prefixes/suffixes
        text = response_text.strip()
        
        # Remove code block markers
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```cypher or ```)
            lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        
        # Remove common prefixes
        prefixes_to_remove = [
            "cypher:",
            "query:",
            "here's the query:",
            "the cypher query is:",
        ]
        
        text_lower = text.lower()
        for prefix in prefixes_to_remove:
            if text_lower.startswith(prefix):
                text = text[len(prefix):].strip()
                break
        
        return text.strip()
    
    async def _generate_answer_from_results(
        self,
        question: str,
        cypher_query: str,
        results: List[Dict[str, Any]],
        llm_client
    ):
        """Generate natural language answer from Cypher query results"""
        
        system_prompt = """You are an expert at interpreting Neo4j query results and generating clear, informative answers about historical Berlin transport networks.

Your task is to:
1. Analyze the query results in context of the original question
2. Provide a clear, factual answer based on the data
3. Include relevant historical context when appropriate
4. If no results were found, explain what this means
5. Be concise but informative

Focus on historical accuracy and transportation domain expertise."""

        # Limit results size for token efficiency
        results_sample = results[:20] if len(results) > 20 else results
        
        user_prompt = f"""
Original Question: {question}

Cypher Query Used: {cypher_query}

Query Results ({len(results)} total records, showing first {len(results_sample)}):
{json.dumps(results_sample, indent=2, default=str)}

Based on these results, provide a clear and informative answer to the original question. Include relevant numbers, names, and historical context when appropriate.

Answer:
"""
        
        return await llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=300
        )
    
    def get_required_capabilities(self) -> List[str]:
        """Return required capabilities for this pipeline"""
        return [
            "cypher_generation",
            "schema_analysis", 
            "query_execution",
            "result_interpretation",
            "temporal_modeling",
            "geographic_analysis"
        ] 