# LLM Code Copier (`copy.sh`)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful Bash script to intelligently gather, filter, format, and copy your project's source code context to the clipboard – perfect for pasting into Large Language Models (LLMs) like ChatGPT, Claude, Gemini, Bard, and more.

## The Problem

When working with LLMs, you often need to provide context about your codebase. Manually finding, copying, and pasting relevant files is tedious, error-prone, and often includes unnecessary clutter like build artifacts, dependencies, or large binary files. This script automates the process, giving you clean, relevant code context with a single command.

## ✨ Powerful Features

*   **Project Structure Overview:** Starts with a `tree` view of your project, intelligently excluding common clutter (like `.git`, `node_modules`, `__pycache__`, etc.).
*   **Source Code Concatenation:** Finds and concatenates the content of relevant source files.
*   **Intelligent Filtering:**
    *   **Extensive Default Exclusions:** Automatically ignores version control dirs (`.git`), dependency folders (`node_modules`, `venv`), build outputs (`dist`, `build`, `target`), caches (`__pycache__`), logs, IDE folders (`.vscode`, `.idea`), OS files (`.DS_Store`), and many common binary/temporary file types (`.log`, `.tmp`, `.exe`, `.dll`, `.so`, `.o`, `.pyc`, `.class`, `.zip`, `.gz`, etc.).
    *   **Custom Exclusions:** Easily add your own project-specific exclusions using the `--exclude` flag (e.g., `--exclude "*.log,*.tmp,dev-config.json"`).
    *   **Large File Prevention:** Excludes files exceeding a size limit (default: 100MB) to prevent accidentally copying huge assets or models.
    *   **Text File Verification:** Uses the `file --mime-type` command to ensure only actual text files are included, preventing binary data from slipping through.
*   **Clear & Organized Formatting:**
    *   Outputs files grouped by directory and then by file extension.
    *   Uses distinct headers (`=============== folder/file ===============`) for easy navigation.
    *   Wraps file content in Markdown code blocks (```) for proper rendering.
    *   Separates files with `---` for visual clarity.
*   **Clipboard Integration:** Automatically copies the entire formatted output to your system clipboard (`pbcopy` on macOS, `xclip` or `xsel` on Linux). Falls back to printing to standard output if no clipboard command is found.
*   **User Feedback:** Reports the total number of lines copied to the clipboard.

## 🚀 Installation & Setup

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-username/llm-code-copier.git # Replace your-username!
    cd llm-code-copier
    ```

2.  **Make the Script Executable:**
    You need to give the script permission to run.
    ```bash
    chmod +x copy.sh
    ```

3.  **Set up an Alias (Recommended):**
    To run the script easily from anywhere, create an alias. Replace `/path/to/llm-code-copier/copy.sh` with the *actual absolute path* where you cloned the repository.

    *   **Add to your shell configuration file:** Open your shell's config file (`~/.bashrc`, `~/.zshrc`, `~/.bash_profile`, or `~/.profile` depending on your shell):
        ```bash
        # Example for ~/.zshrc or ~/.bashrc
        alias copy='bash /path/to/llm-code-copier/copy.sh'
        ```
        **Important:** Replace `/path/to/llm-code-copier/copy.sh` with the correct absolute path on your system! You can find the path by navigating to the cloned directory and running `pwd`.

    *   **Apply the changes:** Either restart your terminal or source the config file:
        ```bash
        source ~/.zshrc  # Or your specific config file
        ```

    *   **Verify the alias:**
        ```bash
        which copy
        # Should output something like: copy: aliased to bash /path/to/llm-code-copier/copy.sh

        type copy
        # Should show the alias definition
        ```

## 🛠️ Usage

1.  **Navigate to your project directory:**
    ```bash
    cd /path/to/your/project
    ```

2.  **Run the script:**
    ```bash
    copy
    ```

3.  **Paste!** The formatted project context is now in your clipboard, ready to be pasted into your LLM prompt.

**Using Custom Exclusions:**

To exclude additional file patterns *beyond* the extensive defaults, use the `--exclude` flag followed by a comma-separated list of patterns (use quotes if patterns contain wildcards or special characters).

```bash
# Exclude all .log files and a specific config file
copy --exclude "*.log,config.dev.json"

# Exclude temporary files and backup files
copy --exclude "*.tmp,*~,*.bak"
```

## 📄 Output Format Explained

The script generates a structured text block designed for clarity. Here's an example snippet and breakdown:

# Project Structure
.
├── src
│   ├── __init__.py
│   └── main.py
├── tests
│   └── test_main.py
└── requirements.txt

# Source Code

=============== root folder ===============
=============== .txt files ===============
=============== ./requirements.txt ================
```
fastapi
uvicorn
pytest
```
---

=============== src folder ===============
=============== .py files ===============
=============== ./src/__init__.py ================
```
# This is the src init file
```
---
=============== ./src/main.py ================
```
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

```
---

=============== tests folder ===============
=============== .py files ===============
=============== ./tests/test_main.py ================
```
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}

```
---
Copied 45 lines to the clipboard.
Project Structure (Excluding specified patterns):
.
├── src
│   ├── __init__.py
│   └── main.py
├── tests
│   └── test_main.py
└── requirements.txt


**Breakdown:**

1.  **`# Project Structure`**: An initial `tree` view showing the directory layout (respecting exclusions).
2.  **`# Source Code`**: Marks the beginning of the concatenated file content.
3.  **`=============== [folder name] folder ===============`**: Header indicating the directory the following files belong to. `root` is used for files in the base directory where the script was run.
4.  **`=============== [.extension] files ===============`**: Header indicating the file type (based on extension) within the current directory. Files are sorted alphabetically by extension within each directory.
5.  **`=============== [./path/to/file] ================`**: Header clearly showing the relative path to the specific file whose content follows.
6.  **``````**: Standard Markdown code block delimiters wrapping the actual content of the file.
7.  **`(File Content)`**: The verbatim content of the file.
8.  **`---`**: A Markdown horizontal rule visually separating the content blocks of different files.
9.  **Feedback Line**: `Copied X lines to the clipboard.` tells you how much text was generated.
10. **Final Tree**: Repeats the project structure view as a reminder of the overall layout considered.

## ⚙️ Exclusion Logic Deep Dive

The script employs multiple layers of filtering:

1.  **Default `tree` Exclusions:** The initial `tree` command uses `-I` with a long pipe-separated list of patterns (defined in `tree_exclude_patterns`) including `node_modules`, `.git`, `__pycache__`, `build`, `dist`, common temporary patterns, etc.
2.  **Default `find` Path Exclusions:** The `find` command explicitly excludes paths containing components like `node_modules`, `__pycache__`, `.git`, `build`, `dist`, `venv`, etc., using `-not -path`. It also excludes hidden files/directories (`-not -path '*/.*'`) *except* for specifically included configuration files.
3.  **Specific `find` Inclusions:** Important hidden dotfiles like `.gitignore`, `.env`, `.eslintrc`, etc., are explicitly included using `-o -name ...`.
4.  **Default `find` Name/Extension Exclusions:** After finding potential candidates, `find` filters out common non-source file extensions like `.log`, `.tmp`, `.pyc`, `.o`, `.dll`, `.exe`, `.zip`, `.pdf`, `.jpg`, model files (`.pth`, `.h5`), data files (`.csv`, `.parquet`), etc., using `-not -name ...`.
5.  **Custom `--exclude` Patterns:** User-provided patterns are added to both the `tree` exclusions and the `find` name exclusions.
6.  **Size Limit:** `find ... ! -size +100M` filters out files larger than 100 Megabytes (adjust in the script if needed).
7.  **MIME Type Check:** The `while read` loop uses `file --mime-type "$file" | grep -q 'text/'` as a final check to ensure only files identified as `text/*` are included in the output.

## 🔧 Customization

For permanent changes to default exclusions or behavior (like the size limit), you can directly edit the `copy.sh` script:

*   Modify the `tree_exclude_patterns` variable.
*   Add/remove patterns in the `find` command's `-not -path` or `-not -name` sections.
*   Change the value in `! -size +100M`.

## 💻 Compatibility

*   **macOS:** Uses `pbcopy` for clipboard access.
*   **Linux:** Uses `xclip -selection clipboard` or `xsel --clipboard --input` if available.
*   **Other/No Clipboard Tool:** Falls back to printing the full output to standard output (stdout).
