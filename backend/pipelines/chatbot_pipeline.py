"""
Chatbot Pipeline - Conversational interface with streaming support
Extends DirectCypherPipeline with query relevance detection and context management
"""

import time
import json
from typing import Optional, Dict, Any, List, AsyncGenerator
from dataclasses import dataclass
from .direct_cypher_pipeline import DirectCypherPipeline
from .base_pipeline import BasePipeline, PipelineResult
from .no_rag_pipeline import NoRAGPipeline
from .multi_query_cypher_pipeline import MultiQueryCypherPipeline
from .vector_pipeline import VectorPipeline
from .path_traversal_pipeline import PathTraversalPipeline
from .graph_embedding_pipeline import GraphEmbeddingPipeline
from .hybrid_pipeline import HybridPipeline
from .graphrag_transport_pipeline import GraphRAGTransportPipeline
from ..llm_clients.client_factory import create_llm_client
from ..services.route_planning_service import (
    get_route_planning_service, 
    RouteRequest, 
    RouteResponse,
    RouteOption
)

@dataclass
class ConversationContext:
    """Context for managing conversation history and state"""
    session_id: str
    history: List[Dict[str, Any]]
    last_query_type: Optional[str] = None
    last_entities: Optional[List[str]] = None
    user_location_context: Optional[Dict[str, Any]] = None

@dataclass
class ChatResponse:
    """Response from the chatbot with streaming support"""
    message: str
    is_streaming: bool = False
    query_type: str = "unknown"
    used_database: bool = False
    suggested_questions: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class ChatbotPipeline(DirectCypherPipeline):
    """
    Conversational chatbot pipeline that intelligently routes queries to appropriate approaches
    
    Features:
    - Query relevance detection (database vs general knowledge)
    - Conversational context management  
    - Streaming response support
    - Route planning capabilities
    - Fallback to no-RAG when appropriate
    """
    
    def __init__(self):
        super().__init__()
        self.name = "Chatbot"
        self.description = "Conversational interface with intelligent query routing"
        self.no_rag_pipeline = NoRAGPipeline()
        self.contexts: Dict[str, ConversationContext] = {}
        
        # Initialize all available pipelines
        self.pipelines = {
            "direct_cypher": DirectCypherPipeline(),
            "multi_query_cypher": MultiQueryCypherPipeline(),
            "vector": VectorPipeline(),
            "path_traversal": PathTraversalPipeline(),
            "graph_embedding": GraphEmbeddingPipeline(),
            "hybrid": HybridPipeline(),
            "graphrag_transport": GraphRAGTransportPipeline(),
            "no_rag": self.no_rag_pipeline
        }
        
    async def chat_response(
        self,
        message: str,
        session_id: str = "default",
        llm_provider: str = "openai",
        stream: bool = False,
        **kwargs
    ) -> AsyncGenerator[ChatResponse, None]:
        """
        Generate chatbot response with streaming support
        
        Args:
            message: User's input message
            session_id: Conversation session identifier
            llm_provider: LLM provider to use
            stream: Whether to stream the response
            **kwargs: Additional parameters
            
        Yields:
            ChatResponse objects with message chunks or final response
        """
        
        # Get or create conversation context
        context = self.contexts.get(session_id, ConversationContext(session_id=session_id, history=[]))
        
        # Add user message to history
        context.history.append({
            "role": "user",
            "content": message,
            "timestamp": time.time()
        })
        
        try:
            # Step 1: Determine query relevance and type
            query_analysis = await self._analyze_query_relevance(message, context, llm_provider)
            
            # Step 2: Route to appropriate pipeline
            if query_analysis["is_database_relevant"]:
                # Use database-backed approach
                async for response in self._handle_database_query(message, context, llm_provider, stream, query_analysis):
                    yield response
            else:
                # Use no-RAG approach with suggestions
                async for response in self._handle_general_query(message, context, llm_provider, stream, query_analysis):
                    yield response
                    
        except Exception as e:
            # Error handling
            yield ChatResponse(
                message=f"I apologize, but I encountered an error: {str(e)}. Please try rephrasing your question.",
                query_type="error",
                used_database=False,
                metadata={"error": str(e)}
            )
        
        # Update context
        self.contexts[session_id] = context
    
    async def _analyze_query_relevance(
        self,
        message: str,
        context: ConversationContext,
        llm_provider: str
    ) -> Dict[str, Any]:
        """
        Analyze whether the query is relevant to the database and what type it is
        
        Returns:
            Analysis results with relevance and query type classification
        """
        
        llm_client = create_llm_client(llm_provider)
        
        if not llm_client:
            return {
                "is_database_relevant": False,
                "query_type": "general",
                "entities": [],
                "confidence": 0.0,
                "reasoning": "LLM client unavailable"
            }
        
        # Build conversation history context
        history_context = ""
        if context.history:
            recent_history = context.history[-3:]  # Last 3 exchanges
            history_context = "\n".join([
                f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                for msg in recent_history[:-1]  # Exclude current message
            ])
        
        system_prompt = """You are a query classifier for a historical Berlin transport network database (1946-1989).

Your task is to determine:
1. Whether the query is relevant to the database (YES/NO)
2. What type of query it is
3. Key entities or concepts mentioned

Database contains:
- Stations (names, locations, types, east/west)
- Lines (frequencies, capacities, types)
- Years (1946-1989)
- Administrative areas (Ortsteile, Bezirke)
- Transport connections and relationships

Query types:
- route_planning: Finding routes between locations
- factual: Facts about stations, lines, frequencies
- temporal: Changes over time
- spatial: Geographic/administrative queries
- relationship: Connections between entities
- multi_step: Complex analytical questions requiring multiple queries
- similarity: Finding similar entities or patterns
- comparison: Comparing different entities or time periods
- general: Not related to transport database

Return JSON with:
{
  "is_database_relevant": boolean,
  "query_type": string,
  "entities": [list of key entities],
  "confidence": float,
  "reasoning": string,
  "complexity": "simple|medium|complex",
  "recommended_pipeline": "direct_cypher|multi_query_cypher|vector|path_traversal|graph_embedding|no_rag"
}"""

        user_prompt = f"""
Conversation history:
{history_context}

Current query: {message}

Analyze this query and classify it:
"""
        
        response = await llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=200
        )
        
        try:
            # Parse JSON response
            analysis = json.loads(response.text.strip())
            return analysis
        except json.JSONDecodeError:
            # Fallback: assume database relevant if contains transport keywords
            transport_keywords = ['station', 'line', 'tram', 'bus', 'transport', 'berlin', 'route', 'frequency']
            is_relevant = any(keyword in message.lower() for keyword in transport_keywords)
            return {
                "is_database_relevant": is_relevant,
                "query_type": "unknown",
                "entities": [],
                "confidence": 0.5,
                "reasoning": "Fallback analysis due to parsing error"
            }
    
    def _select_pipeline(self, query_analysis: Dict[str, Any]) -> BasePipeline:
        """Select the optimal pipeline based on query analysis"""
        
        query_type = query_analysis.get("query_type", "factual")
        complexity = query_analysis.get("complexity", "simple")
        recommended_pipeline = query_analysis.get("recommended_pipeline", "direct_cypher")
        entities = query_analysis.get("entities", [])
        
        # Route based on query type and complexity
        if query_type == "relationship" and len(entities) >= 2:
            # Path traversal is best for finding connections between entities
            return self.pipelines["path_traversal"]
        
        elif query_type == "similarity" or query_type == "comparison":
            # Graph embeddings for structural similarity
            return self.pipelines["graph_embedding"]
        
        elif query_type == "multi_step" or complexity == "complex":
            # Check if this is a global transport network question
            global_transport_indicators = [
                "overall", "main", "key", "primary", "major", "most important",
                "trends", "patterns", "development", "evolution", "changes",
                "comparison", "compare", "differences", "similarities",
                "network", "system", "infrastructure", "coverage",
                "east", "west", "political", "division", "sector"
            ]
            
            query_lower = query_analysis.get("question", "").lower()
            if any(indicator in query_lower for indicator in global_transport_indicators):
                # Use GraphRAG for global transport analysis
                return self.pipelines["graphrag_transport"]
            else:
                # Multi-query pipeline for other complex analytical questions
                return self.pipelines["multi_query_cypher"]
        
        elif query_type == "temporal" and "change" in query_analysis.get("reasoning", "").lower():
            # Check if this is about transport network evolution
            if any(term in query_analysis.get("question", "").lower() for term in ["transport", "network", "development", "infrastructure"]):
                return self.pipelines["graphrag_transport"]
            else:
                # Multi-query for other temporal analysis
                return self.pipelines["multi_query_cypher"]
        
        elif query_type == "factual" and complexity == "simple":
            # Direct Cypher for simple factual queries
            return self.pipelines["direct_cypher"]
        
        elif recommended_pipeline in self.pipelines:
            # Use LLM recommendation if available
            return self.pipelines[recommended_pipeline]
        
        else:
            # Default to direct Cypher with vector fallback
            try:
                # Try direct Cypher first
                return self.pipelines["direct_cypher"]
            except Exception:
                # Fallback to vector pipeline
                return self.pipelines["vector"]
    
    async def _handle_database_query(
        self,
        message: str,
        context: ConversationContext,
        llm_provider: str,
        stream: bool,
        query_analysis: Dict[str, Any]
    ) -> AsyncGenerator[ChatResponse, None]:
        """Handle queries that should use the database"""
        
        if stream:
            # Stream initial acknowledgment
            yield ChatResponse(
                message="Let me search the historical Berlin transport database for you...",
                is_streaming=True,
                query_type=query_analysis["query_type"],
                used_database=True
            )
        
        # Special handling for route planning queries
        if query_analysis["query_type"] == "route_planning":
            async for response in self._handle_route_planning(message, context, llm_provider, stream):
                yield response
        else:
            # Use intelligent pipeline selection
            selected_pipeline = self._select_pipeline(query_analysis)
            
            if stream:
                yield ChatResponse(
                    message=f"Using {selected_pipeline.name} pipeline for optimal results...",
                    is_streaming=True,
                    query_type=query_analysis["query_type"],
                    used_database=True,
                    metadata={"selected_pipeline": selected_pipeline.name}
                )
            
            result = await selected_pipeline.process_query(message, llm_provider)
            
            if result.success:
                # Format response conversationally
                conversational_response = await self._format_conversational_response(
                    message, result.answer, context, llm_provider
                )
                
                yield ChatResponse(
                    message=conversational_response,
                    query_type=query_analysis["query_type"],
                    used_database=True,
                    metadata={
                        "execution_time": result.execution_time_seconds,
                        "cypher_query": result.generated_cypher,
                        "records_returned": len(result.cypher_results) if result.cypher_results else 0,
                        "selected_pipeline": selected_pipeline.name,
                        "pipeline_description": selected_pipeline.description,
                        "query_complexity": query_analysis.get("complexity", "simple"),
                        "confidence": query_analysis.get("confidence", 0.0)
                    }
                )
            else:
                # Database query failed, fall back to no-RAG with explanation
                yield ChatResponse(
                    message=f"I couldn't find specific information in the database about that. {result.error_message or 'The query might be too complex or the data might not be available.'} Let me try to help with general knowledge instead.",
                    query_type="fallback",
                    used_database=False
                )
                
                # Try no-RAG fallback
                no_rag_result = await self.no_rag_pipeline.process_query(message, llm_provider)
                if no_rag_result.success:
                    yield ChatResponse(
                        message=no_rag_result.answer,
                        query_type="no_rag_fallback",
                        used_database=False,
                        suggested_questions=self._generate_suggested_questions(query_analysis["entities"])
                    )
    
    async def _handle_general_query(
        self,
        message: str,
        context: ConversationContext,
        llm_provider: str,
        stream: bool,
        query_analysis: Dict[str, Any]
    ) -> AsyncGenerator[ChatResponse, None]:
        """Handle queries that don't require the database"""
        
        # Use no-RAG pipeline for general queries
        result = await self.no_rag_pipeline.process_query(message, llm_provider)
        
        if result.success:
            # Enhance response with database suggestions
            enhanced_response = await self._enhance_general_response(
                message, result.answer, context, llm_provider
            )
            
            yield ChatResponse(
                message=enhanced_response,
                query_type=query_analysis["query_type"],
                used_database=False,
                suggested_questions=self._generate_suggested_questions(query_analysis["entities"])
            )
        else:
            yield ChatResponse(
                message="I apologize, but I'm having trouble understanding your question. Could you please rephrase it or ask something more specific?",
                query_type="error",
                used_database=False
            )
    
    async def _handle_route_planning(
        self,
        message: str,
        context: ConversationContext,
        llm_provider: str,
        stream: bool
    ) -> AsyncGenerator[ChatResponse, None]:
        """Handle route planning queries using the enhanced route planning service"""
        
        # Extract addresses and year from the message
        route_info = await self._extract_route_info(message, llm_provider)
        
        if stream:
            yield ChatResponse(
                message=f"Planning route from {route_info.get('origin', 'unknown')} to {route_info.get('destination', 'unknown')} in {route_info.get('year', 'current time')}...",
                is_streaming=True,
                query_type="route_planning",
                used_database=True
            )
        
        try:
            # Get the route planning service
            route_service = get_route_planning_service()
            
            # Create route request
            route_request = RouteRequest(
                origin_address=route_info.get('origin', ''),
                destination_address=route_info.get('destination', ''),
                year=route_info.get('year'),
                transport_preferences=route_info.get('transport_preferences', [])
            )
            
            if stream:
                yield ChatResponse(
                    message="Finding nearby stations and calculating optimal route...",
                    is_streaming=True,
                    query_type="route_planning",
                    used_database=True
                )
            
            # Execute route planning
            route_response = await route_service.plan_route(route_request)
            
            # Safely access routes attribute
            routes = getattr(route_response, 'routes', None) if route_response else None
            
            if route_response.success and routes and len(routes) > 0:
                # Format successful route response
                best_route = routes[0]  # Take the best route
                
                route_response_text = await self._format_enhanced_route_response(
                    message, best_route, route_response, llm_provider
                )
                
                yield ChatResponse(
                    message=route_response_text,
                    query_type="route_planning",
                    used_database=True,
                    metadata={
                        "route_info": route_info,
                        "total_routes_found": len(routes),
                        "best_route_time": best_route.estimated_total_time_minutes,
                        "best_route_distance": best_route.total_distance_km,
                        "geocoding_successful": route_response.geocoding_results is not None
                    }
                )
            else:
                # Enhanced error handling with specific failure details
                error_details = []
                
                if route_response.geocoding_results:
                    origin_geocoding = route_response.geocoding_results.get('origin')
                    dest_geocoding = route_response.geocoding_results.get('destination')
                    
                    if origin_geocoding and not origin_geocoding.found:
                        error_details.append(f"Could not find origin address: {route_info.get('origin', 'unknown')}")
                    if dest_geocoding and not dest_geocoding.found:
                        error_details.append(f"Could not find destination address: {route_info.get('destination', 'unknown')}")
                
                if not error_details and route_response.error_message:
                    error_details.append(route_response.error_message)
                
                if not error_details:
                    error_details.append("No nearby stations found within walking distance")
                
                error_message = f"I couldn't plan a specific route: {'; '.join(error_details)}. "
                
                if route_info.get('year'):
                    error_message += f"The historical transport network in {route_info.get('year')} might not have had connections between those areas, or the data might not be available for that time period."
                else:
                    error_message += "Try specifying a year between 1946-1989 for better historical routing."
                
                yield ChatResponse(
                    message=error_message,
                    query_type="route_planning_failed",
                    used_database=True,
                    suggested_questions=[
                        f"What transport lines were available in {route_info.get('year', 'that time period')}?",
                        f"What stations were near {route_info.get('origin', 'that area')}?",
                        f"How did the transport network change around {route_info.get('year', 'that time')}?"
                    ],
                    metadata={
                        "route_info": route_info,
                        "error_details": error_details,
                        "geocoding_results": route_response.geocoding_results if route_response else None
                    }
                )
                
        except Exception as e:
            # Handle unexpected errors
            yield ChatResponse(
                message=f"I encountered an error while planning your route: {str(e)}. Please try rephrasing your request or check if the addresses are valid Berlin locations.",
                query_type="route_planning_error",
                used_database=False,
                metadata={
                    "error": str(e),
                    "route_info": route_info
                }
            )
    
    async def _extract_route_info(self, message: str, llm_provider: str) -> Dict[str, Any]:
        """Extract route information from natural language"""
        
        llm_client = create_llm_client(llm_provider)
        
        if not llm_client:
            return {
                "origin": "unknown",
                "destination": "unknown",
                "year": None,
                "transport_preferences": [],
                "extracted_successfully": False
            }
        
        system_prompt = """Extract route planning information from the user's message.
        
Return JSON with:
{
  "origin": "starting location/address",
  "destination": "ending location/address", 
  "year": integer year,
  "transport_preferences": ["any specific transport types mentioned"],
  "extracted_successfully": boolean
}"""
        
        response = await llm_client.generate(
            prompt=f"Extract route information from: {message}",
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=150
        )
        
        try:
            return json.loads(response.text.strip())
        except json.JSONDecodeError:
            return {
                "origin": "unknown",
                "destination": "unknown",
                "year": None,
                "transport_preferences": [],
                "extracted_successfully": False
            }
    
    async def _generate_route_planning_query(self, route_info: Dict[str, Any], llm_provider: str) -> str:
        """Generate a natural language query for route planning"""
        
        origin = route_info.get('origin', 'unknown location')
        destination = route_info.get('destination', 'unknown location')
        year = route_info.get('year', 'unknown year')
        
        return f"What transport connections were available between areas near {origin} and {destination} in {year}? Include station names, line types, and frequencies if available."
    
    async def _format_conversational_response(
        self,
        original_message: str,
        database_answer: str,
        context: ConversationContext,
        llm_provider: str
    ) -> str:
        """Format database response in a conversational tone"""
        
        llm_client = create_llm_client(llm_provider)
        
        if not llm_client:
            return database_answer  # Return original answer if LLM not available
        
        system_prompt = """You are a friendly, knowledgeable assistant discussing historical Berlin transport.
        
Make the response conversational and engaging while keeping all factual information accurate.
Add context and historical perspective where relevant.
Keep the response concise but informative. You are an tool to educate and assist the user, especially with the data being provided to you."""
        
        user_prompt = f"""
Original question: {original_message}

Database answer: {database_answer}

Please reformat this as a natural, conversational response:
"""
        
        response = await llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=300
        )
        
        return response.text.strip()
    
    async def _enhance_general_response(
        self,
        original_message: str,
        no_rag_answer: str,
        context: ConversationContext,
        llm_provider: str
    ) -> str:
        """Enhance general response with database connection suggestions"""
        
        llm_client = create_llm_client(llm_provider)
        
        if not llm_client:
            return no_rag_answer  # Return original answer if LLM not available
        
        system_prompt = """You are responding to a general question, but you also have access to a historical Berlin transport database (1946-1989).
        
Provide the general answer, then suggest how the user might explore related information from the transport database.
Be helpful, informative and connecting, not pushy."""
        
        user_prompt = f"""
Original question: {original_message}

General answer: {no_rag_answer}

Please enhance this response by suggesting relevant transport database queries:
"""
        
        response = await llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=350
        )
        
        return response.text.strip()
    
    async def _format_route_response(
        self,
        original_message: str,
        result: PipelineResult,
        route_info: Dict[str, Any],
        llm_provider: str
    ) -> str:
        """Format route planning response"""
        
        llm_client = create_llm_client(llm_provider)
        
        if not llm_client:
            return result.answer  # Return original answer if LLM not available
        
        system_prompt = """You are helping someone understand historical Berlin transport routes.
        
Format the database results as a helpful route planning response.
Include practical details like line types, frequencies, and any historical context.
Make it engaging and informative."""
        
        user_prompt = f"""
Original request: {original_message}

Route information: {json.dumps(route_info, indent=2)}

Database results: {result.answer}

Please format this as a helpful route planning response:
"""
        
        response = await llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=400
        )
        
        return response.text.strip()
    
    async def _format_enhanced_route_response(
        self,
        original_message: str,
        best_route: RouteOption,
        route_response: RouteResponse,
        llm_provider: str
    ) -> str:
        """Format the enhanced route response with detailed information"""
        
        llm_client = create_llm_client(llm_provider)
        
        # Build detailed route information
        route_summary = []
        
        # Add geocoding results
        origin_geocoding = route_response.geocoding_results.get('origin')
        dest_geocoding = route_response.geocoding_results.get('destination')
        
        if origin_geocoding and origin_geocoding.found:
            route_summary.append(f"Origin: {origin_geocoding.display_name}")
        if dest_geocoding and dest_geocoding.found:
            route_summary.append(f"Destination: {dest_geocoding.display_name}")
        
        # Add station information
        route_summary.append(f"Nearest origin station: {best_route.origin_station.station_name} ({best_route.origin_station.transport_type}, {best_route.origin_station.distance_km:.1f}km walk)")
        route_summary.append(f"Nearest destination station: {best_route.destination_station.station_name} ({best_route.destination_station.transport_type}, {best_route.destination_station.distance_km:.1f}km walk)")
        
        # Add route steps
        route_summary.append("\nRoute steps:")
        for i, step in enumerate(best_route.steps, 1):
            if step.step_type == 'walk':
                route_summary.append(f"{i}. Walk {step.distance_km:.1f}km from {step.from_location} to {step.to_location} (~{step.estimated_time_minutes:.0f} min)")
            elif step.step_type == 'transit':
                route_summary.append(f"{i}. {step.description} (~{step.estimated_time_minutes:.0f} min)")
        
        # Add totals
        route_summary.append(f"\nTotal distance: {best_route.total_distance_km:.1f}km")
        route_summary.append(f"Total walking: {best_route.total_walking_distance_km:.1f}km")
        route_summary.append(f"Estimated time: {best_route.estimated_total_time_minutes:.0f} minutes")
        
        if best_route.year:
            route_summary.append(f"Historical context: {best_route.year}")
        
        route_info_text = "\n".join(route_summary)
        
        if not llm_client:
            return f"Here's your route for {original_message}:\n\n{route_info_text}"
        
        system_prompt = """You are a helpful assistant providing historical Berlin transport route planning.
        
Format the route information in a conversational, helpful way. Include practical details and historical context.
Make it engaging and easy to understand, while preserving all the important routing information."""
        
        user_prompt = f"""
Original request: {original_message}

Detailed route information:
{route_info_text}

Please format this as a helpful, conversational route planning response:
"""
        
        response = await llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=500
        )
        
        return response.text.strip()
    
    def _generate_suggested_questions(self, entities: List[str]) -> List[str]:
        """Generate suggested questions based on entities"""
        
        suggestions = [
            "What transport lines were available in 1971?",
            "How did the Berlin transport network change after 1961?",
            "What were the main stations in East vs West Berlin?",
            "Which lines had the highest frequency in the 1960s?",
            "How did administrative areas affect transport planning?"
        ]
        
        # Add entity-specific suggestions
        if entities:
            for entity in entities[:2]:  # Max 2 entity-specific suggestions
                suggestions.append(f"Tell me more about {entity} in the Berlin transport network")
        
        return suggestions[:3]  # Return max 3 suggestions
    
    def get_conversation_context(self, session_id: str) -> Optional[ConversationContext]:
        """Get conversation context for a session"""
        return self.contexts.get(session_id)
    
    def clear_conversation_context(self, session_id: str) -> None:
        """Clear conversation context for a session"""
        if session_id in self.contexts:
            del self.contexts[session_id] 