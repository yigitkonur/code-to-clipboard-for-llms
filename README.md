# repo-to-prompt

> Gather project context for LLMs — intelligently scan repositories and format for AI consumption.

[![npm version](https://img.shields.io/npm/v/repo-to-prompt.svg)](https://www.npmjs.com/package/repo-to-prompt)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Why?

When working with AI coding assistants, you often need to share your project's context. Manually copying files is tedious and error-prone. **repo-to-prompt** intelligently scans your codebase, respects `.gitignore`, filters out noise, and formats everything into clean Markdown ready for LLMs.

## Features

- 📁 **Smart Scanning** — Respects `.gitignore`, skips binaries, build artifacts, and node_modules
- 🐙 **GitHub Support** — Clone and scan any public repository directly
- 📋 **Clipboard Ready** — Copies to clipboard by default, ready to paste
- 🌲 **Tree Visualization** — Beautiful project structure display
- 🔍 **Tech Detection** — Automatically detects your stack
- ⚡ **Fast** — Built on native ESM with fast-glob

## Installation

```bash
# Run instantly with npx (no install)
npx repo-to-prompt

# Or install globally
npm install -g repo-to-prompt
```

After global install, use any of these aliases:
```bash
repo-to-prompt .
context .
llmcontext .
repocp .
```

## Quick Start

```bash
# Scan current directory → clipboard
npx repo-to-prompt

# Scan specific folder
npx repo-to-prompt ./src

# Scan GitHub repo
npx repo-to-prompt owner/repo

# Write to file
npx repo-to-prompt -o context.md

# Preview what will be included
npx repo-to-prompt --preview
```

## Usage Examples

### Basic

```bash
# Current directory to clipboard
repo-to-prompt

# Specific directory
repo-to-prompt ./backend

# Output to file
repo-to-prompt -o output.md

# Print to stdout
repo-to-prompt --stdout
```

### GitHub Repositories

```bash
# Clone and scan
repo-to-prompt facebook/react

# Specific branch
repo-to-prompt vercel/next.js@canary

# Full URL
repo-to-prompt https://github.com/microsoft/typescript
```

### Filtering

```bash
# Include only Python files
repo-to-prompt --include "*.py" --include-only

# Exclude test files
repo-to-prompt --exclude "*.test.ts" --exclude "*.spec.ts"

# Include data files (off by default)
repo-to-prompt --include-json --include-yaml --include-markdown

# Limit depth
repo-to-prompt --max-depth 3
```

### Output Control

```bash
# Preview files (no content)
repo-to-prompt --preview

# Dry run (stats only)
repo-to-prompt --dry-run

# JSON format
repo-to-prompt --format json

# Show stats with output
repo-to-prompt --show-stats
```

## Options

### Output
| Option | Description |
|--------|-------------|
| `-o, --output <file>` | Write to file |
| `--stdout` | Print to stdout |
| `--no-clipboard` | Don't copy to clipboard |
| `--format <type>` | `markdown` (default) or `json` |

### Filtering
| Option | Description |
|--------|-------------|
| `--include <pattern>` | Include glob pattern |
| `--exclude <pattern>` | Exclude glob pattern |
| `--include-only` | Only include matching patterns |
| `--max-size <size>` | Max file size (default: `2M`) |
| `--max-depth <n>` | Max directory depth |
| `--include-binary` | Include binary files |

### File Types
| Option | Description |
|--------|-------------|
| `--include-json` | Include JSON files |
| `--include-yaml` | Include YAML/YML files |
| `--include-markdown` | Include Markdown files |
| `--include-html` | Include HTML files |
| `--include-css` | Include CSS files |
| `--include-sql` | Include SQL files |
| `--include-csv` | Include CSV files |
| `--include-xml` | Include XML files |

### Git
| Option | Description |
|--------|-------------|
| `--no-gitignore` | Ignore .gitignore |
| `--use-git` | Only include git-tracked files |

### Features
| Option | Description |
|--------|-------------|
| `--preview` | Preview files without content |
| `--dry-run` | Show stats only |
| `--interactive` | Interactive configuration |
| `--sort-alpha` | Sort alphabetically |
| `--check-updates` | Check for updates |

## Output Example

```markdown
# 📁 Project Context
*Directory: `~/my-project`*

## Overview
- **Stack:** TypeScript, React
- **Files:** 24
- **Lines:** 2,456

## Structure
.
├── 📁 src
│   ├── 📄 index.ts (50L)
│   └── 📁 components
│       └── 📄 App.tsx (120L)
└── 📄 package.json (30L)

---

## Source Files

### 📘 `src/index.ts`
*50 lines • 1,234 chars*

\`\`\`typescript
// Your code here...
\`\`\`
```

## Requirements

- **Node.js 18+**
- **git** (for GitHub cloning)

## License

MIT © [Yigit Konur](https://github.com/yigitkonur)
