# Vector-based RAG Pipeline Guide

## Overview

The Vector-based RAG Pipeline is a comprehensive implementation that converts Neo4j graph data into textual representations, indexes them in a vector database, and uses semantic similarity search to answer questions about Berlin's historical transport network.

## Architecture

```txt
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Neo4j Graph   │    │  Graph-to-Text  │    │  Vector Database│    │  LLM Generation │
│                 │───▶│   Converter     │───▶│   (ChromaDB)    │───▶│                 │
│ - Stations      │    │                 │    │                 │    │ - Context       │
│ - Lines         │    │ - Narratives    │    │ - Embeddings    │    │ - Answer        │
│ - Areas         │    │ - Triples       │    │ - Metadata      │    │ - Temporal      │
│ - Temporal      │    │ - Context       │    │ - Filtering     │    │   Context       │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Core Components

### 1. Graph-to-Text Converter (`graph_to_text.py`)

Converts Neo4j entities into human-readable text chunks:

#### Conversion Strategies

- **Narrative Mode**: Creates contextual descriptions

  ```python
  "In 1964, Alexanderplatz was a tram station located in east Berlin in the Mitte area. 
   It was served by the following transit lines: Line 2, Line 4, Line 68."
  ```

- **Triple Mode**: Extracts subject-predicate-object relationships

  ```python
  "Line 2 serves Alexanderplatz in 1964"
  ```

- **Hybrid Mode**: Combines both approaches

#### Entity Types Processed

1. **Stations**: Location, transport type, served lines, coordinates
2. **Lines**: Route information, frequency, capacity, served stations
3. **Administrative Areas**: Population, area, transport coverage
4. **Temporal Snapshots**: Network evolution over time

### 2. Vector Database Manager (`vector_database.py`)

Manages ChromaDB for storing and retrieving embeddings:

#### Features

- **Embedding Models**: OpenAI `text-embedding-3-large` (primary), Sentence Transformers (fallback)
- **Metadata Filtering**: Temporal, spatial, entity-type filtering
- **Similarity Search**: Configurable thresholds and result limits
- **Persistent Storage**: ChromaDB with disk persistence

#### Search Capabilities

```python
# Basic similarity search
results = await vector_db.search_similar("transport stations in 1964")

# Temporal filtering
results = await vector_db.search_with_temporal_filter(
    "tram lines", year=1964
)

# Spatial filtering
results = await vector_db.search_with_spatial_filter(
    "stations", political_side="west"
)
```

### 3. Data Indexing Service (`vector_indexing.py`)

Orchestrates the complete indexing process:

#### Indexing Process

1. **Extract**: Query Neo4j for entities and relationships
2. **Convert**: Transform to text using graph-to-text converter
3. **Chunk**: Create manageable text chunks with metadata
4. **Embed**: Generate vector embeddings
5. **Store**: Index in ChromaDB with metadata

#### Indexing Options

- **Full Reindex**: Process entire graph dataset
- **Incremental Update**: Update specific entity types
- **Force Rebuild**: Clear and rebuild vector database

### 4. Vector Pipeline (`vector_pipeline.py`)

Main pipeline implementation for question answering:

#### Processing Flow

1. **Question Analysis**: Extract temporal, spatial, entity contexts
2. **Vector Retrieval**: Multi-stage retrieval with filtering
3. **Context Construction**: Organize retrieved chunks coherently
4. **Answer Generation**: LLM generation with structured context

## Configuration

Configure the vector pipeline in `backend/config.py`:

```python
# Vector Pipeline Specific Settings
vector_chunk_size: int = 512
vector_chunk_overlap: int = 50
vector_embedding_model: str = "text-embedding-3-large"
vector_similarity_threshold: float = 0.7
vector_max_retrieved_chunks: int = 10

# Graph-to-Text Conversion Settings
graph_to_text_strategy: str = "narrative"  # "triple", "narrative", "hybrid"
include_temporal_context: bool = True
include_spatial_context: bool = True
include_relationships: bool = True
max_hops_per_entity: int = 2

# Vector Database Settings
chroma_persist_directory: str = "./chroma_db"
vector_db_collection_name: str = "berlin_transport_graph"
rebuild_vector_db_on_startup: bool = False
```

## API Endpoints

### Vector Pipeline Management

#### Get Status

```bash
GET /vector-pipeline/status
```

Returns detailed status including:

- Vector database statistics
- Indexing coverage
- Configuration settings

#### Trigger Indexing

```bash
POST /vector-pipeline/index
Content-Type: application/json

{
  "force_rebuild": false,
  "entity_type": "station"  # optional for incremental updates
}
```

#### Test Retrieval

```bash
POST /vector-pipeline/test?query=Berlin transport stations
```

## Usage Examples

### 1. Initial Setup and Indexing

```python
from backend.pipelines.vector_indexing import VectorIndexingService
from backend.database.neo4j_client import neo4j_client

# Initialize service
indexing_service = VectorIndexingService(neo4j_client)
await indexing_service.initialize()

# Full indexing
stats = await indexing_service.full_reindex(force=True)
print(f"Indexed {stats.total_chunks_created} chunks")
```

### 2. Querying the Pipeline

```python
from backend.pipelines.vector_pipeline import VectorPipeline

# Initialize pipeline
pipeline = VectorPipeline()
await pipeline.initialize()

# Process question
result = await pipeline.process_query(
    question="What tram lines operated in East Berlin in 1964?",
    llm_provider="openai"
)

print(f"Answer: {result.answer}")
print(f"Retrieved {len(result.retrieved_context)} chunks")
```

### 3. Advanced Filtering

```python
# The pipeline automatically detects context from questions:

# Temporal queries
"What happened before 1961?"  # Filters pre-wall period
"How did transport change after the Berlin Wall?"  # Post-1961 focus

# Spatial queries  
"What stations were in West Berlin?"  # Filters by political side
"Transport in Mitte district"  # Area-specific filtering

# Entity-specific queries
"Tram line frequencies"  # Focuses on line entities
"Station coverage in neighborhoods"  # Emphasizes spatial data
```

## Performance Characteristics

### Indexing Performance

- **Processing Rate**: ~50-100 chunks/second (depending on embedding model)
- **Memory Usage**: ~2-4 GB during full indexing
- **Storage**: ~500 MB for complete Berlin transport dataset
- **Time**: 5-15 minutes for full reindex

### Query Performance

- **Retrieval Speed**: <1 second for similarity search
- **End-to-End**: 3-8 seconds including LLM generation
- **Scalability**: Handles 10k+ chunks efficiently

## Comparison with Other Pipelines

| Aspect | Vector Pipeline | Direct Cypher | No-RAG |
|--------|----------------|---------------|--------|
| **Setup Complexity** | High (requires indexing) | Medium | Low |
| **Query Flexibility** | High (natural language) | Medium (schema-dependent) | High |
| **Accuracy** | Good (context-dependent) | Excellent (precise) | Variable |
| **Response Time** | Medium (3-8s) | Fast (1-3s) | Fast (2-4s) |
| **Resource Usage** | High (storage + compute) | Low | Low |

## Troubleshooting

### Common Issues

#### 1. Vector Database Empty

```bash
# Check status
curl http://localhost:8000/vector-pipeline/status

# If empty, trigger indexing
curl -X POST http://localhost:8000/vector-pipeline/index \
  -H "Content-Type: application/json" \
  -d '{"force_rebuild": true}'
```

#### 2. Poor Retrieval Quality

- Adjust `vector_similarity_threshold` (lower for more results)
- Increase `vector_max_retrieved_chunks`
- Try different `graph_to_text_strategy`

#### 3. Slow Performance

- Use sentence-transformers for faster (but lower quality) embeddings
- Reduce `vector_max_retrieved_chunks`
- Implement result caching

#### 4. Memory Issues During Indexing

- Reduce batch size in `VectorDatabaseManager.add_chunks()`
- Process entity types separately using incremental updates

### Logging and Monitoring

Enable detailed logging:

```python
import logging
logging.getLogger("backend.pipelines.vector_pipeline").setLevel(logging.DEBUG)
```

Monitor key metrics:

- Chunk retrieval count and similarity scores
- LLM token usage and costs
- Query processing time
- Vector database size and performance

## Future Enhancements

### 1. Advanced Retrieval

- **Hybrid Search**: Combine vector similarity with keyword matching
- **Reranking**: Use specialized models to reorder results
- **Query Expansion**: Automatically expand queries with synonyms

### 2. Improved Chunking

- **Semantic Chunking**: Split on semantic boundaries
- **Hierarchical Chunking**: Multiple granularity levels
- **Dynamic Chunking**: Adapt chunk size based on content

### 3. Enhanced Filtering

- **Learned Filters**: Train models to improve filtering
- **Multi-hop Reasoning**: Connect information across chunks
- **Temporal Reasoning**: Better handling of time-based queries

### 4. Performance Optimization

- **Caching**: Cache frequent queries and embeddings
- **Async Processing**: Parallel chunk processing
- **Vector Quantization**: Compress embeddings for faster search

## Testing

Run comprehensive tests:

```bash
# Quick functionality test
python test_vector_pipeline.py --quick

# Full pipeline test with indexing
python test_vector_pipeline.py

# Test specific components
python -m pytest backend/pipelines/test_vector_*.py
```

## Dependencies

Key dependencies for the vector pipeline:

```txt
chromadb==0.4.24          # Vector database
sentence-transformers==2.3.1  # Fallback embeddings
openai==1.12.0           # Primary embeddings
numpy==2.2.6             # Numerical operations
```

## Security Considerations

1. **API Keys**: Store OpenAI API keys securely
2. **Data Privacy**: Be aware that data is sent to OpenAI for embeddings
3. **Access Control**: Implement proper authentication for indexing endpoints
4. **Resource Limits**: Set appropriate limits for indexing operations

---

This vector pipeline provides a robust foundation for semantic search over graph data, enabling natural language querying of complex historical transport networks with high flexibility and good performance characteristics.
