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
    ".git", ".svn", ".hg", ".bzr", "node_modules", "vendor",
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
    "*.dll", "*.exe", "*.class", "*.jar", "*.war", "*.ear",
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
    ".eslintrc*", ".prettierrc*", ".editorconfig", ".gitattributes", ".gitmodules",
    ".env*", # Exclude all .env except .env.example
    "tsconfig.json", "tsconfig.*.json",
    # Common data/doc formats to exclude by default
    "*.spec.*", "*.test.*", # Test files
    "*.csv", "*.tsv", "*.xml", "*.yaml", "*.yml", # Data
    "*.htm", "*.html", "*.css", ".sql" # Web/DB assets
    "*.md", "*.markdown", ".rst", # Docs (except specific files)
    "*.json", "*.jsonc", ".yaml", ".yml", ".xml", ".html", ".htm", ".css", ".sql", ".csv", ".tsv", ".md", ".markdown", ".rst",
    "*.json", "*.jsonc", ".yaml", ".yml", ".xml", ".html", ".htm", ".css", ".sql", ".csv", ".tsv", ".md", ".markdown", ".rst",
    "package.json", "**/package.json",
)

# Files to check even if their extension/pattern is in DEFAULT_EXCLUDED_PATTERNS
FILES_TO_ALWAYS_CHECK = {
    "README.md", ".env.example", "docker-compose.yml", "docker-compose.yaml",
    "Dockerfile", "requirements.txt", "pyproject.toml", "go.mod", "go.sum", "Cargo.toml"
}

# Always skip .gitignore itself from output
SKIP_ALWAYS = {".gitignore", "pnpm-lock.yaml", "package.json", "tsconfig.json", ".eslintrc.js", ".prettierrc.js", ".env"}

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
            ".json": args.include_json,
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
        return suffix in self.override_defaults

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


    def should_include(self, abs_path: Path) -> Tuple[bool, str]:
        """Checks if a file should be included. Returns (include_bool, reason_string)."""
        filename = abs_path.name
        rel_path_str = str(abs_path.relative_to(self.config.root_dir))
        rel_path_posix = rel_path_str.replace(os.sep, '/')

        # --- Determine Git Mode for this check --- 
        use_full_git = not self.config.no_gitignore and not self.config.gitignore_only and self.git_tracked_files is not None
        use_gitignore_parsing = not self.config.no_gitignore and self.gitignore_matcher is not None

        # 0. Always Check Files (Highest Priority)
        if filename in FILES_TO_ALWAYS_CHECK:
            if self.config.max_size is not None and abs_path.stat().st_size > self.config.max_size:
                 return False, f"Excluded: Always-check file '{filename}' exceeded max size"
            if not self.config.include_binary and is_likely_binary_file(abs_path):
                 return False, f"Excluded: Always-check file '{filename}' is binary"
            return True, f"Included: Explicitly always checked ('{filename}')"

        # 1. Always Skip Files
        if filename in SKIP_ALWAYS:
             return False, f"Excluded: Explicitly always skipped ('{filename}')"

        # 2. Explicit Exclude Patterns (e.g., 'package.json', '*.log')
        for pattern in self.config.excluded_patterns:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(rel_path_posix, pattern): 
                return False, f"Excluded: Matched exclude pattern for '{filename}'"

        # 3. Excluded Directories (e.g., 'node_modules', '.git')
        is_in_excluded_dir = False
        for excluded_dir_pattern in self.config.excluded_dirs:
            try:
                 if excluded_dir_pattern in rel_path_str.split(os.sep):
                    is_in_excluded_dir = True
                    break
            except Exception as e:
                 logging.error(f"Error checking excluded dir '{excluded_dir_pattern}' for path '{rel_path_str}': {e}")

        if is_in_excluded_dir:
            return False, f"Excluded: Part of default excluded directory ('{excluded_dir_pattern}' in '{rel_path_posix}')"

        # 4. Git Ignore Check
        if use_gitignore_parsing:
            if self.gitignore_matcher(abs_path): # type: ignore
                 return False, f"Excluded: Matched .gitignore pattern for '{rel_path_posix}'"

        # 5. Git Tracking Check
        if use_full_git:
            is_tracked = rel_path_str in self.git_tracked_files # type: ignore
            if not is_tracked:
                 return False, f"Excluded: Not tracked by git ('{rel_path_posix}')"
            suffix = abs_path.suffix.lower()
            if suffix and any(fnmatch.fnmatch(filename, pattern) for pattern in DEFAULT_EXCLUDED_PATTERNS):
                if not self.config.should_override_default_exclude(suffix):
                     return False, f"Excluded: Matched default pattern ('{suffix}') for tracked file '{filename}'"
            return True, f"Included: Tracked by git, passed filters ('{rel_path_posix}')"

        # 6. Explicit CLI Includes
        for pattern in self.config.included_patterns:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(rel_path_posix, pattern): 
                if self.config.max_size is not None and abs_path.stat().st_size > self.config.max_size:
                     return False, f"Excluded: CLI included file '{filename}' exceeded max size"
                if not self.config.include_binary and is_likely_binary_file(abs_path):
                     return False, f"Excluded: CLI included file '{filename}' is binary"
                return True, f"Included: Matched CLI include pattern for '{filename}'"

        # 7. Size Limit
        if self.config.max_size is not None and abs_path.stat().st_size > self.config.max_size:
             return False, f"Excluded: Exceeded max size ({abs_path.stat().st_size} > {self.config.max_size}) for '{filename}'"

        # 8. Binary Files
        if not self.config.include_binary and is_likely_binary_file(abs_path):
             return False, f"Excluded: Likely binary file ('{filename}')"

        # 9. Default Pattern Exclusions
        suffix = abs_path.suffix.lower()
        if suffix:
            if any(fnmatch.fnmatch(filename, pattern) for pattern in self.config.excluded_patterns if pattern.startswith('*.')):
                 return False, f"Excluded: Matched default pattern for suffix '{suffix}'"

        # 10. Fallback to Always Check Files
        if filename in FILES_TO_ALWAYS_CHECK:
            if filename == "README.md" and abs_path.parent != self.config.root_dir:
                 pass
            else:
                 return True, f"Included: Explicitly always checked ('{filename}')"

        # --- Default Behaviour --- 
        is_binary = is_likely_binary_file(abs_path)
        if is_binary and not self.config.include_binary:
             return False, f"Excluded: Binary file ('{filename}')"
        return True, f"Included: Default (likely text or binary allowed for '{filename}')"

class ProjectScanner:
    """Scans the project, filters files, reads content, and gathers stats."""
    def __init__(self, config: Config, file_filter: FileFilter):
        self.config = config
        self.filter = file_filter
        self.included_files_data: List[Dict[str, Any]] = []
        self.all_paths_walked: Set[Path] = set()
        self.scanned_item_count = 0
        self.excluded_files_count = 0 # Count only excluded files
        self.total_lines = 0
        self.total_chars = 0

    def scan(self):
        """Performs the directory scan and filtering."""
        start_time = time.time()
        included_paths_temp = []

        for abs_path in self.config.root_dir.rglob("*"):
            self.scanned_item_count += 1
            resolved_path = abs_path.resolve()
            self.all_paths_walked.add(resolved_path)

            is_included, reason = self.filter.should_include(abs_path)

            # Only include files that are not in excluded directories
            if is_included and abs_path.is_file():
                # Check if any parent directory is in excluded_dirs
                rel_parts = abs_path.relative_to(self.config.root_dir).parts
                if any(part in self.config.excluded_dirs for part in rel_parts):
                    continue  # Skip files in excluded directories
                included_paths_temp.append(abs_path)
            elif abs_path.is_file():
                self.excluded_files_count += 1

        # Sort included files
        included_paths_temp.sort(key=lambda p: (
            len(p.relative_to(self.config.root_dir).parent.parts),
            p.relative_to(self.config.root_dir).parent.parts,
            p.suffix.lower(),
            p.name
        ))

        # Read content and calculate stats for included files
        read_start_time = time.time()
        temp_file_data = [] # Temporary list before adding percentage
        for path in included_paths_temp:
            try:
                if path.is_file(): # Only read if it's actually a file
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
                        "language_hint": get_language_hint(path.name) # Add hint here
                    })
                elif path.is_dir():
                     # Optionally log skipped directories, or just pass
                     pass
                else:
                    print(f"Warning: Skipping non-file/non-directory item: {path}", file=sys.stderr)

            except Exception as e:
                print(f"Warning: Could not read file {path.name}: {e}. Skipping content.", file=sys.stderr)
                # Add placeholder data if read fails but file was intended to be included
                temp_file_data.append({
                     "absolute_path": path, 'lines': 0, 'chars': 0, 'content': f"# Error reading file: {e}", 'language_hint': 'plaintext'
                })

        # Now calculate percentages and populate final list
        for file_data in temp_file_data:
            percentage = (file_data['chars'] / self.total_chars * 100) if self.total_chars > 0 else 0
            file_data['percentage'] = percentage
            self.included_files_data.append(file_data) # Add to the final list

        # read_time = time.time() - read_start_time
        # filter_time = read_start_time - start_time

        # Suppress info logs to stdout/stderr
        # print(f"Info: Scanned {self.scanned_item_count} filesystem items. Filtered out {self.excluded_files_count} files.", file=sys.stderr)
        # print(f"Info: Found {len(self.included_files_data)} files to include.", file=sys.stderr)
        # print(f"Timing: Filtering: {filter_time:.3f}s, Reading: {read_time:.3f}s", file=sys.stderr)

    def get_data(self) -> Dict[str, Any]:
        """Returns the collected scan data."""
        return {
            "root_dir_abs": self.config.root_dir,
            "included_files": self.included_files_data,
            "all_paths_walked": self.all_paths_walked,
            "total_included_files": len(self.included_files_data),
            "total_included_lines": self.total_lines,
            "total_included_chars": self.total_chars,
            "scanned_count": self.scanned_item_count,
        }


class TreeBuilder:
    """Builds the formatted project tree string."""
    def __init__(self, root_dir: Path, config: Config, included_paths: Set[Path], file_stats: Dict[Path, Dict[str, Any]]):
        self.root_dir = root_dir
        self.config = config
        self.included_paths = included_paths # Final set of files to include
        self.file_stats = file_stats # Pre-calculated stats for included files
        # Pre-calculate relative paths for included files for faster lookup
        self.included_relative_paths = {p.relative_to(root_dir) for p in included_paths}

    def _is_dir_explicitly_excluded(self, path: Path) -> bool:
        "Check if a directory path itself matches an excluded_dirs pattern."""
        relative_path = path.relative_to(self.root_dir)
        # Check if any part of the path *is* an excluded directory name
        for part in relative_path.parts:
            if part in self.config.excluded_dirs:
                return True
        # Check if the path itself matches a pattern (less common for dirs, but possible)
        for pattern in self.config.excluded_dirs:
             if fnmatch.fnmatch(path.name, pattern): # Basic name match
                  return True
             # Could add glob matching here if needed: path.match(pattern)
        return False

    def _build_tree_recursive(self, current_path: Path) -> List[Dict[str, Any]]:
        tree = []
        try:
            for item in sorted(current_path.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
                # Skip symlinks to avoid cycles and potential issues
                if item.is_symlink():
                    continue

                relative_path = item.relative_to(self.root_dir)
                node: Dict[str, Any] = {'name': item.name, 'path': relative_path}
                is_explicitly_excluded_dir = self._is_dir_explicitly_excluded(item)

                if item.is_dir():
                    # Recurse first to get children structure
                    children = self._build_tree_recursive(item)
                    node['children'] = children
                    
                    # --- Directory Exclusion/Inclusion Logic ---
                    if is_explicitly_excluded_dir:
                        node['included'] = False
                        # --- CASCADE EXCLUSION --- 
                        # Force all children to be excluded as well
                        for child in children:
                            self._force_exclude_recursive(child)
                        # --- END CASCADE --- 
                    else:
                        # Mark included if it OR any *already determined* included descendant exists
                        node['included'] = any(c.get('included', False) for c in children)
                        # Also check if the directory *itself* might contain directly included files
                        if not node['included']:
                             # Check if any directly included file has this dir as parent
                             node['included'] = any(p.parent == relative_path for p in self.included_relative_paths)

                elif item.is_file():
                    # --- File Inclusion Logic --- 
                    # Check if this specific file is in the final included set
                    # AND if its parent directory was NOT explicitly excluded
                    node['included'] = relative_path in self.included_relative_paths
                    # Note: Cascading exclusion for files happens via parent directory check above
                    
                    if node['included']:
                        stats = self.file_stats.get(item)
                        if stats:
                            node['lines'] = stats.get('lines', 0)
                            node['chars'] = stats.get('chars', 0)
                            node['percentage'] = stats.get('percentage', 0.0)
                        else:
                             # Should not happen if file_stats is built correctly
                             logging.warning(f"Stats not found for included file: {item}")
                             node['lines'], node['chars'], node['percentage'] = 0, 0, 0.0
                    else:
                         node['lines'], node['chars'], node['percentage'] = 0, 0, 0.0

                tree.append(node)

        except OSError as e:
            logging.warning(f"Could not read directory {current_path}: {e}")
            tree.append({'name': f"[Error reading: {e}]", 'included': False})

        return tree

    def _force_exclude_recursive(self, node: Dict[str, Any]):
        """Recursively set included=False for a node and its children."""
        node['included'] = False
        if 'children' in node:
            for child in node['children']:
                self._force_exclude_recursive(child)

    def _format_tree_recursive(self, nodes: List[Dict[str, Any]], indent: str = '', is_last_list: List[bool] = None) -> List[str]:
        if is_last_list is None:
            is_last_list = []

        lines = []
        for i, node in enumerate(nodes):
            is_last = (i == len(nodes) - 1)
            marker = GLYPH_LAST if is_last else GLYPH_CHILD
            
            # Determine the correct prefix based on indentation level
            prefix = indent + marker + ' '

            is_included = node.get('included', False)
            # Status marker
            status_marker = '✅' if is_included else '❌'

            # Format based on whether it's a file or directory
            if 'children' in node: # It's a directory
                if not is_included:
                    # --- Display Excluded Directory --- 
                    lines.append(f"{prefix}{node['name']} {status_marker}")
                    # --- Skip Children --- 
                    continue # Don't recurse/print children for excluded dirs
                else:
                    # Included directory (or contains included files)
                    lines.append(f"{prefix}{node['name']} {status_marker}")
                    # Calculate indentation for children
                    child_indent = indent + (GLYPH_INDENT_LAST if is_last else GLYPH_INDENT_CHILD) + ' '
                    lines.extend(self._format_tree_recursive(node['children'], child_indent, is_last_list + [is_last]))
            else: # It's a file
                stats_str = ""
                if is_included:
                    stats = f" ({node.get('lines', 0):,}L, {node.get('chars', 0):,}C) [~{node.get('percentage', 0.0):.2f}%]"
                    stats_str = stats
                lines.append(f"{prefix}{node['name']} {status_marker}{stats_str}")

        return lines

    def build_and_format(self) -> str:
        """Builds the tree and returns the formatted string representation."""
        logging.info("Building tree structure...")
        start_time = time.time()
        # Build the tree structure starting from the root
        tree_structure = self._build_tree_recursive(self.root_dir)
        
        # Check if root itself contains any included files/dirs
        is_root_included = any(n.get('included', False) for n in tree_structure) or \
                           any(p.parent == Path('.') for p in self.included_relative_paths)
                           
        # Format the structure into lines
        tree_lines = ["." + (" " if is_root_included else " ") + ""] # Root marker
        tree_lines.extend(self._format_tree_recursive(tree_structure))
        tree_string = "\n".join(tree_lines)
        build_time = time.time() - start_time
        logging.info(f"Tree building completed in {build_time:.3f} seconds.")
        return tree_string


class MarkdownFormatter:
    """Formats the collected data into Markdown strings."""
    def __init__(self, scan_data: Dict, tree_string: str, tree_structure: List[Dict[str, Any]]):
        self.scan_data_original = scan_data # Keep original for reference if needed
        self.tree_string = tree_string
        self.tree_structure = tree_structure # The final tree with correct 'included' flags
        self.config = scan_data['config']
        
        # --- Recalculate Stats based on final tree --- 
        self.final_stats = self._calculate_final_stats(self.tree_structure)

    def _calculate_final_stats_recursive(self, nodes: List[Dict[str, Any]], stats: Dict[str, Any]):
        """Helper to traverse tree and sum stats for included files."""
        for node in nodes:
            if node.get('included', False):
                if 'children' in node: # Directory
                    self._calculate_final_stats_recursive(node['children'], stats)
                else: # File
                    stats['total_files'] += 1
                    stats['total_lines'] += node.get('lines', 0)
                    stats['total_chars'] += node.get('chars', 0)

    def _calculate_final_stats(self, tree_structure: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate final summary stats based on the tree's included nodes."""
        final_stats = {
            'total_files': 0,
            'total_lines': 0,
            'total_chars': 0
        }
        self._calculate_final_stats_recursive(tree_structure, final_stats)
        # Add original scanned count for context
        final_stats['scanned_count'] = self.scan_data_original.get('scanned_count', 0)
        return final_stats

    def format_summary(self) -> str:
        """Generates the summary Markdown (tree + stats)."""
        import os
        home = str(Path.home())
        display_dir = str(self.config.root_dir)
        if display_dir.startswith(home):
            display_dir = display_dir.replace(home, "~", 1)
        lines = [
            "# Project Structure & Statistics",
            f"*Directory: {display_dir}*",
            "Legend:  = ✅ Included File | 📁❌ = Excluded/Filtered Files",
            "",
            "## Project Tree & Statistics",
            "```",
            self.tree_string,
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
        """Generates the full Markdown output string including file content, sorted as per custom rules."""
        lines = self.format_summary().splitlines()

        # Add Content Section Header
        lines.append("---") # Separator
        lines.append("")
        lines.append("## Selected File Content")
        lines.append("")

        included_files = self.scan_data_original['included_files']
        root_dir = self.config.root_dir

        # Build a mapping from relative path to file data for fast lookup
        file_map = {str(f['relative_path']): f for f in included_files}

        # Helper: recursively sort and yield files in a folder
        from collections import defaultdict
        def sort_folder(current_path: Path):
            # Group direct files and subfolders
            direct_files = []
            subfolders = defaultdict(list)
            for f in included_files:
                rel = f['relative_path']
                parts = rel.parts
                if len(parts) == len(current_path.parts) + 1 and rel.parts[:len(current_path.parts)] == current_path.parts:
                    direct_files.append(f)
                elif len(parts) > len(current_path.parts) + 1 and rel.parts[:len(current_path.parts)] == current_path.parts:
                    subfolders[rel.parts[len(current_path.parts)]].append(f)
            # Sort direct files by line count descending, then name
            direct_files.sort(key=lambda x: (-x['lines'], x['relative_path']))
            for f in direct_files:
                yield f
            # Sort subfolders by total line count descending
            subfolder_items = list(subfolders.items())
            subfolder_items.sort(key=lambda kv: -sum(f['lines'] for f in kv[1]))
            for subfolder, _ in subfolder_items:
                yield from sort_folder(current_path / subfolder)

        # 1. Root-level .md files first
        root_md_files = [f for f in included_files if f['absolute_path'].parent == root_dir and str(f['absolute_path'].name).lower().endswith('.md')]
        root_md_files.sort(key=lambda x: (-x['lines'], x['relative_path']))
        # 2. Other root files
        root_other_files = [f for f in included_files if f['absolute_path'].parent == root_dir and not str(f['absolute_path'].name).lower().endswith('.md')]
        root_other_files.sort(key=lambda x: (-x['lines'], x['relative_path']))
        # 3. Top-level folders, recursively
        # Find all top-level folders
        top_folders = set(f['relative_path'].parts[0] for f in included_files if len(f['relative_path'].parts) > 1)
        # Sort top-level folders by total line count
        folder_line_counts = {folder: sum(f['lines'] for f in included_files if len(f['relative_path'].parts) > 1 and f['relative_path'].parts[0] == folder) for folder in top_folders}
        sorted_folders = sorted(top_folders, key=lambda k: -folder_line_counts[k])
        # Now yield files in the desired order
        sorted_files = []
        sorted_files.extend(root_md_files)
        sorted_files.extend(root_other_files)
        for folder in sorted_folders:
            sorted_files.extend(list(sort_folder(Path(folder))))
        for file_data in sorted_files:
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

        # 1. Write to Output File if specified
        if self.args.output:
            try:
                self.args.output.parent.mkdir(parents=True, exist_ok=True)
                with open(self.args.output, "w", encoding="utf-8") as f:
                    f.write(full_content)
                print(f"Success: Generated context written to {self.args.output}", file=sys.stderr)
                output_written = True
            except OSError as e:
                print(f"Error: Could not write to output file {self.args.output}: {e}", file=sys.stderr)
                error_occurred = True

        # 2. Print to Stdout if specified
        if self.args.stdout:
            try:
                print(full_content)
                output_written = True
            except Exception as e:
                # Handle potential errors like broken pipes
                print(f"Error: Could not write to stdout: {e}", file=sys.stderr)
                error_occurred = True

        # 3. Copy to Clipboard (Default action if no other output specified)
        if not output_written and PYPERCLIP_AVAILABLE and not self.args.no_clipboard:
            try:
                # --- Print to stdout BEFORE copying to clipboard --- 
                print(summary_content)
                # --- Now attempt clipboard copy --- 
                logging.info("Attempting to copy content to clipboard...")
                start_time = time.time()
                pyperclip.copy(full_content)
                end_time = time.time()
                logging.info(f"pyperclip.copy() finished in {end_time - start_time:.3f} seconds.")
                # Verify clipboard content size if possible and log
                # Note: pyperclip.paste() might be slow/unreliable for large content
                # try:
                #    pasted_content = pyperclip.paste()
                #    logging.info(f"Verification: Intended Chars: {len(full_content)}, Pasted Chars: {len(pasted_content)}")
                #    if len(full_content) != len(pasted_content):
                #        logging.warning("Clipboard content length mismatch after copy!")
                # except Exception as e:
                #    logging.warning(f"Could not verify clipboard content via paste: {e}")
                
                print(f"Success: Generated context ({len(full_content):,} chars) sent to Clipboard.", file=sys.stderr)
                output_written = True # Mark as handled
            except Exception as e:
                logging.error(f"Error copying to clipboard: {e}")
                print(f"Error: Failed to copy content to clipboard: {e}", file=sys.stderr)
                error_occurred = True

        # 4. Fallback to Stdout if no other output method was used
        if not output_written:
             try:
                 print(summary_content)
                 # No success message here, as it's the default fallback
             except Exception as e:
                 print(f"Error: Could not write to stdout (fallback): {e}", file=sys.stderr)
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
    parser.add_argument("--stdout", action="store_true", help="Print Markdown to stdout.")
    parser.add_argument("--no-clipboard", action="store_true", help="Do not copy to clipboard.")
    # Filtering
    parser.add_argument("--exclude", action="append", metavar="PATTERN", help="Glob pattern to exclude.")
    parser.add_argument("--include", action="append", metavar="PATTERN", help="Glob pattern to force include.")
    parser.add_argument("--exclude-extension", action="append", metavar="EXT", help="File extension to exclude (e.g., '.log').")
    parser.add_argument("--include-extension", action="append", metavar="EXT", help="File extension to force include.")
    parser.add_argument("--max-size", default="2M", metavar="SIZE", help="Max file size (e.g., 500k, 10M). 0 for no limit.")
    parser.add_argument("--include-binary", action="store_true", help="Include binary files.")
    # Git Handling Modes (Mutually Exclusive Group)
    git_group = parser.add_mutually_exclusive_group()
    git_group.add_argument("--no-gitignore", action="store_true", help="Ignore .gitignore and git tracking status.")
    git_group.add_argument("--gitignore-only", action="store_true", help="Use .gitignore for exclusions, but ignore git tracking status.")

    # Default Overrides
    parser.add_argument("--include-json", action="store_true", help="Include *.json files.")
    parser.add_argument("--include-yaml", action="store_true", help="Include *.yaml/*.yml files.")
    parser.add_argument("--include-xml", action="store_true", help="Include *.xml files.")
    parser.add_argument("--include-html", action="store_true", help="Include *.html/*.htm files.")
    parser.add_argument("--include-css", action="store_true", help="Include *.css files.")
    parser.add_argument("--include-sql", action="store_true", help="Include *.sql files.")
    parser.add_argument("--include-csv", action="store_true", help="Include *.csv/*.tsv files.")
    parser.add_argument("--include-markdown", action="store_true", help="Include all *.md/*.markdown/*.rst files.") # Grouped related flag
    return parser

# --- Main Orchestration ---

def main():
    """Main function to orchestrate script execution."""
    parser = setup_parser()
    args = parser.parse_args()

    # --- Input Validation ---
    if not args.root_dir.is_dir():
        print(f"Error: Root directory not found or not a directory: {args.root_dir}", file=sys.stderr)
        sys.exit(1)

    # --- Processing Steps ---
    try:
        config = Config(args)
        file_filter = FileFilter(config)
        scanner = ProjectScanner(config, file_filter)
        scanner.scan()
        scan_data = scanner.get_data()

        scan_data['config'] = config  # Add the 'config' object to the scan_data dictionary

        tree_builder = TreeBuilder(
            root_dir=config.root_dir,
            config=config,
            included_paths={f['absolute_path'] for f in scan_data['included_files']},
            file_stats={f['absolute_path']: f for f in scan_data['included_files']}
        )
        tree_structure = tree_builder._build_tree_recursive(config.root_dir) # Get structure first
        tree_string = tree_builder.build_and_format() # Format based on structure

        formatter = MarkdownFormatter(scan_data, tree_string, tree_structure) # Pass structure for stats calc
        full_content = formatter.format_full()
        summary_content = formatter.format_summary()

    except Exception as e:
        print(f"\n--- Error during processing ---", file=sys.stderr)
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

    # --- Output Handling ---
    # Output handler now exits on error internally
    output_handler = OutputHandler(args)
    output_handler.handle(full_content, summary_content)


if __name__ == "__main__":
    main()
