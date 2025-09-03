# Code-to-Clipboard-for-LLMs

**Intelligently package your project's code context for LLMs. Install & try — took less than 60 seconds**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/) [![Platform](https://img.shields.io/badge/platform-osx%20%7C%20linux%20%7C%20windows-lightgrey.svg)]() [![GitHub Stars](https://img.shields.io/github/stars/yigitkonur/code-to-clipboard-for-llms?style=social)](https://github.com/yigitkonur/code-to-clipboard-for-llms)

Interacting with LLMs like ChatGPT, Claude, Gemini or apps like [Thinkbuddy](https://thinkbuddy.ai) 💫 about your codebase often requires providing substantial context. Manually selecting, copying, and formatting relevant files is time-consuming, error-prone, and inefficient, especially when dealing with context window limits and token costs.

`code-to-clipboard-for-llms` streamlines this process. It's a Python script that automatically:

1.  **Scans** your project directory.
2.  **Filters** out irrelevant files and noise (like `node_modules`, build artifacts, `.git`).
3.  **Structures** the relevant code logically.
4.  **Formats** everything into clean Markdown, optimized for LLMs.
5.  **Copies** the result directly to your clipboard.

Spend less time preparing context and more time getting valuable insights from your AI assistant.

## Install

**Recommended (macOS/Linux with Homebrew):**
```bash
brew tap yigitkonur/context
brew install context
```

**Alternative (via pipx - all platforms):**
```bash
pipx install git+https://github.com/yigitkonur/code-to-clipboard-for-llms.git
```

**Alternative (via pip - all platforms):**
```bash
pip install git+https://github.com/yigitkonur/code-to-clipboard-for-llms.git
```


---

## How to use? 

https://github.com/user-attachments/assets/399ccc84-a052-44b0-b26d-3f82cc43e16e

---

## The Problem It Solves

Providing effective code context to LLMs manually is challenging:

*   **Token Limits & Cost:** Including irrelevant files wastes the LLM's limited context window and increases API costs.
*   **Noise & Confusion:** Dependency code, logs, or build artifacts can confuse the LLM, leading to less accurate responses.
*   **Lack of Structure:** Randomly pasted files make it difficult for the LLM to understand project architecture and file relationships.
*   **Manual Effort:** Selecting, filtering, formatting, and copying files by hand is tedious and inefficient.

## The Solution: `code-to-clipboard-for-llms`

This tool addresses these challenges by providing:

*   ✅ **Intelligent Filtering:** Automatically excludes common unnecessary directories and files, respects `.gitignore` rules, and leverages Git tracking status (configurable).
*   🧠 **Optimized Structure & Ordering:** Presents files logically (README first, then key files sorted by relevance) with clear Markdown formatting and syntax hints. Includes a visual file tree.
*   ⏱️ **One-Command Operation:** Simplifies the entire context gathering process into a single command executed in your project directory.
*   📋 **Direct Clipboard Integration:** Sends the formatted context straight to your clipboard, ready to paste.
*   🔧 **Customization:** Offers flags to fine-tune filtering, sizing, and output behavior.

---

## 🚀 Installation

Choose the method that works best for your system:

### Method 1: Homebrew (Recommended for macOS/Linux)

The simplest installation method on macOS and Linux:

```bash
brew tap yigitkonur/context
brew install context
```

**Upgrade later:**
```bash
brew upgrade context
```

**Uninstall:**
```bash
brew uninstall context
brew untap yigitkonur/context
```

### Method 2: pipx (Cross-platform)

`pipx` creates an isolated environment for CLI tools, keeping your system clean:

**First, install pipx if you don't have it:**
```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

**Then install the tool:**
```bash
pipx install git+https://github.com/yigitkonur/code-to-clipboard-for-llms.git
```

**Upgrade later:**
```bash
pipx upgrade llmcontext
```

**Uninstall:**
```bash
pipx uninstall llmcontext
```

### Method 3: pip (Direct installation)

```bash
pip install git+https://github.com/yigitkonur/code-to-clipboard-for-llms.git
```

**➡️ Important:** After installation, the `context` command should be available in your terminal. If not, restart your terminal or ensure your Python scripts directory is in your PATH.

---

## ▶️ Basic Usage

Using the tool is designed to be simple:

1.  **Install** using one of the methods above
2.  **Navigate** to your project directory:
    ```bash
    cd /path/to/your/project
    ```
3.  **Run** the command:
    ```bash
    context
    ```
4.  The script will process the project and copy the formatted Markdown context to your clipboard.
5.  **Paste** the content into your LLM prompt and ask your question.

**Output Options:**

*   **Save to File:** Instead of copying to the clipboard, save the output to a Markdown file:
    ```bash
    context --output project_context.md
    ```
*   **Print to Terminal:** Display the output directly in the terminal (useful for previewing or piping):
    ```bash
    context --stdout
    ```

---

## 🔑 Key Features Summary

*   **Automatic Filtering:** Excludes irrelevant files/directories (`node_modules`, `.git`, `build`, `venv`, logs, etc.).
*   **.gitignore Aware:** Uses `.gitignore` rules for exclusion (requires `gitignore-parser`).
*   **Git Tracking Option:** Can optionally exclude files not tracked by Git.
*   **Smart Ordering:** Prioritizes README, sorts files and directories by estimated importance (lines of code).
*   **LLM-Optimized Markdown:** Clean formatting, code blocks with language hints, file paths.
*   **Visual File Tree:** Includes a tree view (`├──`, `└──`) with markers (✅/❌) showing included/excluded items.
*   **Metadata:** Includes file statistics (lines, characters, percentage) for context.
*   **Privacy:** Masks user's home directory path in the output summary.
*   **Configurable:** Command-line flags for including/excluding specific patterns, types, and controlling behavior.
*   **Flexible Output:** Clipboard (default), file (`--output`), or standard output (`--stdout`).
*   **Cross-Platform:** Python 3 script with installers for macOS, Linux, Windows.

---

## ⚙️ Advanced Usage & Customization

While the defaults work well, you can tailor the script's behavior using flags:

<details>
<summary><strong>Expand for detailed command-line flag reference</strong></summary>

#### Filtering and Inclusion Control

*   `--include PATTERN`: Glob pattern to force inclusion of specific files or directories that might otherwise be excluded (e.g., `--include "tests/specific_test.py"`, `--include "config/**.yaml"`). Does not override excluded directories like `node_modules`. Can be used multiple times.
*   `--exclude PATTERN`: Glob pattern to add custom exclusions beyond the defaults (e.g., `--exclude "*.log"`, `--exclude "docs/*"`). Can be used multiple times.
*   `--exclude-extension EXT`: Exclude all files with a specific extension (e.g., `--exclude-extension .tmp`).
*   `--include-extension EXT`: Force include files with an extension normally excluded by default (use carefully).

#### Include Specific File Types (Overrides default exclusions)

*   `--include-json`: Include `.json` / `.jsonc` files.
*   `--include-yaml`: Include `.yaml` / `.yml` files.
*   `--include-xml`: Include `.xml` files.
*   `--include-html`: Include `.html` / `.htm` files.
*   `--include-css`: Include `.css` files.
*   `--include-sql`: Include `.sql` files.
*   `--include-csv`: Include `.csv` / `.tsv` files.
*   `--include-markdown`: Include *all* Markdown files (`.md`, `.markdown`, `.rst`), not just the root README.

#### Size and Content Control

*   `--max-size SIZE`: Exclude files larger than the specified size (e.g., `500k`, `10M`, `1G`). Use `0` for no limit. Default is `2M`.
*   `--include-binary`: Attempt to include files detected as binary (default is false).

#### Output Behavior

*   `--no-clipboard`: Disable automatic copying to the clipboard.

#### Git Integration Behavior

*(Requires `gitignore-parser` Python library: `pip install gitignore-parser`)*

*   `--no-gitignore`: Ignore `.gitignore` rules and Git tracking status entirely.
*   `--gitignore-only`: Use `.gitignore` rules but *don't* exclude files solely because they are untracked by Git.

</details>

### Permanent Configuration

For persistent changes, you can modify the default lists directly within the `llmcontext.py` script:

*   `DEFAULT_EXCLUDED_DIRS`: Tuple of directory names always excluded recursively.
*   `DEFAULT_EXCLUDED_PATTERNS`: Tuple of file glob patterns excluded by default.
*   `FILES_TO_ALWAYS_CHECK`: Set of crucial filenames (e.g., `Dockerfile`, `requirements.txt`) considered even if their extension is excluded by default patterns.
*   `SKIP_ALWAYS`: Set of filenames always excluded, overriding other rules.

---

## 📄 Understanding the Output Format

The generated Markdown is structured for clarity:

<details>
<summary><strong>Expand for output structure details</strong></summary>

1.  **Header Section:** Title, project directory (masked), legend for tree symbols.
2.  **Tree Section:** Visual tree (`.`, `├──`, `└──`, `│`) showing included (✅) and excluded (❌) files/directories, with stats for included files (lines, chars, percentage).
3.  **Summary Statistics:** Total counts for included files, lines, and characters.
4.  **Separator:** (`---`)
5.  **Selected File Content Section:**
    *   For each included file (in priority order):
        *   `### /relative/path/to/file`: File path header.
        *   `*(Stats: ...)*`: Line and character counts for the file.
        *   ```` ```[language_hint] ````: Fenced code block with detected language hint (e.g., `python`, `javascript`).
        *   File content.
        *   ` ``` `: End of code block.
        *   Blank line separator.

</details>

---

## 🆚 Comparison to Other Methods

How does this tool stack up against common alternatives?

| Feature                 | **This Script (`context`/`copyc`)** | Manual Copy/Paste | GitHub Link Sharing | Simple `cat`/`tree` | Code Search Tools |
| :---------------------- | :-------------------------------: | :---------------: | :-----------------: | :-----------------: | :---------------: |
| **Intelligent Filtering** |                 ✅                |         ❌        |          ❌         |          ❌         |    ⚠️ Limited     |
| **LLM-Optimized Order** |                 ✅                |         ❌        |          ❌         |          ❌         |         ❌        |
| **Tree Visualization**  |                 ✅                |         ❌        |     ⚠️ Partial      |     ⚠️ Basic      |    ⚠️ Limited     |
| **Privacy (Path Mask)** |                 ✅                |         ❌        |     ⚠️ Depends      |          ❌         |    ⚠️ Depends     |
| **File Statistics**     |                 ✅                |         ❌        |          ❌         |          ❌         |    ⚠️ Limited     |
| **Clipboard Ready**     |                 ✅                |     ⚠️ Manual     |          ❌         |          ❌         |         ❌        |
| **Customizable**        |                 ✅                |         ❌        |          ❌         |     ⚠️ Limited      |    ⚠️ Limited     |
| **Syntax Highlighting** |                 ✅                |         ❌        |          ✅         |     ⚠️ Limited      |         ✅        |
| **Offline Usage**       |                 ✅                |         ✅        |          ❌         |          ✅         |    ⚠️ Depends     |
| **No Account Needed**   |                 ✅                |         ✅        |          ❌         |          ✅         |    ⚠️ Depends     |
| **Reduces Token Cost**  |                 ✅                |         ❌        |          ❌         |          ❌         |         ❌        |
| **Improves LLM Focus**  |                 ✅                |         ❌        |          ❌         |          ❌         |         ❌        |

**Conclusion:** This tool provides a purpose-built solution for creating optimized LLM context that manual methods or simple utilities cannot easily replicate.

---

## 🛠️ Alternative Installation Methods

### From Source (For Development)

If you want to contribute or modify the code:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yigitkonur/code-to-clipboard-for-llms.git
    cd code-to-clipboard-for-llms
    ```

2.  **Install in development mode:**
    ```bash
    pip install -e .
    ```
    This installs the tool while allowing you to edit the source code.

### Direct Script Execution

If you prefer to run the script directly without installation:

1.  **Download the script:**
    ```bash
    curl -fLo llmcontext.py https://raw.githubusercontent.com/yigitkonur/code-to-clipboard-for-llms/main/llmcontext.py
    ```

2.  **Install dependencies:**
    ```bash
    pip install pyperclip gitignore-parser
    ```

3.  **Run directly:**
    ```bash
    python3 llmcontext.py
    ```

---

## ❓ Troubleshooting

Common issues and potential solutions:

<details>
<summary><strong>Expand for troubleshooting tips</strong></summary>

*   **`context: command not found`:**
    *   Restart your terminal after installation
    *   Verify the installation worked: `pipx list` (if you used pipx) or `pip show llmcontext`
    *   Check if Python's script directory is in your PATH: `echo $PATH` (Linux/Mac) or `echo $env:Path` (PowerShell)
    *   For `pip` installs, try `pip install --user git+https://github.com/...` and add `~/.local/bin` to your PATH

*   **Clipboard Issues / `pyperclip` errors:**
    *   Ensure `pyperclip` is installed: `pip show pyperclip`. If not, `pip install pyperclip`.
    *   **Linux:** `pyperclip` may require system tools like `xclip` or `xsel`. Install via package manager (e.g., `sudo apt install xclip`).
    *   Try the `--stdout` or `--output` flags to bypass clipboard issues temporarily.

*   **`.gitignore` Not Working:**
    *   Ensure `gitignore-parser` is installed: `pip show gitignore-parser`. If not, `pip install gitignore-parser`.
    *   Ensure you haven't used the `--no-gitignore` flag.

*   **Script Errors:**
    *   Verify Python 3 version (`python3 --version`) is 3.6 or higher.
    *   Check file permissions if the script fails reading specific files.
    *   If you edited the script, check for syntax errors. Try a fresh copy.

*   **Incorrect Files Included/Excluded:**
    *   Review the visual tree output (✅/❌) to understand the script's decisions.
    *   Use `--stdout` to preview before relying on clipboard.
    *   Adjust filtering with `--include` / `--exclude` flags.
    *   Check your `.gitignore` file for relevant patterns.

</details>
