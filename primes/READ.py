"""
READ Prime - Perception of text/input.
"""

import time
import threading
import sys
import select
from typing import Dict, Any, Optional
from core.prime_base import Prime, PrimeError
from core.queues import observation_queue
from core.compound import Compound
from core.primebit import PrimeBit


class READ(Prime):
    """READ prime for text/input perception."""
    
    def __init__(self):
        super().__init__("READ")
        self._recent_sent = set()  # Track hashes of recent observations
        self._send_cooldown = 0.1  # Seconds between same observation
        self._last_sent_time = {}
        self._thread = None
        self._running = False
        self._input_sources = ["stdin"]  # Can be extended: ["stdin", "file", "socket"]
        self._input_buffer = []
        
    def initialize(self) -> None:
        """Start the autonomous observation thread."""
        super().initialize()
        self._running = True
        self._thread = threading.Thread(target=self._observation_loop, daemon=True)
        self._thread.start()
        print(f"READ initialized - monitoring: {self._input_sources}")
    
    def shutdown(self) -> None:
        """Stop the observation thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        super().shutdown()
    
    def __call__(self, context: Dict[str, Any]) -> Any:
        """
        Execute READ prime.
        
        Consultation mode (on-demand):
        {
            "input": "text to read",
            "mode": "consultation"
        }
        
        Or:
        {
            "query": "read this",
            "text": "actual text"
        }
        
        Returns: Compound with READ prime
        """
        # Determine mode
        if "mode" in context and context["mode"] == "consultation":
            return self._consultation_mode(context)
        elif "input" in context or "query" in context:
            # Implicit consultation mode
            return self._consultation_mode(context)
        
        # Autonomous mode - called internally by thread
        return None
    
    def _consultation_mode(self, context: Dict[str, Any]) -> Compound:
        """Handle on-demand consultation."""
        # Extract input text
        input_text = ""
        if "input" in context:
            input_text = context["input"]
        elif "query" in context:
            input_text = context["query"]
        elif "text" in context:
            input_text = context["text"]
        else:
            raise PrimeError("READ consultation: No input text provided")
        
        # Create observation
        observation = self._create_observation(input_text, mode="consultation")
        
        # Create compound
        primebit = PrimeBit.from_prime_names({"READ"})
        
        compound = Compound(
            id=-1,  # Temporary ID - will be assigned by KNOW if stored
            text=input_text,
            primebit=primebit,
            compound_type="data",
            provenance_data={
                "provenance": ["READ_consultation"],
                "raw_input": input_text,
                "tokens": input_text.split(),
                "mode": "consultation",
                "timestamp": time.time()
            }
        )
        
        return compound
    
    def _observation_loop(self) -> None:
        """Autonomous observation loop (runs in background thread)."""
        print("READ: Starting autonomous observation loop")
        
        while self._running:
            try:
                # Check each input source
                if "stdin" in self._input_sources:
                    self._check_stdin()
                
                # Check simulation for testing
                self._check_simulation()
                
                # Brief sleep to prevent CPU spinning
                time.sleep(0.01)
                    
            except Exception as e:
                print(f"READ observation error: {e}")
                time.sleep(1.0)
    
    def _check_stdin(self) -> None:
        """Check stdin for new input (non-blocking)."""
        if select.select([sys.stdin], [], [], 0)[0]:
            try:
                line = sys.stdin.readline().strip()
                if line:  # Non-empty line
                    print(f"READ: Received input: {line}")
                    self._process_input(line, source="stdin")
            except (IOError, EOFError):
                pass  # Handle stdin issues gracefully
    
    def _check_simulation(self) -> None:
        """Simulate occasional observations for testing."""
        # Reduced frequency for testing
        if time.time() % 10 < 0.05:  # Every ~10 seconds
            test_inputs = [
                "the cat moved left",
                "hello world",
                "what is your name",
                "how are you today",
                "tell me something",
                "the dog barked loudly",
                "sun rises in the east",
                "water is wet",
                "time passes slowly",
                "learning is fun"
            ]
            
            import random
            if random.random() < 0.3:  # 30% chance
                raw_input = random.choice(test_inputs)
                self._process_input(raw_input, source="simulation")
    
    def _process_input(self, text: str, source: str = "unknown") -> None:
        """Process input text and create observation."""
        # Simple deduplication
        text_hash = hash(text)
        current_time = time.time()
        
        if (text_hash in self._recent_sent and 
            current_time - self._last_sent_time.get(text_hash, 0) < self._send_cooldown):
            return  # Skip duplicate
        
        # Create observation
        observation = self._create_observation(text, source)
        
        # Check queue capacity
        if observation_queue.full():
            print(f"READ: Queue full, dropping observation: {text[:50]}...")
            return
        
        # Send observation
        observation_queue.put(observation)
        self._recent_sent.add(text_hash)
        self._last_sent_time[text_hash] = current_time
        
        print(f"READ: Queued observation from {source}: {text[:50]}...")
        
        # Clean old entries periodically
        if len(self._recent_sent) > 1000:
            self._clean_old_entries()
    
    def _create_observation(self, text: str, source: str, mode: str = "autonomous") -> Dict[str, Any]:
        """Create a structured observation dictionary."""
        # Basic tokenization
        tokens = text.split()
        
        return {
            "timestamp": time.time(),
            "raw_input": text,
            "preliminary_tokens": tokens,
            "token_count": len(tokens),
            "metadata": {
                "source": source,
                "mode": mode,
                "prime": "READ",
                "tokenized_at": time.time()
            }
        }
    
    def _clean_old_entries(self) -> None:
        """Clean old entries from recent_sent to prevent memory growth."""
        current_time = time.time()
        max_age = 300.0  # Keep entries for 5 minutes
        
        to_remove = []
        for obs_hash, sent_time in self._last_sent_time.items():
            if current_time - sent_time > max_age:
                to_remove.append(obs_hash)
        
        for obs_hash in to_remove:
            self._recent_sent.discard(obs_hash)
            self._last_sent_time.pop(obs_hash, None)


# Singleton instance exported at module level
read = READ()