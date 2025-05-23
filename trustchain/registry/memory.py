"""In-memory trust registry implementation for TrustChain."""

import time
import threading
from typing import Dict, List, Optional, Any, AsyncIterator

from trustchain.core.models import KeyMetadata, SignatureAlgorithm
from trustchain.registry.base import TrustRegistry
from trustchain.utils.exceptions import RegistryError, KeyNotFoundError


class MemoryRegistry(TrustRegistry):
    """In-memory trust registry for development and testing."""
    
    def __init__(self, namespace: str = "trustchain"):
        super().__init__(namespace)
        self._keys: Dict[str, KeyMetadata] = {}
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        
        # Statistics
        self._stats = {
            "keys_registered": 0,
            "keys_revoked": 0,
            "keys_updated": 0,
            "tools_registered": 0,
            "get_key_calls": 0,
            "list_keys_calls": 0,
            "search_calls": 0
        }
    
    async def start(self) -> None:
        """Initialize the memory registry."""
        with self._lock:
            self._started = True
    
    async def stop(self) -> None:
        """Shutdown the memory registry."""
        with self._lock:
            self._started = False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check registry health status."""
        with self._lock:
            return {
                "status": "healthy" if self._started else "stopped",
                "type": "memory",
                "namespace": self.namespace,
                "total_keys": len(self._keys),
                "valid_keys": len([k for k in self._keys.values() if k.is_valid]),
                "total_tools": len(self._tools),
                "memory_usage": {
                    "keys": len(self._keys),
                    "tools": len(self._tools)
                }
            }
    
    async def register_key(self, key_metadata: KeyMetadata) -> None:
        """Register a new key in the registry."""
        self.validate_key_metadata(key_metadata)
        
        with self._lock:
            if key_metadata.key_id in self._keys:
                raise RegistryError(
                    f"Key already exists: {key_metadata.key_id}",
                    operation="register_key"
                )
            
            # Store a copy to prevent external modifications
            self._keys[key_metadata.key_id] = key_metadata.copy(deep=True)
            self._stats["keys_registered"] += 1
    
    async def get_key(self, key_id: str) -> Optional[KeyMetadata]:
        """Retrieve key metadata by ID."""
        with self._lock:
            self._stats["get_key_calls"] += 1
            key_metadata = self._keys.get(key_id)
            
            if key_metadata:
                # Return a copy to prevent external modifications
                return key_metadata.copy(deep=True)
            
            return None
    
    async def update_key(self, key_metadata: KeyMetadata) -> None:
        """Update existing key metadata."""
        self.validate_key_metadata(key_metadata)
        
        with self._lock:
            if key_metadata.key_id not in self._keys:
                raise KeyNotFoundError(key_metadata.key_id)
            
            self._keys[key_metadata.key_id] = key_metadata.copy(deep=True)
            self._stats["keys_updated"] += 1
    
    async def revoke_key(self, key_id: str, reason: str = "Manual revocation") -> None:
        """Revoke a key."""
        with self._lock:
            if key_id not in self._keys:
                raise KeyNotFoundError(key_id)
            
            key_metadata = self._keys[key_id]
            key_metadata.revoke(reason)
            self._stats["keys_revoked"] += 1
    
    async def list_keys(
        self,
        tool_id: Optional[str] = None,
        algorithm: Optional[SignatureAlgorithm] = None,
        valid_only: bool = True
    ) -> List[KeyMetadata]:
        """List keys with optional filtering."""
        with self._lock:
            self._stats["list_keys_calls"] += 1
            keys = []
            
            for key_metadata in self._keys.values():
                # Apply filters
                if tool_id and key_metadata.tool_id != tool_id:
                    continue
                
                if algorithm and key_metadata.algorithm != algorithm:
                    continue
                
                if valid_only and not key_metadata.is_valid:
                    continue
                
                # Return a copy
                keys.append(key_metadata.copy(deep=True))
            
            # Sort by creation time (newest first)
            keys.sort(key=lambda k: k.valid_from, reverse=True)
            return keys
    
    async def register_tool(self, tool_id: str, metadata: Dict[str, Any]) -> None:
        """Register a tool in the registry."""
        with self._lock:
            self._tools[tool_id] = {
                **metadata,
                "registered_at": int(time.time() * 1000),
                "tool_id": tool_id
            }
            self._stats["tools_registered"] += 1
    
    async def get_tool_keys(self, tool_id: str) -> List[KeyMetadata]:
        """Get all keys for a specific tool."""
        return await self.list_keys(tool_id=tool_id)
    
    async def get_tool_metadata(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a tool."""
        with self._lock:
            metadata = self._tools.get(tool_id)
            if metadata:
                return metadata.copy()
            return None
    
    async def search_keys(self, query: Dict[str, Any]) -> List[KeyMetadata]:
        """Search keys based on query parameters."""
        with self._lock:
            self._stats["search_calls"] += 1
            results = []
            
            for key_metadata in self._keys.values():
                match = True
                
                # Check each query parameter
                for field, value in query.items():
                    if field == "tool_id":
                        if key_metadata.tool_id != value:
                            match = False
                            break
                    elif field == "algorithm":
                        if key_metadata.algorithm != value:
                            match = False
                            break
                    elif field == "valid":
                        if key_metadata.is_valid != value:
                            match = False
                            break
                    elif field == "created_after":
                        if key_metadata.valid_from <= value:
                            match = False
                            break
                    elif field == "created_before":
                        if key_metadata.valid_from >= value:
                            match = False
                            break
                    elif field == "usage_min":
                        if key_metadata.usage_count < value:
                            match = False
                            break
                    elif field == "key_rotation_id":
                        if key_metadata.key_rotation_id != value:
                            match = False
                            break
                
                if match:
                    results.append(key_metadata.copy(deep=True))
            
            # Sort by relevance (usage count and recency)
            results.sort(
                key=lambda k: (k.usage_count, k.valid_from),
                reverse=True
            )
            
            return results
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._lock:
            # Calculate additional stats
            valid_keys = [k for k in self._keys.values() if k.is_valid]
            revoked_keys = [k for k in self._keys.values() if k.revoked]
            
            algorithm_counts = {}
            tool_counts = {}
            
            for key in self._keys.values():
                # Count by algorithm
                algo = key.algorithm.value
                algorithm_counts[algo] = algorithm_counts.get(algo, 0) + 1
                
                # Count by tool
                tool_id = key.tool_id
                tool_counts[tool_id] = tool_counts.get(tool_id, 0) + 1
            
            return {
                "operation_stats": self._stats.copy(),
                "key_stats": {
                    "total": len(self._keys),
                    "valid": len(valid_keys),
                    "revoked": len(revoked_keys),
                    "expired": len([k for k in self._keys.values() 
                                  if not k.is_valid and not k.revoked]),
                    "by_algorithm": algorithm_counts,
                    "by_tool": tool_counts
                },
                "tool_stats": {
                    "total": len(self._tools),
                    "tools": list(self._tools.keys())
                },
                "registry_info": {
                    "type": "memory",
                    "namespace": self.namespace,
                    "started": self._started
                }
            }
    
    async def stream_keys(self, batch_size: int = 100) -> AsyncIterator[List[KeyMetadata]]:
        """Stream all keys in batches."""
        with self._lock:
            keys = list(self._keys.values())
        
        # Stream in batches
        for i in range(0, len(keys), batch_size):
            batch = keys[i:i + batch_size]
            # Return copies
            yield [key.copy(deep=True) for key in batch]
    
    async def bulk_register_keys(self, keys: List[KeyMetadata]) -> Dict[str, Any]:
        """Register multiple keys in a single operation."""
        success_count = 0
        error_count = 0
        errors = []
        
        with self._lock:
            for key_metadata in keys:
                try:
                    # Validate without calling async method
                    self.validate_key_metadata(key_metadata)
                    
                    if key_metadata.key_id in self._keys:
                        errors.append({
                            "key_id": key_metadata.key_id,
                            "error": "Key already exists"
                        })
                        error_count += 1
                        continue
                    
                    self._keys[key_metadata.key_id] = key_metadata.copy(deep=True)
                    success_count += 1
                    
                except Exception as e:
                    errors.append({
                        "key_id": key_metadata.key_id,
                        "error": str(e)
                    })
                    error_count += 1
            
            # Update stats
            self._stats["keys_registered"] += success_count
        
        return {
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors,
            "total_processed": len(keys)
        }
    
    # Additional utility methods specific to memory registry
    
    def clear_all_keys(self) -> int:
        """Clear all keys from registry. Returns count of removed keys."""
        with self._lock:
            count = len(self._keys)
            self._keys.clear()
            return count
    
    def clear_all_tools(self) -> int:
        """Clear all tools from registry. Returns count of removed tools."""
        with self._lock:
            count = len(self._tools)
            self._tools.clear()
            return count
    
    def reset_statistics(self) -> None:
        """Reset all statistics counters."""
        with self._lock:
            self._stats = {
                "keys_registered": 0,
                "keys_revoked": 0,
                "keys_updated": 0,
                "tools_registered": 0,
                "get_key_calls": 0,
                "list_keys_calls": 0,
                "search_calls": 0
            }
    
    def get_key_count(self) -> int:
        """Get current key count."""
        with self._lock:
            return len(self._keys)
    
    def get_tool_count(self) -> int:
        """Get current tool count."""
        with self._lock:
            return len(self._tools)
    
    def export_keys(self) -> List[Dict[str, Any]]:
        """Export all keys as dictionaries."""
        with self._lock:
            return [key.dict() for key in self._keys.values()]
    
    def import_keys(self, key_dicts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Import keys from dictionaries."""
        keys = []
        for key_dict in key_dicts:
            try:
                key = KeyMetadata(**key_dict)
                keys.append(key)
            except Exception as e:
                # Skip invalid key data
                continue
        
        # Use bulk register
        return self.bulk_register_keys(keys) 