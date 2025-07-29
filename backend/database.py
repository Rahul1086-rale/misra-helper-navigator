import sqlite3
import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import threading

class DatabaseManager:
    def __init__(self, db_path: str = "sessions.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # User sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    session_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, project_id)
                )
            ''')
            
            # Chat sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    chat_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, project_id)
                )
            ''')
            
            # User model settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_model_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL UNIQUE,
                    settings TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # File tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    original_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, project_id, file_type)
                )
            ''')
            
            conn.commit()
            conn.close()
    
    def get_user_session(self, user_id: str, project_id: str) -> Optional[Dict[str, Any]]:
        """Get user session data"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT session_data FROM user_sessions 
                WHERE user_id = ? AND project_id = ?
            ''', (user_id, project_id))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return json.loads(result[0])
            return None
    
    def save_user_session(self, user_id: str, project_id: str, session_data: Dict[str, Any]):
        """Save or update user session data"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_sessions (user_id, project_id, session_data, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, project_id, json.dumps(session_data)))
            
            conn.commit()
            conn.close()
    
    def get_chat_session(self, user_id: str, project_id: str) -> Optional[Any]:
        """Get chat session (stored as serialized data)"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT chat_data FROM chat_sessions 
                WHERE user_id = ? AND project_id = ?
            ''', (user_id, project_id))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else None
    
    def save_chat_session(self, user_id: str, project_id: str, chat_session: Any):
        """Save chat session (note: actual chat objects can't be serialized easily)"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # For now, we'll store a marker that chat session exists
            cursor.execute('''
                INSERT OR REPLACE INTO chat_sessions (user_id, project_id, chat_data, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, project_id, "active"))
            
            conn.commit()
            conn.close()
    
    def get_user_model_settings(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user-specific model settings"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT settings FROM user_model_settings WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return json.loads(result[0])
            return None
    
    def save_user_model_settings(self, user_id: str, settings: Dict[str, Any]):
        """Save user-specific model settings"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_model_settings (user_id, settings, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, json.dumps(settings)))
            
            conn.commit()
            conn.close()
    
    def save_user_file(self, user_id: str, project_id: str, file_type: str, 
                      file_path: str, original_name: str = None):
        """Track user files"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_files 
                (user_id, project_id, file_type, file_path, original_name, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, project_id, file_type, file_path, original_name))
            
            conn.commit()
            conn.close()
    
    def get_user_file(self, user_id: str, project_id: str, file_type: str) -> Optional[Dict[str, str]]:
        """Get user file information"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT file_path, original_name FROM user_files 
                WHERE user_id = ? AND project_id = ? AND file_type = ?
            ''', (user_id, project_id, file_type))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {"file_path": result[0], "original_name": result[1]}
            return None
    
    def delete_user_session(self, user_id: str, project_id: str):
        """Delete user session and related data"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Delete session data
            cursor.execute('''
                DELETE FROM user_sessions WHERE user_id = ? AND project_id = ?
            ''', (user_id, project_id))
            
            # Delete chat session
            cursor.execute('''
                DELETE FROM chat_sessions WHERE user_id = ? AND project_id = ?
            ''', (user_id, project_id))
            
            # Delete file tracking
            cursor.execute('''
                DELETE FROM user_files WHERE user_id = ? AND project_id = ?
            ''', (user_id, project_id))
            
            conn.commit()
            conn.close()

# Global database instance
db = DatabaseManager()