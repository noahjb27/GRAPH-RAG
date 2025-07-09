# Graph-RAG Research System: Application Guide

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Backend Components](#backend-components)
4. [Frontend Components](#frontend-components)
5. [Database Integration](#database-integration)
6. [LLM Integration](#llm-integration)
7. [Pipeline System](#pipeline-system)
8. [Question Taxonomy](#question-taxonomy)
9. [Setup and Configuration](#setup-and-configuration)
10. [API Reference](#api-reference)
11. [Testing and Evaluation](#testing-and-evaluation)
12. [Troubleshooting](#troubleshooting)

## Overview

The Graph-RAG Research System is a comprehensive platform for evaluating different approaches to question-answering using graph databases and Large Language Models (LLMs). The system focuses on historical Berlin transport network data (1946-1989) and implements multiple retrieval-augmented generation (RAG) pipelines for comparison.

### Key Features
- **Multi-Pipeline Architecture**: Direct Cypher, No-RAG Baseline, Vector-based RAG, and Hybrid approaches
- **Multi-LLM Support**: OpenAI GPT, Google Gemini, and Mistral Large models
- **Rich Graph Database**: Neo4j with temporal and spatial modeling of Berlin transport
- **Comprehensive Evaluation**: 25 questions across 5 categories and 4 difficulty levels
- **Modern Web Interface**: Next.js frontend with real-time evaluation and visualization
- **Research-Focused**: Designed for academic research and experimentation

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │    Database     │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│    (Neo4j)      │
│                 │    │                 │    │                 │
│ - Dashboard     │    │ - API Routes    │    │ - Transport     │
│ - Question UI   │    │ - Pipelines     │    │   Network       │
│ - Evaluation    │    │ - LLM Clients   │    │ - Temporal      │
│ - Results       │    │ - Evaluator     │    │   Modeling      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   LLM Providers │
                    │                 │
                    │ - OpenAI GPT    │
                    │ - Google Gemini │
                    │ - Mistral Large │
                    └─────────────────┘
```

## Backend Components

### Core Structure
```
backend/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration management
├── database/              # Database integration layer
├── llm_clients/           # LLM provider abstractions
├── pipelines/             # Question-answering pipelines
└── evaluation/            # Evaluation framework
```

### 1. Configuration (`config.py`)
Centralized configuration using Pydantic settings:
- Environment variable loading
- LLM provider credentials and models
- Database connection parameters
- Server settings

### 2. Database Layer (`database/`)
- **`neo4j_client.py`**: Neo4j connection and query execution
- **`schema_analyzer.py`**: Dynamic schema analysis for Cypher generation
- **`query_executor.py`**: Safe query execution with complexity limits

### 3. LLM Integration (`llm_clients/`)
- **`base_client.py`**: Abstract interface for all LLM providers
- **`client_factory.py`**: Factory pattern for LLM client creation
- **Provider-specific clients**: OpenAI, Gemini, Mistral implementations
- **Unified Response Format**: Standardized LLM response handling

### 4. Pipeline System (`pipelines/`)
Four distinct approaches to question-answering:

#### Direct Cypher Pipeline
- **Purpose**: Schema-aware Cypher generation from natural language
- **Process**: Question → LLM generates Cypher → Execute → Generate answer
- **Status**: ✅ Fully functional
- **Strengths**: Precise, leverages full database capabilities
- **Use case**: Factual and relational queries

#### No-RAG Baseline
- **Purpose**: Pure LLM knowledge without database access
- **Process**: Question → LLM generates answer from training data
- **Status**: ✅ Fully functional  
- **Strengths**: Fast, no database dependency
- **Use case**: General historical knowledge, baseline comparison

#### Vector-based RAG
- **Purpose**: Semantic search with embeddings
- **Process**: Question → Find similar content → Generate answer
- **Status**: ⚠️ Planned implementation
- **Use case**: Open-ended questions, semantic similarity

#### Hybrid RAG
- **Purpose**: Combines multiple approaches
- **Process**: Route question to best pipeline based on type
- **Status**: ⚠️ Planned implementation
- **Use case**: Complex queries requiring multiple reasoning steps

### 5. Evaluation Framework (`evaluation/`)
- **`evaluator.py`**: Orchestrates pipeline evaluation
- **`question_loader.py`**: Loads and manages question taxonomy
- **`metrics.py`**: Success rate, cost, and performance metrics

## Frontend Components

### Technology Stack
- **Framework**: Next.js 15.3.5 with TypeScript
- **Styling**: Tailwind CSS with Radix UI components
- **State Management**: SWR for data fetching
- **Charts**: Recharts for data visualization
- **Forms**: React Hook Form with Zod validation

### Page Structure
```
frontend/src/app/
├── page.tsx               # Dashboard - System overview
├── questions/             # Question browser and management
├── evaluation/            # Single and batch evaluation interface
├── results/               # Results visualization and comparison
├── database/              # Database schema and statistics
└── settings/              # System configuration
```

### Key Features
1. **Dashboard**: Real-time system status, LLM provider health, pipeline overview
2. **Question Browser**: Search, filter, and explore evaluation questions
3. **Evaluation Interface**: Run single questions or batch evaluations
4. **Results Visualization**: Compare pipeline performance with charts and metrics
5. **Database Explorer**: Schema visualization and query statistics

## Database Integration

### Neo4j Schema
The database models Berlin's transport network with temporal and spatial dimensions:

**Core Entities:**
- **Station**: Individual stops/stations with geographic coordinates
- **Line**: Transport lines (tram, bus, u-bahn, s-bahn) with operational data
- **Year**: Temporal nodes (1946-1989)
- **HistoricalOrtsteil**: Neighborhood-level administrative areas
- **HistoricalBezirk**: District-level administrative areas

**Key Relationships:**
- `SERVES`: Lines serve stations
- `IN_YEAR`: Temporal associations
- `LOCATED_IN`: Geographic containment
- `CONNECTS_TO`: Station connections

**Important Properties:**
- **Lines**: frequency, capacity, type, east_west political classification
- **Stations**: coordinates, type, political classification  
- **Years**: Temporal filtering using `year` property (not `value`)

### Data Coverage
- **24,650+ nodes** across all entity types
- **90,514+ relationships** connecting entities
- **Available years**: 1946, 1951, 1956, 1960-1961, 1964-1965, 1967, 1971, 1980, 1982, 1984-1985, 1989
- **Political context**: East/West Berlin division modeling

## LLM Integration

### Supported Providers

#### OpenAI (Primary)
- **Models**: GPT-4o (primary), GPT-4-turbo-preview
- **Use cases**: All pipelines, high-quality generation
- **Configuration**: Standard OpenAI API
- **Status**: ✅ Fully functional

#### Google Gemini (Backup)
- **Models**: Gemini-1.5-pro
- **Use cases**: Cost-effective alternative
- **Configuration**: Google AI Studio API
- **Status**: ✅ Functional

#### Mistral (University)
- **Models**: Mistral Large (llm1)
- **Endpoint**: University-hosted at `https://llm1-compute.cms.hu-berlin.de/v1/`
- **Access**: Requires VPN connection
- **Status**: ⚠️ VPN-dependent

### LLM Client Architecture
```python
# Unified interface for all providers
class BaseLLMClient(ABC):
    async def generate(self, prompt: str, **kwargs) -> LLMResponse
    async def generate_with_schema(self, prompt: str, schema: dict) -> LLMResponse

# Standardized response format
@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    tokens_used: int
    cost_usd: float
```

## Pipeline System

### Pipeline Evaluation Process
1. **Question Loading**: Load question from taxonomy by ID
2. **LLM Client Creation**: Initialize specified LLM provider
3. **Pipeline Execution**: Run question through selected pipeline
4. **Result Collection**: Gather metrics (success, time, cost, tokens)
5. **Answer Generation**: Create natural language response

### Performance Metrics
- **Success Rate**: Percentage of questions answered correctly
- **Execution Time**: Average time per question (seconds)
- **Cost**: Total USD cost for LLM API calls
- **Token Usage**: Input/output tokens consumed
- **Throughput**: Tokens per second

### Current Performance
Based on testing with fact_001 ("What was the frequency of tram Line 1 in 1964?"):

| Pipeline | Success Rate | Avg Time | Sample Answer Quality |
|----------|-------------|----------|----------------------|
| Direct Cypher | ✅ 100% | ~11s | Excellent - "20 minutes" with context |
| No-RAG | ✅ 100% | ~4s | Good - General historical knowledge |
| Vector RAG | ⚠️ Not implemented | - | - |
| Hybrid RAG | ⚠️ Not implemented | - | - |

## Question Taxonomy

### Structure
The evaluation framework includes 25 carefully designed questions across:

**Categories (5):**
1. **Factual**: Property lookups and basic facts
2. **Relational**: Using entity relationships  
3. **Temporal**: Time-based analysis and comparisons
4. **Spatial**: Geographic and administrative queries
5. **Complex**: Multi-hop reasoning and analysis

**Difficulty Levels (4):**
1. **Level 1**: Simple property access
2. **Level 2**: Single-hop relationships
3. **Level 3**: Multi-hop with filtering
4. **Level 4**: Complex aggregation and analysis

### Example Questions
- **Factual (Level 1)**: "What was the frequency of tram Line 1 in 1964?"
- **Relational (Level 2)**: "Which stations did U-Bahn Line 6 serve in West Berlin in 1971?"
- **Temporal (Level 3)**: "How did the number of stations change from 1960 to 1967?"
- **Complex (Level 4)**: "How did administrative areas adapt their transport offerings between 1964 and 1971?"

### Question Properties
Each question includes:
```python
@dataclass
class Question:
    question_id: str
    question_text: str
    category: str
    difficulty: int
    capabilities: List[str]
    cypher_query: str
    expected_answer: str
    historical_context: str
    notes: str
```

## Setup and Configuration

### Prerequisites
- Python 3.8+
- Node.js 18+
- Neo4j Aura account or local Neo4j instance
- LLM provider API keys (OpenAI recommended)

### Environment Variables
Create `.env` file in project root:
```bash
# Neo4j Database (Required)
NEO4J_AURA_URI=your-neo4j-uri
NEO4J_AURA_USERNAME=neo4j
NEO4J_AURA_PASSWORD=your-password

# OpenAI (Primary - Recommended)
OPENAI_API_KEY=your-openai-key

# Google Gemini (Optional)
GEMINI_API_KEY=your-gemini-key

# Mistral University (Optional - VPN required)
MISTRAL_API_KEY=required-but-not-used
MISTRAL_BASE_URL=https://llm1-compute.cms.hu-berlin.de/v1/

# Server Configuration
DEBUG=true
HOST=0.0.0.0
PORT=8000
```

### Installation Steps
1. **Clone and setup Python environment**:
   ```bash
   git clone [repository]
   cd GRAPH-RAG
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Setup Frontend**:
   ```bash
   cd frontend
   npm install
   ```

3. **Configure environment**:
   ```bash
   cp env_template.txt .env
   # Edit .env with your credentials
   ```

4. **Test setup**:
   ```bash
   python test_setup.py
   ```

5. **Start services**:
   ```bash
   # Terminal 1: Backend
   python -m backend.main

   # Terminal 2: Frontend  
   cd frontend && npm run dev
   ```

6. **Access application**:
   - Backend API: http://localhost:8000
   - Frontend UI: http://localhost:3000
   - API Documentation: http://localhost:8000/docs

## API Reference

### Core Endpoints

#### System Status
```http
GET /status
```
Returns system health, connected LLM providers, and database status.

#### LLM Providers
```http
GET /llm-providers
```
Lists available LLM providers with connectivity status.

#### Pipelines
```http
GET /pipelines  
```
Returns available pipelines with statistics and capabilities.

#### Questions
```http
GET /questions?limit=20&offset=0&category=factual&difficulty=1
```
Browse and filter evaluation questions.

#### Single Question Evaluation
```http
POST /evaluate/question
Content-Type: application/json

{
  "question_id": "fact_001",
  "pipeline_names": ["direct_cypher", "no_rag"],
  "llm_providers": ["openai"]
}
```

#### Batch Evaluation
```http
POST /evaluate/sample
Content-Type: application/json

{
  "sample_size": 5,
  "pipeline_names": ["direct_cypher"],
  "llm_providers": ["openai"],
  "categories": ["factual", "relational"],
  "difficulty_levels": [1, 2]
}
```

#### Database Information
```http
GET /database/info
```
Returns Neo4j schema information and statistics.

### Response Formats

#### Evaluation Result
```json
{
  "question_id": "fact_001",
  "question_text": "What was the frequency of tram Line 1 in 1964?",
  "pipeline_name": "Direct Cypher",
  "llm_provider": "openai",
  "success": true,
  "answer": "In 1964, tram Line 1 operated with a frequency of every 20 minutes...",
  "execution_time_seconds": 11.49,
  "cost_usd": 0.0063,
  "total_tokens": 359,
  "generated_cypher": "MATCH (l:Line {name: '1', type: 'tram'})-[:IN_YEAR]->(y:Year {year: 1964}) RETURN l.frequency",
  "metadata": {
    "records_returned": 1,
    "question_category": "factual",
    "question_difficulty": 1
  }
}
```

## Testing and Evaluation

### Test Script
Run comprehensive system test:
```bash
python test_setup.py
```

Checks:
- Environment variables
- Neo4j connectivity  
- LLM provider availability
- Question taxonomy loading

### Pipeline Testing
Test specific pipeline:
```bash
python test_fixed_pipeline.py
```

Validates:
- Direct Cypher query generation
- Correct database property usage
- Answer quality assessment

### Manual Testing
Use the web interface for interactive testing:
1. Navigate to http://localhost:3000/evaluation
2. Select questions and pipelines
3. Run evaluations and review results
4. Compare pipeline performance in results section

### Automated Evaluation
Run batch evaluations via API:
```python
import httpx

async def run_evaluation():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/evaluate/sample",
            json={
                "sample_size": 10,
                "pipeline_names": ["direct_cypher", "no_rag"],
                "llm_providers": ["openai"]
            }
        )
        return response.json()
```

## Troubleshooting

### Common Issues

#### 1. Neo4j Connection Failures
**Symptoms**: Database connection errors, 502 responses
**Solutions**:
- Verify Neo4j Aura credentials in `.env`
- Check network connectivity
- Ensure database is running and accessible
- Test connection: `python -c "from backend.database.neo4j_client import neo4j_client; import asyncio; asyncio.run(neo4j_client.test_connection())"`

#### 2. LLM Provider Errors
**Symptoms**: 401 authentication errors, provider unavailable
**Solutions**:
- Verify API keys in `.env` file
- Check account credits/quota
- For Mistral: Ensure VPN connection to university network
- Test connectivity via `/llm-providers` endpoint

#### 3. Direct Cypher Query Failures
**Symptoms**: "property key not in database" warnings, 0 records returned
**Solutions**:
- ✅ **FIXED**: Use `{year: 1964}` not `{value: 1964}` for Year nodes
- Verify schema with `/database/info`
- Check data availability for specific years
- Use MCP Neo4j tools for manual verification

#### 4. Frontend Build Errors
**Symptoms**: TypeScript errors, missing dependencies
**Solutions**:
- Run `npm install` in frontend directory
- Check Node.js version (requires 18+)
- Clear `.next` cache: `rm -rf .next`
- Restart development server

#### 5. Performance Issues
**Symptoms**: Slow query execution, timeouts
**Solutions**:
- Monitor query complexity limits
- Check LLM provider response times
- Optimize database indexes
- Use query limits (LIMIT 100)

### Debug Mode
Enable detailed logging:
```bash
export DEBUG=true
python -m backend.main
```

### Health Checks
- **Backend**: http://localhost:8000/health
- **Database**: http://localhost:8000/database/info  
- **LLM Providers**: http://localhost:8000/llm-providers
- **Frontend**: http://localhost:3000 (should load dashboard)

### Log Analysis
Key log patterns to monitor:
- `✓ Neo4j connection established` - Database OK
- `✓ Available LLM providers: ['openai', 'gemini']` - LLMs OK
- `✓ Server ready on 0.0.0.0:8000` - Backend OK
- `Successfully connected to Neo4j database: neo4j` - Query execution OK

### Support
For research-related questions or technical issues:
1. Check this documentation
2. Review API documentation at `/docs`
3. Run test scripts for diagnostics
4. Check backend logs for detailed error messages

---

*Last updated: January 2025*
*Application version: Current state as of documentation* 