import sqlite3
import json
import os
import datetime
import uuid

DB_PATH = "blood_donation.db"

class DBResponse:
    def __init__(self, data=None, error=None):
        self.data = data
        self.error = error

class LocalDB:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
    
    def table(self, table_name):
        return TableQuery(self.db_path, table_name)
    
    def from_(self, table_name):
        # Support both .table() and .from() (v1/v2 sdk styles)
        return self.table(table_name)

class TableQuery:
    def __init__(self, db_path, table_name):
        self.db_path = db_path
        self.table_name = table_name
        self.filters = []
        self.select_cols = "*"
        self.order_by = None
        self.limit_val = None
        self.operation = "select"
        self.data_payload = None

    def select(self, columns="*"):
        self.operation = "select"
        self.select_cols = columns
        return self

    def insert(self, data):
        self.operation = "insert"
        self.data_payload = data if isinstance(data, list) else [data]
        return self

    def update(self, data):
        self.operation = "update"
        self.data_payload = data
        return self
    
    def upsert(self, data, on_conflict=None):
        # SQLite upsert is INSERT OR REPLACE or ON CONFLICT
        # For simplicity in this project, we'll treat it as INSERT OR REPLACE
        self.operation = "upsert"
        self.data_payload = data if isinstance(data, list) else [data]
        return self

    def delete(self):
        self.operation = "delete"
        return self

    # --- Filters ---
    def eq(self, column, value):
        self.filters.append((column, "=", value))
        return self
    
    def neq(self, column, value):
        self.filters.append((column, "!=", value))
        return self
    
    def gt(self, column, value):
        self.filters.append((column, ">", value))
        return self
    
    def lt(self, column, value):
        self.filters.append((column, "<", value))
        return self
    
    def ilike(self, column, value):
        self.filters.append((column, "LIKE", value))
        return self
        
    def order(self, column, desc=False):
        direction = "DESC" if desc else "ASC"
        self.order_by = f"{column} {direction}"
        return self
    
    def limit(self, count):
        self.limit_val = count
        return self

    def execute(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row # To access columns by name
        cursor = conn.cursor()
        
        try:
            if self.operation == "select":
                return self._execute_select(cursor)
                
            elif self.operation == "insert":
                return self._execute_insert(conn, cursor)
                
            elif self.operation == "update":
                return self._execute_update(conn, cursor)
                
            elif self.operation == "upsert":
                 return self._execute_insert(conn, cursor, replace=True)

            elif self.operation == "delete":
                return self._execute_delete(conn, cursor)
                
        except Exception as e:
            conn.close()
            print(f"DB Error: {e}")
            return DBResponse(data=None, error=str(e))
        
        conn.close()
        return DBResponse(data=[]) # operations typically return results in Supabase, handled in helper methods

    def _build_where(self):
        if not self.filters:
            return "", []
        
        clauses = []
        params = []
        for col, op, val in self.filters:
            clauses.append(f"{col} {op} ?")
            params.append(val)
        
        return "WHERE " + " AND ".join(clauses), params

    def _execute_select(self, cursor):
        where_clause, params = self._build_where()
        
        query = f"SELECT {self.select_cols} FROM {self.table_name} {where_clause}"
        
        if self.order_by:
            query += f" ORDER BY {self.order_by}"
            
        if self.limit_val:
            query += f" LIMIT {self.limit_val}"
            
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert to dict list
        results = [dict(row) for row in rows]
        
        # Determine if single result needed? Supabase returns list unless .single() called (not handled here, returning list)
        return DBResponse(data=results, error=None)

    def _execute_insert(self, conn, cursor, replace=False):
        results = []
        action = "INSERT OR REPLACE" if replace else "INSERT"
        
        for item in self.data_payload:
            # Handle standard defaults if missing
            if 'created_at' not in item and replace:
                 # If upsert, we might want to preserve expected behavior, simplified here
                 pass
            if 'created_at' not in item:
                 item['created_at'] = datetime.datetime.now().isoformat()
            
            # Special handling for UUIDs if needed? request ID often auto-gen by DB
            # For 'users', we assume telegram_id is key. For 'requests', if 'id' missing, gen it
            if self.table_name == 'requests' and 'id' not in item:
                item['id'] = str(uuid.uuid4())

            keys = list(item.keys())
            placeholders = ["?"] * len(keys)
            values = list(item.values())
            
            # Serialize dict/lists to json strings for SQLite
            clean_values = []
            for v in values:
                if isinstance(v, (dict, list)):
                    clean_values.append(json.dumps(v))
                else:
                    clean_values.append(v)
            
            query = f"{action} INTO {self.table_name} ({', '.join(keys)}) VALUES ({', '.join(placeholders)})"
            cursor.execute(query, clean_values)
            
            # Fetch the inserted row (for return) - SQLite doesn't support RETURNING * well in all versions
            # We will just return the item payload + any defaults we added
            results.append(item)

        conn.commit()
        return DBResponse(data=results, error=None)

    def _execute_update(self, conn, cursor):
        where_clause, params = self._build_where()
        if not self.filters:
            # Dangerous update all protection
            return DBResponse(data=None, error="Update requires filters")
            
        updates = []
        update_params = []
        for key, val in self.data_payload.items():
            updates.append(f"{key} = ?")
            if isinstance(val, (dict, list)):
                update_params.append(json.dumps(val))
            else:
                update_params.append(val)
                
        query = f"UPDATE {self.table_name} SET {', '.join(updates)} {where_clause}"
        full_params = update_params + params
        
        cursor.execute(query, full_params)
        conn.commit()
        
        # Fetch updated - mock return
        return DBResponse(data=[self.data_payload], error=None)

    def _execute_delete(self, conn, cursor):
        where_clause, params = self._build_where()
        if not self.filters:
            return DBResponse(data=None, error="Delete requires filters")
            
        query = f"DELETE FROM {self.table_name} {where_clause}"
        cursor.execute(query, params)
        conn.commit()
        
        return DBResponse(data=[], error=None)
