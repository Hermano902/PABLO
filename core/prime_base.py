"""
Abstract base class for all primes.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import threading


class PrimeError(Exception):
    """Base exception for prime execution errors."""
    pass


class Prime(ABC):
    """Abstract base class for all primes."""
    
    def __init__(self, name: str, metadata: Optional[Dict] = None):
        self.name = name
        self.metadata = metadata or {}
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        self._initialized = False
        self._shutdown_flag = threading.Event()
    
    def initialize(self) -> None:
        """Optional initialization hook."""
        if not self._initialized:
            self._initialized = True
            self._on_initialize()
    
    def shutdown(self) -> None:
        """Graceful shutdown hook."""
        self._shutdown_flag.set()
        self._on_shutdown()
    
    @abstractmethod
    def __call__(self, context: Dict[str, Any]) -> Any:
        """
        Execute the prime.
        
        Args:
            context: Dict with arbitrary key-values (no fixed schema).
                     Each prime interprets as needed.
        
        Returns:
            The result of prime execution.
        
        Raises:
            PrimeError: On execution failure.
        """
        pass
    
    def validate_context(self, context: Dict[str, Any]) -> bool:
        """
        Optional: Check if context is valid for this prime.
        
        Override in subclasses for specific validation.
        """
        return True
    
    def _on_initialize(self) -> None:
        """Override for custom initialization logic."""
        pass
    
    def _on_shutdown(self) -> None:
        """Override for custom shutdown logic."""
        pass
    
    def _thread_safe_execute(self, func, *args, **kwargs):
        """Execute a function with thread safety."""
        with self._lock:
            return func(*args, **kwargs)
    
    def _check_shutdown(self) -> None:
        """Check if shutdown has been requested."""
        if self._shutdown_flag.is_set():
            raise PrimeError(f"Prime {self.name} is shutting down")
    
    def __repr__(self) -> str:
        return f"Prime({self.name})"