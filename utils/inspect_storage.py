"""
Utility to inspect PABLO's disk storage.
"""

import json
import os
from core.persistence import persistence


def print_storage_info():
    """Print information about storage."""
    print("\n" + "="*60)
    print("PABLO Storage Inspector")
    print("="*60)
    
    info = persistence.get_storage_info()
    
    print("\nStorage Configuration:")
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    # Check data file
    if info["data_file_exists"]:
        try:
            with open(info["data_file"], 'r') as f:
                data = json.load(f)
            
            print(f"\nCompounds in storage: {len(data)}")
            
            # Show a few samples
            print("\nSample compounds (first 5):")
            for i, (compound_id, compound_data) in enumerate(list(data.items())[:5]):
                primes = compound_data.get("primes", [])
                prime_names = []
                for idx in primes:
                    # Import here to avoid circular imports
                    from core.constants import INDEX_TO_PRIME
                    if idx in INDEX_TO_PRIME:
                        prime_names.append(INDEX_TO_PRIME[idx])
                
                print(f"  ID {compound_id}: {prime_names if prime_names else '[no primes]'}")
                print(f"    Type: {compound_data.get('type', 'unknown')}")
                print(f"    Usage: {compound_data.get('metadata', {}).get('usage_count', 0)}")
                print(f"    Created: {compound_data.get('metadata', {}).get('created_at', 'unknown')}")
                print()
            
            # Count by type
            type_counts = {}
            for compound_id, compound_data in data.items():
                compound_type = compound_data.get("type", "unknown")
                type_counts[compound_type] = type_counts.get(compound_type, 0) + 1
            
            print("\nCompound Types:")
            for compound_type, count in type_counts.items():
                print(f"  {compound_type}: {count}")
            
        except Exception as e:
            print(f"Error reading data file: {e}")
    
    # Check metadata file
    if info["metadata_file_exists"]:
        try:
            with open(info["metadata_file"], 'r') as f:
                metadata = json.load(f)
            
            print(f"\nStorage Metadata:")
            for key, value in metadata.items():
                print(f"  {key}: {value}")
        except Exception as e:
            print(f"Error reading metadata file: {e}")
    
    # Check state file
    state_file = os.path.join(persistence.storage_dir, "state.json")
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            print(f"\nSystem State:")
            print(f"  Next ID: {state.get('next_id', 'unknown')}")
            print(f"  Last saved: {state.get('saved_at_human', 'unknown')}")
            
            stats = state.get('stats', {})
            if stats:
                print(f"\nStatistics:")
                for key, value in stats.items():
                    print(f"  {key}: {value}")
        except Exception as e:
            print(f"Error reading state file: {e}")
    
    print("\n" + "="*60)
    print("Inspection complete")
    print("="*60)


def export_compounds(output_file: str = "compounds_export.json"):
    """Export all compounds to a separate file."""
    if not persistence.get_storage_info()["data_file_exists"]:
        print("No data file to export")
        return
    
    try:
        with open(persistence.data_file, 'r') as f:
            data = json.load(f)
        
        # Create a more readable export
        export_data = []
        for compound_id, compound_data in data.items():
            # Extract key information
            primes = compound_data.get("primes", [])
            prime_names = []
            for idx in primes:
                from core.constants import INDEX_TO_PRIME
                if idx in INDEX_TO_PRIME:
                    prime_names.append(INDEX_TO_PRIME[idx])
            
            export_entry = {
                "id": int(compound_id),
                "compound_type": compound_data.get("compound_type", "unknown"),
                "text": compound_data.get("text", ""),
                "primes": prime_names,
                "prime_indices": primes,
                "relations": compound_data.get("relations", []),
                "provenance": compound_data.get("provenance", {}),
                "refinement": compound_data.get("refinement", {})
            }
            export_data.append(export_entry)
        
        # Sort by ID
        export_data.sort(key=lambda x: x["id"])
        
        # Write export
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"Exported {len(export_data)} compounds to {output_file}")
        
    except Exception as e:
        print(f"Error exporting compounds: {e}")


def clear_storage(confirm: bool = False):
    """Clear storage (use with caution!)."""
    if not confirm:
        print("\nWARNING: This will delete all stored compounds!")
        response = input("Type 'YES' to confirm: ")
        if response != 'YES':
            print("Aborted")
            return
    
    try:
        # Delete all storage files
        files_to_delete = [
            persistence.data_file,
            persistence.metadata_file,
            os.path.join(persistence.storage_dir, "state.json")
        ]
        
        deleted_count = 0
        for file_path in files_to_delete:
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted_count += 1
                print(f"Deleted: {file_path}")
        
        print(f"\nCleared {deleted_count} storage files")
        
    except Exception as e:
        print(f"Error clearing storage: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="PABLO Storage Inspector")
    parser.add_argument("--info", action="store_true", help="Show storage information")
    parser.add_argument("--export", action="store_true", help="Export compounds to file")
    parser.add_argument("--export-file", default="compounds_export.json", help="Export file name")
    parser.add_argument("--clear", action="store_true", help="Clear storage (requires confirmation)")
    
    args = parser.parse_args()
    
    if args.info:
        print_storage_info()
    elif args.export:
        export_compounds(args.export_file)
    elif args.clear:
        clear_storage()
    else:
        # Default: show info
        print_storage_info()