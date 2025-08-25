"""
MongoDB Agent Tool for Quiz Game Project
Provides unified database operations as a single tool for the main agent.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import logging
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mongo.connect import MongoDBManager
from mongo.wikipedia import WikipediaStorageManager
from tools.wikipedia_tools import WikipediaSearcher


def query_wikipedia_knowledge(
    query: str,
    operation: str = "fetch_document",
    section_filter: Optional[str] = None,
    search_scope: str = "all",
    limit: int = 10
) -> Dict[str, Any]:
    """
    Unified Wikipedia knowledge query tool for the quiz game.
    
    This tool first checks if the requested information exists in the MongoDB database.
    If not found, it automatically fetches the content from Wikipedia, stores it in the
    database, and then returns the requested information.
    
    Args:
        query (str): The Wikipedia topic or search term
        operation (str): Type of operation - "fetch_document", "list_documents", 
                        "fetch_sections", "search_content", "get_statistics"
        section_filter (str, optional): Filter sections by title (for fetch_sections)
        search_scope (str): Where to search - "all", "titles", "summaries", "sections"
        limit (int): Maximum number of results to return
    
    Returns:
        Dict[str, Any]: Structured result with status, data, and metadata
    """
    
    # Initialize logging
    logger = logging.getLogger(__name__)
    
    # Initialize result structure
    result = {
        "status": "success",
        "operation": operation,
        "query": query,
        "data": None,
        "metadata": {
            "database_checked": False,
            "wikipedia_fetched": False,
            "cached": False
        },
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # Connect to storage
        storage = WikipediaStorageManager()
        
        # Handle different operations
        if operation == "list_documents":
            return _handle_list_documents(storage, limit, result)
        
        elif operation == "get_statistics":
            return _handle_get_statistics(storage, result)
        
        elif operation == "search_content":
            return _handle_search_content(storage, query, search_scope, limit, result)
        
        elif operation in ["fetch_document", "fetch_sections"]:
            return _handle_fetch_operations(
                storage, query, operation, section_filter, limit, result
            )
        
        else:
            result["status"] = "error"
            result["error"] = f"Unknown operation: {operation}"
            return result
            
    except Exception as e:
        logger.error(f"Error in query_wikipedia_knowledge: {e}")
        result["status"] = "error"
        result["error"] = str(e)
        return result


def _handle_list_documents(storage: WikipediaStorageManager, limit: int, result: Dict[str, Any]) -> Dict[str, Any]:
    """Handle listing documents operation."""
    try:
        documents = storage.list_wikipedia_documents(include_stats=True)
        
        if limit and len(documents) > limit:
            documents = documents[:limit]
            result["metadata"]["limited"] = True
        else:
            result["metadata"]["limited"] = False
        
        result["data"] = documents
        result["metadata"]["total_found"] = len(documents)
        result["metadata"]["database_checked"] = True
        
        return result
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"Error listing documents: {str(e)}"
        return result


def _handle_get_statistics(storage: WikipediaStorageManager, result: Dict[str, Any]) -> Dict[str, Any]:
    """Handle getting statistics operation."""
    try:
        stats = storage.get_collection_statistics()
        result["data"] = stats
        result["metadata"]["database_checked"] = True
        
        return result
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"Error getting statistics: {str(e)}"
        return result


def _handle_search_content(
    storage: WikipediaStorageManager, 
    query: str, 
    search_scope: str, 
    limit: int, 
    result: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle search content operation."""
    try:
        search_results = storage.search_content(query, search_scope)
        
        if limit and len(search_results) > limit:
            search_results = search_results[:limit]
            result["metadata"]["limited"] = True
        else:
            result["metadata"]["limited"] = False
        
        result["data"] = search_results
        result["metadata"]["total_matches"] = len(search_results)
        result["metadata"]["database_checked"] = True
        result["metadata"]["search_scope"] = search_scope
        
        return result
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = f"Error searching content: {str(e)}"
        return result


def _handle_fetch_operations(
    storage: WikipediaStorageManager,
    query: str,
    operation: str,
    section_filter: Optional[str],
    limit: int,
    result: Dict[str, Any]
) -> Dict[str, Any]:
    """Handle fetch document and fetch sections operations."""
    logger = logging.getLogger(__name__)
    
    try:
        # First, try to get from database
        document = storage.get_wikipedia_document(query=query)
        result["metadata"]["database_checked"] = True
        
        if document:
            result["metadata"]["cached"] = True
            logger.info(f"Found document for '{query}' in database")
        else:
            # If not found, fetch from Wikipedia and store
            logger.info(f"Document for '{query}' not found in database, fetching from Wikipedia...")
            document = _fetch_from_wikipedia_and_store(storage, query, result)
            
            if not document:
                result["status"] = "error"
                result["error"] = f"Could not retrieve information for: {query}"
                return result
        
        # Process the document based on operation
        if operation == "fetch_document":
            result["data"] = document
            result["metadata"]["sections_count"] = len(document.get("sections", {}))
            
        elif operation == "fetch_sections":
            sections_data = _extract_sections_from_document(document, section_filter, limit)
            result["data"] = sections_data
            result["metadata"]["sections_returned"] = len(sections_data.get("sections", []))
            result["metadata"]["section_filter"] = section_filter
        
        return result
        
    except Exception as e:
        logger.error(f"Error in fetch operations: {e}")
        result["status"] = "error"
        result["error"] = f"Error fetching data: {str(e)}"
        return result


def _fetch_from_wikipedia_and_store(
    storage: WikipediaStorageManager,
    query: str,
    result: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Fetch content from Wikipedia and store in database."""
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize Wikipedia searcher
        searcher = WikipediaSearcher()
        
        # Search for the topic
        search_result = searcher.search(query)
        if not search_result:
            logger.warning(f"No Wikipedia results found for: {query}")
            return None
        
        # Save content to markdown file
        md_file_path = searcher.save_full_text_to_markdown(
            query, 
            extract_format="wiki", 
            directory="temp"
        )
        
        if not md_file_path:
            logger.error(f"Failed to save markdown for: {query}")
            return None
        
        # Read the markdown content
        try:
            with open(md_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read markdown file: {e}")
            return None
        
        # Store in MongoDB
        storage_result = storage.store_wikipedia_document(
            content=content,
            source_file=md_file_path,
            interactive=False
        )
        
        if storage_result:  # If document ID is returned
            result["metadata"]["wikipedia_fetched"] = True
            logger.info(f"Successfully stored '{query}' in database with ID: {storage_result}")
            
            # Retrieve the stored document
            document = storage.get_wikipedia_document(query=query)
            return document
        else:
            logger.error(f"Failed to store document for query: {query}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching from Wikipedia: {e}")
        return None


def _extract_sections_from_document(
    document: Dict[str, Any],
    section_filter: Optional[str],
    limit: int
) -> Dict[str, Any]:
    """Extract sections from a document with optional filtering."""
    
    all_sections = document.get("sections", {})
    sections_list = []
    
    # Apply section filter if provided
    if section_filter:
        filter_lower = section_filter.lower()
        for key, section in all_sections.items():
            if filter_lower in section.get("title", "").lower():
                section_data = {
                    "key": key,
                    "title": section.get("title", ""),
                    "level": section.get("level", 1),
                    "content": section.get("content", ""),
                    "word_count": section.get("word_count", 0),
                    "character_count": section.get("character_count", 0),
                    "parent_section": section.get("parent_section"),
                    "subsections": section.get("subsections", [])
                }
                sections_list.append(section_data)
    else:
        # Include all sections
        for key, section in all_sections.items():
            section_data = {
                "key": key,
                "title": section.get("title", ""),
                "level": section.get("level", 1),
                "content": section.get("content", ""),
                "word_count": section.get("word_count", 0),
                "character_count": section.get("character_count", 0),
                "parent_section": section.get("parent_section"),
                "subsections": section.get("subsections", [])
            }
            sections_list.append(section_data)
    
    # Apply limit
    if limit and len(sections_list) > limit:
        sections_list = sections_list[:limit]
    
    return {
        "document_info": {
            "title": document.get("query", "Unknown"),
            "url": document.get("url", ""),
            "summary": document.get("summary", "") if not section_filter else None
        },
        "sections": sections_list
    }


def main():
    """Main function for testing the agent."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🤖 MongoDB Agent Test Mode")
    print("=" * 40)
    
    # Test the tool function
    result = query_wikipedia_knowledge("Machine Learning", "get_statistics")
    print(f"Statistics: {json.dumps(result, indent=2)}")
    
    result = query_wikipedia_knowledge("Artificial Intelligence", "fetch_document")
    print(f"Fetch result: {result['status']}")
    if result['data']:
        print(f"Document title: {result['data'].get('query', 'Unknown')}")
        print(f"Sections: {len(result['data'].get('sections', {}))}")
    
    print("\n🎯 MongoDB Agent ready for integration!")


if __name__ == "__main__":
    main()