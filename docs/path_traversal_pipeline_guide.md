# Path Traversal Pipeline Documentation

## Overview

The **Path Traversal Pipeline** is a specialized Graph-RAG approach that finds connections between entities mentioned in user questions through graph traversal. It's particularly effective for questions about relationships, connections, and multi-hop associations in the Berlin transit network.

## Core Concept

The pipeline implements a 4-step process:

1. **🎯 Anchor Detection**: Identifies entities (stations, areas, lines) mentioned in the question
2. **🔍 Path Traversal**: Finds paths connecting these entities using graph algorithms
3. **📊 Ranking & Pruning**: Scores paths by relevance and selects the best ones
4. **📝 Serialization**: Converts the subgraph into readable context for the LLM

## How It Works

### Step 1: Anchor Detection

Uses pattern matching and database lookups to find entities mentioned in questions:

```python
# Example anchors detected from: "How are Alexanderplatz and Marienfelde connected?"
anchors = [
    {"name": "Alexanderplatz", "type": "station", "id": "station_123"},
    {"name": "Marienfelde", "type": "station", "id": "station_456"}
]
```

**Supported Entity Types:**

- **Stations**: Regular stations and core stations
- **Lines**: Transit lines (U-Bahn, S-Bahn, Bus, Tram)
- **Administrative Areas**: Neighborhoods (Ortsteil) and districts (Bezirk)

### Step 2: Path Traversal

Finds paths between anchors using Cypher's `shortestPath` algorithm:

```cypher
MATCH path = shortestPath((a)-[*1..3]-(b))
WHERE a.name = "Alexanderplatz" AND b.name = "Marienfelde"
RETURN path
```

**Traversal Relationships** (with priority weights):

- `SERVES` (1.0): Line serves station
- `SERVES_CORE` (1.1): Core line-station relationships  
- `CONNECTS_TO` (1.2): Direct station connections
- `LOCATED_IN` (1.5): Station in administrative area
- `PART_OF` (2.0): Administrative hierarchy
- `HAS_SNAPSHOT` (2.5): Temporal relationships

### Step 3: Ranking & Pruning
Scores paths using:
- **Path Length**: Shorter paths score higher
- **Relationship Quality**: Preferred relationship types boost scores
- **Relevance**: Context-aware scoring

### Step 4: Serialization
Converts paths into structured context:

```
=== ANCHOR ENTITIES ===
• Alexanderplatz (station)
• Marienfelde (station)

=== PATHS BETWEEN ENTITIES ===
Path 1: Alexanderplatz → Marienfelde
  Length: 2 hops
  Score: 0.825
  Route: Alexanderplatz → S-Bahn Line → Marienfelde
  Connections: SERVES → SERVES
```

## Usage Examples

### 1. Direct Station Connections
```python
question = "How are Alexanderplatz and Potsdamer Platz connected?"

# Expected behavior:
# - Detects: Alexanderplatz, Potsdamer Platz
# - Finds: Shortest paths via transit lines
# - Returns: Direct connections and transfer routes
```

### 2. Neighborhood Discovery
```python
question = "What connections does Brandenburger Tor have?"

# Expected behavior:
# - Detects: Brandenburger Tor
# - Finds: Neighborhood of connected stations/lines
# - Returns: All nearby transit options
```

### 3. Administrative Area Connections
```python
question = "How do I get from Friedrichshain to Kreuzberg?"

# Expected behavior:
# - Detects: Friedrichshain, Kreuzberg (administrative areas)
# - Finds: Stations in each area and connections between them
# - Returns: Transit routes connecting the neighborhoods
```

### 4. Temporal Filtering
```python
question = "What stations were connected to Alexanderplatz in 1961?"

# With year_filter=1961:
# - Limits traversal to entities active in 1961
# - Shows historical network state
```

## API Parameters

### Basic Usage
```python
result = await pipeline.process_query(
    question="How are Alexanderplatz and Marienfelde connected?",
    llm_provider="mistral"
)
```

### Advanced Parameters
```python
result = await pipeline.process_query(
    question="What connections does Potsdamer Platz have?",
    llm_provider="mistral",
    max_hops=3,           # Maximum traversal depth
    max_paths=10,         # Maximum paths to return
    year_filter=1961      # Temporal filtering
)
```

**Parameter Details:**
- `max_hops` (int, default=3): Maximum graph traversal depth
- `max_paths` (int, default=10): Maximum number of paths to analyze
- `year_filter` (int, optional): Filter to specific year (1946-1989)

## When to Use Path Traversal

### ✅ Perfect For:
- **Connection Questions**: "How are X and Y connected?"
- **Multi-hop Relationships**: "What's the route from A to B?"
- **Neighborhood Discovery**: "What's around station X?"
- **Network Analysis**: "How do these areas connect?"
- **Temporal Analysis**: "What connections existed in year Y?"

### ❌ Not Ideal For:
- **Simple Facts**: "What is the capacity of line X?"
- **Statistical Queries**: "How many stations are there?"
- **Complex Aggregations**: "What's the average frequency?"
- **General Information**: "Tell me about Berlin transport"

## Performance Considerations

### Strengths
- **Explainable Results**: Shows actual paths and connections
- **Efficient Traversal**: Uses Neo4j's optimized shortest path algorithms
- **Flexible Depth**: Configurable hop limits prevent explosion
- **Temporal Support**: Can filter by historical periods

### Limitations
- **Anchor Dependency**: Requires accurate entity detection
- **Density Sensitivity**: Dense graphs may need tighter hop limits
- **Latency**: Increases with hop count and path complexity

## Configuration

### Default Settings
```python
# Relationship weights (lower = higher priority)
traversal_relationships = {
    'SERVES': 1.0,           # Line serves station
    'CONNECTS_TO': 1.2,      # Direct station connections  
    'LOCATED_IN': 1.5,       # Station in area
    'PART_OF': 2.0,          # Administrative hierarchy
    'SERVES_CORE': 1.1,      # Core line-station relationships
    'HAS_SNAPSHOT': 2.5      # Temporal relationships
}
```

### Entity Detection Patterns
```python
# German location patterns
location_patterns = [
    r'\b([A-ZÄÖÜ][a-zäöü]+(?:\s+[A-ZÄÖÜ][a-zäöü]+)*(?:platz|straße|str\.|bahnhof|station|bf\.?))\b',
    r'\b([A-ZÄÖÜ][a-zäöü]+(?:\s+[A-ZÄÖÜ][a-zäöü]+)*(?:berg|burg|dorf|felde|hagen|hof|ow|stedt|thal|wald|werder))\b',
    r'\b(U\d+|S\d+|Bus\s+\d+|Linie\s+\d+)\b'
]
```

## Error Handling

### Common Issues
1. **No Anchors Detected**: Question doesn't contain recognizable entities
2. **No Paths Found**: Entities exist but aren't connected within hop limit
3. **Traversal Timeout**: Graph too dense or complex for current limits

### Error Messages
```python
# No anchors detected
"I couldn't identify any specific locations or entities in your question. 
 Could you mention specific stations, areas, or transit lines?"

# Traversal failure
"I encountered an error while analyzing the connections: [error details]"
```

## Integration with Frontend

The pipeline integrates seamlessly with the web interface:

1. **Pipeline Selection**: Available in the pipeline dropdown
2. **Parameter Control**: Advanced settings for hop limits and temporal filtering
3. **Results Display**: Shows detected anchors, paths, and traversal statistics
4. **Visualization**: Path context is formatted for easy reading

## Testing

### Test Script
Run the comprehensive test script:
```bash
python test_path_traversal_pipeline.py
```

### Test Categories
- **Basic Path Finding**: Two-entity connections
- **Neighborhood Discovery**: Single-entity exploration
- **Temporal Filtering**: Historical network states
- **Anchor Detection**: Entity recognition accuracy
- **Performance**: Execution time and accuracy metrics

## Comparison with Other Pipelines

| Pipeline | Best For | Path Traversal Advantage |
|----------|----------|-------------------------|
| Direct Cypher | Precise queries | Better for relationship discovery |
| Multi-Query | Complex analysis | Simpler for connection questions |
| Vector RAG | Similar text | Better for structural relationships |
| No-RAG | General knowledge | Grounded in actual graph structure |

## Advanced Usage

### Custom Traversal
For specialized use cases, extend the pipeline:

```python
class CustomPathTraversal(PathTraversalPipeline):
    def __init__(self):
        super().__init__()
        # Custom relationship weights
        self.traversal_relationships['CUSTOM_REL'] = 0.8
        
    async def custom_traversal_logic(self, anchors):
        # Implement specialized path finding
        pass
```

### Temporal Analysis
```python
# Compare connections across different years
years = [1946, 1961, 1989]
for year in years:
    result = await pipeline.process_query(
        "What stations connect to Alexanderplatz?",
        year_filter=year
    )
```

## Troubleshooting

### Common Problems

1. **Anchor Detection Issues**
   - **Problem**: Important entities not detected
   - **Solution**: Check entity names in database, adjust patterns

2. **No Paths Found**
   - **Problem**: Entities exist but aren't connected
   - **Solution**: Increase `max_hops` or check database connectivity

3. **Too Many Results**
   - **Problem**: Overwhelming path count
   - **Solution**: Decrease `max_paths` or increase specificity

4. **Slow Performance**
   - **Problem**: Long execution times
   - **Solution**: Reduce `max_hops` or add temporal filtering

### Debug Tips
- Use the test script to verify functionality
- Check anchor detection with simple entity names
- Start with small hop counts and increase gradually
- Use temporal filtering to reduce search space

---

## Quick Start Checklist

1. ✅ Pipeline is registered in the system
2. ✅ Database connection is active
3. ✅ LLM provider is configured
4. ✅ Test with simple two-entity question
5. ✅ Verify anchor detection works
6. ✅ Check path finding accuracy
7. ✅ Optimize parameters for your use case

The Path Traversal Pipeline is now ready to discover connections in your Berlin transit network! 🚇✨ 