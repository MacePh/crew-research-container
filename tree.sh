#!/bin/bash

# Default values
MAX_DEPTH=4
OUTPUT_FILE="project_structure.txt"
EXPORT_FOLDER="export"
IGNORE_DIRS=("venv" ".venv" ".git" "docs" "Informational" "data" "backups" ".vscode" "__pycache__" "export" ".ruff_cache")

# Function to check if an element is in an array
contains() {
    local element="$1"
    shift
    for item in "$@"; do
        if [[ "$item" == "$element" ]]; then
            return 0
        fi
    done
    return 1
}

# Function to get gitignored files
get_gitignored_files() {
    if git ls-files --others --ignored --exclude-standard > /dev/null 2>&1; then
        git ls-files --others --ignored --exclude-standard | while read -r line; do
            echo "$line"
        done
    else
        echo "Error: Ensure you are inside a Git repository." >&2
        return 1
    fi
}

# Function to generate the tree
generate_tree() {
    local dir="$1"
    local depth=0
    local prefix=""

    # Create export folder if it doesn't exist
    mkdir -p "$EXPORT_FOLDER"

    # Output file path
    local output_path="$EXPORT_FOLDER/$OUTPUT_FILE"

    # Clear the output file
    > "$output_path"

    # Get gitignored files into an array
    mapfile -t IGNORE_FILES < <(get_gitignored_files)

    # Recursive function to build the tree
    build_tree() {
        local current_dir="$1"
        local current_depth="$2"
        local current_prefix="$3"

        # Stop if max depth is exceeded
        if [[ "$current_depth" -gt "$MAX_DEPTH" ]]; then
            return
        fi

        # Get basename of the current directory
        local base=$(basename "$current_dir")

        # Write the current directory
        echo "${current_prefix}${base}/" >> "$output_path"

        # New prefix for children
        local new_prefix="${current_prefix}│   "

        # List directories and files
        local dirs=()
        local files=()
        while IFS= read -r -d '' entry; do
            entry_name=$(basename "$entry")
            if [[ -d "$entry" ]]; then
                if ! contains "$entry_name" "${IGNORE_DIRS[@]}"; then
                    dirs+=("$entry")
                fi
            elif [[ -f "$entry" ]]; then
                if ! [[ "$entry" =~ \.pyc$ ]] && ! contains "$entry" "${IGNORE_FILES[@]}"; then
                    files+=("$entry_name")
                fi
            fi
        done < <(find "$current_dir" -maxdepth 1 -not -path "$current_dir" -print0)

        # Write files
        for file in "${files[@]}"; do
            echo "${new_prefix}├── $file" >> "$output_path"
        done

        # Process subdirectories
        for i in "${!dirs[@]}"; do
            local d="${dirs[$i]}"
            local last_index=$((${#dirs[@]} - 1))
            if [[ "$i" -eq "$last_index" ]]; then
                local sub_prefix="${current_prefix}    "
            else
                local sub_prefix="${new_prefix}"
            fi
            build_tree "$d" "$((current_depth + 1))" "$sub_prefix"
        done
    }

    # Start building the tree from the current directory
    build_tree "$dir" "$depth" ""

    echo "Project structure saved to $output_path (excluding .gitignored files, __pycache__, .pyc files, and export folder)"
}

# Run the script with the current directory
generate_tree "."