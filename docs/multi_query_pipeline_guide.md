# Multi-Query Cypher Pipeline Guide

## Overview

The **Multi-Query Cypher Pipeline** is an enhanced version of the Direct Cypher Pipeline that can handle complex questions requiring multiple Cypher queries. It intelligently determines when a question needs to be broken down into multiple queries and integrates the results.

## Key Features

### 🧠 **Intelligent Complexity Analysis**

- Uses heuristics to detect complex questions
- Analyzes temporal ranges, entity types, and complexity indicators
- Falls back to single query when multi-query isn't needed

### 🔄 **Automated Query Planning**

- LLM generates execution plans for multi-query scenarios
- Supports different integration strategies (aggregate, compare, correlate, timeline)
- Handles query dependencies and execution order

### 🛡️ **Robust Error Handling**

- Continues with partial results if some queries fail
- Falls back to Direct Cypher Pipeline when planning fails
- Comprehensive error reporting and metadata

### 📊 **Enhanced Evaluation**

- Detailed metadata about query planning and execution
- Performance comparison with single-query approach
- Success/failure tracking for individual queries

## When Multi-Query is Triggered

The pipeline uses multi-query when it detects:

### **Complexity Indicators** (≥2 required)

- "compare", "comparison", "between", "change", "difference"
- "evolution", "timeline", "relationship between"
- "impact of", "both", "as well as", "correlation"

### **Temporal Ranges** (≥2 required)

- "from", "to", "between", "before", "after"
- Specific years like "1960", "1970"

### **Multiple Entity Types** (≥3 required)

- "station", "line", "district", "transport", "bezirk", "ortsteil"

## Example Usage

### Complex Question (Multi-Query)

```python
question = "How did U-Bahn stations change between 1960 and 1970, and what was the impact on different districts?"

# Pipeline will:
# 1. Query 1: Count U-Bahn stations by district in 1960
# 2. Query 2: Count U-Bahn stations by district in 1970  
# 3. Integrate: Calculate differences and analyze impact
```

### Simple Question (Single Query)

```python
question = "How many U-Bahn stations were there in 1970?"

# Pipeline will:
# 1. Use Direct Cypher Pipeline (single query)
```

## Integration Strategies

The pipeline supports different ways to combine multiple query results:

- **`single`**: One query sufficient (falls back to Direct Cypher)
- **`aggregate`**: Combine counts, sums, or other aggregations
- **`compare`**: Side-by-side comparison of results
- **`correlate`**: Find relationships between different result sets
- **`timeline`**: Merge temporal data into chronological analysis

## Usage in Evaluation Framework

The pipeline is integrated into the evaluation system and can be compared with other approaches:

```python
# Available in evaluator as "multi_query_cypher"
pipeline_names = ["direct_cypher", "multi_query_cypher", "no_rag"]
```

## Performance Characteristics

### **Expected Performance**

- **Single Query Questions**: Similar performance to Direct Cypher
- **Multi-Query Questions**: 2-4x execution time (multiple LLM calls)
- **Accuracy**: Potentially higher for complex questions
- **Cost**: Higher due to additional LLM calls for planning

### **LLM Call Pattern**

1. **Query Planning**: Determine if multi-query needed
2. **Query Generation**: Generate individual Cypher queries (if multi-query)
3. **Answer Integration**: Combine results from multiple queries

## Testing

Use the provided test script to evaluate the pipeline:

```bash
python test_multi_query_pipeline.py
```

The test script will:

- Test complexity analysis heuristics
- Compare multi-query vs. direct pipeline performance
- Show detailed execution metadata
- Demonstrate different question types

## Benefits

### **For Research**

- Compare single vs. multi-query approaches
- Analyze performance trade-offs
- Evaluate accuracy improvements for complex questions

### **For Complex Questions**

- Handle temporal comparisons
- Support cross-domain analysis
- Enable multi-step reasoning
- Provide richer context integration

## Limitations

- **Higher Cost**: More LLM calls than single-query approach
- **Increased Latency**: Sequential query execution
- **Complexity**: More potential failure points
- **Heuristic-Based**: May misclassify question complexity

## Future Enhancements

- **Parallel Query Execution**: Execute independent queries simultaneously
- **Adaptive Complexity Analysis**: ML-based complexity detection
- **Query Dependency Resolution**: Advanced dependency management
- **Result Caching**: Cache intermediate results for efficiency
