"""
MongoDB Connection Manager for Quiz Game Project
Provides a class-based interface for connecting to local MongoDB instance.
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from pymongo.database import Database
from pymongo.collection import Collection


class MongoDBManager:
    """
    A class to manage MongoDB connections and operations for the quiz game project.
    
    This class provides methods to connect to local MongoDB, manage databases and collections,
    and handle session state data for the quiz game.
    """
    
    def __init__(self, 
                 host: str = "localhost", 
                 port: int = 27017, 
                 database_name: str = "quiz_game_db",
                 connection_timeout: int = 5000):
        """
        Initialize the MongoDB manager.
        
        Args:
            host (str): MongoDB host address
            port (int): MongoDB port number
            database_name (str): Default database name for the quiz game
            connection_timeout (int): Connection timeout in milliseconds
        """
        self.host = host
        self.port = port
        self.database_name = database_name
        self.connection_timeout = connection_timeout
        self.client: Optional[MongoClient] = None
        self.database: Optional[Database] = None
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
    def connect(self) -> bool:
        """
        Establish connection to MongoDB.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Create MongoDB URI
            uri = f"mongodb://{self.host}:{self.port}/"
            
            # Create client with connection timeout
            self.client = MongoClient(
                uri,
                serverSelectionTimeoutMS=self.connection_timeout,
                connectTimeoutMS=self.connection_timeout
            )
            
            # Test the connection
            self.client.admin.command('ping')
            
            # Get the database
            self.database = self.client[self.database_name]
            
            self.logger.info(f"Successfully connected to MongoDB at {self.host}:{self.port}")
            self.logger.info(f"Using database: {self.database_name}")
            
            return True
            
        except ConnectionFailure as e:
            self.logger.error(f"Failed to connect to MongoDB: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to MongoDB: {e}")
            return False
    
    def disconnect(self) -> None:
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
            self.client = None
            self.database = None
            self.logger.info("Disconnected from MongoDB")
    
    def is_connected(self) -> bool:
        """
        Check if the MongoDB connection is active.
        
        Returns:
            bool: True if connected, False otherwise
        """
        if not self.client:
            return False
        
        try:
            # Ping the server to check connection
            self.client.admin.command('ping')
            return True
        except Exception:
            return False
    
    def list_collections(self) -> List[str]:
        """
        List all collections in the current database.
        
        Returns:
            List[str]: List of collection names
        """
        if self.database is None:
            self.logger.warning("No database connection available")
            return []
        
        try:
            collections = self.database.list_collection_names()
            self.logger.info(f"Found {len(collections)} collections in database '{self.database_name}'")
            return collections
        except Exception as e:
            self.logger.error(f"Error listing collections: {e}")
            return []
    
    def get_collection_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed information about all collections.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary with collection names as keys and info as values
        """
        if self.database is None:
            self.logger.warning("No database connection available")
            return {}
        
        collection_info = {}
        
        try:
            for collection_name in self.list_collections():
                collection = self.database[collection_name]
                
                # Get collection stats
                stats = self.database.command("collStats", collection_name)
                
                collection_info[collection_name] = {
                    "document_count": collection.count_documents({}),
                    "size_bytes": stats.get("size", 0),
                    "average_object_size": stats.get("avgObjSize", 0),
                    "indexes": len(list(collection.list_indexes())),
                    "index_names": [idx["name"] for idx in collection.list_indexes()]
                }
                
            return collection_info
            
        except Exception as e:
            self.logger.error(f"Error getting collection info: {e}")
            return {}
    
    def get_collection(self, collection_name: str) -> Optional[Collection]:
        """
        Get a specific collection object.
        
        Args:
            collection_name (str): Name of the collection
            
        Returns:
            Collection: MongoDB collection object or None if error
        """
        if self.database is None:
            self.logger.warning("No database connection available")
            return None
        
        try:
            return self.database[collection_name]
        except Exception as e:
            self.logger.error(f"Error getting collection '{collection_name}': {e}")
            return None
    
    def create_collection(self, collection_name: str) -> bool:
        """
        Create a new collection.
        
        Args:
            collection_name (str): Name of the collection to create
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.database is None:
            self.logger.warning("No database connection available")
            return False
        
        try:
            self.database.create_collection(collection_name)
            self.logger.info(f"Created collection: {collection_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating collection '{collection_name}': {e}")
            return False
    
    def drop_collection(self, collection_name: str) -> bool:
        """
        Drop a collection.
        
        Args:
            collection_name (str): Name of the collection to drop
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.database is None:
            self.logger.warning("No database connection available")
            return False
        
        try:
            self.database.drop_collection(collection_name)
            self.logger.info(f"Dropped collection: {collection_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error dropping collection '{collection_name}': {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dict[str, Any]: Database statistics
        """
        if self.database is None:
            self.logger.warning("No database connection available")
            return {}
        
        try:
            stats = self.database.command("dbStats")
            return {
                "database_name": self.database_name,
                "collections": stats.get("collections", 0),
                "objects": stats.get("objects", 0),
                "data_size": stats.get("dataSize", 0),
                "storage_size": stats.get("storageSize", 0),
                "indexes": stats.get("indexes", 0),
                "index_size": stats.get("indexSize", 0)
            }
        except Exception as e:
            self.logger.error(f"Error getting database stats: {e}")
            return {}
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
    
    def __repr__(self) -> str:
        """String representation of the MongoDB manager."""
        status = "connected" if self.is_connected() else "disconnected"
        return f"MongoDBManager(host='{self.host}', port={self.port}, database='{self.database_name}', status='{status}')"


# Example usage and testing
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test the MongoDB connection
    print("Testing MongoDB Connection...")
    
    # Using context manager (recommended)
    with MongoDBManager() as mongo_manager:
        if mongo_manager.is_connected():
            print(f"✅ Connected to MongoDB: {mongo_manager}")
            
            # List all collections
            collections = mongo_manager.list_collections()
            print(f"\n📁 Collections in database:")
            if collections:
                for i, collection in enumerate(collections, 1):
                    print(f"  {i}. {collection}")
            else:
                print("  No collections found")
            
            # Get detailed collection info
            collection_info = mongo_manager.get_collection_info()
            if collection_info:
                print(f"\n📊 Collection Details:")
                for name, info in collection_info.items():
                    print(f"  {name}:")
                    print(f"    Documents: {info['document_count']}")
                    print(f"    Size: {info['size_bytes']} bytes")
                    print(f"    Indexes: {info['indexes']}")
            
            # Get database statistics
            db_stats = mongo_manager.get_database_stats()
            if db_stats:
                print(f"\n🗃️  Database Statistics:")
                print(f"  Database: {db_stats['database_name']}")
                print(f"  Collections: {db_stats['collections']}")
                print(f"  Total Objects: {db_stats['objects']}")
                print(f"  Data Size: {db_stats['data_size']} bytes")
                print(f"  Storage Size: {db_stats['storage_size']} bytes")
        else:
            print("❌ Failed to connect to MongoDB")
            print("Make sure MongoDB is running on localhost:27017")
