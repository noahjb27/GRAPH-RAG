# Graph-RAG Research System

A comprehensive platform for evaluating and comparing different approaches to question-answering using graph databases and Large Language Models (LLMs). This research system focuses on historical Berlin transport network data (1946-1989) and implements multiple retrieval-augmented generation (RAG) pipelines for academic analysis.

## 🎯 Research Focus

This system enables comparative evaluation of different RAG approaches:
- **Direct Cypher Generation**: LLM-to-Cypher translation for precise graph queries
- **No-RAG Baseline**: Pure LLM knowledge without database access  
- **Vector-based RAG**: Semantic search with embeddings
- **Community Summarisation**: Hierarchied community-based summarisation
- **Traversal Algorithms**: Retrieving relevant nodes and running algorithms for graph routing

## ✨ Key Features

### 🏗️ **Multi-Pipeline Architecture**
- Four distinct question-answering approaches
- Standardized evaluation framework
- Performance comparison and analysis

### 🤖 **Multi-LLM Support**  
- OpenAI GPT-4o (primary)
- Google Gemini 1.5 Pro
- Mistral Large (university-hosted)
- Unified client interface

### 📊 **Rich Graph Database**
- Neo4j with 24,650+ nodes and 90,514+ relationships
- Temporal modeling (1946-1989)
- Spatial modeling (East/West Berlin division)
- Transport network with stations, lines, and administrative areas

### 🎓 **Research-Grade Evaluation**
- 60 crafted questions across 12 categories
- 4 difficulty levels from simple facts to complex analysis
- Comprehensive metrics: success rate, cost, performance, token usage

### 🖥️ **Modern Web Interface**
- Next.js TypeScript frontend
- Real-time evaluation and monitoring
- Interactive results visualization
- Pipeline performance comparison

## 📁 Project Structure

```
GRAPH-RAG/
├── backend/               # FastAPI backend
│   ├── pipelines/        # Question-answering pipelines
│   ├── llm_clients/      # LLM provider integrations
│   ├── database/         # Neo4j client and schema analysis
│   └── evaluation/       # Evaluation framework
├── frontend/             # Next.js TypeScript UI
│   └── src/app/         # Dashboard, evaluation, results pages
├── question_taxonomy/    # Research questions and expected answers
├── docs/                # Comprehensive documentation
└── db_testing/          # Database exploration and testing
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 18+
- Neo4j Aura account (or local Neo4j)
- OpenAI API key (recommended)

### 1. Clone and Setup
```bash
git clone [your-repository-url]
cd GRAPH-RAG
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp env_template.txt .env
# Edit .env with your credentials:
# - NEO4J_AURA_URI, NEO4J_AURA_USERNAME, NEO4J_AURA_PASSWORD
# - OPENAI_API_KEY
# - Optional: GEMINI_API_KEY, MISTRAL credentials
```

### 3. Setup Frontend
```bash
cd frontend
npm install
cd ..
```

### 4. Test Your Setup
```bash
python test_setup.py
```
This validates your configuration and connections.

### 5. Start the System
```bash
# Terminal 1: Start backend
python -m backend.main

# Terminal 2: Start frontend
cd frontend && npm run dev
```

### 6. Access the Application
- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000  
- **API Docs**: http://localhost:8000/docs

## 📖 Documentation

### Quick Links
- **[Application Guide](docs/application_guide.md)** - Comprehensive system documentation
- **[Database Description](docs/db_description.md)** - Neo4j schema and data details
- **[API Documentation](http://localhost:8000/docs)** - Interactive API reference (when running)

### Sample Research Questions
- **Factual**: "What was the frequency of tram Line 1 in 1964?"
- **Relational**: "Which stations did U-Bahn Line 6 serve in West Berlin in 1971?"
- **Temporal**: "How did the number of stations change from 1960 to 1967?"
- **Complex**: "How did administrative areas adapt their transport offerings between 1964 and 1971?"

## 🧪 Running Evaluations

### Web Interface
1. Navigate to http://localhost:3000/evaluation
2. Select questions and pipelines to test
3. Run evaluations and view results
4. Compare performance in the results section

### API Example
```python
import httpx

async def evaluate_question():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/evaluate/question",
            json={
                "question_id": "fact_001",
                "pipeline_names": ["direct_cypher", "no_rag"],
                "llm_providers": ["openai"]
            }
        )
        return response.json()
```

### Batch Evaluation
```bash
curl -X POST "http://localhost:8000/evaluate/sample" \
  -H "Content-Type: application/json" \
  -d '{
    "sample_size": 10,
    "pipeline_names": ["direct_cypher"],
    "llm_providers": ["openai"],
    "categories": ["factual", "relational"]
  }'
```

## 📊 Current Performance

Based on testing with OpenAI GPT-4o:

| Pipeline | Status | Success Rate | Avg Time | Use Case |
|----------|--------|-------------|----------|----------|
| **Direct Cypher** | ✅ Functional | 100% | ~11s | Factual & relational queries |
| **No-RAG** | ✅ Functional | 100% | ~4s | Baseline comparison |
| **Vector RAG** | ⚠️ Planned | - | - | Semantic similarity |
| **Hybrid RAG** | ⚠️ Planned | - | - | Multi-modal reasoning |

## 🛠️ Development

### Test Pipeline Performance
```bash
python test_fixed_pipeline.py
```

### Explore Database Schema
```bash
# Use MCP Neo4j tools or:
curl "http://localhost:8000/database/info"
```

### Debug Issues
```bash
# Enable debug mode
export DEBUG=true
python -m backend.main
```

## 🎓 Research Applications

This system is designed for:
- **RAG Methodology Comparison**: Evaluate different retrieval strategies
- **LLM Performance Analysis**: Compare models across structured tasks
- **Graph Database Research**: Study temporal and spatial query patterns
- **Historical Data Analysis**: Berlin transport network evolution
- **Academic Publications**: Reproducible experimental framework

## 🤝 Contributing

### Research Guidelines
- Document all experiments and findings
- Use clear commit messages
- Add new questions to the taxonomy with proper categorization
- Include performance benchmarks for new pipelines

### Code Quality
- Backend: Python with FastAPI, async/await patterns
- Frontend: TypeScript with Next.js, proper type safety
- Database: Cypher queries with proper indexing
- Testing: Comprehensive evaluation framework

## 📧 Support

For research collaboration or technical questions:
1. Check the [Application Guide](docs/application_guide.md)
2. Review API documentation at `/docs`
3. Run diagnostic scripts (`test_setup.py`)
4. Check backend logs for detailed error information

## 📄 License

This is an academic research project. Please cite appropriately if using in publications.

---

**Research System Status**: ✅ Direct Cypher & No-RAG pipelines functional | ⚠️ Vector & Hybrid RAG in development

*Last updated: July 2025*
