# Documentation Index

This folder contains comprehensive documentation for the Graph-RAG Research System.

## 📚 Documentation Files

### 🚀 [Application Guide](application_guide.md)
**Complete system documentation** - Start here for comprehensive understanding

**Contents:**
- Architecture overview and component descriptions
- Backend and frontend detailed explanations  
- Database integration and schema details
- LLM integration and pipeline system
- Setup, configuration, and troubleshooting
- API reference and testing procedures

**Target audience:** Developers, researchers, system administrators

### 🗄️ [Database Description](db_description.md)
**Neo4j schema and data details** - Deep dive into the graph database

**Contents:**
- Detailed schema documentation
- Entity relationships and properties
- Data coverage and temporal modeling
- Query examples and optimization

**Target audience:** Database administrators, data analysts, researchers working with the graph data

### 🔗 [Path Traversal Pipeline Guide](path_traversal_pipeline_guide.md)
**Neighborhood and path-based retrieval** - Connect entities through graph traversal

**Contents:**
- Anchor detection and entity recognition
- Path finding algorithms and traversal strategies
- Ranking, pruning, and result optimization
- Usage examples and performance considerations
- Integration with temporal filtering

**Target audience:** Developers, researchers interested in relationship discovery and multi-hop connections

### 🧠 [Graph Embedding Pipeline Guide](graph_embedding_pipeline_guide.md)
**Topological similarity retrieval** - Find structurally similar entities using Node2Vec embeddings

**Contents:**
- Node2Vec training and graph preprocessing
- FAISS vector indexing and similarity search
- Hybrid semantic-structural search strategies
- Performance optimization and caching
- Use cases for structural pattern discovery

**Target audience:** Developers, researchers interested in structural similarity and topological analysis

### 🌐 [GraphRAG Transport Pipeline Guide](graphrag_transport_pipeline_guide.md)
**Hierarchical community-based transport analysis** - System-wide transport network analysis inspired by Microsoft's GraphRAG

**Contents:**
- Multi-dimensional community detection (geographic, operational, temporal, service-type)
- LLM-based hierarchical summarization of transport communities
- Global vs local question routing and map-reduce processing
- Integration with existing pipeline architecture
- Historical transport network analysis for divided Berlin

**Target audience:** Researchers, transport analysts, developers working with complex network analysis

## 🔗 External Documentation

### Interactive API Reference
- **URL**: http://localhost:8000/docs (when backend is running)
- **Content**: Live API documentation with request/response examples
- **Features**: Interactive testing, schema validation, endpoint discovery

### Application Interfaces
- **Frontend UI**: http://localhost:3000 (comprehensive web interface)
- **Backend API**: http://localhost:8000 (REST API endpoints)

## 📖 Quick Navigation

### For New Users
1. **Start**: [Application Guide - Overview](application_guide.md#overview)
2. **Setup**: [Application Guide - Setup and Configuration](application_guide.md#setup-and-configuration)
3. **First Run**: [Application Guide - Testing and Evaluation](application_guide.md#testing-and-evaluation)

### For Developers
1. **Architecture**: [Application Guide - Architecture](application_guide.md#architecture)
2. **Backend**: [Application Guide - Backend Components](application_guide.md#backend-components)
3. **Frontend**: [Application Guide - Frontend Components](application_guide.md#frontend-components)
4. **API**: [Interactive API Docs](http://localhost:8000/docs)

### For Researchers  
1. **Research Focus**: [Application Guide - Overview](application_guide.md#overview)
2. **Question Taxonomy**: [Application Guide - Question Taxonomy](application_guide.md#question-taxonomy)
3. **Pipeline System**: [Application Guide - Pipeline System](application_guide.md#pipeline-system)
4. **Database Schema**: [Database Description](db_description.md)

### For Troubleshooting
1. **Common Issues**: [Application Guide - Troubleshooting](application_guide.md#troubleshooting)
2. **Test Scripts**: [Application Guide - Testing and Evaluation](application_guide.md#testing-and-evaluation)
3. **Debug Mode**: [Application Guide - Debug Mode](application_guide.md#debug-mode)

## 🆕 Recent Updates

- **Graph Embedding Pipeline**: New pipeline for topological similarity retrieval using Node2Vec embeddings and FAISS search
- **Path Traversal Pipeline**: Pipeline for discovering connections between entities through graph traversal
- **GraphRAG Transport Pipeline**: Hierarchical community-based transport network analysis inspired by Microsoft's GraphRAG
- **Application Guide**: Comprehensive system documentation reflecting current state
- **README.md**: Updated project overview and quick start guide
- **GraphRAG Production Deployment**: Full production deployment with 137MB+ cached communities and summaries
- **Pipeline Status**: All pipelines fully functional including GraphRAG Transport (production-ready)

## 📝 Contributing to Documentation

When updating documentation:
1. Keep this index synchronized with new files
2. Update cross-references between documents
3. Include code examples where helpful
4. Mark planned features clearly (⚠️ symbol)
5. Test all setup instructions and code examples

---

*Documentation index last updated: January 2025* 