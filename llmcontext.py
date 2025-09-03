#!/usr/bin/env python3
"""
Project Context Gatherer - Clean Architecture Version

A tool to intelligently scan a project directory and format its contents
for consumption by Large Language Models (LLMs).

Architecture:
    CLI Args -> Configuration -> File Discovery -> Filtering -> 
    Content Reading -> Analysis -> Formatting -> Output
"""

import argparse
import fnmatch
import json
import logging
import os
import re
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# ============================================================================
# OPTIONAL IMPORTS
# ============================================================================

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

try:
    import gitignore_parser
    GITIGNORE_PARSER_AVAILABLE = True
except ImportError:
    GITIGNORE_PARSER_AVAILABLE = False

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# ============================================================================
# CONSTANTS
# ============================================================================

DEFAULT_EXCLUDED_DIRS = frozenset({
    ".git", ".svn", ".hg", ".bzr", "node_modules", "vendor", ".tap",
    "venv", "env", ".venv", "ENV", "virtualenv",
    "build", "dist", "target", "out", "bin", "obj",
    "__pycache__", ".cache", "cache",
    ".pytest_cache", ".mypy_cache", ".tox",
    ".idea", ".vscode", "logs", "log", "coverage", "htmlcov",
    ".terraform", ".next", ".nuxt", "public", "static",
    "assets", "images", "img", "icons", "fonts", "media", "uploads", 
    "downloads", "resources", "screenshots", "thumbnails", "previews",
    "demos", "examples", "tests", "__tests__", "test", "docs", "documentation"
})

DEFAULT_EXCLUDED_PATTERNS = frozenset({
    # Compiled/object files
    "*.pyc", "*.pyo", "*.pyd", "*.so", "*.o", "*.a", "*.lib", "*.dylib",
    "*.bundle", "*.dll", "*.exe", "*.class", "*.jar", "*.war", "*.ear", ".tap",
    # Logs and build info
    "*.log", "*.tsbuildinfo",
    # Editor backups/swaps
    "*.swp", "*.swo", "*~", "#*#", ".DS_Store", "Thumbs.db",
    # Patches and diffs
    "*.patch", "*.diff",
    # Lock files
    "*.lock", "pnpm-lock.yaml", "yarn.lock", "package-lock.json", 
    "poetry.lock", "composer.lock", "Gemfile.lock",
    # State files
    "*.tfstate", "*.tfstate.backup",
    # Backups and temps
    "*.bak", "*.tmp", "*.temp",
    # Minified files and source maps
    "*.min.*", "*.map",
    # Asset files
    "*.svg", "*.png", "*.jpg", "*.jpeg", "*.gif", "*.ico", "*.webp", "*.bmp",
    "*.tiff", "*.tif", "*.woff", "*.woff2", "*.ttf", "*.eot", "*.otf",
    "*.mp3", "*.mp4", "*.avi", "*.mov", "*.wmv", "*.flv", "*.webm",
    "*.zip", "*.tar", "*.gz", "*.rar", "*.7z",
    "*.psd", "*.ai", "*.eps", "*.sketch", "*.fig", "*.xd",
    "*.blend", "*.obj", "*.fbx", "*.dae", "*.3ds",
    "*.pdf", "*.doc", "*.docx", "*.xls", "*.xlsx", "*.ppt", "*.pptx",
    # Common data formats
    "*.spec.*", "*.test.*", "*.csv", "*.tsv", "*.xml", "*.yaml", "*.yml",
    "*.htm", "*.html", "*.css", ".sql", "*.md", "*.markdown", ".rst",
    "*.json", "*.jsonc", "package.json", "**/package.json",
    # Common config files
    ".editorconfig", ".gitattributes", ".gitmodules",
    "tsconfig.json", "tsconfig.*.json",
})

FILES_TO_ALWAYS_CHECK = frozenset({
    "README.md", ".env.example", "docker-compose.yml", "docker-compose.yaml",
    "Dockerfile", "requirements.txt", "pyproject.toml", "go.mod", "go.sum",
    "Cargo.toml"
})

FILES_TO_ALWAYS_SKIP = frozenset({
    ".gitignore", "pnpm-lock.yaml", "package.json", "tsconfig.json",
    ".eslintrc.js", ".prettierrc.js", ".env", ".tap", "bun.lock", "LICENSE",
    "eslint.config.js", ".prettierrc", ".prettierignore", "package-lock.json",
    "worker-configuration.d.ts"
})

LANGUAGE_HINTS = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "jsx", ".tsx": "tsx", ".java": "java", ".kt": "kotlin",
    ".cs": "csharp", ".go": "go", ".rs": "rust", ".c": "c", ".cpp": "cpp",
    ".h": "c", ".hpp": "cpp", ".rb": "ruby", ".php": "php",
    ".swift": "swift", ".scala": "scala", ".html": "html", ".htm": "html",
    ".css": "css", ".scss": "scss", ".sass": "sass", ".json": "json",
    ".jsonc": "jsonc", ".yaml": "yaml", ".yml": "yaml", ".xml": "xml",
    ".sh": "bash", ".bash": "bash", ".zsh": "zsh", ".fish": "fish",
    ".sql": "sql", ".md": "markdown", ".markdown": "markdown", ".rst": "rst",
    ".dockerfile": "dockerfile", "Dockerfile": "dockerfile",
    ".toml": "toml", ".ini": "ini", ".cfg": "ini", ".conf": "ini",
    ".env": "env", ".env.example": "env", ".tf": "terraform",
    ".tfvars": "terraform"
}

# Tree display constants
GLYPH_CHILD = "├──"
GLYPH_LAST = "└──"
GLYPH_INDENT_CHILD = "│"
GLYPH_INDENT_LAST = " "
BLOCK_CHAR = "🔲"
MAX_BLOCKS = 10


# ============================================================================
# DATA MODELS
# ============================================================================

class GitMode(Enum):
    """Git handling modes."""
    NONE = "none"           # Ignore git completely
    GITIGNORE_ONLY = "gitignore"  # Use .gitignore only
    FULL = "full"           # Use both .gitignore and tracking


@dataclass(frozen=True)
class ScanConfig:
    """Immutable configuration for scanning and filtering."""
    root_dir: Path
    git_mode: GitMode
    include_binary: bool
    max_size_bytes: Optional[int]
    max_depth: Optional[int]
    sort_alphabetically: bool
    is_targeted_directory: bool
    include_only_mode: bool
    
    # Pattern collections
    excluded_dirs: Set[str] = field(default_factory=lambda: set(DEFAULT_EXCLUDED_DIRS))
    excluded_patterns: Set[str] = field(default_factory=set)
    included_patterns: Set[str] = field(default_factory=set)
    
    # File type overrides
    type_overrides: Dict[str, bool] = field(default_factory=dict)


@dataclass
class FileResult:
    """Represents a single file that has been successfully processed."""
    relative_path: Path
    absolute_path: Path
    content: str
    size_bytes: int
    line_count: int
    char_count: int
    language_hint: str
    percentage: float = 0.0  # Will be calculated later


@dataclass(frozen=True)
class FileStats:
    """Statistics for a file in the tree."""
    lines: int
    chars: int
    percentage: float


@dataclass
class TreeNode:
    """Represents a node in the file tree structure."""
    name: str
    path: Path
    is_directory: bool
    is_included: bool
    children: List['TreeNode'] = field(default_factory=list)
    file_stats: Optional[FileStats] = None


@dataclass
class ProjectAnalysis:
    """Complete analysis results for the project."""
    config: ScanConfig
    total_scanned: int
    included_files: List[FileResult]  # Already sorted
    tree_structure: List[TreeNode]
    tech_stack: Set[str]
    key_directories: List[str]
    execution_time: float


# ============================================================================
# FILTER RULES (Strategy Pattern)
# ============================================================================

class FilterRule(ABC):
    """Abstract base class for file filter rules."""
    
    @abstractmethod
    def passes(self, path: Path, config: ScanConfig) -> Tuple[bool, str]:
        """Check if a path passes this rule.
        Returns (passes, reason_if_fails)"""
        pass


class AlwaysSkipRule(FilterRule):
    """Rule to skip hardcoded files."""
    
    def passes(self, path: Path, config: ScanConfig) -> Tuple[bool, str]:
        if path.name in FILES_TO_ALWAYS_SKIP:
            return False, f"Always skipped file: {path.name}"
        return True, ""


class DirectoryExcludeRule(FilterRule):
    """Rule to exclude files in excluded directories."""
    
    def passes(self, path: Path, config: ScanConfig) -> Tuple[bool, str]:
        try:
            rel_parts = path.relative_to(config.root_dir).parts
            for part in rel_parts[:-1]:  # Check parent directories
                if part in config.excluded_dirs:
                    return False, f"In excluded directory: {part}"
                # Check patterns against directory parts
                for pattern in config.excluded_patterns:
                    if fnmatch.fnmatch(part, pattern):
                        return False, f"Directory matches exclude pattern: {pattern}"
        except ValueError:
            return False, "Path not relative to root"
        return True, ""


class PatternRule(FilterRule):
    """Rule for include/exclude patterns."""
    
    def passes(self, path: Path, config: ScanConfig) -> Tuple[bool, str]:
        filename = path.name
        rel_path = str(path.relative_to(config.root_dir)).replace(os.sep, '/')
        
        # Check exclude patterns
        for pattern in config.excluded_patterns:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(rel_path, pattern):
                return False, f"Matches exclude pattern: {pattern}"
        
        # Include-only mode
        if config.include_only_mode and config.included_patterns:
            for pattern in config.included_patterns:
                if (fnmatch.fnmatch(filename, pattern) or 
                    fnmatch.fnmatch(rel_path, pattern) or
                    ("**/" in pattern and pattern.endswith(filename))):
                    return True, ""
            return False, "Include-only mode: doesn't match any include pattern"
        
        return True, ""


class SizeRule(FilterRule):
    """Rule to check file size limits."""
    
    def passes(self, path: Path, config: ScanConfig) -> Tuple[bool, str]:
        if config.max_size_bytes is None:
            return True, ""
        
        try:
            size = path.stat().st_size
            if size > config.max_size_bytes:
                return False, f"File too large: {size} > {config.max_size_bytes}"
        except OSError:
            return False, "Cannot stat file"
        
        return True, ""


class BinaryRule(FilterRule):
    """Rule to exclude binary files."""
    
    def passes(self, path: Path, config: ScanConfig) -> Tuple[bool, str]:
        if config.include_binary:
            return True, ""
        
        try:
            with open(path, 'rb') as f:
                chunk = f.read(1024)
                if b'\x00' in chunk:
                    return False, "Binary file detected"
        except Exception:
            return False, "Cannot read file for binary check"
        
        return True, ""


class DefaultPatternRule(FilterRule):
    """Rule for default excluded patterns with overrides."""
    
    def passes(self, path: Path, config: ScanConfig) -> Tuple[bool, str]:
        filename = path.name
        suffix = path.suffix.lower()
        
        # Check if file should always be included
        if filename in FILES_TO_ALWAYS_CHECK:
            return True, ""
        
        # Check if type is overridden
        if suffix in config.type_overrides and config.type_overrides[suffix]:
            return True, ""
        
        # Check default exclusions
        for pattern in DEFAULT_EXCLUDED_PATTERNS:
            if fnmatch.fnmatch(filename, pattern):
                # Check if explicitly included
                rel_path = str(path.relative_to(config.root_dir)).replace(os.sep, '/')
                for inc_pattern in config.included_patterns:
                    if (fnmatch.fnmatch(filename, inc_pattern) or
                        fnmatch.fnmatch(rel_path, inc_pattern)):
                        return True, ""
                return False, f"Matches default exclude pattern: {pattern}"
        
        return True, ""


class GitignoreRule(FilterRule):
    """Rule to handle .gitignore exclusions."""
    
    def __init__(self, gitignore_matcher: Optional[Callable] = None):
        self.gitignore_matcher = gitignore_matcher
    
    def passes(self, path: Path, config: ScanConfig) -> Tuple[bool, str]:
        if not self.gitignore_matcher or config.git_mode == GitMode.NONE:
            return True, ""
        
        if self.gitignore_matcher(path):
            # Check if explicitly included despite gitignore
            filename = path.name
            rel_path = str(path.relative_to(config.root_dir)).replace(os.sep, '/')
            for pattern in config.included_patterns:
                if (fnmatch.fnmatch(filename, pattern) or
                    fnmatch.fnmatch(rel_path, pattern)):
                    return True, ""
            return False, "Matched .gitignore pattern"
        
        return True, ""


class GitTrackingRule(FilterRule):
    """Rule to check git tracking status."""
    
    def __init__(self, tracked_files: Optional[Set[str]] = None):
        self.tracked_files = tracked_files
    
    def passes(self, path: Path, config: ScanConfig) -> Tuple[bool, str]:
        if not self.tracked_files or config.git_mode != GitMode.FULL:
            return True, ""
        
        rel_path = str(path.relative_to(config.root_dir)).replace(os.sep, '/')
        if rel_path not in self.tracked_files:
            # Check if explicitly included or always check
            if path.name in FILES_TO_ALWAYS_CHECK:
                return True, ""
            for pattern in config.included_patterns:
                if (fnmatch.fnmatch(path.name, pattern) or
                    fnmatch.fnmatch(rel_path, pattern)):
                    return True, ""
            return False, "Not tracked by git"
        
        return True, ""


# ============================================================================
# CONFIGURATION FACTORY
# ============================================================================

class ConfigFactory:
    """Factory for creating ScanConfig from command-line arguments."""
    
    @staticmethod
    def from_args(args: argparse.Namespace) -> ScanConfig:
        """Create configuration from parsed arguments."""
        root_dir = args.root_dir.resolve()
        
        # Determine git mode
        git_mode = ConfigFactory._determine_git_mode(args)
        
        # Detect if targeted directory
        is_targeted = ConfigFactory._is_targeted_directory(root_dir)
        
        # Auto-detect markdown inclusion
        auto_include_markdown = ConfigFactory._should_auto_include_markdown(
            root_dir, args
        )
        
        # Build pattern sets
        excluded_dirs = set(DEFAULT_EXCLUDED_DIRS)
        excluded_patterns = set(args.exclude or [])
        included_patterns = set(args.include or [])
        
        # Add extension patterns
        for ext in (args.exclude_extension or []):
            ext = ext if ext.startswith('.') else '.' + ext
            excluded_patterns.add(f"*{ext}")
        
        for ext in (args.include_extension or []):
            ext = ext if ext.startswith('.') else '.' + ext
            included_patterns.add(f"*{ext}")
        
        # Build type overrides
        type_overrides = ConfigFactory._build_type_overrides(
            args, is_targeted, auto_include_markdown
        )
        
        # Parse max size
        max_size = ConfigFactory._parse_size(args.max_size)
        
        return ScanConfig(
            root_dir=root_dir,
            git_mode=git_mode,
            include_binary=args.include_binary,
            max_size_bytes=max_size,
            max_depth=getattr(args, 'max_depth', None),
            sort_alphabetically=getattr(args, 'sort_alpha', False),
            is_targeted_directory=is_targeted,
            include_only_mode=args.include_only,
            excluded_dirs=excluded_dirs,
            excluded_patterns=excluded_patterns,
            included_patterns=included_patterns,
            type_overrides=type_overrides
        )
    
    @staticmethod
    def _determine_git_mode(args: argparse.Namespace) -> GitMode:
        """Determine git handling mode from arguments."""
        if args.no_gitignore:
            return GitMode.NONE
        elif args.gitignore_only:
            return GitMode.GITIGNORE_ONLY
        elif args.use_git:
            return GitMode.FULL
        else:
            return GitMode.NONE  # Default
    
    @staticmethod
    def _is_targeted_directory(root_dir: Path) -> bool:
        """Check if targeting a specific subdirectory."""
        try:
            cwd = Path.cwd()
            if root_dir != cwd and root_dir.exists() and root_dir.is_dir():
                try:
                    root_dir.relative_to(cwd)
                    return True
                except ValueError:
                    return True
        except Exception:
            pass
        return False
    
    @staticmethod
    def _should_auto_include_markdown(root_dir: Path, 
                                     args: argparse.Namespace) -> bool:
        """Detect if markdown should be auto-included."""
        if args.include_markdown or args.no_gitignore:
            return False
        
        dir_name = root_dir.name.lower()
        doc_indicators = ['docs', 'documentation', 'doc', 'guide', 
                         'manual', 'readme', 'wiki', 'help']
        
        if any(indicator in dir_name for indicator in doc_indicators):
            return True
        
        # Sample files to check composition
        try:
            total_files = 0
            md_files = 0
            for item in root_dir.rglob("*"):
                if item.is_file():
                    total_files += 1
                    if item.suffix.lower() in ('.md', '.markdown', '.rst'):
                        md_files += 1
                    if total_files >= 100:
                        break
            
            if total_files > 0 and (md_files / total_files) > 0.5:
                return True
        except Exception:
            pass
        
        return False
    
    @staticmethod
    def _build_type_overrides(args: argparse.Namespace,
                             is_targeted: bool,
                             auto_include_markdown: bool) -> Dict[str, bool]:
        """Build file type override mappings."""
        overrides = {
            ".json": args.include_json or is_targeted,
            ".jsonc": args.include_json or is_targeted,
            ".yaml": args.include_yaml or is_targeted,
            ".yml": args.include_yaml or is_targeted,
            ".xml": args.include_xml,
            ".html": args.include_html,
            ".htm": args.include_html,
            ".css": args.include_css,
            ".sql": args.include_sql,
            ".csv": args.include_csv,
            ".tsv": args.include_csv,
            ".md": args.include_markdown or auto_include_markdown or is_targeted,
            ".markdown": args.include_markdown or auto_include_markdown or is_targeted,
            ".rst": args.include_markdown or auto_include_markdown or is_targeted,
        }
        
        # Add more for targeted directories
        if is_targeted:
            targeted_extensions = [
                ".txt", ".log", ".sh", ".bash", ".zsh", ".fish",
                ".ps1", ".bat", ".cmd", ".ini", ".cfg", ".conf",
                ".properties", ".toml", ".lock"
            ]
            for ext in targeted_extensions:
                overrides[ext] = True
        
        return overrides
    
    @staticmethod
    def _parse_size(size_str: str) -> Optional[int]:
        """Parse size string to bytes."""
        size_str = size_str.lower().strip()
        if not size_str or size_str == '0':
            return None
        
        try:
            if size_str.endswith('g'):
                return int(size_str[:-1]) * 1024**3
            elif size_str.endswith('m'):
                return int(size_str[:-1]) * 1024**2
            elif size_str.endswith('k'):
                return int(size_str[:-1]) * 1024
            elif size_str.isdigit():
                return int(size_str)
            else:
                logging.warning(f"Invalid size format: {size_str}")
                return None
        except (ValueError, TypeError):
            logging.warning(f"Invalid size: {size_str}")
            return None


# ============================================================================
# GIT UTILITIES
# ============================================================================

def load_gitignore_matcher(root_dir: Path) -> Optional[Callable]:
    """Load .gitignore matcher if available."""
    if not GITIGNORE_PARSER_AVAILABLE:
        logging.warning("gitignore-parser not installed")
        return None
    
    gitignore_path = root_dir / ".gitignore"
    if not gitignore_path.is_file():
        return None
    
    try:
        return gitignore_parser.parse_gitignore(gitignore_path)
    except Exception as e:
        logging.warning(f"Could not parse .gitignore: {e}")
        return None


def get_git_tracked_files(root_dir: Path) -> Optional[Set[str]]:
    """Get set of git-tracked file paths."""
    try:
        # Check if in git repo
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(root_dir),
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0 or result.stdout.strip() != "true":
            return None
        
        # Get tracked files
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=str(root_dir),
            capture_output=True,
            text=True,
            check=True
        )
        return {line.strip().replace('\\', '/') 
               for line in result.stdout.splitlines() if line.strip()}
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        logging.warning(f"Could not get git tracked files: {e}")
        return None


# ============================================================================
# FILE FILTERING
# ============================================================================

class FileFilter:
    """Composite filter using multiple rules."""
    
    def __init__(self, config: ScanConfig, 
                 gitignore_matcher: Optional[Callable] = None,
                 tracked_files: Optional[Set[str]] = None):
        self.config = config
        self.rules: List[FilterRule] = []
        self._initialize_rules(gitignore_matcher, tracked_files)
    
    def _initialize_rules(self, gitignore_matcher: Optional[Callable],
                         tracked_files: Optional[Set[str]]):
        """Set up filter rules based on configuration."""
        # Always apply these rules first
        self.rules.append(AlwaysSkipRule())
        self.rules.append(DirectoryExcludeRule())
        
        # Git-related rules
        if gitignore_matcher and self.config.git_mode in [GitMode.GITIGNORE_ONLY, GitMode.FULL]:
            self.rules.append(GitignoreRule(gitignore_matcher))
        
        if tracked_files is not None and self.config.git_mode == GitMode.FULL:
            self.rules.append(GitTrackingRule(tracked_files))
        
        # Pattern-based rules
        self.rules.append(PatternRule())
        
        # Size and binary checks
        self.rules.append(SizeRule())
        self.rules.append(BinaryRule())
        
        # Default pattern exclusions
        self.rules.append(DefaultPatternRule())
    
    def should_include(self, path: Path) -> Tuple[bool, str]:
        """Check if a file should be included."""
        for rule in self.rules:
            passes, reason = rule.passes(path, self.config)
            if not passes:
                return False, reason
        return True, "Passed all filters"


# ============================================================================
# FILE DISCOVERY & READING
# ============================================================================

class ProjectScanner:
    """Scans the project directory and yields filtered paths."""
    
    def __init__(self, config: ScanConfig, file_filter: FileFilter):
        self.config = config
        self.filter = file_filter
        self.scan_count = 0
    
    def scan(self) -> List[Path]:
        """Scan directory and return list of included file paths."""
        included_paths = []
        
        for item in self.config.root_dir.rglob("*"):
            self.scan_count += 1
            
            if item.is_symlink():
                continue
            
            # Check max depth
            if self.config.max_depth is not None:
                try:
                    rel_path = item.relative_to(self.config.root_dir)
                    if len(rel_path.parts) > self.config.max_depth:
                        continue
                except ValueError:
                    continue
            
            if item.is_file():
                should_include, reason = self.filter.should_include(item)
                if should_include:
                    included_paths.append(item)
                else:
                    logging.debug(f"Excluded {item}: {reason}")
        
        return included_paths


class ContentReader:
    """Reads file contents and creates FileResult objects."""
    
    @staticmethod
    def read_files(paths: List[Path], root_dir: Path) -> List[FileResult]:
        """Read content from list of paths."""
        results = []
        
        for path in paths:
            try:
                content = path.read_text(encoding='utf-8', errors='ignore')
                lines = content.count('\n') + 1 if content else 0
                chars = len(content)
                
                language_hint = ContentReader._get_language_hint(path.name)
                
                results.append(FileResult(
                    relative_path=path.relative_to(root_dir),
                    absolute_path=path,
                    content=content,
                    size_bytes=path.stat().st_size,
                    line_count=lines,
                    char_count=chars,
                    language_hint=language_hint
                ))
            except Exception as e:
                logging.warning(f"Could not read {path}: {e}")
                # Add placeholder for failed reads
                results.append(FileResult(
                    relative_path=path.relative_to(root_dir),
                    absolute_path=path,
                    content=f"# Error reading file: {e}",
                    size_bytes=0,
                    line_count=0,
                    char_count=0,
                    language_hint='plaintext'
                ))
        
        return results
    
    @staticmethod
    def _get_language_hint(filename: str) -> str:
        """Get language hint for syntax highlighting."""
        name = Path(filename).name
        suffix = Path(filename).suffix.lower()
        if name == "Dockerfile":
            return LANGUAGE_HINTS.get(name, "")
        return LANGUAGE_HINTS.get(suffix, "")


# ============================================================================
# PROJECT ANALYSIS
# ============================================================================

class ProjectAnalyzer:
    """Analyzes project structure and content."""
    
    def analyze(self, files: List[FileResult], config: ScanConfig,
                scan_count: int, scan_time: float) -> ProjectAnalysis:
        """Perform complete project analysis."""
        # Calculate percentages
        total_chars = sum(f.char_count for f in files)
        for file in files:
            file.percentage = (file.char_count / total_chars * 100) if total_chars > 0 else 0
        
        # Sort files
        sorted_files = self._sort_files(files, config)
        
        # Detect tech stack
        tech_stack = self._detect_tech_stack(sorted_files)
        
        # Find key directories
        key_dirs = self._find_key_directories(sorted_files)
        
        # Build tree structure
        tree = self._build_tree(sorted_files, config)
        
        return ProjectAnalysis(
            config=config,
            total_scanned=scan_count,
            included_files=sorted_files,
            tree_structure=tree,
            tech_stack=tech_stack,
            key_directories=key_dirs,
            execution_time=scan_time
        )
    
    def _sort_files(self, files: List[FileResult], 
                   config: ScanConfig) -> List[FileResult]:
        """Sort files using intelligent prioritization."""
        if config.sort_alphabetically:
            return self._sort_alphabetically(files)
        
        # Check for numbered files
        numbered_count = sum(1 for f in files 
                           if re.match(r'^\d+_', f.relative_path.name))
        if numbered_count > len(files) / 2:
            return self._sort_numerically(files)
        
        return self._sort_by_relevance(files, config)
    
    def _sort_alphabetically(self, files: List[FileResult]) -> List[FileResult]:
        """Sort files alphabetically."""
        return sorted(files, key=lambda f: f.relative_path.name.lower())
    
    def _sort_numerically(self, files: List[FileResult]) -> List[FileResult]:
        """Sort files with numerical prefixes."""
        def sort_key(file: FileResult):
            match = re.match(r'^(\d+)_', file.relative_path.name)
            if match:
                return (0, int(match.group(1)), file.relative_path.name.lower())
            return (1, 0, file.relative_path.name.lower())
        
        return sorted(files, key=sort_key)
    
    def _calculate_file_relevance_score(self, file: FileResult) -> float:
        """Calculate relevance score for a file."""
        score = 0.0
        name = file.relative_path.name.lower()
        ext = file.relative_path.suffix.lower()
        path_parts = file.relative_path.parts
        
        # Base category scores (higher is more important)
        if name == 'readme.md':
            score += 1000
        elif name in ['package.json', 'pyproject.toml', 'cargo.toml', 'go.mod']:
            score += 900
        elif name in ['main.tsx', 'main.ts', 'main.js', 'main.py', 'main.go', 'main.rs']:
            score += 800
        elif name in ['app.tsx', 'app.ts', 'app.js', 'app.py', 'app.go', 'app.rs']:
            score += 750
        elif name in ['index.tsx', 'index.ts', 'index.js', 'index.py']:
            score += 700
        elif 'main' in name or 'app' in name or 'index' in name:
            score += 600
        
        # File type priority
        type_scores = {
            '.tsx': 100, '.ts': 95, '.jsx': 90, '.js': 85,
            '.py': 80, '.go': 75, '.rs': 70, '.java': 65,
            '.kt': 60, '.swift': 55, '.rb': 50, '.php': 45,
            '.c': 40, '.cpp': 35, '.h': 30, '.hpp': 25
        }
        score += type_scores.get(ext, 0)
        
        # Special filename bonuses
        special_names = {
            'dockerfile': 50, 'docker-compose.yml': 50,
            'makefile': 40, 'rakefile': 40, 'gemfile': 40,
            'requirements.txt': 45, 'setup.py': 45, 'setup.cfg': 40
        }
        score += special_names.get(name, 0)
        
        # Directory depth penalty (prefer files closer to root)
        depth = len(path_parts) - 1
        score -= depth * 10
        
        # Content-based bonuses
        if ext in ['.tsx', '.ts', '.jsx', '.js']:
            content_lower = file.content.lower()
            if any(kw in content_lower for kw in ['react.fc', 'usestate', 'useeffect']):
                score += 50
            if 'export default' in content_lower:
                score += 30
            if any(kw in content_lower for kw in ['function', 'class', 'const']):
                score += 20
        
        elif ext == '.py':
            content_lower = file.content.lower()
            if any(kw in content_lower for kw in ['def main', 'if __name__']):
                score += 50
            if any(kw in content_lower for kw in ['class ', 'def ']):
                score += 30
        
        # Size factor (moderate preference for substantial files)
        if 50 <= file.line_count <= 500:
            score += 20
        elif 10 <= file.line_count < 50:
            score += 10
        elif file.line_count > 500:
            score -= 10  # Very long files get slight penalty
        
        # Directory context bonuses
        if any(part in ['src', 'lib', 'app', 'components'] for part in path_parts):
            score += 25
        elif any(part in ['test', 'tests', '__tests__'] for part in path_parts):
            score -= 50  # Tests are less relevant for context
        
        return score
    
    def _sort_by_relevance(self, files: List[FileResult], 
                          config: ScanConfig) -> List[FileResult]:
        """Sort files by calculated relevance score."""
        # Calculate scores and sort
        scored_files = [(self._calculate_file_relevance_score(f), f) for f in files]
        scored_files.sort(key=lambda x: (-x[0], x[1].relative_path.name.lower()))
        
        return [f for _, f in scored_files]
    
    def _detect_tech_stack(self, files: List[FileResult]) -> Set[str]:
        """Detect technology stack from files."""
        tech_stack = set()
        
        for file in files:
            suffix = file.relative_path.suffix.lower()
            
            if suffix in ['.tsx', '.ts']:
                tech_stack.add('TypeScript')
            elif suffix in ['.jsx', '.js']:
                tech_stack.add('JavaScript')
            elif suffix == '.py':
                tech_stack.add('Python')
            elif suffix == '.go':
                tech_stack.add('Go')
            elif suffix == '.rs':
                tech_stack.add('Rust')
            elif suffix == '.java':
                tech_stack.add('Java')
            elif suffix == '.kt':
                tech_stack.add('Kotlin')
            elif suffix == '.cs':
                tech_stack.add('C#')
            elif suffix == '.rb':
                tech_stack.add('Ruby')
            elif suffix == '.php':
                tech_stack.add('PHP')
        
        return tech_stack
    
    def _find_key_directories(self, files: List[FileResult]) -> List[str]:
        """Find directories with most files."""
        dir_counts = defaultdict(int)
        
        for file in files:
            parent = str(file.relative_path.parent)
            if parent != '.':
                dir_counts[parent] += 1
        
        sorted_dirs = sorted(dir_counts.items(), key=lambda x: x[1], reverse=True)
        return [dir_name for dir_name, _ in sorted_dirs[:10]]
    
    def _build_tree(self, files: List[FileResult], 
                   config: ScanConfig) -> List[TreeNode]:
        """Build tree structure from files without filesystem I/O."""
        file_map = {f.relative_path: f for f in files}
        tree_dict = {}  # Nested dictionary to represent the tree

        # Get all unique paths (both files and their parent directories)
        all_paths = set(file_map.keys())
        for path in list(all_paths):
            for parent in path.parents:
                if parent != Path('.'):
                    all_paths.add(parent)

        # Build nested dictionary structure
        for path in sorted(all_paths):
            current_level = tree_dict
            for part in path.parts:
                current_level = current_level.setdefault(part, {})
        
        # Convert nested dictionary to TreeNode objects
        def convert_dict_to_nodes(d: dict, current_path: Path) -> List[TreeNode]:
            nodes = []
            for name, children_dict in sorted(d.items()):
                path = current_path / name
                is_dir = bool(children_dict)
                
                if is_dir:
                    children = convert_dict_to_nodes(children_dict, path)
                    is_included = any(c.is_included for c in children)
                    node = TreeNode(
                        name=name, 
                        path=path, 
                        is_directory=True,
                        is_included=is_included, 
                        children=children
                    )
                else:
                    is_included = path in file_map
                    file_stats = None
                    if is_included:
                        f = file_map[path]
                        file_stats = FileStats(
                            lines=f.line_count,
                            chars=f.char_count,
                            percentage=f.percentage
                        )
                    node = TreeNode(
                        name=name, 
                        path=path, 
                        is_directory=False,
                        is_included=is_included, 
                        file_stats=file_stats
                    )
                nodes.append(node)
            return nodes

        return convert_dict_to_nodes(tree_dict, Path())


# ============================================================================
# OUTPUT FORMATTING
# ============================================================================

class MarkdownFormatter:
    """Formats project analysis as Markdown."""
    
    def format_summary(self, analysis: ProjectAnalysis) -> str:
        """Format summary with tree and statistics."""
        lines = []
        lines.append("# 📁 Project Structure & Statistics")
        lines.append(f"*Directory: {self._format_path(analysis.config.root_dir)}*")
        lines.append("")
        
        # Quick overview
        lines.append("## 🎯 Quick Overview")
        tech_str = ', '.join(analysis.tech_stack) if analysis.tech_stack else 'Unknown'
        lines.append(f"*{tech_str} project with {len(analysis.included_files):,} source files*")
        lines.append("")
        
        # Legend
        lines.append(f"Legend: ✅=Included, ❌=Excluded, {BLOCK_CHAR}=% Size (Max {MAX_BLOCKS})")
        lines.append("")
        
        # Tree
        lines.append("## 🏗️ Project Tree & Statistics")
        lines.append("```")
        lines.append(self._format_tree_with_blocks(analysis))
        lines.append("```")
        lines.append("")
        
        # Statistics
        total_lines = sum(f.line_count for f in analysis.included_files)
        total_chars = sum(f.char_count for f in analysis.included_files)
        
        lines.append("## 📊 Summary Statistics")
        lines.append(f"*   **Total Files:** {len(analysis.included_files):,} of {analysis.total_scanned:,} scanned")
        lines.append(f"*   **Total Lines:** {total_lines:,}")
        lines.append(f"*   **Total Characters:** {total_chars:,} ({total_chars/1024:.1f} kB)")
        lines.append("")
        
        # Insights
        lines.append("## 🔍 Key Insights")
        if analysis.tech_stack:
            lines.append(f"- **Technology Stack:** {', '.join(analysis.tech_stack)}")
        if analysis.key_directories:
            lines.append(f"- **Key Directories:** {', '.join(analysis.key_directories[:5])}")
        lines.append("")
        
        return "\n".join(lines)
    
    def format_full(self, analysis: ProjectAnalysis) -> str:
        """Format complete output with file contents."""
        lines = []
        
        # Header
        lines.append("# 📁 Project Context & Codebase Analysis")
        lines.append(f"*Project Directory: `{self._format_path(analysis.config.root_dir)}`*")
        lines.append("")
        
        # Overview
        total_lines = sum(f.line_count for f in analysis.included_files)
        total_chars = sum(f.char_count for f in analysis.included_files)
        tech_str = ', '.join(analysis.tech_stack) if analysis.tech_stack else 'Unknown'
        
        lines.append("## 🎯 Project Overview")
        lines.append(f"*This is a **{tech_str}** project with **{len(analysis.included_files):,} source files** and **{total_lines:,} lines of code**.*")
        lines.append("")
        
        # Quick stats
        lines.append("### 📊 Quick Stats")
        lines.append(f"- **Files:** {len(analysis.included_files):,}")
        lines.append(f"- **Lines:** {total_lines:,}")
        lines.append(f"- **Size:** ~{total_chars/1024:.1f} kB")
        lines.append(f"- **Scanned:** {analysis.total_scanned:,} items")
        lines.append("")
        
        # Tree (without blocks for clean output)
        lines.append("### 🏗️ Project Structure")
        lines.append("```")
        lines.append(self._format_tree_plain(analysis))
        lines.append("```")
        lines.append("")
        
        # Insights
        lines.append("### 🔍 Key Insights")
        if analysis.tech_stack:
            lines.append(f"- **Technology Stack:** {', '.join(analysis.tech_stack)}")
        if analysis.key_directories:
            lines.append(f"- **Key Directories:** {', '.join(analysis.key_directories[:5])}")
        lines.append("")
        
        # Content section
        lines.append("---")
        lines.append("")
        lines.append("## 📄 Source Code & Configuration Files")
        lines.append("")
        lines.append("*Files are organized by importance and relevance.*")
        lines.append("")
        
        # Add file contents
        for file in analysis.included_files:
            # Generate header based on file type
            header = self._get_file_header(file)
            lines.append(header)
            lines.append(f"**File Info:** {file.line_count:,} lines • {file.char_count:,} chars • ~{file.percentage:.2f}% of codebase")
            if file.language_hint:
                lines.append(f"**Language:** {file.language_hint}")
            lines.append("")
            lines.append(f"```{file.language_hint}")
            lines.append(file.content)
            lines.append("```")
            lines.append("")
        
        return "\n".join(lines).strip()
    
    def _format_path(self, path: Path) -> str:
        """Format path for display."""
        home = Path.home()
        path_str = str(path)
        if path_str.startswith(str(home)):
            return path_str.replace(str(home), "~", 1)
        return path_str
    
    def _format_tree_with_blocks(self, analysis: ProjectAnalysis) -> str:
        """Format tree with percentage blocks."""
        lines = [". ✅"]  # Root
        self._format_nodes_with_blocks(analysis.tree_structure, lines, "")
        return "\n".join(lines)
    
    def _format_tree_plain(self, analysis: ProjectAnalysis) -> str:
        """Format tree without blocks."""
        lines = [". ✅"]  # Root
        self._format_nodes_plain(analysis.tree_structure, lines, "")
        return "\n".join(lines)
    
    def _format_nodes_with_blocks(self, nodes: List[TreeNode], lines: List[str], 
                                 indent: str):
        """Recursively format nodes with blocks."""
        for i, node in enumerate(nodes):
            is_last = i == len(nodes) - 1
            marker = GLYPH_LAST if is_last else GLYPH_CHILD
            status = "✅" if node.is_included else "❌"
            
            line = f"{indent}{marker} {node.name} {status}"
            
            if not node.is_directory and node.file_stats:
                stats = node.file_stats
                line += f" ({stats.lines:,}L, {stats.chars:,}C) [~{stats.percentage:.2f}%]"
                
                # Add blocks
                if stats.percentage > 0.1:
                    num_blocks = max(1, round(stats.percentage / 100 * MAX_BLOCKS))
                    line += f" {BLOCK_CHAR * num_blocks}"
            
            lines.append(line)
            
            if node.children:
                child_indent = indent + (GLYPH_INDENT_LAST if is_last else GLYPH_INDENT_CHILD) + " "
                self._format_nodes_with_blocks(node.children, lines, child_indent)
    
    def _format_nodes_plain(self, nodes: List[TreeNode], lines: List[str], 
                           indent: str):
        """Recursively format nodes without blocks."""
        for i, node in enumerate(nodes):
            is_last = i == len(nodes) - 1
            marker = GLYPH_LAST if is_last else GLYPH_CHILD
            status = "✅" if node.is_included else "❌"
            
            if not node.is_included and not node.children:
                continue  # Skip excluded files in plain tree
            
            line = f"{indent}{marker} {node.name} {status}"
            
            if not node.is_directory and node.file_stats:
                stats = node.file_stats
                line += f" ({stats.lines:,}L, {stats.chars:,}C) [~{stats.percentage:.2f}%]"
            
            lines.append(line)
            
            if node.children:
                child_indent = indent + (GLYPH_INDENT_LAST if is_last else GLYPH_INDENT_CHILD) + " "
                self._format_nodes_plain(node.children, lines, child_indent)
    
    def _get_file_header(self, file: FileResult) -> str:
        """Generate descriptive header for file."""
        name = file.relative_path.name.lower()
        ext = file.relative_path.suffix.lower()
        
        if name == 'readme.md':
            return f"### 📖 `/{file.relative_path}` - Project Documentation"
        elif ext in ['.tsx', '.ts', '.jsx', '.js']:
            return f"### ⚛️ `/{file.relative_path}` - React/JS Component"
        elif ext == '.py':
            return f"### 🐍 `/{file.relative_path}` - Python Module"
        elif ext == '.go':
            return f"### 🐹 `/{file.relative_path}` - Go Module"
        elif ext == '.rs':
            return f"### 🦀 `/{file.relative_path}` - Rust Module"
        elif ext == '.json':
            return f"### ⚙️ `/{file.relative_path}` - Configuration"
        elif ext == '.md':
            return f"### 📝 `/{file.relative_path}` - Documentation"
        else:
            return f"### 📄 `/{file.relative_path}`"


class JsonFormatter:
    """Formats project analysis as JSON."""
    
    def format(self, analysis: ProjectAnalysis) -> str:
        """Format as JSON."""
        total_lines = sum(f.line_count for f in analysis.included_files)
        total_chars = sum(f.char_count for f in analysis.included_files)
        
        output = {
            "project_info": {
                "root_dir": str(analysis.config.root_dir),
                "total_files": len(analysis.included_files),
                "total_lines": total_lines,
                "total_chars": total_chars,
                "scanned_count": analysis.total_scanned,
                "tech_stack": list(analysis.tech_stack)
            },
            "files": [
                {
                    "path": str(f.relative_path),
                    "lines": f.line_count,
                    "chars": f.char_count,
                    "percentage": f.percentage,
                    "language": f.language_hint
                }
                for f in analysis.included_files
            ]
        }
        
        return json.dumps(output, indent=2)


# ============================================================================
# OUTPUT HANDLING
# ============================================================================

class OutputWriter:
    """Handles writing output to various destinations."""
    
    @staticmethod
    def write(content: str, summary: str, args: argparse.Namespace):
        """Write content to specified destination."""
        written = False
        error = False
        
        # File output
        if args.output:
            try:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(content)
                print(summary, file=sys.stderr)
                print(f"\nSuccess: Written to {args.output}", file=sys.stderr)
                written = True
            except OSError as e:
                print(f"Error writing to file: {e}", file=sys.stderr)
                error = True
        
        # Stdout output
        elif args.stdout:
            try:
                print(content)
                written = True
            except Exception as e:
                print(f"Error writing to stdout: {e}", file=sys.stderr)
                error = True
        
        # Clipboard output (default)
        elif PYPERCLIP_AVAILABLE and not args.no_clipboard:
            try:
                print(summary, file=sys.stderr)
                pyperclip.copy(content)
                print(f"\nSuccess: {len(content):,} chars copied to clipboard", 
                     file=sys.stderr)
                written = True
            except Exception as e:
                print(f"Error copying to clipboard: {e}", file=sys.stderr)
                error = True
        
        # Fallback: print summary only
        if not written:
            print(summary, file=sys.stderr)
        
        if error:
            sys.exit(1)


# ============================================================================
# CLI HANDLING
# ============================================================================

class CliHandler:
    """Handles command-line interface."""
    
    @staticmethod
    def create_parser() -> argparse.ArgumentParser:
        """Create argument parser."""
        parser = argparse.ArgumentParser(
            description="Gather project context into Markdown for LLMs",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        
        # Input/Output
        parser.add_argument("root_dir", nargs="?", type=Path, default=Path("."),
                          help="Root project directory")
        parser.add_argument("-o", "--output", type=Path,
                          help="Output file path")
        parser.add_argument("--stdout", action="store_true",
                          help="Print to stdout")
        parser.add_argument("--no-clipboard", action="store_true",
                          help="Don't copy to clipboard")
        
        # Filtering
        parser.add_argument("--exclude", action="append", metavar="PATTERN",
                          help="Glob pattern to exclude")
        parser.add_argument("--include", action="append", metavar="PATTERN",
                          help="Glob pattern to include")
        parser.add_argument("--include-only", action="store_true",
                          help="Include ONLY matching patterns")
        parser.add_argument("--exclude-extension", action="append", metavar="EXT",
                          help="File extension to exclude")
        parser.add_argument("--include-extension", action="append", metavar="EXT",
                          help="File extension to include")
        parser.add_argument("--max-size", default="2M",
                          help="Max file size (e.g., 500k, 10M)")
        parser.add_argument("--include-binary", action="store_true",
                          help="Include binary files")
        
        # Git handling
        git_group = parser.add_mutually_exclusive_group()
        git_group.add_argument("--no-gitignore", action="store_true",
                             help="Ignore .gitignore and git")
        git_group.add_argument("--gitignore-only", action="store_true",
                             help="Use .gitignore only")
        git_group.add_argument("--use-git", action="store_true",
                             help="Use full git integration")
        
        # Type overrides
        parser.add_argument("--include-json", action="store_true",
                          help="Include JSON files")
        parser.add_argument("--include-yaml", action="store_true",
                          help="Include YAML files")
        parser.add_argument("--include-xml", action="store_true",
                          help="Include XML files")
        parser.add_argument("--include-html", action="store_true",
                          help="Include HTML files")
        parser.add_argument("--include-css", action="store_true",
                          help="Include CSS files")
        parser.add_argument("--include-sql", action="store_true",
                          help="Include SQL files")
        parser.add_argument("--include-csv", action="store_true",
                          help="Include CSV files")
        parser.add_argument("--include-markdown", action="store_true",
                          help="Include Markdown files")
        
        # Features
        parser.add_argument("--preview", action="store_true",
                          help="Preview what would be included")
        parser.add_argument("--dry-run", action="store_true",
                          help="Simulate without output")
        parser.add_argument("--interactive", action="store_true",
                          help="Interactive configuration")
        parser.add_argument("--format", choices=["markdown", "json"],
                          default="markdown", help="Output format")
        parser.add_argument("--max-depth", type=int,
                          help="Maximum directory depth")
        parser.add_argument("--show-stats", action="store_true",
                          help="Show detailed statistics")
        parser.add_argument("--sort-alpha", action="store_true",
                          help="Sort files alphabetically")
        
        return parser


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s',
        stream=sys.stderr
    )
    
    # Parse arguments
    parser = CliHandler.create_parser()
    args = parser.parse_args()
    
    # Validate input
    if not args.root_dir.is_dir():
        logging.error(f"Directory not found: {args.root_dir}")
        sys.exit(1)
    
    try:
        start_time = time.time()
        
        # Create configuration
        config = ConfigFactory.from_args(args)
        
        # Perform I/O for filtering setup
        gitignore_matcher = None
        if config.git_mode in [GitMode.GITIGNORE_ONLY, GitMode.FULL]:
            gitignore_matcher = load_gitignore_matcher(config.root_dir)
            
        tracked_files = None
        if config.git_mode == GitMode.FULL:
            tracked_files = get_git_tracked_files(config.root_dir)
        
        # Set up filtering with I/O results
        file_filter = FileFilter(config, gitignore_matcher, tracked_files)
        
        # Scan for files
        scanner = ProjectScanner(config, file_filter)
        included_paths = scanner.scan()
        
        if not included_paths:
            logging.warning("No files matched the filters")
            if not args.dry_run:
                OutputWriter.write(
                    "# No files included",
                    "# No files matched the filters",
                    args
                )
            return
        
        # Read file contents
        file_results = ContentReader.read_files(included_paths, config.root_dir)
        
        # Analyze project
        analyzer = ProjectAnalyzer()
        analysis = analyzer.analyze(
            file_results, config, scanner.scan_count, time.time() - start_time
        )
        
        # Format output
        if args.format == "json":
            formatter = JsonFormatter()
            content = formatter.format(analysis)
            summary = content  # Use same for JSON
        else:
            formatter = MarkdownFormatter()
            content = formatter.format_full(analysis)
            summary = formatter.format_summary(analysis)
        
        # Handle special modes
        if args.show_stats:
            print(summary, file=sys.stderr)
            return
        
        if args.dry_run:
            print(f"\n🔍 Dry Run Complete!")
            print(f"Would process {len(analysis.included_files)} files")
            print(f"Would generate {len(content):,} characters")
            return
        
        # Write output
        OutputWriter.write(content, summary, args)
        
    except Exception as e:
        logging.critical(f"Critical error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()