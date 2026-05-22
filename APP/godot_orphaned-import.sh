#!/bin/bash

# report orphaned .import files; make sure to assign PROJECT_DIR
PROJECT_DIR=$1
while IFS= read -r import_file; do
    filename="$PROJECT_DIR/.godot/imported/${import_file%.import}"
    if [ ! -f "$filename" ]; then
        echo "Found orphaned import file: $import_file"
    fi
done < <(find "$PROJECT_DIR" -type f -name "*.import")