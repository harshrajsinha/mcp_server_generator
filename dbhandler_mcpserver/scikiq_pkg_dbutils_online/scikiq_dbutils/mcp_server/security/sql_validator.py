"""
SQL Injection Prevention Module

Validates SQL queries for security threats and dangerous patterns.
"""

import re
import logging
from typing import Tuple, List, Set


class SQLValidator:
    """
    SQL query validator to prevent injection attacks and dangerous operations
    """
    
    # Dangerous SQL patterns that should be blocked
    DANGEROUS_PATTERNS = [
        # Multiple statements
        r";\s*DROP\s+",
        r";\s*DELETE\s+FROM\s+",
        r";\s*UPDATE\s+.*SET\s+",
        r";\s*INSERT\s+INTO\s+",
        r";\s*CREATE\s+",
        r";\s*ALTER\s+",
        r";\s*TRUNCATE\s+",
        r";\s*GRANT\s+",
        r";\s*REVOKE\s+",
        
        # Stored procedures and functions
        r"EXEC\s*\(",
        r"EXECUTE\s*\(",
        r"xp_cmdshell",
        r"sp_executesql",
        r"CALL\s+",
        
        # Union-based injection
        r"UNION\s+ALL\s+SELECT",
        r"UNION\s+SELECT",
        
        # Information schema access
        r"information_schema\.",
        r"sys\.",
        r"mysql\.",
        r"pg_catalog\.",
        
        # File operations
        r"INTO\s+OUTFILE",
        r"LOAD_FILE\s*\(",
        r"LOAD\s+DATA",
        
        # Conditional logic that might be injection
        r"IF\s*\(",
        r"CASE\s+WHEN",
        
        # Script tags (for NoSQL injection)
        r"<script",
        r"javascript:",
        
        # MongoDB injection patterns
        r"\$where",
        r"\$ne",
        r"\$gt",
        r"\$lt",
        r"\$or",
        r"\$and",
    ]
    
    # Allowed SQL keywords for SELECT queries
    ALLOWED_SELECT_KEYWORDS = {
        'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER',
        'ON', 'AND', 'OR', 'NOT', 'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'IS',
        'NULL', 'ORDER', 'BY', 'GROUP', 'HAVING', 'LIMIT', 'OFFSET', 'DISTINCT',
        'AS', 'ASC', 'DESC', 'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'COALESCE',
        'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'CAST', 'CONVERT'
    }
    
    # Allowed SQL keywords for modification queries
    ALLOWED_DML_KEYWORDS = {
        'INSERT', 'UPDATE', 'DELETE', 'INTO', 'VALUES', 'SET'
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @classmethod
    def is_safe_query(cls, query: str) -> Tuple[bool, str]:
        """
        Check if a query is safe to execute
        
        Args:
            query: SQL query to validate
            
        Returns:
            Tuple of (is_safe, reason)
        """
        if not query or not query.strip():
            return False, "Empty query not allowed"
        
        query_clean = query.strip()
        query_upper = query_clean.upper()
        
        # Check for multiple statements (basic check)
        semicolon_count = query_clean.count(';')
        if semicolon_count > 1:
            return False, "Multiple SQL statements detected"
        
        # Allow single trailing semicolon
        if semicolon_count == 1 and not query_clean.rstrip().endswith(';'):
            return False, "Multiple SQL statements detected"
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return False, f"Dangerous pattern detected: {pattern}"
        
        # Check for SQL comments that might hide malicious code
        if '--' in query or '/*' in query or '*/' in query:
            return False, "SQL comments not allowed"
        
        # Check for suspicious character combinations
        if '@@' in query:
            return False, "System variable access not allowed"
        
        # Check for hex-encoded strings (possible obfuscation)
        if re.search(r'0x[0-9a-f]+', query, re.IGNORECASE):
            return False, "Hexadecimal literals not allowed"
        
        # Basic keyword validation based on query type
        first_word = query_upper.split()[0] if query_upper.split() else ""
        
        if first_word in ['SELECT', 'WITH']:
            # SELECT queries are generally safer
            pass
        elif first_word in ['INSERT', 'UPDATE', 'DELETE']:
            # DML operations need extra scrutiny
            if not cls._validate_dml_query(query_upper):
                return False, "Invalid DML query structure"
        else:
            return False, f"Query type '{first_word}' not allowed"
        
        return True, "Query appears safe"
    
    @classmethod
    def _validate_dml_query(cls, query_upper: str) -> bool:
        """
        Validate DML (INSERT/UPDATE/DELETE) queries
        
        Args:
            query_upper: Uppercase SQL query
            
        Returns:
            True if query structure is valid
        """
        # Basic validation for DML queries
        if query_upper.startswith('DELETE'):
            # DELETE must have WHERE clause (prevent accidental full table deletes)
            if 'WHERE' not in query_upper:
                return False
        
        if query_upper.startswith('UPDATE'):
            # UPDATE must have WHERE clause and SET clause
            if 'WHERE' not in query_upper or 'SET' not in query_upper:
                return False
        
        return True
    
    @classmethod
    def sanitize_identifier(cls, identifier: str) -> str:
        """
        Sanitize table/column names and other SQL identifiers
        
        Args:
            identifier: SQL identifier to sanitize
            
        Returns:
            Sanitized identifier
            
        Raises:
            ValueError: If identifier is invalid
        """
        if not identifier:
            raise ValueError("Empty identifier not allowed")
        
        # Only allow alphanumeric, underscore, and dot (for schema.table)
        if not re.match(r'^[a-zA-Z0-9_\.]+$', identifier):
            raise ValueError(f"Invalid identifier: {identifier}")
        
        # Check length
        if len(identifier) > 128:
            raise ValueError("Identifier too long")
        
        # Must start with letter or underscore
        if identifier[0].isdigit():
            raise ValueError("Identifier cannot start with digit")
        
        return identifier
    
    @classmethod
    def sanitize_limit_clause(cls, limit_value: any) -> int:
        """
        Sanitize LIMIT clause values
        
        Args:
            limit_value: Limit value to sanitize
            
        Returns:
            Safe integer limit value
            
        Raises:
            ValueError: If limit value is invalid
        """
        if limit_value is None:
            return 1000  # Default safe limit
        
        try:
            limit_int = int(limit_value)
        except (ValueError, TypeError):
            raise ValueError("Invalid limit value - must be integer")
        
        if limit_int < 1:
            raise ValueError("Limit must be positive")
        
        if limit_int > 10000:  # Reasonable maximum
            raise ValueError("Limit too large (maximum 10000)")
        
        return limit_int
    
    @classmethod
    def validate_like_pattern(cls, pattern: str) -> Tuple[bool, str]:
        """
        Validate LIKE pattern for safety
        
        Args:
            pattern: LIKE pattern to validate
            
        Returns:
            Tuple of (is_valid, reason)
        """
        if not pattern:
            return False, "Empty LIKE pattern"
        
        # Check for overly broad patterns that might cause performance issues
        if pattern == '%':
            return False, "Overly broad LIKE pattern"
        
        if pattern.startswith('%') and pattern.endswith('%') and len(pattern) < 5:
            return False, "LIKE pattern too broad, may cause performance issues"
        
        # Check for injection attempts in LIKE patterns
        if any(char in pattern for char in [';', '--', '/*', '*/']):
            return False, "Invalid characters in LIKE pattern"
        
        return True, "LIKE pattern is valid"