"""
Wikipedia Storage and Query System for MongoDB
Provides tools to store and retrieve structured Wikipedia content in MongoDB.
"""

import re
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import logging
from dataclasses import dataclass

from .connect import MongoDBManager


@dataclass
class WikipediaSection:
    """
    Represents a Wikipedia section with its content and metadata.
    """
    title: str
    content: str
    level: int  # Heading level (1=##, 2=###, etc.)
    parent_section: Optional[str] = None
    subsections: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.subsections is None:
            self.subsections = []


class WikipediaStorageManager(MongoDBManager):
    """
    Extends MongoDBManager to provide specialized Wikipedia content storage and retrieval.
    
    Key Features:
    - Flexible heading/subheading structure parsing
    - Hierarchical section storage
    - Advanced querying capabilities
    - Metadata preservation
    """
    
    def __init__(self, collection_name: str = "wikipedia_docs", **kwargs):
        """
        Initialize the Wikipedia Storage Manager.
        
        Args:
            collection_name (str): Name of the MongoDB collection for Wikipedia docs
            **kwargs: Additional arguments passed to MongoDBManager
        """
        super().__init__(**kwargs)
        self.collection_name = collection_name
        self.logger = logging.getLogger(__name__)
    
    def parse_markdown_content(self, content: str) -> Dict[str, Any]:
        """
        Parse structured Wikipedia markdown content and extract sections.
        
        Args:
            content (str): Raw markdown content from Wikipedia file
            
        Returns:
            Dict[str, Any]: Parsed document with metadata and sections
        """
        lines = content.split('\n')
        document = {
            'metadata': {},
            'summary': '',
            'sections': {},
            'section_hierarchy': [],
            'created_at': datetime.now(),
            'content_type': 'wikipedia'
        }
        
        current_section = None
        current_content = []
        separator_found = False
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip title line (starts with #)
            if line.startswith('#'):
                i += 1
                continue
            
            # Check for separator line
            if line == '---':
                separator_found = True
                i += 1
                continue
            
            # Parse metadata (before the separator ---)
            if not separator_found and line.startswith('**') and ':' in line:
                # Extract metadata like **Query:** Artificial Intelligence
                # Look for the pattern **Key:** Value
                colon_pos = line.find(':**')
                if colon_pos > 2:  # Must have at least **X:**
                    key_part = line[2:colon_pos]  # Remove ** prefix
                    value = line[colon_pos + 3:].strip()  # Remove :** and whitespace
                    key = key_part.strip().lower().replace(' ', '_')
                    
                    document['metadata'][key] = value
                    
                    # Special handling for common metadata
                    if key == 'query':
                        document['query'] = value
                    elif key == 'url':
                        document['url'] = value
                    elif key == 'extract_format':
                        document['format'] = value
                    elif key == 'extracted_on':
                        document['extracted_at'] = value
                i += 1
                continue
                
            # Skip empty lines or lines before separator
            if not separator_found or not line:
                i += 1
                continue
            
            # Now we're in the content section
            
            # Check for markdown headers first
            header_match = re.match(r'^(#{2,6})\s+(.+)$', line)
            if header_match:
                # Save previous section
                if current_section == 'summary' and current_content:
                    document['summary'] = '\n'.join(current_content).strip()
                elif current_section and current_content:
                    self._add_section_to_document(
                        document, current_section, current_content, 
                        len(header_match.group(1)) - 1
                    )
                
                # Start new section
                current_section = header_match.group(2).strip()
                current_content = []
                i += 1
                continue
            
            # Check if this looks like a section header (not markdown formatted)
            # This is for Wikipedia's format where sections are just plain text titles
            if (len(line) < 80 and  # Reasonable title length
                i + 1 < len(lines) and 
                lines[i + 1].strip() and  # Next line has content
                not line.endswith('.') and  # Doesn't end like a sentence
                not line.endswith(',') and
                not line.endswith(';') and
                len(line.split()) <= 8):  # Not too many words
                
                # Look ahead to see if this looks like a section
                next_few_lines = []
                for j in range(i + 1, min(i + 4, len(lines))):
                    if lines[j].strip():
                        next_few_lines.append(lines[j].strip())
                
                # If the next lines look like content (sentences), this is likely a header
                if (next_few_lines and 
                    any(next_line.endswith('.') for next_line in next_few_lines[:2])):
                    
                    # Save previous content
                    if current_section == 'summary' and current_content:
                        document['summary'] = '\n'.join(current_content).strip()
                        current_content = []
                    elif current_section and current_content:
                        self._add_section_to_document(
                            document, current_section, current_content, 2
                        )
                        current_content = []
                    
                    # Start new section
                    current_section = line
                    i += 1
                    continue
            
            # Collect content for current section or summary
            if line:
                if not current_section:
                    current_section = 'summary'
                current_content.append(line)
            
            i += 1
        
        # Save final section
        if current_section == 'summary' and current_content:
            document['summary'] = '\n'.join(current_content).strip()
        elif current_section and current_content:
            self._add_section_to_document(
                document, current_section, current_content, 2
            )
        
        return document
    
    def _add_section_to_document(self, document: Dict[str, Any], 
                                section_title: str, content: List[str], level: int):
        """
        Add a section to the document with proper hierarchy tracking.
        
        Args:
            document (Dict): Document being built
            section_title (str): Title of the section
            content (List[str]): Content lines for the section
            level (int): Heading level (1=##, 2=###, etc.)
        """
        section_key = self._normalize_section_key(section_title)
        section_content = '\n'.join(content).strip()
        
        # Create section object
        section_data = {
            'title': section_title,
            'content': section_content,
            'level': level,
            'word_count': len(section_content.split()),
            'character_count': len(section_content)
        }
        
        # Handle subsections (level > 2)
        if level > 2:
            # Find parent section
            parent_key = self._find_parent_section(document['section_hierarchy'], level)
            if parent_key:
                section_data['parent_section'] = parent_key
                # Add to parent's subsections list
                if parent_key in document['sections']:
                    if 'subsections' not in document['sections'][parent_key]:
                        document['sections'][parent_key]['subsections'] = []
                    document['sections'][parent_key]['subsections'].append(section_key)
        
        document['sections'][section_key] = section_data
        document['section_hierarchy'].append({
            'key': section_key,
            'title': section_title,
            'level': level
        })
    
    def _normalize_section_key(self, title: str) -> str:
        """
        Normalize section title to create a consistent key.
        
        Args:
            title (str): Original section title
            
        Returns:
            str: Normalized key
        """
        # Convert to lowercase, replace spaces and special chars with underscores
        key = re.sub(r'[^\w\s]', '', title.lower())
        key = re.sub(r'\s+', '_', key)
        return key
    
    def _find_parent_section(self, hierarchy: List[Dict], current_level: int) -> Optional[str]:
        """
        Find the parent section for a given level in the hierarchy.
        
        Args:
            hierarchy (List[Dict]): Current section hierarchy
            current_level (int): Level of current section
            
        Returns:
            Optional[str]: Parent section key or None
        """
        # Look backwards through hierarchy to find parent
        for section in reversed(hierarchy):
            if section['level'] < current_level:
                return section['key']
        return None
    
    def store_wikipedia_document(self, content: str, source_file: Optional[str] = None, 
                                interactive: bool = True) -> Optional[str]:
        """
        Parse and store a Wikipedia document in MongoDB.
        
        Args:
            content (str): Raw markdown content
            source_file (str): Optional source file path
            interactive (bool): Whether to prompt user for duplicate handling
            
        Returns:
            Optional[str]: Document ID if successful, None otherwise
        """
        try:
            if not self.is_connected():
                if not self.connect():
                    self.logger.error("Failed to connect to MongoDB")
                    return None
            
            # Parse the content
            document = self.parse_markdown_content(content)
            
            # Add source information
            if source_file:
                document['source_file'] = source_file
            
            # Add document statistics
            document['statistics'] = {
                'total_sections': len(document['sections']),
                'total_words': sum(section.get('word_count', 0) for section in document['sections'].values()),
                'total_characters': len(document.get('summary', '')) + sum(
                    section.get('character_count', 0) for section in document['sections'].values()
                ),
                'hierarchy_depth': max((s['level'] for s in document['section_hierarchy']), default=0)
            }
            
            # Get collection
            collection = self.get_collection(self.collection_name)
            if collection is None:
                self.logger.error(f"Failed to get collection: {self.collection_name}")
                return None
            
            # Check for existing documents with same query or URL
            existing_docs = self._find_duplicate_documents(collection, document)
            
            if existing_docs and interactive:
                action = self._prompt_duplicate_action(document, existing_docs)
                
                if action == 'skip':
                    print("⏭️ Skipping document insertion.")
                    return None
                elif action == 'overwrite':
                    # Delete existing documents and insert new one
                    for existing_doc in existing_docs:
                        collection.delete_one({'_id': existing_doc['_id']})
                        print(f"🗑️ Deleted existing document: {existing_doc.get('query', 'Unknown')}")
                elif action == 'update':
                    # Update the first existing document
                    existing_doc = existing_docs[0]
                    document['updated_at'] = datetime.now()
                    document['_id'] = existing_doc['_id']  # Keep the same ID
                    result = collection.replace_one({'_id': existing_doc['_id']}, document)
                    print(f"🔄 Updated existing document: {existing_doc.get('query', 'Unknown')}")
                    return str(existing_doc['_id'])
                # If action is 'add', continue to insert as new document
            elif existing_docs and not interactive:
                # Non-interactive mode: update existing document
                existing_doc = existing_docs[0]
                document['updated_at'] = datetime.now()
                result = collection.replace_one({'_id': existing_doc['_id']}, document)
                self.logger.info(f"Updated existing document: {existing_doc['_id']}")
                return str(existing_doc['_id'])
            
            # Insert new document
            result = collection.insert_one(document)
            doc_id = str(result.inserted_id)
            self.logger.info(f"Stored new Wikipedia document: {doc_id}")
            if interactive:
                print(f"✅ Stored new document: {document.get('query', 'Unknown')}")
            return doc_id
            
        except Exception as e:
            self.logger.error(f"Error storing Wikipedia document: {e}")
            return None
    
    def _find_duplicate_documents(self, collection, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find existing documents with the same query or URL.
        
        Args:
            collection: MongoDB collection
            document (Dict): Document to check for duplicates
            
        Returns:
            List[Dict[str, Any]]: List of existing documents that match
        """
        duplicates = []
        
        # Check by query
        query_value = document.get('query') or document.get('metadata', {}).get('query')
        if query_value:
            existing = collection.find_one({'query': query_value})
            if existing:
                duplicates.append(existing)
        
        # Check by URL (if not already found by query)
        url_value = document.get('url') or document.get('metadata', {}).get('url')
        if url_value and not duplicates:
            existing = collection.find_one({'url': url_value})
            if existing:
                duplicates.append(existing)
        
        return duplicates
    
    def _prompt_duplicate_action(self, new_document: Dict[str, Any], 
                                existing_docs: List[Dict[str, Any]]) -> str:
        """
        Prompt user for action when duplicate documents are found.
        
        Args:
            new_document (Dict): New document to be inserted
            existing_docs (List): List of existing documents
            
        Returns:
            str: Action to take ('skip', 'add', 'overwrite', 'update')
        """
        new_query = new_document.get('query', 'Unknown')
        new_url = new_document.get('url', new_document.get('metadata', {}).get('url', 'Unknown'))
        new_stats = new_document.get('statistics', {})
        
        print("\n⚠️  DUPLICATE DOCUMENT DETECTED")
        print("=" * 50)
        print(f"📄 New document: {new_query}")
        print(f"🌐 URL: {new_url}")
        print(f"📊 Sections: {new_stats.get('total_sections', 0)}, "
              f"Words: {new_stats.get('total_words', 0)}")
        
        print(f"\n🔍 Found {len(existing_docs)} existing document(s):")
        for i, existing in enumerate(existing_docs, 1):
            existing_stats = existing.get('statistics', {})
            print(f"  {i}. {existing.get('query', 'Unknown')}")
            print(f"     Created: {existing.get('created_at', 'Unknown')}")
            print(f"     Sections: {existing_stats.get('total_sections', 0)}, "
                  f"Words: {existing_stats.get('total_words', 0)}")
        
        print("\nAvailable actions:")
        print("  [1] Skip - Don't insert the new document")
        print("  [2] Add - Insert as a new document anyway")
        print("  [3] Update - Replace the existing document with new content")
        print("  [4] Overwrite - Delete existing document(s) and insert new one")
        
        while True:
            try:
                choice = input("\nPlease choose an action [1-4]: ").strip()
                
                if choice == '1' or choice.lower() == 'skip':
                    return 'skip'
                elif choice == '2' or choice.lower() == 'add':
                    return 'add'
                elif choice == '3' or choice.lower() == 'update':
                    return 'update'
                elif choice == '4' or choice.lower() == 'overwrite':
                    return 'overwrite'
                else:
                    print("❌ Invalid choice. Please enter 1-4 or skip/add/update/overwrite.")
                    
            except (EOFError, KeyboardInterrupt):
                print("\n⏹️ Operation cancelled by user.")
                return 'skip'
    
    def list_wikipedia_documents(self, include_stats: bool = True) -> List[Dict[str, Any]]:
        """
        List all Wikipedia documents in the collection.
        
        Args:
            include_stats (bool): Whether to include document statistics
            
        Returns:
            List[Dict[str, Any]]: List of document summaries
        """
        try:
            if not self.is_connected():
                if not self.connect():
                    return []
            
            collection = self.get_collection(self.collection_name)
            if collection is None:
                return []
            
            # Project only essential fields for listing
            projection = {
                'query': 1,
                'metadata.query': 1,
                'metadata.url': 1,
                'metadata.extracted_on': 1,
                'summary': 1,
                'created_at': 1,
                'updated_at': 1
            }
            
            if include_stats:
                projection['statistics'] = 1
                projection['section_hierarchy'] = 1
            
            documents = []
            for doc in collection.find({}, projection):
                doc_summary = {
                    'id': str(doc['_id']),
                    'title': doc.get('query') or doc.get('metadata', {}).get('query', 'Unknown'),
                    'url': doc.get('metadata', {}).get('url', ''),
                    'summary_preview': (doc.get('summary', '')[:200] + '...' 
                                      if len(doc.get('summary', '')) > 200 
                                      else doc.get('summary', '')),
                    'created_at': doc.get('created_at'),
                    'updated_at': doc.get('updated_at')
                }
                
                if include_stats and 'statistics' in doc:
                    doc_summary['stats'] = doc['statistics']
                    doc_summary['sections'] = [
                        {'title': s['title'], 'level': s['level']} 
                        for s in doc.get('section_hierarchy', [])
                    ]
                
                documents.append(doc_summary)
            
            return documents
            
        except Exception as e:
            self.logger.error(f"Error listing Wikipedia documents: {e}")
            return []
    
    def get_wikipedia_document(self, query: Optional[str] = None, doc_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve a complete Wikipedia document by query or ID.
        
        Args:
            query (str): Wikipedia query/title to search for
            doc_id (str): Document ID to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Complete document or None
        """
        try:
            if not self.is_connected():
                if not self.connect():
                    return None
            
            collection = self.get_collection(self.collection_name)
            if collection is None:
                return None
            
            # Build search filter
            search_filter = {}
            if doc_id:
                from bson.objectid import ObjectId
                search_filter['_id'] = ObjectId(doc_id)
            elif query:
                search_filter['$or'] = [
                    {'query': {'$regex': re.escape(query), '$options': 'i'}},
                    {'metadata.query': {'$regex': re.escape(query), '$options': 'i'}}
                ]
            else:
                self.logger.error("Either query or doc_id must be provided")
                return None
            
            document = collection.find_one(search_filter)
            if document:
                document['_id'] = str(document['_id'])  # Convert ObjectId to string
                return document
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving Wikipedia document: {e}")
            return None
    
    def get_document_section(self, query: str, section_title: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific section from a Wikipedia document.
        
        Args:
            query (str): Document query/title
            section_title (str): Section title or key to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Section data or None
        """
        try:
            document = self.get_wikipedia_document(query=query)
            if not document:
                return None
            
            # Try to find section by title or normalized key
            section_key = self._normalize_section_key(section_title)
            
            # Check if it's a direct key match
            if section_key in document.get('sections', {}):
                return document['sections'][section_key]
            
            # Search by title
            for key, section in document.get('sections', {}).items():
                if section['title'].lower() == section_title.lower():
                    return section
            
            # Special case for summary
            if section_title.lower() in ['summary', 'introduction']:
                return {
                    'title': 'Summary',
                    'content': document.get('summary', ''),
                    'level': 1,
                    'word_count': len(document.get('summary', '').split()),
                    'character_count': len(document.get('summary', ''))
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving document section: {e}")
            return None
    
    def search_content(self, search_term: str, search_in: str = "all") -> List[Dict[str, Any]]:
        """
        Search for content across Wikipedia documents.
        
        Args:
            search_term (str): Term to search for
            search_in (str): Where to search - "all", "titles", "summaries", "sections"
            
        Returns:
            List[Dict[str, Any]]: Matching documents with highlighted content
        """
        try:
            if not self.is_connected():
                if not self.connect():
                    return []
            
            collection = self.get_collection(self.collection_name)
            if collection is None:
                return []
            
            # Build search query based on search_in parameter
            search_filter = {}
            if search_in == "titles":
                search_filter = {
                    '$or': [
                        {'query': {'$regex': re.escape(search_term), '$options': 'i'}},
                        {'metadata.query': {'$regex': re.escape(search_term), '$options': 'i'}}
                    ]
                }
            elif search_in == "summaries":
                search_filter = {
                    'summary': {'$regex': re.escape(search_term), '$options': 'i'}
                }
            elif search_in == "sections":
                search_filter = {
                    'sections': {
                        '$elemMatch': {
                            'content': {'$regex': re.escape(search_term), '$options': 'i'}
                        }
                    }
                }
            else:  # search_in == "all"
                search_filter = {
                    '$or': [
                        {'query': {'$regex': re.escape(search_term), '$options': 'i'}},
                        {'summary': {'$regex': re.escape(search_term), '$options': 'i'}},
                        {'sections': {
                            '$elemMatch': {
                                'content': {'$regex': re.escape(search_term), '$options': 'i'}
                            }
                        }}
                    ]
                }
            
            results = []
            for doc in collection.find(search_filter):
                result = {
                    'id': str(doc['_id']),
                    'title': doc.get('query', 'Unknown'),
                    'url': doc.get('metadata', {}).get('url', ''),
                    'matches': []
                }
                
                # Find specific matches
                if re.search(re.escape(search_term), doc.get('summary', ''), re.IGNORECASE):
                    result['matches'].append({
                        'type': 'summary',
                        'content': self._highlight_text(doc.get('summary', ''), search_term)
                    })
                
                for section_key, section in doc.get('sections', {}).items():
                    if re.search(re.escape(search_term), section.get('content', ''), re.IGNORECASE):
                        result['matches'].append({
                            'type': 'section',
                            'section_title': section.get('title', section_key),
                            'content': self._highlight_text(section.get('content', ''), search_term)
                        })
                
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error searching content: {e}")
            return []
    
    def _highlight_text(self, text: str, search_term: str, context_chars: int = 150) -> str:
        """
        Highlight search term in text with surrounding context.
        
        Args:
            text (str): Full text content
            search_term (str): Term to highlight
            context_chars (int): Characters to show around the match
            
        Returns:
            str: Text with highlighted term and context
        """
        if not text or not search_term:
            return text
        
        # Find the first occurrence
        match = re.search(re.escape(search_term), text, re.IGNORECASE)
        if not match:
            return text[:context_chars] + "..." if len(text) > context_chars else text
        
        start = max(0, match.start() - context_chars // 2)
        end = min(len(text), match.end() + context_chars // 2)
        
        excerpt = text[start:end]
        
        # Add ellipsis if truncated
        if start > 0:
            excerpt = "..." + excerpt
        if end < len(text):
            excerpt = excerpt + "..."
        
        # Highlight the search term
        highlighted = re.sub(
            f'({re.escape(search_term)})', 
            r'**\1**', 
            excerpt, 
            flags=re.IGNORECASE
        )
        
        return highlighted
    
    def get_collection_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the Wikipedia collection.
        
        Returns:
            Dict[str, Any]: Collection statistics
        """
        try:
            if not self.is_connected():
                if not self.connect():
                    return {}
            
            collection = self.get_collection(self.collection_name)
            if collection is None:
                return {}
            
            # Basic collection stats
            total_docs = collection.count_documents({})
            
            if total_docs == 0:
                return {
                    'total_documents': 0,
                    'message': 'No Wikipedia documents found in collection'
                }
            
            # Aggregate statistics
            pipeline = [
                {
                    '$group': {
                        '_id': None,
                        'total_sections': {'$sum': '$statistics.total_sections'},
                        'total_words': {'$sum': '$statistics.total_words'},
                        'total_characters': {'$sum': '$statistics.total_characters'},
                        'avg_sections': {'$avg': '$statistics.total_sections'},
                        'max_depth': {'$max': '$statistics.hierarchy_depth'}
                    }
                }
            ]
            
            agg_result = list(collection.aggregate(pipeline))
            stats = agg_result[0] if agg_result else {}
            
            return {
                'total_documents': total_docs,
                'total_sections': stats.get('total_sections', 0),
                'total_words': stats.get('total_words', 0),
                'total_characters': stats.get('total_characters', 0),
                'average_sections_per_doc': round(stats.get('avg_sections', 0), 2),
                'maximum_hierarchy_depth': stats.get('max_depth', 0),
                'collection_name': self.collection_name,
                'database_name': self.database_name
            }
            
        except Exception as e:
            self.logger.error(f"Error getting collection statistics: {e}")
            return {}


# Example usage and testing functions
def store_wikipedia_file(file_path: str, storage_manager: WikipediaStorageManager, 
                        interactive: bool = True) -> bool:
    """
    Helper function to store a Wikipedia markdown file.
    
    Args:
        file_path (str): Path to the Wikipedia markdown file
        storage_manager (WikipediaStorageManager): Storage manager instance
        interactive (bool): Whether to prompt user for duplicate handling
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        doc_id = storage_manager.store_wikipedia_document(content, file_path, interactive)
        return doc_id is not None
        
    except Exception as e:
        logging.error(f"Error storing file {file_path}: {e}")
        return False


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test the Wikipedia Storage Manager
    print("Testing Wikipedia Storage Manager...")
    
    with WikipediaStorageManager() as storage:
        if storage.is_connected():
            print(f"✅ Connected to MongoDB: {storage}")
            
            # Get collection statistics
            stats = storage.get_collection_statistics()
            print(f"\n📊 Collection Statistics:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
            
            # List existing documents
            documents = storage.list_wikipedia_documents()
            print(f"\n📄 Existing Documents ({len(documents)}):")
            for doc in documents:
                print(f"  - {doc['title']}: {doc['summary_preview']}")
                if 'stats' in doc:
                    print(f"    Sections: {doc['stats']['total_sections']}, "
                          f"Words: {doc['stats']['total_words']}")
        else:
            print("❌ Failed to connect to MongoDB")
            print("Make sure MongoDB is running on localhost:27017")
