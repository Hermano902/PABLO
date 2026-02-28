"""
PABLO Main Entry Point - Phase 1C Implementation with Persistence.
"""

import time
import sys
from core.queues import prime_registry, observation_queue
from core.persistence import persistence


def initialize_primes():
    """Initialize all prime instances."""
    print("="*60)
    print("PABLO Phase 1C - Prime Scaffolds with Persistence")
    print("="*60)
    
    # Show storage info
    storage_info = persistence.get_storage_info()
    if storage_info["data_file_exists"]:
        print(f"Found existing storage: {storage_info['data_file']}")
        if 'data_file_size' in storage_info:
            print(f"Storage size: {storage_info['data_file_size']} bytes")
    
    print("\nInitializing primes...")
    
    # List of core primes to initialize
    core_primes = ["READ", "SEE", "HEAR", "DATA", "KNOW", "THINK"]
    
    for prime_name in core_primes:
        try:
            prime = prime_registry.get_prime(prime_name)
            prime.initialize()
            print(f"  [OK] {prime_name:10} - initialized")
            time.sleep(0.1)  # Small delay for orderly startup
        except Exception as e:
            print(f"  [!!] {prime_name:10} - failed: {e}")
    
    print("\n" + "="*60)
    print("PABLO is now running!")
    print("\nSystem Status:")
    print("  * READ   - Monitoring stdin and simulation")
    print("  * DATA   - Structuring observations")
    print("  * KNOW   - Storing compounds with disk persistence")
    print("  * THINK  - Available for consultation")
    print("\nLogic Operators Recognized:")
    print("  * IF, AND, OR, NOT, XOR, NAND, NOR, XNOR")
    print("  * TRUE, FALSE (constants)")
    print("\nStorage: Compounds auto-save every 30 seconds")
    print("         Stored in: ./storage/compounds.json")
    print("\nExample observations with logic operators:")
    print('  "if the dog barks then alert"')
    print('  "the light is on and the door is open"')
    print('  "either sun is bright or it is night"')
    print('  "not the water is cold"')
    print("\nTo interact:")
    print("  1. Type directly (PABLO reads stdin)")
    print("  2. Run: python test_interactive.py")
    print("  3. Run: python inspect_storage.py --info")
    print("  4. Press Ctrl+C to shutdown")
    print("="*60 + "\n")
    
    # Queue initial test observations with logic operators
    print("Sending initial observations with logic operators...")
    initial_tests = [
        "if the dog barks then alert",
        "the cat is here and the dog is here",
        "either night or day time",
        "not the water is cold"
    ]
    
    for text in initial_tests:
        observation = {
            "timestamp": time.time(),
            "raw_input": text,
            "preliminary_tokens": text.split(),
            "metadata": {
                "source": "bootstrap",
                "mode": "initialization"
            }
        }
        observation_queue.put(observation)
        time.sleep(0.2)
    
    print(f"Queued {len(initial_tests)} bootstrap observations\n")


def shutdown_primes():
    """Shutdown all prime instances."""
    print("\n" + "="*60)
    print("Shutting down PABLO...")
    
    # We need to get all primes that were loaded
    primes_to_shutdown = ["READ", "SEE", "HEAR", "DATA", "KNOW", "THINK"]
    
    for prime_name in primes_to_shutdown:
        try:
            prime = prime_registry.get_prime(prime_name)
            prime.shutdown()
            print(f"  ✓ {prime_name:10} - shutdown complete")
        except Exception as e:
            print(f"  ✗ {prime_name:10} - shutdown failed: {e}")
    
    # Final storage info
    storage_info = persistence.get_storage_info()
    if storage_info["data_file_exists"] and 'data_file_size' in storage_info:
        print(f"\nFinal storage size: {storage_info['data_file_size']} bytes")
    
    print("="*60)
    print("PABLO shutdown complete.")
    print("="*60)


def main():
    """Main execution loop."""
    try:
        initialize_primes()
        
        # Keep main thread alive
        print("Main thread running. Press Ctrl+C to shutdown.")
        while True:
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        print("\nReceived shutdown signal...")
    finally:
        shutdown_primes()


if __name__ == "__main__":
    main()