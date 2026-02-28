"""
HEAR Prime - Auditory perception scaffold.
"""

import time
import threading
import random
from typing import Dict, Any
from core.prime_base import Prime
from core.queues import observation_queue
from core.compound import Compound
from core.primebit import PrimeBit


class HEAR(Prime):
    """HEAR prime for auditory perception."""
    
    def __init__(self):
        super().__init__("HEAR")
        self._thread = None
        self._running = False
        self._last_observation_time = 0
        
    def initialize(self) -> None:
        super().initialize()
        self._running = True
        self._thread = threading.Thread(target=self._observation_loop, daemon=True)
        self._thread.start()
    
    def shutdown(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        super().shutdown()
    
    def __call__(self, context: Dict[str, Any]) -> Any:
        """HEAR prime interface."""
        primebit = PrimeBit.from_prime_names({"HEAR"})
        return Compound(
            id=-1,
            text="listen",
            primebit=primebit,
            compound_type="data",
            provenance_data={"mode": "consultation"}
        )
    
    def _observation_loop(self) -> None:
        """Auditory observation loop."""
        audio_observations = [
            "dog barking sound",
            "bell ringing",
            "music playing",
            "footsteps heard",
            "voice detected",
        ]
        
        while self._running:
            try:
                current_time = time.time()
                
                # Generate observation every 3 seconds
                if current_time - self._last_observation_time >= 3.0:
                    if not observation_queue.full():
                        observation_text = random.choice(audio_observations)
                        observation = {
                            "timestamp": current_time,
                            "raw_input": observation_text,
                            "preliminary_tokens": observation_text.split(),
                            "metadata": {
                                "source": "audio_simulation",
                                "mode": "autonomous",
                                "prime": "HEAR"
                            }
                        }
                        
                        observation_queue.put(observation)
                        print(f"[HEAR] Generated observation: {observation_text}")
                        self._last_observation_time = current_time
                    
                time.sleep(0.2)
                    
            except Exception as e:
                print(f"HEAR observation error: {e}")
                time.sleep(1.0)


# Singleton instance
hear = HEAR()
