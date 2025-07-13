# Vector-based RAG Pipeline Guide

## Overview

The Vector-based RAG Pipeline is a comprehensive implementation that converts Neo4j graph data into textual representations, indexes them in a vector database, and uses semantic similarity search to answer questions about Berlin's historical transport network.

**Recent Achievement**: Successfully indexed **135,063 chunks** covering the complete Berlin transport dataset (1946-1989) with comprehensive 5-phase conversion strategy.

## Architecture

```txt
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Neo4j Graph   │    │  Graph-to-Text  │    │  Vector Database│    │  LLM Generation │
│                 │───▶│   Converter     │───▶│   (ChromaDB)    │───▶│                 │
│ - Stations      │    │                 │    │                 │    │ - Context       │
│ - Lines         │    │ - Narratives    │    │ - Embeddings    │    │ - Answer        │
│ - Areas         │    │ - Triples       │    │ - Metadata      │    │ - Temporal      │
│ - Temporal      │    │ - Properties    │    │ - Filtering     │    │   Context       │
│ - Relationships │    │ - Relationships │    │ - Exports       │    │ - Spatial       │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Core Components

### 1. Graph-to-Text Converter (`graph_to_text.py`)

Converts Neo4j entities into human-readable text chunks using a **5-phase comprehensive strategy**:

#### Phase 1: Individual Entity Properties (~69K chunks)
Extracts detailed properties for every entity:

**Station Properties** (~63K chunks):
```python
"Alexanderplatz (ID: 12345) - Station name: Alexanderplatz, Transport type: Tram, Political side: east, Coordinates: 52.5219, 13.4132, Located in Mitte"
```

**Line Properties** (~6K chunks):
```python
"Line 2 (ID: 678) - Line number: 2, Transport type: Tram, Frequency: 10 minutes, Capacity: 120 passengers"
```

#### Phase 2: Individual Relationships (~60K chunks)
Captures every relationship between entities:

```python
"Station Alexanderplatz SERVES Line 2 in year 1964"
"Station Alexanderplatz LOCATED_IN administrative area Mitte"
"Line 2 CONNECTS_TO Line 4 at Alexanderplatz"
```

#### Phase 3: Aggregated Narratives (~5K chunks)
Creates contextual descriptions combining multiple data points:

```python
"In 1964, Alexanderplatz was a tram station located in east Berlin in the Mitte area. 
 It was served by the following transit lines: Line 2, Line 4, Line 68."
```

#### Phase 4: Complex Relationship Patterns (~2K chunks)
Multi-hop relationships and network patterns:

```python
"Line 2 connects neighborhoods Mitte and Friedrichshain through stations 
 Alexanderplatz, Warschauer, serving both east and west political areas"
```

#### Phase 5: Structured Triples (~30K chunks)
Subject-predicate-object relationships:

```python
"Line 2 serves Alexanderplatz in 1964"
"Alexanderplatz located_in Mitte district"
```

#### Conversion Strategies

- **Narrative Mode**: Creates contextual descriptions
- **Triple Mode**: Extracts subject-predicate-object relationships  
- **Hybrid Mode**: Combines both approaches
- **Property Mode**: Individual entity properties
- **Relationship Mode**: Individual relationship facts

### 2. Vector Database Manager (`vector_database.py`)

Manages ChromaDB for storing and retrieving embeddings with **enhanced stability**:

#### Features

- **Embedding Models**: OpenAI `text-embedding-3-large` (primary), Sentence Transformers (fallback)
- **Metadata Filtering**: Temporal, spatial, entity-type filtering
- **Similarity Search**: Configurable thresholds and result limits (default: 0.2)
- **Persistent Storage**: ChromaDB with disk persistence
- **Collection Management**: Singleton pattern for stability
- **Exception Handling**: Robust ChromaDB error handling

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

Orchestrates the complete indexing process with **chunk export functionality**:

#### Indexing Process

1. **Extract**: Query Neo4j for entities and relationships
2. **Convert**: Transform to text using 5-phase strategy
3. **Chunk**: Create manageable text chunks with metadata
4. **Embed**: Generate vector embeddings (cost: ~$2.93 for 135K chunks)
5. **Store**: Index in ChromaDB with metadata
6. **Export**: Optionally export chunks to text files for inspection

#### Indexing Options

- **Full Reindex**: Process entire graph dataset (~135K chunks)
- **Complete Indexing**: Resume incomplete indexing operations
- **Incremental Update**: Update specific entity types
- **Force Rebuild**: Clear and rebuild vector database
- **Chunk Export**: Export text files to `chunk_exports/` directory

#### Chunk Export Structure

When `export_chunks=True`, creates organized text files:

```
chunk_exports/
├── SUMMARY.txt                     # Overview statistics
├── station_property_chunks.txt     # ~62,836 station properties  
├── line_property_chunks.txt        # ~6,639 line properties
├── relationship_chunks.txt         # ~60,110 relationships
├── narrative_chunks.txt            # ~5,000 aggregated narratives
└── triple_chunks.txt              # ~30,000 structured triples
```

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
vector_similarity_threshold: float = 0.2  # Updated for better retrieval
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

- Vector database statistics (e.g., 135,063 chunks indexed)
- Indexing coverage and completion percentage
- Configuration settings

#### Trigger Full Indexing

```bash
POST /api/vector/index
Content-Type: application/json

{
  "force_rebuild": true,
  "export_chunks": true  # Creates text exports
}
```

**Response includes**:
- Total chunks created (~135,063)
- Export directory path (`chunk_exports/`)
- Processing time and embedding costs

#### Complete Partial Indexing

```bash
POST /api/vector/complete-indexing
```

Resumes indexing from where it left off if process was interrupted.

#### Test Retrieval

```bash
POST /vector-pipeline/test?query=Berlin transport stations
```

## Usage Examples

### 1. Initial Setup and Full Indexing

```python
from backend.pipelines.vector_indexing import VectorIndexingService
from backend.database.neo4j_client import neo4j_client

# Initialize service
indexing_service = VectorIndexingService(neo4j_client)
await indexing_service.initialize()

# Full indexing with exports
stats = await indexing_service.full_reindex(force=True, export_chunks=True)
print(f"Indexed {stats.total_chunks_created} chunks")
print(f"Exports available in chunk_exports/ directory")
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
print(f"Avg similarity: {result.metadata['avg_similarity_score']:.3f}")
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

- **Dataset Scale**: 135,063 chunks from complete Berlin transport network
- **Processing Rate**: ~30-50 chunks/second (with OpenAI API rate limits)
- **Memory Usage**: ~4-6 GB during full indexing
- **Storage**: ~800 MB for complete dataset
- **Time**: 45-90 minutes for full reindex (depending on API speed)
- **Cost**: ~$2.93 for OpenAI embeddings (text-embedding-3-large)

### Query Performance

- **Retrieval Speed**: <1 second for similarity search
- **End-to-End**: 3-8 seconds including LLM generation
- **Scalability**: Efficiently handles 135K+ chunks
- **Similarity Threshold**: 0.2 (optimized for recall)

### Coverage Statistics

- **Station Properties**: 62,836 chunks (every station attribute)
- **Line Properties**: 6,639 chunks (every line attribute) 
- **Relationships**: 60,110 chunks (every connection)
- **Narratives**: ~5,000 chunks (contextual descriptions)
- **Triples**: ~30,000 chunks (structured facts)

## Comparison with Other Pipelines

| Aspect | Vector Pipeline | Direct Cypher | No-RAG |
|--------|----------------|---------------|--------|
| **Setup Complexity** | High (requires indexing) | Medium | Low |
| **Query Flexibility** | High (natural language) | Medium (schema-dependent) | High |
| **Accuracy** | Good (context-dependent) | Excellent (precise) | Variable |
| **Response Time** | Medium (3-8s) | Fast (1-3s) | Fast (2-4s) |
| **Resource Usage** | High (storage + compute) | Low | Low |
| **Coverage** | Comprehensive (135K chunks) | Complete (direct DB) | Variable |

## Troubleshooting

### Common Issues

#### 1. Vector Database Empty

```bash
# Check status
curl http://localhost:8000/vector-pipeline/status

# If empty, trigger indexing
curl -X POST http://localhost:8000/api/vector/index \
  -H "Content-Type: application/json" \
  -d '{"force_rebuild": true, "export_chunks": true}'
```

#### 2. Incomplete Indexing

```bash
# Resume indexing from where it stopped
curl -X POST http://localhost:8000/api/vector/complete-indexing
```

#### 3. Poor Retrieval Quality

- Adjust `vector_similarity_threshold` (current: 0.2, lower for more results)
- Increase `vector_max_retrieved_chunks`
- Try different `graph_to_text_strategy`
- Check chunk exports to verify content quality

#### 4. Slow Performance

- Use sentence-transformers for faster (but lower quality) embeddings
- Reduce `vector_max_retrieved_chunks`
- Implement result caching

#### 5. Memory Issues During Indexing

- Reduce batch size in `VectorDatabaseManager.add_chunks()`
- Process entity types separately using incremental updates
- Monitor system memory during large indexing operations

### Monitoring Chunk Exports

Check exported text files for debugging:

```bash
# View summary statistics
cat chunk_exports/SUMMARY.txt

# Sample station properties
head -20 chunk_exports/station_property_chunks.txt

# Check relationship coverage
wc -l chunk_exports/relationship_chunks.txt
```

### Logging and Monitoring

Enable detailed logging:

```python
import logging
logging.getLogger("backend.pipelines.vector_pipeline").setLevel(logging.DEBUG)
```

Monitor key metrics:

- Chunk retrieval count and similarity scores
- LLM token usage and costs (~$2.93 for full dataset)
- Query processing time
- Vector database size (800MB+) and performance

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
- **Incremental Updates**: Only reprocess changed data

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
5. **Cost Management**: Monitor OpenAI API usage (~$2.93 per full reindex)

---

This vector pipeline provides a robust foundation for semantic search over graph data, enabling natural language querying of complex historical transport networks with comprehensive coverage (135K+ chunks) and good performance characteristics.
