"""
Interactive test for PABLO Phase 1C.
"""

import time
import threading
from core.queues import prime_registry, observation_queue


def interactive_loop():
    """Interactive command loop."""
    print("\n" + "="*60)
    print("PABLO Phase 1C - Interactive Test")
    print("="*60)
    print("Commands:")
    print("  input <text>    - Send text to PABLO")
    print("  stats          - Show system statistics")
    print("  list [n]       - List recent compounds")
    print("  find <prime>   - Find compounds with prime")
    print("  test <n>       - Send n test observations")
    print("  logic          - Send test observations with logic operators")
    print("  save           - Save storage state")
    print("  storage        - Show storage information")
    print("  quit           - Exit")
    print("\nLogic operator examples:")
    print('  "if condition then action"')
    print('  "something and something_else"')
    print('  "this or that"')
    print('  "not something"')
    print("="*60)
    
    while True:
        try:
            cmd = input("\nPABLO> ").strip()
            
            if not cmd:
                continue
            
            if cmd.lower() == "quit":
                print("Exiting interactive mode...")
                break
            
            elif cmd.lower().startswith("input "):
                text = cmd[6:].strip()
                if text:
                    # Send as direct input
                    print(f"Sending input: {text}")
                    
                    # Create and queue observation
                    import time
                    observation = {
                        "timestamp": time.time(),
                        "raw_input": text,
                        "preliminary_tokens": text.split(),
                        "metadata": {
                            "source": "interactive",
                            "mode": "interactive",
                            "prime": "READ"
                        }
                    }
                    observation_queue.put(observation)
                    print("Input queued for processing")
            
            elif cmd.lower() == "stats":
                # Get stats from KNOW
                know_prime = prime_registry.get_prime("KNOW")
                stats = know_prime({"query": "stats"})
                
                print("\nKNOW Statistics:")
                print(f"  Total compounds: {stats['store_stats']['total_compounds']}")
                print(f"  By type: {stats['store_stats']['by_type']}")
                print(f"  Compounds stored: {stats['operation_stats']['compounds_stored']}")
                print(f"  Compounds retrieved: {stats['operation_stats']['compounds_retrieved']}")
                
                # Get DATA stats
                data_prime = prime_registry.get_prime("DATA")
                data_stats = data_prime({"query": "stats"})
                print("\nDATA Statistics:")
                for key, value in data_stats.get('stats', {}).items():
                    print(f"  {key}: {value}")
            
            elif cmd.lower().startswith("list"):
                parts = cmd.split()
                limit = 10
                if len(parts) > 1:
                    try:
                        limit = int(parts[1])
                    except:
                        pass
                
                know_prime = prime_registry.get_prime("KNOW")
                compounds = know_prime({"query": "list", "limit": limit})
                
                print(f"\nRecent Compounds (showing {len(compounds)}):")
                for comp in compounds:
                    prime_str = ", ".join(comp['primes']) if comp['primes'] else "[no primes]"
                    print(f"  ID {comp['id']} ({comp['type']}): {prime_str}")
            
            elif cmd.lower().startswith("find "):
                prime_name = cmd[5:].strip().upper()
                
                know_prime = prime_registry.get_prime("KNOW")
                results = know_prime({
                    "query": "find",
                    "filter": {"has_prime": prime_name}
                })
                
                print(f"\nCompounds with prime '{prime_name}': {len(results)} found")
                for comp in results[:10]:  # Limit to 10
                    prime_str = ", ".join(comp['primes']) if comp['primes'] else "[no primes]"
                    print(f"  ID {comp['id']}: {prime_str}")
                if len(results) > 10:
                    print(f"  ... and {len(results) - 10} more")
            
            elif cmd.lower().startswith("test "):
                try:
                    n = int(cmd[5:].strip())
                    print(f"Sending {n} test observations...")
                    
                    test_texts = [
                        "the cat moved left",
                        "dog barked right",
                        "bird flew up",
                        "fish swam down",
                        "sun is bright light",
                        "moon is far",
                        "water is wet",
                        "fire is hot heat",
                        "think about this",
                        "know something new",
                        # Logic operator examples
                        "if the dog barks then the cat hides",
                        "the light is on and the door is open",
                        "either the sun is bright or it is night time",
                        "not the water is cold",
                        "if something moves then something changes",
                        "the cat is here and the dog is there",
                        "if the heat is high then the water boils and the fire grows"
                    ]
                    
                    for i in range(min(n, len(test_texts))):
                        observation = {
                            "timestamp": time.time(),
                            "raw_input": test_texts[i],
                            "preliminary_tokens": test_texts[i].split(),
                            "metadata": {
                                "source": "test",
                                "mode": "test",
                                "prime": "READ",
                                "test_id": i
                            }
                        }
                        observation_queue.put(observation)
                        time.sleep(0.1)  # Small delay
                    
                    print(f"Queued {min(n, len(test_texts))} test observations")
                    
                except ValueError:
                    print("Usage: test <number>")
            
            elif cmd.lower() == "logic":
                print("Sending logic operator test observations...")
                
                logic_tests = [
                    "if the light is on then the room is bright",
                    "if something moves and something changes then something happened",
                    "the cat is here and the dog is there",
                    "the door is open or the door is closed",
                    "not the water is cold",
                    "if the fire is hot then the heat rises and things change",
                    "something is true or something is false",
                    "if condition then action and consequence",
                ]
                
                for i, text in enumerate(logic_tests):
                    observation = {
                        "timestamp": time.time(),
                        "raw_input": text,
                        "preliminary_tokens": text.split(),
                        "metadata": {
                            "source": "logic_test",
                            "mode": "logic",
                            "test_id": i
                        }
                    }
                    observation_queue.put(observation)
                    time.sleep(0.15)  # Slightly longer delay for logic tests
                
                print(f"Queued {len(logic_tests)} logic operator observations")
            
            elif cmd.lower() == "save":
                know_prime = prime_registry.get_prime("KNOW")
                result = know_prime({"query": "save"})
                print(f"Save result: {result}")
            
            elif cmd.lower() == "storage":
                know_prime = prime_registry.get_prime("KNOW")
                result = know_prime({"query": "storage_info"})
                print("\nStorage Information:")
                for key, value in result.items():
                    print(f"  {key}: {value}")
            
            else:
                print(f"Unknown command: {cmd}")
                print("Available: input, stats, list, find, test, save, storage, quit")
        
        except KeyboardInterrupt:
            print("\nInterrupted. Use 'quit' to exit.")
        except Exception as e:
            print(f"Error: {e}")


def monitor_queue():
    """Background thread to monitor queue size."""
    while True:
        time.sleep(5)
        size = observation_queue.qsize()
        if size > 0:
            print(f"[Monitor] Queue size: {size}")
        if size > 50:
            print(f"[Monitor] Warning: Queue growing ({size} items)")


if __name__ == "__main__":
    # Initialize primes
    from main import initialize_primes
    initialize_primes()
    
    # Start queue monitor in background
    monitor_thread = threading.Thread(target=monitor_queue, daemon=True)
    monitor_thread.start()
    
    # Run interactive loop
    interactive_loop()