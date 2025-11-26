#!/usr/bin/env python3
"""
Context - Project Context Gatherer for LLMs

A clean, well-architected tool to intelligently scan a project directory 
and format its contents for consumption by Large Language Models.

Architecture:
    CLI Args → Configuration → File Discovery → Filtering → 
    Content Reading → Analysis → Formatting → Output
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import logging
import os
import re
import subprocess
import sys
import time
import urllib.request
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    List,
    Optional,
    Set,
    Tuple,
    TYPE_CHECKING,
)

# =============================================================================
# VERSION MANAGEMENT
# =============================================================================

__version__ = "3.0.0"


def get_version() -> str:
    """Get version from package metadata or fallback to hardcoded."""
    try:
        from importlib.metadata import version
        return version("repo-to-llm-context")
    except Exception:
        pass
    
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return __version__
    
    try:
        pyproject = Path(__file__).parent / "pyproject.toml"
        if pyproject.exists():
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
                return data.get("project", {}).get("version", __version__)
    except Exception:
        pass
    
    return __version__


# =============================================================================
# OPTIONAL DEPENDENCIES
# =============================================================================

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

try:
    import gitignore_parser
    HAS_GITIGNORE_PARSER = True
except ImportError:
    HAS_GITIGNORE_PARSER = False


# =============================================================================
# CONSTANTS
# =============================================================================

class Defaults:
    """Default configuration values."""
    MAX_SIZE = "2M"
    MAX_FILE_CHARS = 50000
    OUTPUT_FORMAT = "markdown"
    

class ExcludedDirs:
    """Directories to exclude by default."""
    DIRS: FrozenSet[str] = frozenset({
        # Version control
        ".git", ".svn", ".hg", ".bzr",
        # Dependencies
        "node_modules", "vendor", "bower_components",
        # Virtual environments
        "venv", "env", ".venv", "ENV", "virtualenv", ".virtualenv",
        # Build outputs
        "build", "dist", "target", "out", "bin", "obj", "_build",
        # Cache directories
        "__pycache__", ".cache", "cache", ".pytest_cache", 
        ".mypy_cache", ".tox", ".nox", ".ruff_cache",
        # IDE directories
        ".idea", ".vscode", ".vs",
        # Logs and coverage
        "logs", "log", "coverage", "htmlcov", ".nyc_output",
        # Framework specific
        ".terraform", ".next", ".nuxt", ".svelte-kit",
        # Static assets (usually not code)
        "public", "static", "assets", "images", "img", "icons", 
        "fonts", "media", "uploads", "downloads",
        # Documentation and tests (can be included via flags)
        "docs", "documentation", "tests", "__tests__", "test", "spec",
    })


class ExcludedPatterns:
    """File patterns to exclude by default."""
    PATTERNS: FrozenSet[str] = frozenset({
        # Compiled/binary files
        "*.pyc", "*.pyo", "*.pyd", "*.so", "*.o", "*.a", "*.lib",
        "*.dylib", "*.dll", "*.exe", "*.class", "*.jar", "*.war",
        # Build artifacts
        "*.log", "*.tsbuildinfo", "*.d.ts.map",
        # Editor files
        "*.swp", "*.swo", "*~", "#*#", ".DS_Store", "Thumbs.db",
        # Patches
        "*.patch", "*.diff",
        # Lock files
        "*.lock", "pnpm-lock.yaml", "yarn.lock", "package-lock.json",
        "poetry.lock", "composer.lock", "Gemfile.lock", "bun.lockb",
        # State files  
        "*.tfstate", "*.tfstate.backup",
        # Temp files
        "*.bak", "*.tmp", "*.temp",
        # Minified and maps
        "*.min.js", "*.min.css", "*.map",
        # Media files
        "*.svg", "*.png", "*.jpg", "*.jpeg", "*.gif", "*.ico", "*.webp",
        "*.bmp", "*.tiff", "*.tif", "*.woff", "*.woff2", "*.ttf", 
        "*.eot", "*.otf", "*.mp3", "*.mp4", "*.avi", "*.mov", "*.wmv",
        "*.flv", "*.webm", "*.wav", "*.ogg",
        # Archives
        "*.zip", "*.tar", "*.gz", "*.rar", "*.7z", "*.bz2",
        # Design files
        "*.psd", "*.ai", "*.eps", "*.sketch", "*.fig", "*.xd",
        # 3D files
        "*.blend", "*.obj", "*.fbx", "*.dae", "*.3ds",
        # Documents
        "*.pdf", "*.doc", "*.docx", "*.xls", "*.xlsx", "*.ppt", "*.pptx",
    })

    # Data formats excluded by default (can be included via --include-X flags)
    DATA_PATTERNS: FrozenSet[str] = frozenset({
        "*.json", "*.jsonc", "*.yaml", "*.yml", "*.xml",
        "*.html", "*.htm", "*.css", "*.sql", "*.csv", "*.tsv",
        "*.md", "*.markdown", "*.rst",
    })

    # Config files to skip
    CONFIG_SKIP: FrozenSet[str] = frozenset({
        ".editorconfig", ".gitattributes", ".gitmodules",
        "tsconfig.json", "tsconfig.*.json", "jsconfig.json",
        ".eslintrc*", ".prettierrc*", ".stylelintrc*",
    })


class AlwaysInclude:
    """Files to always consider for inclusion."""
    FILES: FrozenSet[str] = frozenset({
        "README.md", "README.rst", "README.txt", "README",
        ".env.example", ".env.sample",
        "docker-compose.yml", "docker-compose.yaml", "Dockerfile",
        "requirements.txt", "pyproject.toml", "setup.py", "setup.cfg",
        "go.mod", "go.sum", "Cargo.toml", "Cargo.lock",
        "Makefile", "CMakeLists.txt",
    })


class AlwaysSkip:
    """Files to always skip."""
    FILES: FrozenSet[str] = frozenset({
        ".gitignore", ".dockerignore", ".npmignore",
        "package.json", "package-lock.json", "pnpm-lock.yaml",
        "yarn.lock", "bun.lockb",
        ".env", ".env.local", ".env.development", ".env.production",
        "LICENSE", "LICENSE.md", "LICENSE.txt",
        "CHANGELOG.md", "CHANGELOG", "HISTORY.md",
        ".prettierignore", ".eslintignore",
    })


LANGUAGE_HINTS: Dict[str, str] = {
    ".py": "python", ".pyi": "python", ".pyx": "cython",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".mts": "typescript", ".cts": "typescript",
    ".jsx": "jsx", ".tsx": "tsx",
    ".java": "java", ".kt": "kotlin", ".kts": "kotlin",
    ".cs": "csharp", ".fs": "fsharp", ".vb": "vb",
    ".go": "go", ".rs": "rust", ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp",
    ".rb": "ruby", ".php": "php", ".pl": "perl", ".pm": "perl",
    ".swift": "swift", ".scala": "scala", ".clj": "clojure",
    ".html": "html", ".htm": "html", ".vue": "vue", ".svelte": "svelte",
    ".css": "css", ".scss": "scss", ".sass": "sass", ".less": "less",
    ".json": "json", ".jsonc": "jsonc",
    ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
    ".xml": "xml", ".xsl": "xsl", ".xslt": "xslt",
    ".sh": "bash", ".bash": "bash", ".zsh": "zsh", ".fish": "fish",
    ".ps1": "powershell", ".psm1": "powershell",
    ".sql": "sql", ".graphql": "graphql", ".gql": "graphql",
    ".md": "markdown", ".markdown": "markdown", ".rst": "rst",
    ".dockerfile": "dockerfile",
    ".tf": "terraform", ".tfvars": "terraform",
    ".ini": "ini", ".cfg": "ini", ".conf": "ini",
    ".env": "dotenv", ".env.example": "dotenv",
    ".r": "r", ".R": "r",
    ".lua": "lua", ".ex": "elixir", ".exs": "elixir",
    ".erl": "erlang", ".hrl": "erlang",
    ".hs": "haskell", ".ml": "ocaml", ".mli": "ocaml",
    ".nim": "nim", ".zig": "zig", ".v": "v",
    ".dart": "dart", ".groovy": "groovy",
}

# Tree display glyphs
GLYPH_CHILD = "├──"
GLYPH_LAST = "└──"
GLYPH_PIPE = "│   "
GLYPH_SPACE = "    "


# =============================================================================
# ENUMS AND DATA MODELS
# =============================================================================

class GitMode(Enum):
    """Git integration modes."""
    NONE = auto()          # Ignore git completely
    GITIGNORE = auto()     # Use .gitignore only (DEFAULT)
    FULL = auto()          # Use .gitignore + git tracking


class OutputMode(Enum):
    """Output destination modes."""
    CLIPBOARD = auto()
    FILE = auto()
    STDOUT = auto()


@dataclass(frozen=True)
class ScanConfig:
    """Immutable scan configuration."""
    root_dir: Path
    git_mode: GitMode
    output_mode: OutputMode
    output_file: Optional[Path]
    output_format: str
    
    # Size limits
    max_size_bytes: Optional[int]
    max_file_chars: int
    max_depth: Optional[int]
    
    # Behavior flags
    include_binary: bool
    sort_alphabetically: bool
    include_only_mode: bool
    truncate_large_files: bool
    skip_large_files: bool
    
    # Pattern sets
    excluded_dirs: FrozenSet[str]
    excluded_patterns: FrozenSet[str]
    included_patterns: FrozenSet[str]
    
    # Type overrides (extension -> should include)
    type_overrides: Dict[str, bool] = field(default_factory=dict)


@dataclass
class FileInfo:
    """Information about a processed file."""
    relative_path: Path
    absolute_path: Path
    content: str
    size_bytes: int
    line_count: int
    char_count: int
    language: str
    percentage: float = 0.0
    was_truncated: bool = False


@dataclass
class TreeNode:
    """Node in the file tree structure."""
    name: str
    path: Path
    is_dir: bool
    included: bool
    children: List[TreeNode] = field(default_factory=list)
    lines: int = 0
    chars: int = 0
    percentage: float = 0.0


@dataclass
class ScanResult:
    """Complete scan results."""
    config: ScanConfig
    files: List[FileInfo]
    tree: List[TreeNode]
    total_scanned: int
    tech_stack: Set[str]
    key_dirs: List[str]
    duration: float


# =============================================================================
# FILTER RULES (Strategy Pattern)
# =============================================================================

class FilterRule(ABC):
    """Abstract base for file filter rules."""
    
    @abstractmethod
    def check(self, path: Path, config: ScanConfig) -> Tuple[bool, str]:
        """Check if path passes this rule. Returns (passes, reason)."""
        pass


class SkipListRule(FilterRule):
    """Skip hardcoded files."""
    
    def check(self, path: Path, config: ScanConfig) -> Tuple[bool, str]:
        if path.name in AlwaysSkip.FILES:
            return False, f"In skip list: {path.name}"
        return True, ""


class DirectoryRule(FilterRule):
    """Exclude files in excluded directories."""
    
    def check(self, path: Path, config: ScanConfig) -> Tuple[bool, str]:
        try:
            parts = path.relative_to(config.root_dir).parts
            for part in parts[:-1]:
                if part in config.excluded_dirs:
                    return False, f"In excluded dir: {part}"
                for pattern in config.excluded_patterns:
                    if fnmatch.fnmatch(part, pattern):
                        return False, f"Dir matches pattern: {pattern}"
        except ValueError:
            return False, "Path not relative to root"
        return True, ""


class PatternRule(FilterRule):
    """Handle include/exclude glob patterns."""
    
    def check(self, path: Path, config: ScanConfig) -> Tuple[bool, str]:
        name = path.name
        try:
            rel = str(path.relative_to(config.root_dir)).replace(os.sep, "/")
        except ValueError:
            rel = name
        
        # Check excludes first
        for pattern in config.excluded_patterns:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel, pattern):
                return False, f"Matches exclude: {pattern}"
        
        # Include-only mode
        if config.include_only_mode and config.included_patterns:
            for pattern in config.included_patterns:
                if (fnmatch.fnmatch(name, pattern) or 
                    fnmatch.fnmatch(rel, pattern) or
                    fnmatch.fnmatch(f"**/{name}", pattern)):
                    return True, ""
            return False, "No include pattern matched"
        
        return True, ""


class SizeRule(FilterRule):
    """Check file size limits."""
    
    def check(self, path: Path, config: ScanConfig) -> Tuple[bool, str]:
        if config.max_size_bytes is None:
            return True, ""
        try:
            size = path.stat().st_size
            if size > config.max_size_bytes:
                return False, f"Too large: {size:,} > {config.max_size_bytes:,}"
        except OSError:
            return False, "Cannot stat file"
        return True, ""


class BinaryRule(FilterRule):
    """Detect and exclude binary files."""
    
    def check(self, path: Path, config: ScanConfig) -> Tuple[bool, str]:
        if config.include_binary:
            return True, ""
        try:
            with open(path, "rb") as f:
                chunk = f.read(8192)
                if b"\x00" in chunk:
                    return False, "Binary file"
        except Exception:
            return False, "Cannot read file"
        return True, ""


class DefaultPatternRule(FilterRule):
    """Apply default exclusion patterns with overrides."""
    
    def check(self, path: Path, config: ScanConfig) -> Tuple[bool, str]:
        name = path.name
        suffix = path.suffix.lower()
        
        # Always include special files
        if name in AlwaysInclude.FILES:
            return True, ""
        
        # Check type overrides
        if suffix in config.type_overrides:
            if config.type_overrides[suffix]:
                return True, ""
        
        # Check if explicitly included
        try:
            rel = str(path.relative_to(config.root_dir)).replace(os.sep, "/")
        except ValueError:
            rel = name
            
        for pattern in config.included_patterns:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel, pattern):
                return True, ""
        
        # Check default patterns
        for pattern in ExcludedPatterns.PATTERNS:
            if fnmatch.fnmatch(name, pattern):
                return False, f"Default exclude: {pattern}"
        
        # Check data patterns
        for pattern in ExcludedPatterns.DATA_PATTERNS:
            if fnmatch.fnmatch(name, pattern):
                return False, f"Data format excluded: {pattern}"
        
        # Check config skip
        for pattern in ExcludedPatterns.CONFIG_SKIP:
            if fnmatch.fnmatch(name, pattern):
                return False, f"Config file excluded: {pattern}"
        
        return True, ""


class GitignoreRule(FilterRule):
    """Apply .gitignore patterns."""
    
    def __init__(self, matcher: Optional[Callable[[Path], bool]] = None):
        self.matcher = matcher
    
    def check(self, path: Path, config: ScanConfig) -> Tuple[bool, str]:
        if not self.matcher or config.git_mode == GitMode.NONE:
            return True, ""
        
        if self.matcher(path):
            # Check if explicitly included despite gitignore
            name = path.name
            try:
                rel = str(path.relative_to(config.root_dir)).replace(os.sep, "/")
            except ValueError:
                rel = name
            
            for pattern in config.included_patterns:
                if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel, pattern):
                    return True, ""
            return False, "Matched .gitignore"
        return True, ""


class GitTrackingRule(FilterRule):
    """Check if file is tracked by git."""
    
    def __init__(self, tracked: Optional[Set[str]] = None):
        self.tracked = tracked
    
    def check(self, path: Path, config: ScanConfig) -> Tuple[bool, str]:
        if not self.tracked or config.git_mode != GitMode.FULL:
            return True, ""
        
        try:
            rel = str(path.relative_to(config.root_dir)).replace(os.sep, "/")
        except ValueError:
            return False, "Path not relative"
        
        if rel not in self.tracked:
            # Allow special files
            if path.name in AlwaysInclude.FILES:
                return True, ""
            for pattern in config.included_patterns:
                if fnmatch.fnmatch(path.name, pattern):
                    return True, ""
            return False, "Not tracked by git"
        return True, ""


class CharLimitRule(FilterRule):
    """Skip files exceeding character limit."""
    
    def check(self, path: Path, config: ScanConfig) -> Tuple[bool, str]:
        if not config.skip_large_files or not config.max_file_chars:
            return True, ""
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            if len(content) > config.max_file_chars:
                return False, f"Too many chars: {len(content):,}"
        except Exception:
            return False, "Cannot read for char check"
        return True, ""


# =============================================================================
# FILE FILTER COMPOSITE
# =============================================================================

class FileFilter:
    """Composite filter applying multiple rules."""
    
    def __init__(
        self,
        config: ScanConfig,
        gitignore_matcher: Optional[Callable] = None,
        tracked_files: Optional[Set[str]] = None,
    ):
        self.config = config
        self.rules: List[FilterRule] = self._build_rules(
            gitignore_matcher, tracked_files
        )
    
    def _build_rules(
        self,
        gitignore_matcher: Optional[Callable],
        tracked_files: Optional[Set[str]],
    ) -> List[FilterRule]:
        """Build rule chain based on config."""
        rules = [
            SkipListRule(),
            DirectoryRule(),
        ]
        
        # Git rules
        if self.config.git_mode in (GitMode.GITIGNORE, GitMode.FULL):
            rules.append(GitignoreRule(gitignore_matcher))
        
        if self.config.git_mode == GitMode.FULL:
            rules.append(GitTrackingRule(tracked_files))
        
        rules.extend([
            PatternRule(),
            SizeRule(),
            BinaryRule(),
            DefaultPatternRule(),
            CharLimitRule(),
        ])
        
        return rules
    
    def should_include(self, path: Path) -> Tuple[bool, str]:
        """Check if file should be included."""
        for rule in self.rules:
            passes, reason = rule.check(path, self.config)
            if not passes:
                return False, reason
        return True, "Passed all filters"


# =============================================================================
# CONFIGURATION BUILDER
# =============================================================================

class ConfigBuilder:
    """Builds ScanConfig from CLI arguments."""
    
    @staticmethod
    def from_args(args: argparse.Namespace) -> ScanConfig:
        """Create config from parsed arguments."""
        root = Path(args.root_dir).resolve()
        
        # Determine output mode
        if args.output:
            output_mode = OutputMode.FILE
        elif args.stdout:
            output_mode = OutputMode.STDOUT
        elif args.no_clipboard or not HAS_PYPERCLIP:
            output_mode = OutputMode.STDOUT  # Fallback to stdout
        else:
            output_mode = OutputMode.CLIPBOARD
        
        # Git mode - DEFAULT is GITIGNORE (not NONE)
        if args.no_gitignore:
            git_mode = GitMode.NONE
        elif args.use_git:
            git_mode = GitMode.FULL
        else:
            git_mode = GitMode.GITIGNORE  # Default behavior
        
        # Build pattern sets
        excluded_dirs = set(ExcludedDirs.DIRS)
        excluded_patterns: Set[str] = set()
        included_patterns: Set[str] = set()
        
        # Add CLI patterns
        for pattern in (args.exclude or []):
            excluded_patterns.add(pattern)
        
        for pattern in (args.include or []):
            included_patterns.add(pattern)
        
        # Extension patterns
        for ext in (args.exclude_extension or []):
            ext = ext if ext.startswith(".") else f".{ext}"
            excluded_patterns.add(f"*{ext}")
        
        for ext in (args.include_extension or []):
            ext = ext if ext.startswith(".") else f".{ext}"
            included_patterns.add(f"*{ext}")
        
        # Type overrides
        type_overrides = ConfigBuilder._build_type_overrides(args)
        
        # Parse size
        max_size = ConfigBuilder._parse_size(args.max_size)
        
        return ScanConfig(
            root_dir=root,
            git_mode=git_mode,
            output_mode=output_mode,
            output_file=Path(args.output) if args.output else None,
            output_format=args.format,
            max_size_bytes=max_size,
            max_file_chars=args.max_file_chars,
            max_depth=args.max_depth,
            include_binary=args.include_binary,
            sort_alphabetically=args.sort_alpha,
            include_only_mode=args.include_only,
            truncate_large_files=args.truncate_large_files,
            skip_large_files=args.skip_large_files,
            excluded_dirs=frozenset(excluded_dirs),
            excluded_patterns=frozenset(excluded_patterns),
            included_patterns=frozenset(included_patterns),
            type_overrides=type_overrides,
        )
    
    @staticmethod
    def _build_type_overrides(args: argparse.Namespace) -> Dict[str, bool]:
        """Build file type override mappings."""
        return {
            ".json": args.include_json,
            ".jsonc": args.include_json,
            ".yaml": args.include_yaml,
            ".yml": args.include_yaml,
            ".xml": args.include_xml,
            ".html": args.include_html,
            ".htm": args.include_html,
            ".css": args.include_css,
            ".sql": args.include_sql,
            ".csv": args.include_csv,
            ".tsv": args.include_csv,
            ".md": args.include_markdown,
            ".markdown": args.include_markdown,
            ".rst": args.include_markdown,
        }
    
    @staticmethod
    def _parse_size(size_str: str) -> Optional[int]:
        """Parse size string (e.g., '2M', '500k') to bytes."""
        if not size_str:
            return None
        
        size_str = size_str.strip().lower()
        if size_str == "0":
            return None
        
        multipliers = {"k": 1024, "m": 1024**2, "g": 1024**3}
        
        try:
            if size_str[-1] in multipliers:
                return int(size_str[:-1]) * multipliers[size_str[-1]]
            return int(size_str)
        except (ValueError, IndexError):
            logging.warning(f"Invalid size format: {size_str}")
            return None


# =============================================================================
# GIT UTILITIES
# =============================================================================

def load_gitignore(root: Path) -> Optional[Callable[[Path], bool]]:
    """Load .gitignore matcher if available."""
    if not HAS_GITIGNORE_PARSER:
        return None
    
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return None
    
    try:
        return gitignore_parser.parse_gitignore(gitignore)
    except Exception as e:
        logging.warning(f"Could not parse .gitignore: {e}")
        return None


def get_tracked_files(root: Path) -> Optional[Set[str]]:
    """Get set of git-tracked files."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=True,
        )
        return {line.strip().replace("\\", "/") 
                for line in result.stdout.splitlines() if line.strip()}
    except Exception:
        return None


# =============================================================================
# SCANNER
# =============================================================================

class ProjectScanner:
    """Scans project directory for files."""
    
    def __init__(self, config: ScanConfig, filter_: FileFilter):
        self.config = config
        self.filter = filter_
        self.scan_count = 0
    
    def scan(self) -> List[Path]:
        """Scan and return list of included file paths."""
        paths = []
        
        for item in self.config.root_dir.rglob("*"):
            self.scan_count += 1
            
            if item.is_symlink():
                continue
            
            if not item.is_file():
                continue
            
            # Check depth
            if self.config.max_depth is not None:
                try:
                    rel = item.relative_to(self.config.root_dir)
                    if len(rel.parts) > self.config.max_depth:
                        continue
                except ValueError:
                    continue
            
            ok, reason = self.filter.should_include(item)
            if ok:
                paths.append(item)
            else:
                logging.debug(f"Excluded {item}: {reason}")
        
        return paths


# =============================================================================
# CONTENT READER
# =============================================================================

class ContentReader:
    """Reads file contents."""
    
    @staticmethod
    def read_files(
        paths: List[Path],
        root: Path,
        config: ScanConfig,
    ) -> List[FileInfo]:
        """Read content from files."""
        results = []
        
        for path in paths:
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                original_len = len(content)
                truncated = False
                
                # Truncate if needed
                if (config.truncate_large_files and 
                    config.max_file_chars and 
                    original_len > config.max_file_chars):
                    content = content[:config.max_file_chars]
                    content += f"\n\n... [TRUNCATED: {original_len:,} → {config.max_file_chars:,} chars]"
                    truncated = True
                
                lines = content.count("\n") + 1 if content else 0
                language = ContentReader._get_language(path)
                
                results.append(FileInfo(
                    relative_path=path.relative_to(root),
                    absolute_path=path,
                    content=content,
                    size_bytes=path.stat().st_size,
                    line_count=lines,
                    char_count=len(content),
                    language=language,
                    was_truncated=truncated,
                ))
            except Exception as e:
                logging.warning(f"Could not read {path}: {e}")
                results.append(FileInfo(
                    relative_path=path.relative_to(root),
                    absolute_path=path,
                    content=f"# Error reading file: {e}",
                    size_bytes=0,
                    line_count=0,
                    char_count=0,
                    language="text",
                ))
        
        return results
    
    @staticmethod
    def _get_language(path: Path) -> str:
        """Get language hint for syntax highlighting."""
        name = path.name
        if name == "Dockerfile":
            return "dockerfile"
        if name == "Makefile":
            return "makefile"
        if name.startswith(".env"):
            return "dotenv"
        return LANGUAGE_HINTS.get(path.suffix.lower(), "")


# =============================================================================
# ANALYZER
# =============================================================================

class ProjectAnalyzer:
    """Analyzes project structure."""
    
    def analyze(
        self,
        files: List[FileInfo],
        config: ScanConfig,
        scan_count: int,
        duration: float,
    ) -> ScanResult:
        """Perform complete analysis."""
        # Calculate percentages
        total_chars = sum(f.char_count for f in files)
        for f in files:
            f.percentage = (f.char_count / total_chars * 100) if total_chars else 0
        
        # Sort files
        sorted_files = self._sort_files(files, config)
        
        # Detect tech stack
        tech = self._detect_tech(sorted_files)
        
        # Key directories
        key_dirs = self._find_key_dirs(sorted_files)
        
        # Build tree
        tree = self._build_tree(sorted_files, config)
        
        return ScanResult(
            config=config,
            files=sorted_files,
            tree=tree,
            total_scanned=scan_count,
            tech_stack=tech,
            key_dirs=key_dirs,
            duration=duration,
        )
    
    def _sort_files(
        self, files: List[FileInfo], config: ScanConfig
    ) -> List[FileInfo]:
        """Sort files intelligently."""
        if config.sort_alphabetically:
            return sorted(files, key=lambda f: str(f.relative_path).lower())
        
        # Check for numbered files
        numbered = sum(1 for f in files if re.match(r"^\d+_", f.relative_path.name))
        if numbered > len(files) / 2:
            return self._sort_numbered(files)
        
        return self._sort_by_importance(files)
    
    def _sort_numbered(self, files: List[FileInfo]) -> List[FileInfo]:
        """Sort files with numeric prefixes."""
        def key(f: FileInfo):
            match = re.match(r"^(\d+)_", f.relative_path.name)
            if match:
                return (0, int(match.group(1)), f.relative_path.name.lower())
            return (1, 0, f.relative_path.name.lower())
        return sorted(files, key=key)
    
    def _sort_by_importance(self, files: List[FileInfo]) -> List[FileInfo]:
        """Sort files by importance: README first, then by depth."""
        def key(f: FileInfo):
            name = f.relative_path.name.lower()
            depth = len(f.relative_path.parts)
            
            # Priority ordering
            if name.startswith("readme"):
                return (0, depth, name)
            if f.relative_path.name in AlwaysInclude.FILES:
                return (1, depth, name)
            return (2, depth, name)
        
        return sorted(files, key=key)
    
    def _detect_tech(self, files: List[FileInfo]) -> Set[str]:
        """Detect technology stack."""
        tech = set()
        mapping = {
            (".ts", ".tsx"): "TypeScript",
            (".js", ".jsx", ".mjs"): "JavaScript",
            (".py",): "Python",
            (".go",): "Go",
            (".rs",): "Rust",
            (".java",): "Java",
            (".kt", ".kts"): "Kotlin",
            (".cs",): "C#",
            (".rb",): "Ruby",
            (".php",): "PHP",
            (".swift",): "Swift",
            (".scala",): "Scala",
            (".c", ".h"): "C",
            (".cpp", ".cc", ".hpp"): "C++",
        }
        
        for f in files:
            suffix = f.relative_path.suffix.lower()
            for exts, name in mapping.items():
                if suffix in exts:
                    tech.add(name)
                    break
        
        return tech
    
    def _find_key_dirs(self, files: List[FileInfo]) -> List[str]:
        """Find directories with most files."""
        counts: Dict[str, int] = defaultdict(int)
        for f in files:
            parent = str(f.relative_path.parent)
            if parent != ".":
                counts[parent] += 1
        
        sorted_dirs = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [d for d, _ in sorted_dirs[:10]]
    
    def _build_tree(
        self, files: List[FileInfo], config: ScanConfig
    ) -> List[TreeNode]:
        """Build tree structure from files."""
        file_map = {f.relative_path: f for f in files}
        tree_dict: Dict[str, Any] = {}
        
        # Get all paths
        all_paths = set(file_map.keys())
        for path in list(all_paths):
            for parent in path.parents:
                if parent != Path("."):
                    all_paths.add(parent)
        
        # Build nested dict
        for path in sorted(all_paths):
            current = tree_dict
            for part in path.parts:
                current = current.setdefault(part, {})
        
        # Convert to TreeNode
        def convert(d: dict, current_path: Path) -> List[TreeNode]:
            nodes = []
            for name, children_dict in sorted(d.items()):
                path = current_path / name
                is_dir = bool(children_dict)
                
                if is_dir:
                    children = convert(children_dict, path)
                    included = any(c.included for c in children)
                    node = TreeNode(
                        name=name,
                        path=path,
                        is_dir=True,
                        included=included,
                        children=children,
                    )
                else:
                    included = path in file_map
                    f = file_map.get(path)
                    node = TreeNode(
                        name=name,
                        path=path,
                        is_dir=False,
                        included=included,
                        lines=f.line_count if f else 0,
                        chars=f.char_count if f else 0,
                        percentage=f.percentage if f else 0,
                    )
                nodes.append(node)
            return nodes
        
        return convert(tree_dict, Path())


# =============================================================================
# FORMATTERS
# =============================================================================

class MarkdownFormatter:
    """Formats output as Markdown."""
    
    def format_preview(self, result: ScanResult) -> str:
        """Format preview output."""
        lines = ["# 📁 Preview - Files to be Included", ""]
        
        total_lines = sum(f.line_count for f in result.files)
        total_chars = sum(f.char_count for f in result.files)
        
        lines.append(f"**Files:** {len(result.files):,}")
        lines.append(f"**Lines:** {total_lines:,}")
        lines.append(f"**Characters:** {total_chars:,}")
        lines.append("")
        lines.append("## File List")
        lines.append("```")
        
        for f in result.files:
            lines.append(f"  {f.relative_path} ({f.line_count:,}L, {f.char_count:,}C)")
        
        lines.append("```")
        return "\n".join(lines)
    
    def format_summary(self, result: ScanResult) -> str:
        """Format summary with tree."""
        lines = [
            "# 📁 Project Structure",
            f"*Directory: {self._format_path(result.config.root_dir)}*",
            "",
        ]
        
        # Overview
        tech = ", ".join(result.tech_stack) if result.tech_stack else "Unknown"
        lines.append(f"**Stack:** {tech}")
        lines.append(f"**Files:** {len(result.files):,} of {result.total_scanned:,} scanned")
        lines.append("")
        
        # Tree
        lines.append("## Project Tree")
        lines.append("```")
        lines.append(".")
        self._format_tree(result.tree, lines, "")
        lines.append("```")
        
        return "\n".join(lines)
    
    def format_full(self, result: ScanResult) -> str:
        """Format complete output with file contents."""
        lines = [
            "# 📁 Project Context",
            f"*Directory: `{self._format_path(result.config.root_dir)}`*",
            "",
        ]
        
        # Stats
        total_lines = sum(f.line_count for f in result.files)
        total_chars = sum(f.char_count for f in result.files)
        tech = ", ".join(result.tech_stack) if result.tech_stack else "Unknown"
        
        lines.extend([
            "## Overview",
            f"- **Stack:** {tech}",
            f"- **Files:** {len(result.files):,}",
            f"- **Lines:** {total_lines:,}",
            f"- **Size:** ~{total_chars/1024:.1f} KB",
            "",
            "## Structure",
            "```",
            ".",
        ])
        
        self._format_tree(result.tree, lines, "")
        lines.extend(["```", "", "---", "", "## Source Files", ""])
        
        # File contents
        for f in result.files:
            header = self._file_header(f)
            lines.extend([
                header,
                f"*{f.line_count:,} lines • {f.char_count:,} chars*",
                "",
                f"```{f.language}",
                f.content,
                "```",
                "",
            ])
        
        return "\n".join(lines).strip()
    
    def _format_path(self, path: Path) -> str:
        """Format path for display."""
        try:
            return f"~/{path.relative_to(Path.home())}"
        except ValueError:
            return str(path)
    
    def _format_tree(
        self, nodes: List[TreeNode], lines: List[str], prefix: str
    ) -> None:
        """Recursively format tree nodes."""
        for i, node in enumerate(nodes):
            is_last = i == len(nodes) - 1
            connector = GLYPH_LAST if is_last else GLYPH_CHILD
            
            if not node.included and not node.children:
                continue
            
            icon = "📁" if node.is_dir else "📄"
            status = "✓" if node.included else "✗"
            line = f"{prefix}{connector} {icon} {node.name}"
            
            if not node.is_dir and node.included:
                line += f" ({node.lines:,}L)"
            
            lines.append(line)
            
            if node.children:
                child_prefix = prefix + (GLYPH_SPACE if is_last else GLYPH_PIPE)
                self._format_tree(node.children, lines, child_prefix)
    
    def _file_header(self, f: FileInfo) -> str:
        """Generate file header."""
        name = f.relative_path.name.lower()
        icons = {
            "readme": "📖",
            ".py": "🐍",
            ".go": "🐹",
            ".rs": "🦀",
            ".ts": "📘",
            ".js": "📒",
            ".json": "⚙️",
            ".md": "📝",
        }
        
        icon = "📄"
        for key, emoji in icons.items():
            if key in name or f.relative_path.suffix.lower() == key:
                icon = emoji
                break
        
        return f"### {icon} `{f.relative_path}`"


class JsonFormatter:
    """Formats output as JSON."""
    
    def format(self, result: ScanResult, include_content: bool = False) -> str:
        """Format as JSON."""
        total_lines = sum(f.line_count for f in result.files)
        total_chars = sum(f.char_count for f in result.files)
        
        output = {
            "project": {
                "root": str(result.config.root_dir),
                "files": len(result.files),
                "lines": total_lines,
                "chars": total_chars,
                "scanned": result.total_scanned,
                "tech_stack": list(result.tech_stack),
            },
            "files": [
                {
                    "path": str(f.relative_path),
                    "lines": f.line_count,
                    "chars": f.char_count,
                    "percentage": round(f.percentage, 2),
                    "language": f.language,
                    **({"content": f.content} if include_content else {}),
                }
                for f in result.files
            ],
        }
        
        return json.dumps(output, indent=2)


# =============================================================================
# OUTPUT WRITER
# =============================================================================

class OutputWriter:
    """Handles output to various destinations."""
    
    @staticmethod
    def write(
        content: str,
        summary: str,
        config: ScanConfig,
    ) -> bool:
        """Write content to configured destination."""
        if config.output_mode == OutputMode.FILE:
            return OutputWriter._write_file(content, summary, config.output_file)
        elif config.output_mode == OutputMode.STDOUT:
            return OutputWriter._write_stdout(content)
        else:
            return OutputWriter._write_clipboard(content, summary)
    
    @staticmethod
    def _write_file(content: str, summary: str, path: Optional[Path]) -> bool:
        """Write to file."""
        if not path:
            return False
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(summary, file=sys.stderr)
            print(f"\n✅ Written to {path}", file=sys.stderr)
            return True
        except OSError as e:
            print(f"❌ Error writing file: {e}", file=sys.stderr)
            return False
    
    @staticmethod
    def _write_stdout(content: str) -> bool:
        """Write to stdout."""
        try:
            print(content)
            return True
        except Exception as e:
            print(f"❌ Error writing to stdout: {e}", file=sys.stderr)
            return False
    
    @staticmethod
    def _write_clipboard(content: str, summary: str) -> bool:
        """Copy to clipboard."""
        if not HAS_PYPERCLIP:
            print("⚠️ pyperclip not installed, printing to stdout", file=sys.stderr)
            return OutputWriter._write_stdout(content)
        
        try:
            print(summary, file=sys.stderr)
            pyperclip.copy(content)
            print(f"\n✅ {len(content):,} chars copied to clipboard", file=sys.stderr)
            return True
        except Exception as e:
            print(f"❌ Clipboard error: {e}", file=sys.stderr)
            return False


# =============================================================================
# INTERACTIVE MODE
# =============================================================================

class InteractiveConfig:
    """Interactive configuration wizard."""
    
    @staticmethod
    def run(args: argparse.Namespace) -> argparse.Namespace:
        """Run interactive configuration."""
        print("\n🔧 Interactive Configuration\n")
        print("Press Enter to accept defaults, or type new value.\n")
        
        # Root directory
        current = str(args.root_dir)
        inp = input(f"Root directory [{current}]: ").strip()
        if inp:
            args.root_dir = Path(inp)
        
        # Output format
        inp = input(f"Output format (markdown/json) [{args.format}]: ").strip().lower()
        if inp in ("markdown", "json"):
            args.format = inp
        
        # Include types
        types = [
            ("json", "JSON files"),
            ("yaml", "YAML files"),
            ("markdown", "Markdown files"),
            ("html", "HTML files"),
            ("css", "CSS files"),
            ("sql", "SQL files"),
        ]
        
        print("\nInclude additional file types? (y/n)")
        for attr, desc in types:
            current = getattr(args, f"include_{attr}", False)
            default = "y" if current else "n"
            inp = input(f"  {desc} [{default}]: ").strip().lower()
            if inp == "y":
                setattr(args, f"include_{attr}", True)
            elif inp == "n":
                setattr(args, f"include_{attr}", False)
        
        # Max depth
        inp = input(f"Max directory depth (empty for unlimited) [{args.max_depth or ''}]: ").strip()
        if inp.isdigit():
            args.max_depth = int(inp)
        
        # Output destination
        print("\nOutput destination:")
        print("  1. Clipboard (default)")
        print("  2. File")
        print("  3. Stdout")
        inp = input("Choice [1]: ").strip()
        if inp == "2":
            path = input("Output file path: ").strip()
            if path:
                args.output = path
        elif inp == "3":
            args.stdout = True
        
        print("\n✅ Configuration complete!\n")
        return args


# =============================================================================
# CLI PARSER
# =============================================================================

def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="context",
        description="Gather project context into Markdown for LLMs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  context                      # Scan current dir, copy to clipboard
  context ./src                # Scan specific directory
  context -o output.md         # Write to file
  context --include-json       # Include JSON files
  context --include "*.py"     # Include only Python files
  context --preview            # Preview what would be included
        """,
    )
    
    # Positional
    parser.add_argument(
        "root_dir",
        nargs="?",
        type=Path,
        default=Path("."),
        help="Root project directory (default: current)",
    )
    
    # Output options
    out = parser.add_argument_group("Output Options")
    out.add_argument("-o", "--output", metavar="FILE", help="Write to file")
    out.add_argument("--stdout", action="store_true", help="Print to stdout")
    out.add_argument("--no-clipboard", action="store_true", help="Don't copy to clipboard")
    out.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    
    # Filtering
    filt = parser.add_argument_group("Filtering")
    filt.add_argument("--exclude", action="append", metavar="PATTERN", help="Glob pattern to exclude")
    filt.add_argument("--include", action="append", metavar="PATTERN", help="Glob pattern to include")
    filt.add_argument("--include-only", action="store_true", help="Include ONLY matching --include patterns")
    filt.add_argument("--exclude-extension", action="append", metavar="EXT", help="Extension to exclude")
    filt.add_argument("--include-extension", action="append", metavar="EXT", help="Extension to include")
    filt.add_argument("--max-size", default="2M", help="Max file size (default: 2M)")
    filt.add_argument("--max-depth", type=int, metavar="N", help="Max directory depth")
    filt.add_argument("--include-binary", action="store_true", help="Include binary files")
    
    # Git options
    git = parser.add_argument_group("Git Integration")
    git_excl = git.add_mutually_exclusive_group()
    git_excl.add_argument("--no-gitignore", action="store_true", help="Ignore .gitignore completely")
    git_excl.add_argument("--gitignore-only", action="store_true", help="Use .gitignore only (default)")
    git_excl.add_argument("--use-git", action="store_true", help="Use full git integration (tracked files only)")
    
    # File types
    types = parser.add_argument_group("Include File Types")
    types.add_argument("--include-json", action="store_true", help="Include JSON files")
    types.add_argument("--include-yaml", action="store_true", help="Include YAML files")
    types.add_argument("--include-xml", action="store_true", help="Include XML files")
    types.add_argument("--include-html", action="store_true", help="Include HTML files")
    types.add_argument("--include-css", action="store_true", help="Include CSS files")
    types.add_argument("--include-sql", action="store_true", help="Include SQL files")
    types.add_argument("--include-csv", action="store_true", help="Include CSV files")
    types.add_argument("--include-markdown", action="store_true", help="Include Markdown files")
    
    # Large files
    large = parser.add_argument_group("Large File Handling")
    large.add_argument("--max-file-chars", type=int, default=50000, help="Max chars per file (default: 50000)")
    large.add_argument("--skip-large-files", action="store_true", help="Skip files exceeding char limit")
    large.add_argument("--truncate-large-files", action="store_true", help="Truncate large files")
    
    # Features
    feat = parser.add_argument_group("Features")
    feat.add_argument("--preview", action="store_true", help="Preview files without content")
    feat.add_argument("--dry-run", action="store_true", help="Simulate without output")
    feat.add_argument("--interactive", action="store_true", help="Interactive configuration")
    feat.add_argument("--show-stats", action="store_true", help="Show stats alongside output")
    feat.add_argument("--sort-alpha", action="store_true", help="Sort files alphabetically")
    
    # Meta
    meta = parser.add_argument_group("Information")
    meta.add_argument("--version", action="version", version=f"%(prog)s {get_version()}")
    meta.add_argument("--check-updates", action="store_true", help="Check for updates")
    
    return parser


# =============================================================================
# VERSION CHECKER
# =============================================================================

class VersionChecker:
    """Checks for available updates."""
    
    @staticmethod
    def check() -> Optional[Dict[str, str]]:
        """Check PyPI for newer version."""
        current = get_version()
        if current == "unknown":
            return None
        
        try:
            with urllib.request.urlopen(
                "https://pypi.org/pypi/repo-to-llm-context/json",
                timeout=3,
            ) as resp:
                data = json.loads(resp.read())
                latest = data.get("info", {}).get("version", "")
                
                if latest and VersionChecker._is_newer(current, latest):
                    return {
                        "current": current,
                        "latest": latest,
                        "command": "pipx upgrade repo-to-llm-context",
                    }
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def _is_newer(current: str, latest: str) -> bool:
        """Compare version strings."""
        def parse(v: str) -> Tuple[int, ...]:
            try:
                return tuple(int(x) for x in v.lstrip("v").split(".")[:3])
            except ValueError:
                return (0, 0, 0)
        
        return parse(latest) > parse(current)


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:
    """Main entry point."""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )
    
    parser = create_parser()
    args = parser.parse_args()
    
    # Check for updates
    if args.check_updates:
        print("🔍 Checking for updates...")
        update = VersionChecker.check()
        if update:
            print(f"🚀 Update available: v{update['current']} → v{update['latest']}")
            print(f"   Run: {update['command']}")
        else:
            print("✅ You're running the latest version!")
        return 0
    
    # Interactive mode
    if args.interactive:
        args = InteractiveConfig.run(args)
    
    # Validate root directory
    if not args.root_dir.is_dir():
        print(f"❌ Directory not found: {args.root_dir}", file=sys.stderr)
        return 1
    
    try:
        start = time.time()
        
        # Build configuration
        config = ConfigBuilder.from_args(args)
        
        # Load git data
        gitignore = None
        tracked = None
        
        if config.git_mode in (GitMode.GITIGNORE, GitMode.FULL):
            gitignore = load_gitignore(config.root_dir)
        
        if config.git_mode == GitMode.FULL:
            tracked = get_tracked_files(config.root_dir)
        
        # Create filter and scanner
        filter_ = FileFilter(config, gitignore, tracked)
        scanner = ProjectScanner(config, filter_)
        
        # Scan
        paths = scanner.scan()
        
        if not paths:
            print("⚠️ No files matched the filters", file=sys.stderr)
            if not args.dry_run:
                if config.output_mode == OutputMode.STDOUT:
                    print("# No files included")
            return 0
        
        # Read files
        files = ContentReader.read_files(paths, config.root_dir, config)
        
        # Analyze
        analyzer = ProjectAnalyzer()
        result = analyzer.analyze(files, config, scanner.scan_count, time.time() - start)
        
        # Format output
        if config.output_format == "json":
            formatter = JsonFormatter()
            content = formatter.format(result, include_content=True)
            summary = formatter.format(result, include_content=False)
        else:
            formatter = MarkdownFormatter()
            if args.preview:
                content = formatter.format_preview(result)
                summary = content
            else:
                content = formatter.format_full(result)
                summary = formatter.format_summary(result)
        
        # Handle special modes
        if args.dry_run:
            print(f"\n🔍 Dry Run Complete")
            print(f"   Files: {len(result.files):,}")
            print(f"   Output size: {len(content):,} chars")
            return 0
        
        if args.show_stats:
            print(summary, file=sys.stderr)
        
        # Write output
        success = OutputWriter.write(content, summary, config)
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted", file=sys.stderr)
        return 130
    except Exception as e:
        logging.exception("Critical error")
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
