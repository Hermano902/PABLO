from pathlib import Path
import sys
import json

def build_structure(root: Path, max_depth: int = 6, current_depth: int = 0):
    """
    Builds a nested dictionary representing the directory structure of `root`.

    - Special handling for a directory named 'dictionary': only include its immediate children.
    """
    node = {
        'name': root.name,
        'type': 'directory' if root.is_dir() else 'file'
    }
    if root.is_dir():
        node['children'] = []
        try:
            entries = sorted(root.iterdir(), key=lambda e: e.name.lower())
        except PermissionError:
            return node

        for entry in entries:
            if entry.is_dir():
                if entry.name.lower() == 'dictionary' or entry.name.lower() == 'dictionarybak':
                    # Only one level under 'dictionary'
                    child_nodes = []
                    for child in sorted(entry.iterdir(), key=lambda e: e.name.lower()):
                        child_nodes.append({'name': child.name, 'type': 'directory' if child.is_dir() else 'file'})
                    node['children'].append({'name': entry.name, 'type': 'directory', 'children': child_nodes})
                else:
                    if max_depth is None or current_depth < max_depth:
                        node['children'].append(build_structure(entry, max_depth, current_depth + 1))
            else:
                node['children'].append({'name': entry.name, 'type': 'file'})
    return node

if __name__ == '__main__':
    base = Path(__file__).resolve().parent
    tree = build_structure(base)
    with open('structure.json', 'w', encoding='utf-8') as f:
        json.dump(tree, f, indent=2, ensure_ascii=False)
    print("Saved structure to structure.json")
