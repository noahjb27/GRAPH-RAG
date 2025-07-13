# Evaluation Export Guide

This guide explains how to export evaluation results from the Graph-RAG pipeline evaluator for analysis in external tools.

## Overview

The evaluator now supports exporting evaluation results in two formats:
- **JSON**: Structured format with nested data, includes evaluation summary
- **CSV**: Tabular format optimized for analysis in Excel, pandas, etc.

## Export Methods

### 1. `export_results_to_json()`

Exports results to JSON format with full data structure preservation.

```python
evaluator.export_results_to_json(
    results=evaluation_results,
    file_path="my_evaluation.json",
    include_summary=True  # Optional: include summary statistics
)
```

**Features:**
- Preserves all data types and nested structures
- Includes evaluation summary statistics
- Timestamps in ISO format
- Complex fields (metadata, cypher_results) preserved as nested objects

### 2. `export_results_to_csv()`

Exports results to CSV format for spreadsheet analysis.

```python
evaluator.export_results_to_csv(
    results=evaluation_results,
    file_path="my_evaluation.csv",
    flatten_metadata=True  # Optional: flatten metadata into separate columns
)
```

**Features:**
- Tabular format compatible with Excel, pandas, etc.
- Option to flatten metadata fields into separate columns
- Complex fields (cypher_results, metadata) converted to JSON strings
- All numeric fields preserved for statistical analysis

### 3. `export_results_with_timestamp()`

Convenience method that automatically adds timestamps to filenames.

```python
exported_files = evaluator.export_results_with_timestamp(
    results=evaluation_results,
    base_filename="pipeline_evaluation",
    formats=["json", "csv"],  # Export both formats
    output_dir="evaluation_exports"
)
```

**Features:**
- Automatic timestamp in filename (YYYYMMDD_HHMMSS format)
- Export multiple formats simultaneously
- Automatic directory creation
- Returns list of created files

## Data Structure

### JSON Export Structure

```json
{
  "export_timestamp": "2024-01-15T14:30:00.000Z",
  "total_results": 50,
  "results": [
    {
      "question_id": "Q001",
      "question_text": "What stations were built in East Berlin?",
      "pipeline_name": "direct_cypher",
      "llm_provider": "openai",
      "answer": "Based on the data...",
      "success": true,
      "execution_time_seconds": 2.34,
      "cost_usd": 0.0045,
      "total_tokens": 1200,
      "tokens_per_second": 512.8,
      "generated_cypher": "MATCH (s:Station)...",
      "cypher_results": [...],
      "timestamp": "2024-01-15T14:25:30.000Z",
      "error_message": null,
      "metadata": {
        "question_category": "historical",
        "question_difficulty": 2,
        "question_capabilities": ["temporal", "geographic"]
      }
    }
  ],
  "summary": {
    "total_evaluations": 50,
    "success_rate": 0.92,
    "total_cost": 0.234,
    "by_pipeline": {...},
    "by_llm_provider": {...}
  }
}
```

### CSV Export Structure

| Column | Description |
|--------|-------------|
| `question_id` | Unique question identifier |
| `question_text` | Full question text |
| `pipeline_name` | Name of the pipeline used |
| `llm_provider` | LLM provider used |
| `answer` | Generated answer |
| `success` | Whether evaluation succeeded (true/false) |
| `execution_time_seconds` | Time taken in seconds |
| `cost_usd` | Cost in USD |
| `total_tokens` | Total tokens used |
| `tokens_per_second` | Processing speed |
| `generated_cypher` | Generated Cypher query (if applicable) |
| `cypher_results` | Query results as JSON string |
| `timestamp` | Execution timestamp |
| `error_message` | Error message if failed |
| `metadata_*` | Flattened metadata fields (if flatten_metadata=True) |

## Usage Examples

### Basic Evaluation and Export

```python
import asyncio
from backend.evaluation.evaluator import Evaluator

async def run_evaluation():
    evaluator = Evaluator()
    
    # Run evaluation
    results = await evaluator.evaluate_sample_questions(
        pipeline_names=["direct_cypher", "vector"],
        llm_providers=["openai"],
        question_count=10
    )
    
    # Export results
    evaluator.export_results_with_timestamp(
        results, 
        "my_evaluation",
        formats=["json", "csv"]
    )

asyncio.run(run_evaluation())
```

### Full Taxonomy Evaluation

```python
async def full_evaluation():
    evaluator = Evaluator()
    
    # Run full evaluation with progress tracking
    def progress_callback(status):
        print(f"Progress: {status['progress_percent']:.1f}%")
    
    results = await evaluator.evaluate_full_taxonomy(
        pipeline_names=evaluator.get_available_pipelines(),
        llm_providers=evaluator.get_available_llm_providers(),
        progress_callback=progress_callback
    )
    
    # Export comprehensive results
    evaluator.export_results_to_json(
        results, 
        "evaluation_exports/full_taxonomy_evaluation.json"
    )
    
    evaluator.export_results_to_csv(
        results, 
        "evaluation_exports/full_taxonomy_evaluation.csv"
    )

asyncio.run(full_evaluation())
```

## Analysis Tips

### Using JSON Exports

JSON exports are ideal for:
- Programmatic analysis with Python/pandas
- Preserving complex data structures
- Further processing in other tools
- Detailed debugging and inspection

```python
import json
import pandas as pd

# Load JSON export
with open("evaluation_results.json", "r") as f:
    data = json.load(f)

# Convert to DataFrame
df = pd.DataFrame(data["results"])

# Analysis examples
success_rate_by_pipeline = df.groupby("pipeline_name")["success"].mean()
cost_by_provider = df.groupby("llm_provider")["cost_usd"].sum()
```

### Using CSV Exports

CSV exports are ideal for:
- Excel analysis and visualization
- Statistical analysis
- Sharing with non-technical stakeholders
- Quick data exploration

Common Excel analyses:
- Pivot tables by pipeline and LLM provider
- Success rate charts
- Cost and performance comparisons
- Error analysis

## File Organization

Recommended directory structure:
```
evaluation_exports/
├── daily_evaluations/
│   ├── pipeline_comparison_20240115_143000.json
│   ├── pipeline_comparison_20240115_143000.csv
│   └── ...
├── full_taxonomy/
│   ├── full_evaluation_20240115_090000.json
│   └── full_evaluation_20240115_090000.csv
└── experiments/
    └── ...
```

## Integration with Analysis Tools

### Pandas Analysis

```python
import pandas as pd

# Load CSV for analysis
df = pd.read_csv("evaluation_results.csv")

# Performance analysis
performance_summary = df.groupby(["pipeline_name", "llm_provider"]).agg({
    "success": "mean",
    "execution_time_seconds": "mean",
    "cost_usd": "sum",
    "total_tokens": "sum"
}).round(4)

print(performance_summary)
```

### Excel Analysis

1. Open CSV file in Excel
2. Create pivot tables for pipeline comparison
3. Use conditional formatting for success rates
4. Create charts for cost and performance trends

This export functionality makes it easy to analyze evaluation results and make data-driven decisions about pipeline performance and optimization. 