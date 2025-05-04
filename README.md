# Code-to-Clipboard-for-LLMs

**Intelligently package your project's code context for Large Language Models.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/) [![Platform](https://img.shields.io/badge/platform-osx%20%7C%20linux%20%7C%20windows-lightgrey.svg)]() [![GitHub Stars](https://img.shields.io/github/stars/yigitkonur/code-to-clipboard-for-llms?style=social)](https://github.com/yigitkonur/code-to-clipboard-for-llms)

Interacting with LLMs like ChatGPT, Claude, Gemini or apps like [Thinkbuddy](https://thinkbuddy.ai) 💫 about your codebase often requires providing substantial context. Manually selecting, copying, and formatting relevant files is time-consuming, error-prone, and inefficient, especially when dealing with context window limits and token costs.

`code-to-clipboard-for-llms` streamlines this process. It's a Python script that automatically:

1.  **Scans** your project directory.
2.  **Filters** out irrelevant files and noise (like `node_modules`, build artifacts, `.git`).
3.  **Structures** the relevant code logically.
4.  **Formats** everything into clean Markdown, optimized for LLMs.
5.  **Copies** the result directly to your clipboard.

Spend less time preparing context and more time getting valuable insights from your AI assistant.

---

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

## 🚀 Quick Installation (Recommended)

The easiest way to get started is using the provided installers. They handle downloading the script, setting up the necessary PATH environment variable, installing dependencies, and creating a convenient command alias (`context` on macOS/Linux, `copyc` on Windows).

**Choose your operating system and run the corresponding one-line command in your terminal:**

### macOS / Linux (Bash or Zsh)

```bash
# For macOS:
bash -c "$(curl -fsSL https://raw.githubusercontent.com/yigitkonur/code-to-clipboard-for-llms/main/install-mac.sh)"

# For Linux (Debian/Ubuntu based tested):
bash -c "$(curl -fsSL https://raw.githubusercontent.com/yigitkonur/code-to-clipboard-for-llms/main/install-linux.sh)"
```

### Windows (PowerShell 5.1+)

```powershell
# Ensure PowerShell can run scripts (you might need to run as Administrator or adjust policy: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser)
iex "& {$(irm 'https://raw.githubusercontent.com/yigitkonur/code-to-clipboard-for-llms/main/install-windows.ps1')}"
```

**➡️ Important:** After installation, **close and reopen your terminal** window or tab. This is necessary for the new command and PATH changes to take effect.

---

## ▶️ Basic Usage

Using the tool is designed to be simple:

1.  Install by extremely easy scripts to follow:
    ```bash
    git clone https://github.com/yigitkonur/code-to-clipboard-for-llms/
    cd code-to-clipboard-for-llms && chmod +x install-mac.sh && ./install-mac.sh
    ```
2.  Run the command:
    *   macOS/Linux: `context` (some people, incl **me** use `copy`)
    *   Windows: `copyc` (you can change it by editing powershell script)
    ```bash
    context # Or copyc on Windows
    ```
3.  The script will process the project and copy the formatted Markdown context to your clipboard.
4.  Paste the content into your LLM prompt and ask your question.

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

For persistent changes, you can modify the default lists directly within the `copy.py` script:

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

## 🛠️ Manual Installation (Alternative)

If you prefer not to use the installers:

1.  **Prerequisites:** Ensure Python 3 (3.6+ recommended) and pip are installed.
2.  **(Optional but Recommended) Install Dependencies:** For clipboard and `.gitignore` support:
    ```bash
    pip install --user pyperclip gitignore-parser
    # Or pip3, depending on your system setup
    ```
3.  **Download:** Get the `copy.py` script from this repository (e.g., via `curl` or by downloading the repo):
    ```bash
    curl -fLo copy.py https://raw.githubusercontent.com/yigitkonur/code-to-clipboard-for-llms/main/copy.py
    ```
4.  **Move to PATH:** Place `copy.py` in a directory included in your system's PATH. A common choice is `~/bin` on Linux/macOS or a dedicated scripts folder on Windows.
    ```bash
    mkdir -p ~/bin && mv copy.py ~/bin/
    ```
5.  **Make Executable (Linux/macOS):**
    ```bash
    chmod +x ~/bin/copy.py
    ```
6.  **Add to PATH (if needed):** Ensure the directory (e.g., `~/bin`) is in your PATH environment variable. This often involves editing shell configuration files (`~/.zshrc`, `~/.bashrc`, `~/.bash_profile`) or system environment variables (Windows). Example for `~/.bashrc` or `~/.zshrc`:
    ```bash
    # Add this line if ~/bin is not in your PATH
    export PATH="$HOME/bin:$PATH"
    ```
7.  **(Optional) Create Alias:** For easier use, add an alias to your shell configuration file:
    ```bash
    # Add this line after the PATH export
    alias context='python3 $HOME/bin/copy.py'
    ```
8.  **Reload Shell:** Apply changes by restarting your terminal or sourcing the config file (e.g., `source ~/.bashrc`).

---

## ❓ Troubleshooting

Common issues and potential solutions:

<details>
<summary><strong>Expand for troubleshooting tips</strong></summary>

*   **`context: command not found` / `copyc: command not found`:**
    *   Did you restart your terminal after installation? (Most common fix)
    *   Is the script's directory (`~/bin` or `Scripts`) correctly added to your system's PATH? Verify with `echo $PATH` (Linux/Mac) or `echo $env:Path` (PowerShell).
    *   (Manual Install) Did you correctly set up the alias in your shell config file? Check with `alias context`.
    *   (Manual Install) Did you source your shell config file after editing?

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
