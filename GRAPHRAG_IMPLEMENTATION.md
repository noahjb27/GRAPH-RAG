# GraphRAG Transport Network Implementation

## Overview

This document describes the complete implementation of Microsoft's GraphRAG methodology adapted for hierarchical transport network analysis in the Berlin Historical Transport Graph-RAG Research System.

## 🎯 What is GraphRAG?

GraphRAG (Graph Retrieval-Augmented Generation) is Microsoft's approach to analyzing large datasets through:

1. **Hierarchical Community Detection**: Breaking complex networks into meaningful communities
2. **LLM-based Summarization**: Generating comprehensive summaries of each community  
3. **Global vs Local Query Routing**: Using appropriate analysis methods based on question scope
4. **Map-Reduce Processing**: Analyzing communities in parallel and synthesizing results

## 🚀 Our Implementation

### Adaptation for Transport Networks

Instead of text documents, we analyze **structured transport graph data** with:

- **Synchronic Analysis**: Network state at specific points in time (1946, 1961, 1970, etc.)
- **Diachronic Analysis**: Evolution patterns across historical periods
- **Multi-dimensional Communities**: Geographic, operational, temporal, and service-type clustering

### Core Components

#### 1. Community Detection (`TransportCommunityDetector`)

**Geographic Communities**: Based on administrative boundaries (Bezirk/Ortsteil)
```python
# Example: 71 geographic communities detected
# Each represents a district with its transport infrastructure
```

**Operational Communities**: Topological clustering using Louvain algorithm
```python
# Example: 30 operational clusters based on connectivity patterns
# Reveals natural transport network structure
```

**Temporal Communities**: 
- **Era-based**: Post-war (1946-1949), Pre-wall (1950-1961), Wall era (1962-1975)
- **Evolution patterns**: Single-year, short-term, medium-term, long-term operations
- **Snapshots**: Network state in key years (1946, 1961, 1970, 1989)

**Service Type Communities**: By transport mode (U-Bahn, S-Bahn, Tram, Bus, Ferry)

#### 2. Community Summarization (`TransportCommunitySummarizer`)

Generates LLM-powered summaries covering:
- **Network Characteristics**: Infrastructure and connectivity patterns
- **Service Quality**: Operational efficiency and capacity
- **Geographic Significance**: Coverage and accessibility
- **Historical Development**: Evolution within political context
- **Political Impact**: Effects of East/West division
- **Strategic Importance**: Role in overall transport system

#### 3. GraphRAG Pipeline (`GraphRAGTransportPipeline`)

**Question Type Analysis**: Determines if query requires global or local analysis
- **Global**: System-wide questions needing multiple communities
- **Local**: Specific questions about particular areas/lines

**Map-Reduce Processing**: 
1. Generate answers from relevant community summaries
2. Reduce/synthesize into comprehensive final answer

#### 4. Persistent Caching (`GraphRAGCache`)

**Community Cache**: Stores detection results to avoid recomputation
**Summary Cache**: Stores LLM-generated summaries by provider
**Hierarchical Storage**: Organized by parameters (year, types, etc.)

## 📁 File Structure

```
backend/pipelines/
├── graphrag_transport_pipeline.py    # Main pipeline implementation
├── graphrag_cache.py                 # Persistent caching system
├── graphrag_community_detector.py    # Community detection algorithms
└── graphrag_summarizer.py           # LLM-based summarization

scripts/
├── graphrag_cache_manager.py        # Cache management utilities
├── deploy_graphrag_production.py    # Production deployment
└── test_community_summaries.py      # Testing and validation

frontend/src/app/graphrag/
└── page.tsx                         # GraphRAG interface

docs/
└── graphrag_transport_pipeline_guide.md  # Detailed documentation
```

## 🛠️ Production Deployment

### Quick Start

1. **Install Dependencies**:
```bash
pip install networkx sklearn graspologic
```

2. **Deploy for Production**:
```bash
# Full deployment (all scenarios)
python deploy_graphrag_production.py

# Quick deployment (essential scenarios only)  
python deploy_graphrag_production.py --quick

# Validation only
python deploy_graphrag_production.py --validate-only
```

3. **Manual Cache Management**:
```bash
# Warm cache for common queries
python graphrag_cache_manager.py warm

# Check cache statistics
python graphrag_cache_manager.py stats

# Clear cache
python graphrag_cache_manager.py clear

# Validate cache integrity
python graphrag_cache_manager.py validate
```

### API Integration

GraphRAG is fully integrated into the main API:

```bash
# GraphRAG query endpoint
POST /graphrag/query
{
  "question": "How did transport evolve during the wall era?",
  "llm_provider": "openai",
  "year_filter": 1970,
  "community_types": ["temporal", "geographic"]
}

# Cache management endpoints  
GET /graphrag/cache/stats
POST /graphrag/cache/manage
```

### Frontend Interface

Access the GraphRAG interface at `http://localhost:3000/graphrag`:
- **Query Interface**: Submit questions with filtering options
- **Sample Questions**: Pre-defined examples for different analysis types
- **Cache Management**: Monitor and manage cache statistics
- **Real-time Results**: View analysis results with metadata

## 📊 Performance Characteristics

### Community Detection Results

**Production Scale**:
- **Geographic**: 71 communities (district-level coverage)
- **Operational**: 30 communities (connectivity clusters)
- **Temporal**: 8 communities (era + evolution + snapshots)
- **Service Type**: 7 communities (transport mode clustering)

**Cache Performance**:
- **Cold Start**: ~30-60 seconds for full community detection
- **Warm Cache**: <1 second for cached community retrieval
- **Summary Generation**: 2-5 seconds per community per LLM provider
- **Query Processing**: 5-20 seconds depending on scope

### Sample Query Results

**Global Question**: "What were the main characteristics of Berlin's transport network in terms of political division?"
- **Communities Analyzed**: 8
- **Execution Time**: ~18 seconds
- **Result**: Comprehensive analysis synthesizing insights from all temporal communities

**Local Question**: "What transport developments occurred in 1961?"
- **Communities Analyzed**: 1-3
- **Execution Time**: ~5 seconds  
- **Result**: Focused analysis of specific temporal/geographic communities

## 🔧 Configuration

### Environment Variables

```bash
# GraphRAG-specific settings (optional)
GRAPHRAG_CACHE_DIR=graphrag_cache
GRAPHRAG_CACHE_ENABLED=true
GRAPHRAG_SUMMARY_MAX_TOKENS=1000
GRAPHRAG_SUMMARY_TEMPERATURE=0.3
```

### Configuration Options

See `backend/config.py` for full configuration options:

```python
# GraphRAG Transport Pipeline Settings
graphrag_cache_enabled: bool = True
graphrag_summary_max_tokens: int = 1000
graphrag_global_question_threshold: int = 3
graphrag_community_min_size: int = 5

# Cache Warming Settings  
graphrag_cache_warm_years: List[int] = [1961, 1970, 1989]
graphrag_cache_warm_community_types: List[str] = ["geographic", "temporal"]

# Performance Settings
graphrag_max_communities_per_query: int = 100
graphrag_parallel_summary_generation: bool = True
```

## 📚 Usage Examples

### Python API

```python
from backend.pipelines.graphrag_transport_pipeline import GraphRAGTransportPipeline

# Initialize pipeline
pipeline = GraphRAGTransportPipeline()

# Process query
result = await pipeline.process_query(
    question="How did the U-Bahn network develop during the wall era?",
    llm_provider="openai",
    year_filter=None,
    community_types=["temporal", "service_type"]
)

print(f"Answer: {result.answer}")
print(f"Communities analyzed: {result.metadata['communities_analyzed']}")
```

### REST API

```bash
curl -X POST "http://localhost:8000/graphrag/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What transport modes were most affected by political division?",
    "llm_provider": "openai",
    "year_filter": 1970,
    "community_types": ["service_type", "geographic"]
  }'
```

### Frontend Interface

1. Navigate to `http://localhost:3000/graphrag`
2. Select from sample questions or enter custom query
3. Configure filters (year, community types, LLM provider)
4. View comprehensive analysis results

## 🧪 Testing and Validation

### Community Summary Validation

```bash
# Generate sample summaries for validation
python test_community_summaries.py

# Output includes:
# - Geographic community summaries (district analysis)
# - Operational community summaries (connectivity analysis)  
# - Temporal community summaries (historical analysis)
# - Service type community summaries (mode-specific analysis)
```

### Cache Validation

```bash
# Validate cache integrity
python graphrag_cache_manager.py validate

# Expected output:
# ✅ Successfully loaded X communities
# ✅ Successfully loaded Y cached summaries
```

## 🔄 Integration Status

✅ **Community Detection**: Multi-dimensional clustering implemented  
✅ **LLM Summarization**: OpenAI, Gemini, Mistral support  
✅ **Persistent Caching**: File-based cache with management tools  
✅ **API Integration**: REST endpoints for all functionality  
✅ **Frontend Interface**: Complete GraphRAG query interface  
✅ **Production Deployment**: Automated setup and cache warming  
✅ **Documentation**: Comprehensive guides and examples  

## 📈 Future Enhancements

**Planned Features**:
- Database-backed caching for distributed deployments
- Real-time community detection updates
- Advanced temporal analysis with trend detection
- Integration with external data sources
- GraphQL API support
- Performance monitoring and metrics

---

*Last updated: July 2025*
