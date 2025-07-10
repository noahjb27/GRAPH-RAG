"""
Multi-Query Cypher Pipeline - Enhanced version that can handle complex questions requiring multiple Cypher queries
Extends the Direct Cypher Pipeline with multi-query planning and execution
"""

import time
import json
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from .direct_cypher_pipeline import DirectCypherPipeline
from .base_pipeline import PipelineResult
from ..llm_clients.client_factory import create_llm_client
from ..database.query_executor import QueryExecutor
from ..config import settings

@dataclass
class QueryPlan:
    """Plan for executing one or more Cypher queries"""
    queries: List[str]
    integration_strategy: str  # "single", "aggregate", "compare", "correlate"
    dependencies: List[List[int]]  # Query dependencies (which queries depend on which)
    reasoning: str  # Why this plan was chosen

@dataclass
class QueryResult:
    """Result from executing a single query in a multi-query plan"""
    query: str
    records: List[Dict[str, Any]]
    success: bool
    error_message: Optional[str] = None
    execution_time: float = 0.0

class MultiQueryCypherPipeline(DirectCypherPipeline):
    """
    Enhanced Cypher pipeline that can break complex questions into multiple queries
    
    Process:
    1. Analyze question complexity and determine if multi-query is needed
    2. Generate query plan (single or multiple queries)
    3. Execute queries in dependency order
    4. Integrate results from multiple queries
    5. Generate comprehensive answer
    """
    
    def __init__(self):
        super().__init__()
        self.name = "Multi-Query Cypher"
        self.description = "Enhanced Cypher generation with multi-query planning for complex questions"
        
        # Complexity indicators that suggest multi-query approach
        self.multi_query_indicators = [
            "compare", "comparison", "between", "before and after", "change",
            "difference", "evolution", "timeline", "both", "as well as",
            "in addition to", "meanwhile", "at the same time", "correlation",
            "relationship between", "impact of", "how did", "what happened to",
            "breakdown by", "analysis of", "multiple", "various"
        ]
    
    async def process_query(
        self,
        question: str,
        llm_provider: str = "mistral",
        **kwargs
    ) -> PipelineResult:
        """Process a natural language question using Multi-Query Cypher approach"""
        
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
            
            # Step 2: Analyze question complexity
            needs_multi_query = await self._analyze_question_complexity(question)
            
            # Step 3: Generate query plan
            if needs_multi_query:
                print("🎯 Complex question detected - attempting multi-query approach")
                query_plan = await self._generate_multi_query_plan(question, llm_client)
                
                if not query_plan or not query_plan.queries:
                    # Fall back to single query if planning fails
                    print("⚡ Query planning failed - falling back to Direct Cypher approach")
                    result = await super().process_query(question, llm_provider, **kwargs)
                    # Update metadata to indicate fallback
                    if result.metadata is None:
                        result.metadata = {}
                    result.metadata["fallback_reason"] = "query_planning_failed"
                    result.metadata["intended_approach"] = "multi_query"
                    return result
                
                # Execute multi-query plan
                print(f"📋 Query plan created: {query_plan.integration_strategy} strategy with {len(query_plan.queries)} queries")
                return await self._execute_multi_query_plan(question, query_plan, llm_client, start_time)
            
            else:
                # Use single query approach (delegate to parent)
                print("🎯 Simple question detected - using Direct Cypher approach")
                result = await super().process_query(question, llm_provider, **kwargs)
                # Update metadata to indicate intended single query
                if result.metadata is None:
                    result.metadata = {}
                result.metadata["intended_approach"] = "single_query"
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
    
    async def _analyze_question_complexity(self, question: str) -> bool:
        """Analyze if question requires multiple queries (simple heuristic approach)"""
        
        question_lower = question.lower()
        
        # Check for complexity indicators
        indicator_count = sum(1 for indicator in self.multi_query_indicators 
                            if indicator in question_lower)
        
        # Simple heuristic: if question has multiple complexity indicators, use multi-query
        if indicator_count >= 2:
            print(f"🔍 Multi-query triggered by complexity indicators: {indicator_count}")
            return True
        
        # Check for temporal range indicators
        temporal_indicators = ["from", "to", "between", "1960", "1970", "1971", "before", "after"]
        temporal_count = sum(1 for indicator in temporal_indicators 
                           if indicator in question_lower)
        
        # Questions with temporal ranges often need multiple queries
        if temporal_count >= 2:
            print(f"🔍 Multi-query triggered by temporal indicators: {temporal_count}")
            return True
        
        # Check for multiple entity types
        entity_indicators = ["station", "line", "district", "transport", "bezirk", "ortsteil"]
        entity_count = sum(1 for indicator in entity_indicators 
                         if indicator in question_lower)
        
        # Questions asking about multiple entity types may need multiple queries
        if entity_count >= 3:
            print(f"🔍 Multi-query triggered by entity types: {entity_count}")
            return True
        
        # Lower threshold for obvious complex questions
        if any(phrase in question_lower for phrase in ["compare", "comparison"]) and entity_count >= 2:
            print(f"🔍 Multi-query triggered by comparison + entities: {entity_count}")
            return True
        
        print(f"🔍 Single query approach: indicators={indicator_count}, temporal={temporal_count}, entities={entity_count}")
        return False
    
    async def _generate_multi_query_plan(self, question: str, llm_client) -> Optional[QueryPlan]:
        """Generate a plan for multiple Cypher queries"""
        
        schema_context = await self._get_schema_context()
        
        system_prompt = """You are an expert at breaking down complex questions about historical Berlin transport networks into multiple, focused Cypher queries.

CRITICAL: You MUST respond with valid JSON only. No explanations, no markdown, no additional text.

Your task is to analyze a question and determine if it requires multiple queries, then create a plan.

Guidelines:
1. Only suggest multiple queries if the question truly requires it
2. Each query should be focused and answerable independently
3. Identify dependencies between queries
4. Choose appropriate integration strategy

Integration strategies:
- "single": One query is sufficient
- "aggregate": Combine counts, sums, or other aggregations
- "compare": Side-by-side comparison of results
- "correlate": Find relationships between different result sets
- "timeline": Merge temporal data into chronological analysis

REQUIRED OUTPUT FORMAT (valid JSON only):
{
    "queries": ["MATCH (s:Station) RETURN count(s)", "MATCH (l:Line) RETURN count(l)"],
    "integration_strategy": "compare",
    "dependencies": [[], [0]],
    "reasoning": "Why this approach was chosen"
}"""
        
        user_prompt = f"""
Analyze this question about Berlin transport networks and create a query plan:

QUESTION: {question}

GRAPH SCHEMA:
{schema_context}

Important context:
- Database covers Berlin transport 1946-1989
- Political division: unified (1946-1960), east/west (1961+)
- Year nodes use year property: (y:Year {{year: 1964}})
- Transport types: tram, u-bahn, s-bahn, autobus, ferry, oberleitungsbus

If this question can be answered with a single focused query, return:
{{"queries": ["SINGLE_QUERY"], "integration_strategy": "single", "dependencies": [[]], "reasoning": "Single query sufficient"}}

If multiple queries are needed, break it down thoughtfully.

Generate the query plan:
"""
        
        response = await llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=800
        )
        
        if not response or not response.text.strip():
            print("❌ Empty response from LLM for query planning")
            return None
        
        response_text = response.text.strip()
        print(f"🔍 LLM Query Plan Response: {response_text[:200]}...")
        
        # Try to extract JSON from response if it's wrapped in markdown
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            if json_end != -1:
                response_text = response_text[json_start:json_end].strip()
                print(f"🔍 Extracted JSON: {response_text[:200]}...")
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            if json_end != -1:
                response_text = response_text[json_start:json_end].strip()
                print(f"🔍 Extracted from code block: {response_text[:200]}...")
        
        try:
            plan_data = json.loads(response_text)
            print(f"✅ Successfully parsed query plan with {len(plan_data.get('queries', []))} queries")
            return QueryPlan(
                queries=plan_data["queries"],
                integration_strategy=plan_data["integration_strategy"],
                dependencies=plan_data.get("dependencies", [[] for _ in plan_data["queries"]]),
                reasoning=plan_data.get("reasoning", "")
            )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"❌ Failed to parse query plan: {e}")
            print(f"❌ Raw response: {response_text}")
            return None
    
    async def _execute_multi_query_plan(
        self,
        question: str,
        query_plan: QueryPlan,
        llm_client,
        start_time: float
    ) -> PipelineResult:
        """Execute a multi-query plan and integrate results"""
        
        # If only one query, delegate to parent
        if len(query_plan.queries) == 1:
            return await super().process_query(question, llm_client.provider_name)
        
        # Execute queries in dependency order
        query_results = []
        
        print(f"🔄 Executing {len(query_plan.queries)} queries...")
        for i, query in enumerate(query_plan.queries):
            query_start = time.time()
            print(f"🔄 Query {i+1}: {query[:100]}...")
            
            # Execute query safely
            result = await self.query_executor.execute_query_safely(
                query,
                max_complexity=4,
                allow_write=False
            )
            
            execution_time = time.time() - query_start
            query_results.append(QueryResult(
                query=query,
                records=result.records if result.success else [],
                success=result.success,
                error_message=result.error_message,
                execution_time=execution_time
            ))
            
            # Log query result
            if result.success:
                print(f"✅ Query {i+1} completed: {len(result.records)} records ({execution_time:.2f}s)")
            else:
                print(f"❌ Query {i+1} failed: {result.error_message} ({execution_time:.2f}s)")
        
        # Check if we have any successful results
        successful_results = [r for r in query_results if r.success]
        
        if not successful_results:
            return PipelineResult(
                answer="",
                approach=self.name,
                llm_provider=llm_client.provider_name,
                execution_time_seconds=time.time() - start_time,
                success=False,
                error_message="All queries in plan failed",
                error_stage="multi_query_execution"
            )
        
        # Generate integrated answer
        answer_response = await self._generate_integrated_answer(
            question, query_plan, query_results, llm_client
        )
        
        execution_time = time.time() - start_time
        
        # Combine all results for cypher_results field
        all_records = []
        for qr in successful_results:
            all_records.extend(qr.records)
        
        result = PipelineResult(
            answer=answer_response.text if answer_response and answer_response.text.strip() else "Unable to generate integrated answer",
            approach=self.name,
            llm_provider=llm_client.provider_name,
            execution_time_seconds=execution_time,
            success=bool(answer_response and answer_response.text.strip()),
            generated_cypher="\n".join([f"-- QUERY {i+1} --\n{query}" for i, query in enumerate(query_plan.queries)]),
            cypher_results=all_records,  # All results combined
            llm_response=answer_response,
            metadata={
                "intended_approach": "multi_query",
                "actually_used_multi_query": True,
                "query_plan": {
                    "num_queries": len(query_plan.queries),
                    "integration_strategy": query_plan.integration_strategy,
                    "reasoning": query_plan.reasoning
                },
                "individual_queries": [
                    {
                        "query": r.query,
                        "success": r.success,
                        "records_count": len(r.records),
                        "execution_time": r.execution_time,
                        "error": r.error_message
                    }
                    for r in query_results
                ],
                "successful_queries": len(successful_results),
                "failed_queries": len(query_results) - len(successful_results),
                "total_records": len(all_records)
            }
        )
        
        self.update_stats(result)
        return result
    
    async def _generate_integrated_answer(
        self,
        question: str,
        query_plan: QueryPlan,
        query_results: List[QueryResult],
        llm_client
    ):
        """Generate natural language answer from multiple query results"""
        
        system_prompt = """You are an expert at synthesizing information from multiple Neo4j query results to answer complex questions about historical Berlin transport networks.

Your task is to:
1. Analyze results from multiple related queries
2. Integrate the information according to the specified strategy
3. Provide a comprehensive, coherent answer
4. Handle partial results gracefully if some queries failed
5. Include relevant historical context

Focus on creating a unified narrative that addresses the original question completely."""
        
        # Prepare results summary
        results_summary = []
        for i, result in enumerate(query_results):
            if result.success:
                results_summary.append(f"Query {i+1}: {len(result.records)} records")
                results_summary.append(f"Data: {json.dumps(result.records[:5], indent=2, default=str)}")  # First 5 records
            else:
                results_summary.append(f"Query {i+1}: FAILED - {result.error_message}")
        
        user_prompt = f"""
Original Question: {question}

Query Plan Strategy: {query_plan.integration_strategy}
Plan Reasoning: {query_plan.reasoning}

Queries Executed:
{chr(10).join(f"{i+1}. {query}" for i, query in enumerate(query_plan.queries))}

Query Results:
{chr(10).join(results_summary)}

Integration Strategy: {query_plan.integration_strategy}

Based on these multiple query results, provide a comprehensive answer to the original question. 
Integrate the information thoughtfully and provide historical context where relevant.
If some queries failed, work with the available data and note any limitations.

Answer:
"""
        
        return await llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=500
        )
    
    def get_required_capabilities(self) -> List[str]:
        """Return required capabilities for this pipeline"""
        return [
            "multi_query_planning",
            "cypher_generation",
            "schema_analysis",
            "query_execution",
            "result_integration",
            "temporal_modeling",
            "geographic_analysis",
            "dependency_management"
        ] 