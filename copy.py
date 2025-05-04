#!/usr/bin/env python3

import argparse
import fnmatch
import os
import sys
from pathlib import Path
import subprocess # For git ls-files
import time
import logging
# No need for defaultdict with current structure
from typing import Set, List, Tuple, Optional, Dict, Any, Callable

# --- Optional Imports ---
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

try:
    # Make gitignore_parser optional at runtime check
    import gitignore_parser
    GITIGNORE_PARSER_AVAILABLE = True
except ImportError:
    GITIGNORE_PARSER_AVAILABLE = False
    gitignore_parser = None # Define it as None if not available

# --- Constants ---

# Using tuples for immutability and slight performance gain on iteration
DEFAULT_EXCLUDED_DIRS = (
    ".git", ".svn", ".hg", ".bzr", "node_modules", "vendor", ".tap",
    "venv", "env", ".venv", "ENV", "virtualenv",
    "build", "dist", "target", "out", "bin", "obj",
    "__pycache__", ".cache", "cache",
    ".pytest_cache", ".mypy_cache", ".tox",
    ".idea", ".vscode", "logs", "log", "coverage", "htmlcov",
    ".terraform", ".next", ".nuxt", "public", "static",
    "tests", "__tests__", "test", "docs", "documentation"
)

# Combine default + common CLI patterns here for simplicity later
DEFAULT_EXCLUDED_PATTERNS = (
    # Compiled/object files
    "*.pyc", "*.pyo", "*.pyd", "*.so", "*.o", "*.a", "*.lib", "*.dylib", "*.bundle",
    "*.dll", "*.exe", "*.class", "*.jar", "*.war", "*.ear", ".tap",
    # Logs and build info
    "*.log", "*.tsbuildinfo",
    # Editor backups/swaps
    "*.swp", "*.swo", "*~", "#*#", ".DS_Store", "Thumbs.db",
    # Patches and diffs
    "*.patch", "*.diff",
    # Lock files
    "*.lock", "pnpm-lock.yaml", "yarn.lock", "package-lock.json", "poetry.lock", "composer.lock", "Gemfile.lock",
    # Terraform state
    "*.tfstate", "*.tfstate.backup",
    # Backups and temps
    "*.bak", "*.tmp", "*.temp",
    # Minified files and source maps
    "*.min.*", "*.map",
    # Common config files often not needed for core logic understanding
    ".editorconfig", ".gitattributes", ".gitmodules",
    ".env*", # Exclude all .env except .env.example
    "tsconfig.json", "tsconfig.*.json",
    # Common data/doc formats to exclude by default
    "*.spec.*", "*.test.*", # Test files
    "*.csv", "*.tsv", "*.xml", "*.yaml", "*.yml", # Data
    "*.htm", "*.html", "*.css", ".sql" # Web/DB assets
    "*.md", "*.markdown", ".rst", # Docs (except specific files)
    "*.json", "*.jsonc", ".yaml", ".yml", ".xml", ".html", ".htm", ".css", ".sql", ".csv", ".tsv", ".md", ".markdown", ".rst",
    "package.json", "**/package.json",
)

# Files to check even if their extension/pattern is in DEFAULT_EXCLUDED_PATTERNS
FILES_TO_ALWAYS_CHECK = {
    "README.md", ".env.example", "docker-compose.yml", "docker-compose.yaml",
    "Dockerfile", "requirements.txt", "pyproject.toml", "go.mod", "go.sum", "Cargo.toml"
}

# Always skip .gitignore itself from output
SKIP_ALWAYS = {".gitignore", "pnpm-lock.yaml", "package.json", "tsconfig.json", ".eslintrc.js", ".prettierrc.js", ".env",".tap","bun.lock", "LICENSE", "eslint.config.js", ".prettierrc",".prettierignore","package-lock.json"}

LANGUAGE_HINTS = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".jsx": "jsx", ".tsx": "tsx",
    ".java": "java", ".kt": "kotlin", ".cs": "csharp", ".go": "go", ".rs": "rust",
    ".c": "c", ".cpp": "cpp", ".h": "c", ".hpp": "cpp",
    ".rb": "ruby", ".php": "php", ".swift": "swift", ".scala": "scala",
    ".html": "html", ".htm": "html", ".css": "css", ".scss": "scss", ".sass": "sass",
    ".json": "json", ".jsonc": "jsonc", ".yaml": "yaml", ".yml": "yaml", ".xml": "xml",
    ".sh": "bash", ".bash": "bash", ".zsh": "zsh", ".fish": "fish",
    ".sql": "sql", ".md": "markdown", ".markdown": "markdown", ".rst": "rst",
    ".dockerfile": "dockerfile", "Dockerfile": "dockerfile",
    ".toml": "toml", ".ini": "ini", ".cfg": "ini", ".conf": "ini",
    ".env": "env", ".env.example": "env",
    ".tf": "terraform", ".tfvars": "terraform"
}

# --- Tree Glyphs ---
GLYPH_CHILD = "├──"
GLYPH_LAST = "└──"
GLYPH_INDENT_CHILD = "│"
GLYPH_INDENT_LAST = " "

# --- Helper Functions ---

def get_language_hint(filename: str) -> str:
    """Get the Markdown language hint based on file extension."""
    name = Path(filename).name # Use name for Dockerfile check
    suffix = Path(filename).suffix.lower()
    if name == "Dockerfile":
        return LANGUAGE_HINTS.get(name, "")
    return LANGUAGE_HINTS.get(suffix, "")

def parse_size(size_str: str) -> Optional[int]:
    """Converts size string like '1M', '500k' to bytes. Returns None if invalid or '0'."""
    size_str = size_str.lower().strip()
    if not size_str or size_str == '0': return None
    try:
        if size_str.endswith('g'):
            val = int(size_str[:-1]) * 1024**3
        elif size_str.endswith('m'):
            val = int(size_str[:-1]) * 1024**2
        elif size_str.endswith('k'):
            val = int(size_str[:-1]) * 1024
        elif size_str.isdigit():
            val = int(size_str)
        else:
            raise ValueError(f"Invalid size format: {size_str}")
        return val if val > 0 else None # Treat explicit 0 bytes as no limit
    except (ValueError, TypeError) as e:
        print(f"Warning: Invalid size '{size_str}': {e}. Disabling size limit.", file=sys.stderr)
        return None

def is_likely_binary_file(path: Path) -> bool:
    """Fast check if a file is likely binary by looking for null bytes."""
    if not path.is_file(): return False
    try:
        with open(path, 'rb') as f:
            return b'\x00' in f.read(1024)
    except Exception as e:
        print(f"Warning: Cannot read {path.name} to check for binary content: {e}", file=sys.stderr)
        return True # Assume binary if unreadable

def get_git_tracked_files(root_dir: Path) -> Optional[Set[str]]:
    """Gets git tracked files relative to root. None if not repo or error."""
    try:
        check_proc = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(root_dir), capture_output=True, text=True, check=False, encoding='utf-8'
        )
        if check_proc.returncode != 0 or check_proc.stdout.strip() != "true":
            return None

        result = subprocess.run(
            ["git", "ls-files"],
            cwd=str(root_dir), capture_output=True, text=True, check=True, encoding='utf-8'
        )
        return {line.strip().replace('\\', '/') for line in result.stdout.splitlines() if line.strip()}
    except FileNotFoundError:
        return None
    except subprocess.CalledProcessError as e:
        print(f"Warning: 'git ls-files' failed: {e.stderr.strip()}. Proceeding without git filtering.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Warning: Could not run git ls-files: {e}. Proceeding without git filtering.", file=sys.stderr)
        return None

# --- Core Logic Classes ---

class Config:
    """Holds combined configuration from defaults and argparse."""
    def __init__(self, args: argparse.Namespace):
        self.root_dir: Path = args.root_dir.resolve()
        self.no_gitignore: bool = args.no_gitignore
        self.gitignore_only: bool = args.gitignore_only # New flag
        self.include_binary: bool = args.include_binary
        self.max_size: Optional[int] = parse_size(args.max_size)

        # --- Combine Include/Exclude Rules --- 
        # Start with defaults, then modify with args
        self.excluded_dirs: Set[str] = set(DEFAULT_EXCLUDED_DIRS)
        self.excluded_patterns: Set[str] = set(args.exclude or [])
        self.included_patterns: Set[str] = set(args.include or [])

        # Handle extension args, ensuring leading dot
        excluded_ext = {f"*{ext if ext.startswith('.') else '.' + ext}" for ext in args.exclude_extension or []}
        included_ext = {f"*{ext if ext.startswith('.') else '.' + ext}" for ext in args.include_extension or []}
        self.excluded_patterns.update(excluded_ext)
        self.included_patterns.update(included_ext)

        # --- Default Pattern Overrides --- 
        self.override_defaults: Dict[str, bool] = {
            # Added missing .json override
            ".json": args.include_json,
            ".jsonc": args.include_json, # Map jsonc to json flag
            ".yaml": args.include_yaml,
            ".yml": args.include_yaml, # Map yml to yaml flag
            ".xml": args.include_xml,
            ".html": args.include_html,
            ".htm": args.include_html, # Map htm to html flag
            ".css": args.include_css,
            ".sql": args.include_sql,
            ".csv": args.include_csv,
            ".tsv": args.include_csv, # Map tsv to csv flag
            ".md": args.include_markdown,
            ".markdown": args.include_markdown,
            ".rst": args.include_markdown
        }

        # --- Validation --- 
        if self.no_gitignore and self.gitignore_only:
            raise ValueError("--no-gitignore and --gitignore-only are mutually exclusive.")

    def should_override_default_exclude(self, suffix: str) -> bool:
        """Check if a default exclusion pattern matching this suffix is overridden by a flag."""
        # Check if the specific suffix override is True
        if suffix in self.override_defaults and self.override_defaults[suffix]:
            return True
        return False

class FileFilter:
    """Determines if a file should be included based on Config."""
    def __init__(self, config: Config):
        self.config = config
        self.gitignore_matcher: Optional[Callable[[Path], bool]] = None
        self.git_tracked_files: Optional[Set[str]] = None # Relative paths

        # --- Determine Git handling mode ---
        # Mode 1: Full Git (Default) - Use tracking and .gitignore
        # Mode 2: Gitignore Only (--gitignore-only) - Use .gitignore, ignore tracking
        # Mode 3: No Git (--no-gitignore) - Ignore both

        use_gitignore_parsing = not config.no_gitignore # Modes 1 & 2
        use_git_tracking = not config.no_gitignore and not config.gitignore_only # Mode 1 only

        gitignore_path = config.root_dir / ".gitignore"

        # Attempt to load .gitignore if needed (Modes 1 & 2)
        if use_gitignore_parsing and gitignore_path.is_file():
            if GITIGNORE_PARSER_AVAILABLE:
                try:
                    # Correctly call parse_gitignore with the file path
                    self.gitignore_matcher = gitignore_parser.parse_gitignore(gitignore_path)
                except Exception as e:
                    print(f"Warning: Could not parse .gitignore: {e}", file=sys.stderr)
                    self.gitignore_matcher = lambda _: False # Treat as no match on error
            else:
                print("Warning: 'gitignore-parser' not installed. Cannot process .gitignore.", file=sys.stderr)
                self.gitignore_matcher = lambda _: False # Treat as no match if unavailable
        else:
            self.gitignore_matcher = lambda _: False # No .gitignore file or not needed

        # --- Get Git Tracked Files if needed (Mode 1) ---
        if use_git_tracking:
            self.git_tracked_files = get_git_tracked_files(config.root_dir)


    def should_include(self, abs_path: Path) -> Tuple[bool, str]:
        """Checks if a file should be included. Returns (include_bool, reason_string)."""
        filename = abs_path.name
        try:
            # Handle potential ValueError if path isn't relative (shouldn't happen with rglob)
            rel_path_str = str(abs_path.relative_to(self.config.root_dir))
        except ValueError:
             return False, f"Excluded: Path '{abs_path}' not relative to root '{self.config.root_dir}'"
        rel_path_posix = rel_path_str.replace(os.sep, '/')

        # --- Determine Git Mode for this check ---
        # Use pre-calculated git_tracked_files if available (Mode 1)
        use_full_git = not self.config.no_gitignore and not self.config.gitignore_only and self.git_tracked_files is not None
        use_gitignore_parsing = not self.config.no_gitignore and self.gitignore_matcher is not None

        # --- Filtering Steps (with priority) ---

        # 0. Explicit CLI Includes (Highest Override, except for size/binary)
        for pattern in self.config.included_patterns:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(rel_path_posix, pattern):
                if self.config.max_size is not None and abs_path.stat().st_size > self.config.max_size:
                     return False, f"Excluded: CLI included file '{filename}' exceeded max size"
                if not self.config.include_binary and is_likely_binary_file(abs_path):
                     return False, f"Excluded: CLI included file '{filename}' is binary"
                # Note: CLI Include does NOT override excluded dirs or always_skip
                in_excluded_dir = any(part in self.config.excluded_dirs for part in abs_path.relative_to(self.config.root_dir).parts[:-1])
                if in_excluded_dir:
                    return False, f"Excluded: CLI included file '{filename}' is within an excluded directory"
                if filename in SKIP_ALWAYS:
                    return False, f"Excluded: CLI included file '{filename}' is in SKIP_ALWAYS"

                return True, f"Included: Matched CLI include pattern for '{filename}'"

        # 1. Always Skip Files
        if filename in SKIP_ALWAYS:
             return False, f"Excluded: Explicitly always skipped ('{filename}')"

        # 2. Excluded Directories (Applies to all items within)
        rel_parts = abs_path.relative_to(self.config.root_dir).parts
        # Check parent parts for directory exclusion
        if any(part in self.config.excluded_dirs for part in rel_parts[:-1]):
             return False, f"Excluded: Part of excluded directory tree ('{rel_path_posix}')"

        # 3. Explicit CLI Exclude Patterns
        for pattern in self.config.excluded_patterns:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(rel_path_posix, pattern):
                return False, f"Excluded: Matched CLI exclude pattern for '{filename}'"

        # 4. Git Ignore Check (Modes 1 & 2)
        if use_gitignore_parsing:
            if self.gitignore_matcher(abs_path): # type: ignore
                 # Check if this file is *specifically* included by CLI despite gitignore
                 is_cli_included = False
                 for pattern in self.config.included_patterns:
                     if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(rel_path_posix, pattern):
                         is_cli_included = True
                         break
                 if not is_cli_included:
                     return False, f"Excluded: Matched .gitignore pattern for '{rel_path_posix}'"
                 # If CLI included, fall through to check other conditions like binary/size

        # 5. Git Tracking Check (Mode 1 Only)
        if use_full_git:
            is_tracked = rel_path_posix in self.git_tracked_files # type: ignore
            if not is_tracked:
                 # Allow if explicitly included by CLI or always_check
                 is_cli_included = any(fnmatch.fnmatch(filename, p) or fnmatch.fnmatch(rel_path_posix, p) for p in self.config.included_patterns)
                 is_always_check = filename in FILES_TO_ALWAYS_CHECK
                 if not is_cli_included and not is_always_check:
                     return False, f"Excluded: Not tracked by git ('{rel_path_posix}')"
                 # If CLI included or always_check, fall through

        # --- Checks for files that passed initial filters or were forced through ---

        # 6. Size Limit
        if self.config.max_size is not None and abs_path.stat().st_size > self.config.max_size:
             return False, f"Excluded: Exceeded max size ({abs_path.stat().st_size} > {self.config.max_size}) for '{filename}'"

        # 7. Binary Files
        if not self.config.include_binary and is_likely_binary_file(abs_path):
             return False, f"Excluded: Likely binary file ('{filename}')"

        # 8. Default Pattern Exclusions (Applies unless overridden)
        suffix = abs_path.suffix.lower()
        is_default_excluded = False
        if suffix:
            # Check against the original DEFAULT_EXCLUDED_PATTERNS list
            for pattern in DEFAULT_EXCLUDED_PATTERNS:
                if fnmatch.fnmatch(filename, pattern):
                    is_default_excluded = True
                    break
        # Check if the override flag for this suffix is set to True in Config
        if is_default_excluded and not self.config.should_override_default_exclude(suffix):
            # Only exclude if it matches a default pattern AND is NOT overridden
            # Allow if explicitly included by CLI or always_check
            is_cli_included = any(fnmatch.fnmatch(filename, p) or fnmatch.fnmatch(rel_path_posix, p) for p in self.config.included_patterns)
            is_always_check = filename in FILES_TO_ALWAYS_CHECK
            if not is_cli_included and not is_always_check:
                return False, f"Excluded: Matched default pattern ('{suffix}') for '{filename}'"

        # 9. Always Check Files (Final check if it wasn't excluded earlier)
        if filename in FILES_TO_ALWAYS_CHECK:
            # It passed size/binary checks if we got here
            return True, f"Included: Explicitly always checked ('{filename}')"

        # --- Default Behaviour (Include if not excluded by any rule above) ---
        return True, f"Included: Default (passed all filters for '{filename}')"


class ProjectScanner:
    """Scans the project, filters files, reads content, and gathers stats."""
    def __init__(self, config: Config, file_filter: FileFilter):
        self.config = config
        self.filter = file_filter
        self.included_files_data: List[Dict[str, Any]] = []
        self.excluded_files_count = 0 # Count only excluded files
        self.total_lines = 0
        self.total_chars = 0
        self.scanned_item_count = 0 # Renamed for clarity

    def scan(self):
        """Performs the directory scan and filtering."""
        start_time = time.time()
        included_paths_temp = []
        scanned_count_local = 0 # Use local counter during iteration

        for item in self.config.root_dir.rglob("*"):
            scanned_count_local += 1
            if item.is_symlink(): # Skip symlinks early
                continue

            # Check if item is within an explicitly excluded directory (optimization)
            try:
                 rel_parts = item.relative_to(self.config.root_dir).parts
                 if any(part in self.config.excluded_dirs for part in rel_parts[:-1]):
                     continue # Skip processing items inside excluded dirs
            except ValueError:
                 continue # Skip if path isn't relative (should not happen with rglob)

            if item.is_file():
                 is_included, reason = self.filter.should_include(item)
                 # logging.debug(f"File: {item.relative_to(self.config.root_dir)} -> Included: {is_included}, Reason: {reason}") # Optional debug log
                 if is_included:
                     included_paths_temp.append(item)
                 else:
                     self.excluded_files_count += 1
            # We don't explicitly handle directories here anymore, tree builder does

        self.scanned_item_count = scanned_count_local # Update class member at the end

        # Sort included files (consider a more sophisticated sort later if needed)
        included_paths_temp.sort(key=lambda p: str(p.relative_to(self.config.root_dir)))

        # Read content and calculate stats for included files
        read_start_time = time.time()
        temp_file_data = [] # Temporary list before adding percentage
        for path in included_paths_temp:
            try:
                # Double check it's a file, though it should be from the filtering logic
                if path.is_file():
                    content = path.read_text(encoding='utf-8', errors='ignore')
                    lines = content.count('\n') + 1 if content else 0
                    chars = len(content)
                    self.total_lines += lines
                    self.total_chars += chars
                    temp_file_data.append({ # Add to temporary list first
                        "absolute_path": path,
                        "relative_path": path.relative_to(self.config.root_dir),
                        "lines": lines,
                        "chars": chars,
                        "content": content,
                        "language_hint": get_language_hint(path.name), # Add hint here
                        "included": True # Mark as included based on filter decision
                    })
            except Exception as e:
                print(f"Warning: Could not read file {path.name}: {e}. Skipping content.", file=sys.stderr)
                # Add placeholder data if read fails but file was intended to be included
                temp_file_data.append({
                     "absolute_path": path,
                     "relative_path": path.relative_to(self.config.root_dir),
                     'lines': 0,
                     'chars': 0,
                     'content': f"# Error reading file: {e}",
                     'language_hint': 'plaintext',
                     "included": True # Still mark as included intent
                })

        # Now calculate percentages and populate final list
        for file_data in temp_file_data:
            percentage = (file_data['chars'] / self.total_chars * 100) if self.total_chars > 0 else 0
            file_data['percentage'] = percentage
            self.included_files_data.append(file_data) # Add to the final list

        read_time = time.time() - read_start_time
        filter_time = read_start_time - start_time

        logging.info(f"Scan complete. Scanned: {self.scanned_item_count}, Included: {len(self.included_files_data)}, Excluded Files: {self.excluded_files_count}")
        logging.info(f"Timing: Filtering: {filter_time:.3f}s, Reading: {read_time:.3f}s")

    def get_data(self) -> Dict[str, Any]:
        """Returns the collected scan data."""
        return {
            "config": self.config, # Pass config through
            "root_dir_abs": self.config.root_dir,
            "included_files": self.included_files_data, # Files that passed filter and were read
            "total_included_files": len(self.included_files_data),
            "total_included_lines": self.total_lines,
            "total_included_chars": self.total_chars,
            "scanned_count": self.scanned_item_count,
        }


class TreeBuilder:
    """Builds the tree structure and optionally formats it."""
    def __init__(self, root_dir: Path, config: Config, included_files_data: List[Dict]):
        self.root_dir = root_dir
        self.config = config
        # Use the detailed file data which includes stats and relative path
        self.included_files_map: Dict[Path, Dict] = {
            data['relative_path']: data for data in included_files_data
        }
        # Set of included relative paths for quick lookup
        self.included_relative_paths: Set[Path] = set(self.included_files_map.keys())

    def _is_dir_explicitly_excluded(self, relative_path: Path) -> bool:
        """Check if a directory's name matches an excluded_dirs pattern."""
        # Check if any part of the path *is* an excluded directory name
        for part in relative_path.parts:
            if part in self.config.excluded_dirs:
                return True
        # Check base name against patterns too (less common)
        # for pattern in self.config.excluded_dirs:
        #    if fnmatch.fnmatch(relative_path.name, pattern):
        #        return True
        return False

    def _build_tree_recursive(self, current_path: Path) -> List[Dict[str, Any]]:
        """Builds the hierarchical structure."""
        tree_nodes = []
        try:
            # Sort items: directories first, then files, then by name
            sorted_items = sorted(
                current_path.iterdir(),
                key=lambda p: (p.is_file(), p.name.lower())
            )

            for item in sorted_items:
                if item.is_symlink():
                    continue

                relative_path = item.relative_to(self.root_dir)
                node: Dict[str, Any] = {'name': item.name, 'path': relative_path}

                is_dir_excluded_by_name = self._is_dir_explicitly_excluded(relative_path)

                if item.is_dir():
                    # If dir name itself is excluded, skip recursion entirely
                    if is_dir_excluded_by_name:
                        node['included'] = False
                        node['children'] = [] # No need to show children of excluded dir
                    else:
                        children = self._build_tree_recursive(item)
                        node['children'] = children
                        # A directory is included if it wasn't excluded by name AND
                        # it contains any included children (files or subdirs)
                        node['included'] = any(c.get('included', False) for c in children)
                elif item.is_file():
                    # File inclusion is determined by whether it's in our map
                    node['included'] = relative_path in self.included_files_map
                    if node['included']:
                        # Copy stats from the map
                        file_data = self.included_files_map[relative_path]
                        node['lines'] = file_data.get('lines', 0)
                        node['chars'] = file_data.get('chars', 0)
                        node['percentage'] = file_data.get('percentage', 0.0)

                # Only add the node to the tree if it's included OR if it's a directory
                # (We might show empty included dirs, or excluded dirs if needed later)
                # For now, let's simplify: only add if included
                # Revision: We need the structure, filter display later
                tree_nodes.append(node)

        except OSError as e:
            logging.warning(f"Could not read directory {current_path}: {e}")
            tree_nodes.append({'name': f"[Error reading: {e}]", 'path': current_path.relative_to(self.root_dir), 'included': False})

        return tree_nodes

    def build_structure(self) -> List[Dict[str, Any]]:
        """Builds and returns the raw tree structure."""
        logging.info("Building tree structure...")
        start_time = time.time()
        structure = self._build_tree_recursive(self.root_dir)
        build_time = time.time() - start_time
        logging.info(f"Tree structure build completed in {build_time:.3f} seconds.")
        return structure


class MarkdownFormatter:
    """Formats the collected data into Markdown strings."""
    # --- New constants for blocks ---
    BLOCK_CHAR = "🔲"
    MAX_BLOCKS = 10 # Max blocks for 100%

    def __init__(self, scan_data: Dict, tree_structure: List[Dict[str, Any]]):
        self.scan_data = scan_data # Keep original for reference if needed
        self.tree_structure = tree_structure # The final tree with correct 'included' flags
        self.config = scan_data['config']
        # Stats are now directly from scan_data (calculated during scan)
        self.final_stats = {
            'total_files': scan_data['total_included_files'],
            'total_lines': scan_data['total_included_lines'],
            'total_chars': scan_data['total_included_chars'],
            'scanned_count': scan_data['scanned_count'],
        }

    # --- New recursive formatter for summary ---
    def _format_tree_for_summary_recursive(self, nodes: List[Dict[str, Any]], indent: str = '', is_last_list: Optional[List[bool]] = None) -> List[str]:
        """Recursively formats the tree structure WITH percentage blocks for summary output."""
        if is_last_list is None:
            is_last_list = []

        lines = []
        for i, node in enumerate(nodes):
            is_last = (i == len(nodes) - 1)
            marker = GLYPH_LAST if is_last else GLYPH_CHILD
            prefix = indent + marker + ' '

            is_included = node.get('included', False)
            status_marker = '✅' if is_included else '❌'

            if 'children' in node: # Directory
                # Only display directory node if it's included itself OR contains included items
                # (This hides empty excluded directories)
                # Revision: Show all dirs for structure, but mark excluded
                lines.append(f"{prefix}{node['name']} {status_marker}")
                if is_included or any(c.get('included') for c in node.get('children', [])):
                    child_indent = indent + (GLYPH_INDENT_LAST if is_last else GLYPH_INDENT_CHILD) + ' '
                    lines.extend(self._format_tree_for_summary_recursive(node['children'], child_indent, is_last_list + [is_last]))
                # else: # Skip children of fully excluded dirs

            else: # It's a file
                if not is_included:
                     # Optionally show excluded files with ❌ marker if needed
                     # lines.append(f"{prefix}{node['name']} {status_marker}")
                     continue # Skip excluded files for summary display

                # File is included
                stats_str = ""
                blocks_str = "" # Initialize blocks string
                percentage = node.get('percentage', 0.0)
                stats = f" ({node.get('lines', 0):,}L, {node.get('chars', 0):,}C) [~{percentage:.2f}%]"
                stats_str = stats

                # --- Add Block Calculation ---
                if percentage > 0.1: # Add threshold to avoid single blocks for tiny files
                    # Scale percentage slightly for better visual distribution
                    scaled_percentage = min(100, percentage * 1.1) # Example scaling
                    num_blocks = round(scaled_percentage / 100.0 * self.MAX_BLOCKS)
                    num_blocks = max(1, num_blocks) # Ensure at least one block if > threshold
                    if num_blocks > 0:
                        blocks_str = f" {self.BLOCK_CHAR * num_blocks}"
                # --- End Block Calculation ---

                # Append line with stats and potentially blocks
                lines.append(f"{prefix}{node['name']} {status_marker}{stats_str}{blocks_str}")

        return lines

    # --- New method to generate the plain tree for LLM context ---
    def _format_tree_plain_recursive(self, nodes: List[Dict[str, Any]], indent: str = '', is_last_list: Optional[List[bool]] = None) -> List[str]:
        """Recursively formats the tree structure WITHOUT blocks for main output."""
        if is_last_list is None:
            is_last_list = []

        lines = []
        for i, node in enumerate(nodes):
            is_last = (i == len(nodes) - 1)
            marker = GLYPH_LAST if is_last else GLYPH_CHILD
            prefix = indent + marker + ' '

            is_included = node.get('included', False)
            status_marker = '✅' if is_included else '❌'

            if 'children' in node: # Directory
                lines.append(f"{prefix}{node['name']} {status_marker}")
                # Always recurse for structure, even if dir itself isn't marked included initially
                child_indent = indent + (GLYPH_INDENT_LAST if is_last else GLYPH_INDENT_CHILD) + ' '
                lines.extend(self._format_tree_plain_recursive(node['children'], child_indent, is_last_list + [is_last]))
            else: # It's a file
                 # Only show included files in the plain tree for LLM
                 if is_included:
                     stats_str = ""
                     stats = f" ({node.get('lines', 0):,}L, {node.get('chars', 0):,}C) [~{node.get('percentage', 0.0):.2f}%]"
                     stats_str = stats
                     lines.append(f"{prefix}{node['name']} {status_marker}{stats_str}")
                 # else: skip excluded files in plain output

        return lines

    def _generate_plain_tree_string(self) -> str:
        """Generates the plain tree string without blocks."""
        is_root_included = any(n.get('included', False) for n in self.tree_structure) or \
                           any(f['relative_path'].parent == Path('.') for f in self.scan_data['included_files'])
        root_marker = "." + (" ✅" if is_root_included else " ❌")
        tree_lines_plain = [root_marker]
        tree_lines_plain.extend(self._format_tree_plain_recursive(self.tree_structure))
        return "\n".join(tree_lines_plain)

    def format_summary(self) -> str:
        """Generates the summary Markdown (tree + stats) WITH blocks."""
        home = str(Path.home())
        display_dir = str(self.config.root_dir)
        if display_dir.startswith(home):
            display_dir = display_dir.replace(home, "~", 1)

        # --- Generate Tree with Blocks ---
        is_root_included = any(n.get('included', False) for n in self.tree_structure) or \
                           any(f['relative_path'].parent == Path('.') for f in self.scan_data['included_files'])
        root_marker = "." + (" ✅" if is_root_included else " ❌") # Add marker to root
        tree_lines_with_blocks = [root_marker]
        tree_lines_with_blocks.extend(self._format_tree_for_summary_recursive(self.tree_structure))
        tree_string_with_blocks = "\n".join(tree_lines_with_blocks)
        # --- End Generate Tree with Blocks ---

        lines = [
            "# Project Structure & Statistics",
            f"*Directory: {display_dir}*",
            # Updated Legend
            f"Legend: ✅=Included, ❌=Excluded, {self.BLOCK_CHAR}=% Size Contribution (Max {self.MAX_BLOCKS}, Threshold >0.1%)",
            "",
            "## Project Tree & Statistics",
            "```",
            tree_string_with_blocks, # Use the tree with blocks
            "```",
            "",
            "**Summary Statistics (Included Items):**",
            f"*   **Total Files Included:** {self.final_stats['total_files']:,} (out of {self.final_stats['scanned_count']:,} filesystem items scanned)",
            f"*   **Total Lines Included:** {self.final_stats['total_lines']:,}",
            f"*   **Total Characters Included:** {self.final_stats['total_chars']:,} ({self.final_stats['total_chars']/1024:.1f} kB)",
            ""
        ]
        return "\n".join(lines)

    def format_full(self) -> str:
        """Generates the full Markdown output string including file content."""
        home = str(Path.home())
        display_dir = str(self.config.root_dir)
        if display_dir.startswith(home):
            display_dir = display_dir.replace(home, "~", 1)

        # --- Generate the PLAIN tree string for the full output ---
        plain_tree_string = self._generate_plain_tree_string()

        # --- Construct Header using PLAIN tree ---
        header_lines = [
            "# Project Context", # Simplified title for LLM
            f"*Directory: {display_dir}*",
            # Simpler legend for LLM context
            "Legend: ✅=Included File/Dir, ❌=Excluded/Filtered",
            "",
            "## Project Tree", # Simplified section title
            "```",
            plain_tree_string, # Use the plain tree string
            "```",
            "",
            "**Summary Statistics (Included Items):**",
            f"*   Files: {self.final_stats['total_files']:,}",
            f"*   Lines: {self.final_stats['total_lines']:,}",
            f"*   Characters: {self.final_stats['total_chars']:,} (~{self.final_stats['total_chars']/1024:.1f} kB)",
            ""
        ]
        lines = header_lines
        # --- End Header ---

        # Add Content Section Header
        lines.append("---") # Separator
        lines.append("")
        lines.append("## Selected File Content")
        lines.append("")

        # Get included files data from scan_data
        included_files = self.scan_data['included_files']
        root_dir = self.config.root_dir

        # --- Sorting Logic (same as before) ---
        from collections import defaultdict
        def sort_folder(current_path: Path, files_in_folder: List[Dict]):
            direct_files = [f for f in files_in_folder if f['relative_path'].parent == current_path]
            subfolder_map = defaultdict(list)
            for f in files_in_folder:
                if f['relative_path'].parent != current_path and f['relative_path'].parts[:len(current_path.parts)] == current_path.parts:
                     if len(f['relative_path'].parts) > len(current_path.parts):
                         subfolder_name = f['relative_path'].parts[len(current_path.parts)]
                         subfolder_map[subfolder_name].append(f)

            # Sort direct files by line count descending, then name
            direct_files.sort(key=lambda x: (-x['lines'], x['relative_path'].name))
            for f in direct_files:
                yield f

            # Sort subfolders by total line count descending
            subfolder_items = list(subfolder_map.items())
            subfolder_items.sort(key=lambda kv: -sum(f['lines'] for f in kv[1]))
            for subfolder_name, files_in_subfolder in subfolder_items:
                yield from sort_folder(current_path / subfolder_name, files_in_subfolder)

        # Separate files by root vs subdirs
        root_files = [f for f in included_files if f['relative_path'].parent == Path('.')]
        subdir_files = [f for f in included_files if f['relative_path'].parent != Path('.')]

        # Prioritize README.md at the very top if present
        readme_file = next((f for f in root_files if f['relative_path'].name.lower() == 'readme.md'), None)
        other_root_files = [f for f in root_files if f != readme_file]
        other_root_files.sort(key=lambda x: (-x['lines'], x['relative_path'].name)) # Sort other root files

        # Group subdir files by top-level folder
        top_folder_map = defaultdict(list)
        for f in subdir_files:
            if f['relative_path'].parts:
                top_folder_map[f['relative_path'].parts[0]].append(f)

        # Sort top-level folders by total line count
        sorted_top_folders = sorted(
            top_folder_map.items(),
            key=lambda kv: -sum(f['lines'] for f in kv[1])
        )

        # --- Yield files in the final sorted order ---
        sorted_files_final = []
        if readme_file:
            sorted_files_final.append(readme_file)
        sorted_files_final.extend(other_root_files)
        for folder_name, files_in_folder in sorted_top_folders:
            sorted_files_final.extend(list(sort_folder(Path(folder_name), files_in_folder)))
        # --- End Sorting ---

        # Append file content
        for file_data in sorted_files_final:
             # Ensure we only append files that were actually included
             if file_data.get('included', False):
                 lines.append(f"### `/{file_data['relative_path']}`")
                 lines.append(f"*(Stats: {file_data['lines']} lines, {file_data['chars']} chars [~{file_data['percentage']:.2f}%])* ")
                 lines.append("```" + file_data.get('language_hint', '') + "\n" + file_data['content'] + "\n```")
                 lines.append("") # Add blank line between files

        return "\n".join(lines).strip()


class OutputHandler:
    """Handles sending the formatted content to the specified destination."""
    def __init__(self, args: argparse.Namespace):
        self.args = args

    def handle(self, full_content: str, summary_content: str):
        """Writes to file, stdout, or clipboard based on args."""
        output_written = False
        error_occurred = False

        # Determine the target for the summary message (stderr unless --stdout is used)
        summary_target_stream = sys.stdout if self.args.stdout else sys.stderr

        # 1. Write to Output File if specified
        if self.args.output:
            try:
                self.args.output.parent.mkdir(parents=True, exist_ok=True)
                with open(self.args.output, "w", encoding="utf-8") as f:
                    f.write(full_content)
                # Print summary with blocks to stderr when writing to file
                print(summary_content, file=sys.stderr)
                print(f"\nSuccess: Generated context written to {self.args.output}", file=sys.stderr)
                output_written = True
            except OSError as e:
                print(f"Error: Could not write to output file {self.args.output}: {e}", file=sys.stderr)
                error_occurred = True

        # 2. Print full content to Stdout if specified
        elif self.args.stdout: # Use elif because --output implies not printing full to stdout
            try:
                print(full_content) # Print full, plain content
                output_written = True
            except Exception as e:
                print(f"Error: Could not write to stdout: {e}", file=sys.stderr)
                error_occurred = True

        # 3. Copy to Clipboard (Default action if no other output specified)
        elif PYPERCLIP_AVAILABLE and not self.args.no_clipboard: # Use elif
            try:
                # --- Print summary with blocks to stderr BEFORE copying ---
                print(summary_content, file=sys.stderr)

                # --- Now attempt clipboard copy with full, plain content ---
                logging.info("Attempting to copy content to clipboard...")
                start_time = time.time()
                pyperclip.copy(full_content)
                end_time = time.time()
                logging.info(f"pyperclip.copy() finished in {end_time - start_time:.3f} seconds.")

                print(f"\nSuccess: Generated context ({len(full_content):,} chars) sent to Clipboard.", file=sys.stderr)
                output_written = True # Mark as handled
            except Exception as e:
                logging.error(f"Error copying to clipboard: {e}")
                print(f"\nError: Failed to copy content to clipboard: {e}", file=sys.stderr)
                error_occurred = True

        # 4. Fallback: If no output method used (e.g., --no-clipboard and no --output/--stdout)
        #    Print summary with blocks to stderr as the only output.
        if not output_written:
             try:
                 print(summary_content, file=sys.stderr)
                 # No explicit success message needed here
             except Exception as e:
                 print(f"Error: Could not write summary to stderr (fallback): {e}", file=sys.stderr)
                 error_occurred = True


        # --- Final Exit ---
        # Exit with error code if any issues occurred during output
        if error_occurred:
            sys.exit(1)


# --- Argument Parser Setup ---

def setup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gather project context (code, config) into Markdown for LLMs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    # Input/Output
    parser.add_argument("root_dir", nargs="?", type=Path, default=Path("."), help="Root project directory.")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output file path (writes Markdown).")
    parser.add_argument("--stdout", action="store_true", help="Print full context (plain tree) to stdout.")
    parser.add_argument("--no-clipboard", action="store_true", help="Do not copy to clipboard.")
    # Filtering
    parser.add_argument("--exclude", action="append", metavar="PATTERN", help="Glob pattern to exclude.")
    parser.add_argument("--include", action="append", metavar="PATTERN", help="Glob pattern to force include (overrides most excludes).")
    parser.add_argument("--exclude-extension", action="append", metavar="EXT", help="File extension to exclude (e.g., '.log').")
    parser.add_argument("--include-extension", action="append", metavar="EXT", help="File extension to force include.")
    parser.add_argument("--max-size", default="2M", metavar="SIZE", help="Max file size (e.g., 500k, 10M). 0 for no limit.")
    parser.add_argument("--include-binary", action="store_true", help="Include binary files.")
    # Git Handling Modes (Mutually Exclusive Group)
    git_group = parser.add_mutually_exclusive_group()
    git_group.add_argument("--no-gitignore", action="store_true", help="Ignore .gitignore and git tracking status.")
    git_group.add_argument("--gitignore-only", action="store_true", help="Use .gitignore for exclusions, but ignore git tracking status.")

    # Default Overrides (Clarify help text)
    parser.add_argument("--include-json", action="store_true", help="Include *.json/*.jsonc files (overrides default exclude).")
    parser.add_argument("--include-yaml", action="store_true", help="Include *.yaml/*.yml files (overrides default exclude).")
    parser.add_argument("--include-xml", action="store_true", help="Include *.xml files (overrides default exclude).")
    parser.add_argument("--include-html", action="store_true", help="Include *.html/*.htm files (overrides default exclude).")
    parser.add_argument("--include-css", action="store_true", help="Include *.css files (overrides default exclude).")
    parser.add_argument("--include-sql", action="store_true", help="Include *.sql files (overrides default exclude).")
    parser.add_argument("--include-csv", action="store_true", help="Include *.csv/*.tsv files (overrides default exclude).")
    parser.add_argument("--include-markdown", action="store_true", help="Include all non-root *.md/*.markdown/*.rst files (overrides default exclude).") # Grouped related flag
    return parser

# --- Main Orchestration ---

def main():
    """Main function to orchestrate script execution."""
    # Basic logging setup (can be configured further)
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s', stream=sys.stderr)

    parser = setup_parser()
    args = parser.parse_args()

    # --- Input Validation ---
    if not args.root_dir.is_dir():
        logging.error(f"Root directory not found or not a directory: {args.root_dir}")
        sys.exit(1)

    # --- Processing Steps ---
    try:
        start_total_time = time.time()
        config = Config(args)
        file_filter = FileFilter(config)
        scanner = ProjectScanner(config, file_filter)
        scanner.scan()
        scan_data = scanner.get_data()

        # Check if any files were included
        if not scan_data['included_files']:
             logging.warning("No files were included based on the current filters. Output will be minimal.")
             # Create minimal structure/content if needed, or let it proceed to generate empty sections
             tree_structure = []
             full_content = "# No files included"
             summary_content = "# No files included"
        else:
             tree_builder = TreeBuilder(
                 root_dir=config.root_dir,
                 config=config,
                 included_files_data=scan_data['included_files'] # Pass detailed data
             )
             tree_structure = tree_builder.build_structure() # Get structure first

             formatter = MarkdownFormatter(scan_data, tree_structure) # Pass structure
             # Generate both versions of the content
             full_content = formatter.format_full()       # Plain tree for LLM
             summary_content = formatter.format_summary() # Tree with blocks for terminal

        end_total_time = time.time()
        logging.info(f"Total processing time: {end_total_time - start_total_time:.3f} seconds.")

    except Exception as e:
        logging.error(f"Error during processing: {e}", exc_info=False) # Set exc_info=True for full traceback
        # Optional: Print traceback to stderr for debugging
        # import traceback
        # traceback.print_exc(file=sys.stderr)
        sys.exit(1)

    # --- Output Handling ---
    output_handler = OutputHandler(args)
    output_handler.handle(full_content, summary_content)


if __name__ == "__main__":
    main()
