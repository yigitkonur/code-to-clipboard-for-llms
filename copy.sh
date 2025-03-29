#!/bin/bash

# Function to clean up the temporary file on exit
cleanup() {
  rm -f "$tmp_file"
  # echo "Debug: Temporary file $tmp_file cleaned up." >&2 # Uncomment for debugging
}

# --- Initialization ---
exclude_patterns=""
# Create a temporary file safely and store its name
tmp_file=$(mktemp) || { echo "Error: Failed to create temporary file." >&2; exit 1; }
# Ensure the temporary file is cleaned up when the script exits (normally or via signal)
trap cleanup EXIT INT TERM HUP

# --- Argument Parsing ---
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --exclude)
      exclude_patterns="$2"
      shift 2
      ;;
    *)
      echo "Unknown parameter passed: $1" >&2
      echo "Usage: $0 [--exclude pattern1,pattern2,...]" >&2
      exit 1
      ;;
  esac
done

# --- Prepare Exclusions ---
IFS=',' read -r -a exclude_array <<< "$exclude_patterns"
find_exclude_options=""
# Using the original, simpler exclusion list as requested
tree_exclude_patterns="node_modules|env|venv|ENV|.git|.svn|.hg|.bzr|build|dist|target|out|bin|obj|__pycache__|.cache|cache|.pytest_cache|logs|.idea|.vscode|.DS_Store|Thumbs.db|*~|#*#|.*.swp|.*.swo|.*.tmp|.*.temp"

for pattern in "${exclude_array[@]}"; do
  find_exclude_options+=" -not -name '$pattern'"
  tree_exclude_patterns+="|$pattern"
done

# --- Core Logic: Generate output and redirect to temp file ---
{ # Start command grouping to redirect collective output
  # 1. Display the Project Structure
  echo "# Project Structure"
  tree -I "$tree_exclude_patterns"

  echo
  echo "# Source Code"

  # 2. Find relevant files, filter, and format
  # NO MORE NESTING PROBLEM, so NO ESCAPING NEEDED inside loop
  eval "find . -type f \( \
      \( -not -path '*/.*' -not -path '*/node_modules/*' -not -path '*/env/*' -not -path '*/venv/*' -not -path '*/ENV/*' -not -path '*/build/*' -not -path '*/dist/*' -not -path '*/target/*' -not -path '*/out/*' -not -path '*/bin/*' -not -path '*/obj/*' -not -path '*/__pycache__/*' -not -path '*/.cache/*' -not -path '*/cache/*' -not -path '*/.pytest_cache/*' -not -path '*/logs/*' -not -path '*/.idea/*' -not -path '*/.vscode/*' $find_exclude_options \) \
      -o \
      \( -name '.env' -o -name '.env.example' -o -name '.gitignore' -o -name '.gitattributes' -o -name '.gitmodules' -o -name '.editorconfig' -o -name '.prettierrc' -o -name '.eslintrc' -o -name '.stylelintrc' -o -name '.pylintrc' -o -name '.flake8' -o -name '.bashrc' -o -name '.bash_profile' -o -name '.zshrc' -o -name '.profile' \) \
  \) \( -not -name '*.log' -not -name '*.tmp' -not -name '*.class' -not -name '*.o' -not -name '*.so' -not -name '*.dll' -not -name '*.exe' -not -name '*.pyc' -not -name '*.pyo' -not -name '*.whl' $find_exclude_options \) ! -size +100M" | \
  while read -r file; do
      # Check if the file is a text file using the `file` command
      if command -v file >/dev/null && file --mime-type "$file" 2>/dev/null | grep -q 'text/'; then
          # Extract directory and extension (NO escaping needed now)
          dir=$(dirname "$file")
          ext="${file##*.}"
          # Remove leading './' for cleaner display
          clean_dir=${dir#./}
          clean_file=${file#./}
          # Handle root directory
          if [ "$clean_dir" = "$clean_file" ] || [ "$clean_dir" = "." ]; then
              clean_dir="root"
          fi
          # Format extension, handle files with no extension
          if [ -n "$ext" ] && [ "$ext" != "$clean_file" ]; then
               formatted_ext=".$ext"
          else
               formatted_ext=".noextension"
          fi
          # Echo the result for awk
          echo "$clean_dir|$formatted_ext|./$clean_file"
      fi
  done | \
  # 3. Sort the output
  sort -t '|' -k1,1 -k2,2 | \
  # 4. Process the sorted list with awk
  awk -F'|' '
  BEGIN {
      current_dir = ""
      current_ext = ""
  }
  {
      dir = $1
      ext = $2
      file = $3
      # If directory changes, print directory header
      if (dir != current_dir) {
          current_dir = dir
          print ""
          printf "=============== %s folder ===============\\n", (dir == "root" ? "root" : dir)
          current_ext = ""  # Reset extension when directory changes
      }
      # If extension changes, print extension header
      if (ext != current_ext) {
          current_ext = ext
          printf "=============== %s files ===============\\n", ext
      }
      # Print file header and content
      printf "=============== %s ================\\n", file
      print "```"
      # Use system() with cat for robust filename handling
      # Ensure quotes inside the system command are escaped for awk
      cmd = "cat \"" file "\""
      while ( (cmd | getline line) > 0 ) {
          print line
      }
      close(cmd) # Close the pipe
      print "```"
      print "---"
  }
  '
# End command grouping and redirect stdout to the temporary file
} > "$tmp_file"

# Check if the pipeline wrote anything to the temp file (basic error check)
if [ ! -s "$tmp_file" ]; then
    echo "Warning: No output was generated. Check file permissions and patterns." >&2
    # Optionally keep the temp file for debugging in this case, or just exit
    # exit 1 # Or just continue to report 0 lines copied
fi

# --- Post-processing: Copy to clipboard and count lines ---

# Copy the content of the temp file to the clipboard
clipboard_cmd="stdout" # Default action
if command -v pbcopy >/dev/null 2>&1; then
    pbcopy < "$tmp_file"
    clipboard_cmd="pbcopy"
elif command -v xclip >/dev/null 2>&1; then
    xclip -selection clipboard < "$tmp_file"
    clipboard_cmd="xclip"
elif command -v xsel >/dev/null 2>&1; then
    xsel --clipboard --input < "$tmp_file"
    clipboard_cmd="xsel"
else
    echo "Clipboard command (pbcopy, xclip, xsel) not found. Outputting temp file content to stdout instead." >&2
    cat "$tmp_file" # Display content if no clipboard tool
fi

# Count the number of lines in the temp file
# Use < to prevent filename in output, awk to strip whitespace
lines=$(wc -l < "$tmp_file" | awk '{print $1}')

# Output feedback message to stderr to avoid polluting potential stdout usage
if [ "$clipboard_cmd" != "stdout" ]; then
    echo "Copied $lines lines to the clipboard via $clipboard_cmd." >&2
else
    echo "Outputted $lines lines to stdout." >&2
fi

# --- Final Structure Display ---
# Display the initial tree structure view again (to stderr)
echo # Add newline for spacing
echo "---" >&2
echo "Project Structure (Initial View, Excluding Patterns):" >&2
tree -I "$tree_exclude_patterns" >&2

# The trap will automatically remove $tmp_file on exit
exit 0
