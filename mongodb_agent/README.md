# MongoDB Agent for ADK Framework

## Overview

The MongoDB Agent is a comprehensive database interface for the quiz game system, built using the Google ADK (Agent Development Kit) framework. It provides tools for interacting with Wikipedia documents stored in MongoDB, designed for agent team architectures.

## Features

### Database Operations
- **Connection Management**: Automatic connection handling with reconnection logic
- **Document Retrieval**: Fetch complete Wikipedia documents by query or ID
- **Section Extraction**: Retrieve specific document sections with filtering
- **Content Search**: Full-text search across document content
- **Statistics**: Comprehensive collection statistics and metadata

### Agent Framework Integration
- **ADK Compatible**: Built for Google Agent Development Kit
- **Tool-based Architecture**: Each function is exposed as a `@tool` for agent use
- **Structured Results**: All operations return `MongoDBQueryResult` objects
- **State Management**: Uses `context_var` and `state_var` for agent coordination
- **Error Handling**: Robust error handling with detailed error messages

## Tools Available

### Core Database Tools

#### `connect_to_mongodb()`
Establishes connection to the quiz_game_db database.
- **Returns**: Connection status and basic collection statistics
- **Auto-stores**: Connection for use by other tools

#### `list_wikipedia_documents(include_stats=True, limit=50)`
Lists all Wikipedia documents in the collection.
- **Parameters**: 
  - `include_stats`: Include document statistics
  - `limit`: Maximum number of documents to return
- **Returns**: Array of document summaries with metadata

#### `fetch_wikipedia_document(query=None, doc_id=None)`
Retrieves a complete Wikipedia document.
- **Parameters**: Either query string or document ID
- **Returns**: Full document with sections, statistics, and metadata

#### `fetch_document_sections(query=None, doc_id=None, section_filter=None, limit=None)`
Retrieves specific sections from a document.
- **Parameters**: 
  - Document identifier (query or doc_id)
  - `section_filter`: Filter sections by title substring
  - `limit`: Maximum sections to return
- **Returns**: Document info and filtered sections array

#### `search_document_content(search_term, search_in="all", limit=20)`
Searches across document content.
- **Parameters**:
  - `search_term`: Text to search for
  - `search_in`: Where to search ("summary", "sections", "all")
  - `limit`: Maximum results to return
- **Returns**: Array of matching documents with highlighted content

#### `get_collection_statistics()`
Retrieves comprehensive collection statistics.
- **Returns**: Document counts, word counts, section statistics, etc.

### Utility Tools

#### `get_query_history()`
Returns the history of queries executed by the agent.

#### `clear_query_history()`
Clears the agent's query history.

## Data Structures

### MongoDBQueryResult
All tools return a standardized result object:
```python
{
  "success": bool,           # Operation success status
  "operation": str,          # Name of operation performed
  "data": Any,              # Operation result data
  "error": str|None,        # Error message if failed
  "metadata": dict,         # Additional operation metadata
  "timestamp": str          # ISO timestamp of operation
}
```

### Document Structure
Wikipedia documents contain:
- **Metadata**: Query, URL, extraction date
- **Summary**: Document overview text
- **Sections**: Hierarchical content sections
- **Statistics**: Word counts, character counts, section counts
- **Section Hierarchy**: Structured navigation

## Usage Examples

### Basic Connection and Listing
```python
# Connect to database
result = connect_to_mongodb()
print(f"Connected: {result.success}")

# List documents
docs = list_wikipedia_documents(limit=5)
for doc in docs.data:
    print(f"- {doc['title']}: {doc['stats']['total_words']} words")
```

### Document Retrieval
```python
# Fetch complete document
doc = fetch_wikipedia_document(query="Python")
if doc.success:
    print(f"Document: {doc.data['query']}")
    print(f"Sections: {len(doc.data['sections'])}")
    print(f"Summary: {doc.data['summary'][:200]}...")
```

### Content Search
```python
# Search for content
results = search_document_content("machine learning", search_in="summary")
for result in results.data:
    print(f"Found in: {result['query']}")
```

## Agent Team Integration

The MongoDB agent is designed to work in agent teams where:
- **Main Agent**: Receives user queries and delegates to specialist agents
- **MongoDB Agent**: Handles all database operations and returns structured results
- **Communication**: Uses ADK context variables and structured result objects

### Agent Prompt
The agent is configured with a comprehensive prompt that defines its role as a database specialist, available tools, and communication protocols for agent teams.

## Database Schema

### Collection: wikipedia_docs
Located in database: `quiz_game_db`

Document structure:
```json
{
  "_id": ObjectId,
  "metadata": {
    "query": "Original search query",
    "url": "Wikipedia URL",
    "extracted_on": "ISO timestamp"
  },
  "summary": "Document summary text",
  "sections": [
    {
      "title": "Section title",
      "level": 2,
      "content": "Section content"
    }
  ],
  "statistics": {
    "total_words": int,
    "total_characters": int,
    "total_sections": int,
    "hierarchy_depth": int
  },
  "query": "Search query used",
  "url": "Wikipedia URL",
  "created_at": "ISO timestamp"
}
```

## Current Status

✅ **Fully Functional**
- All 8 tools implemented and tested
- Connection management working
- Error handling robust
- Data structures consistent
- ADK framework compatible

## Test Results

Recent comprehensive testing shows:
- 11 documents in collection
- 402 total sections
- 74,695 total words
- All CRUD operations working
- Search functionality operational
- Statistics generation complete

## Next Steps

For agent team implementation:
1. Create main agent that delegates queries to this MongoDB agent
2. Implement query routing logic based on user intent
3. Add quiz game specific logic that uses the retrieved Wikipedia data
4. Test inter-agent communication and result processing