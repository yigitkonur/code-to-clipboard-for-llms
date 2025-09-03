<h1 align="center">📦 repo-to-llm-context 📦</h1>
<h3 align="center">Stop copy-pasting code. Start shipping smarter prompts.</h3>

<p align="center">
 <strong>
    <em>the ultimate context packer for your AI coding assistant. it scans your repo, ditches the junk, and bundles the good stuff into one perfect, clipboard-ready prompt.</em>
  </strong>
</p>

<p align="center">
  <!-- Package Info -->
  <a href="#"><img alt="pypi" src="https://img.shields.io/pypi/v/repo-to-llm-context.svg?style=flat-square&color=4D87E6"></a>
  <a href="#"><img alt="python" src="https://img.shields.io/badge/python-3.6+-4D87E6.svg?style=flat-square"></a>
  &nbsp;&nbsp;•&nbsp;&nbsp;
  <!-- Features -->
  <a href="#"><img alt="license" src="https://img.shields.io/badge/License-MIT-F9A825.svg?style=flat-square"></a> 
  <a href="#"><img alt="platform" src="https://img.shields.io/badge/platform-macOS_|_Linux_|_Windows-2ED573.svg?style=flat-square"></a>
</p>

<p align="center">
  <img alt="zero config" src="https://img.shields.io/badge/⚙️_zero_config-works_out_of_the_box-2ED573.svg?style=for-the-badge">
  <img alt="clipboard ready" src="https://img.shields.io/badge/📋_clipboard_ready-one_command_to_copy-2ED573.svg?style=for-the-badge">
</p>

<div align="center">
  
### 🧭 Quick Navigation

[**⚡ Get Started**](#-get-started-in-60-seconds) • 
[**✨ Key Features**](#-feature-breakdown-the-secret-sauce) • 
[**🎮 Usage & Examples**](#-usage-fire-and-forget) • 
[**⚙️ Advanced Flags**](#️-advanced-usage--customization) •
[**🆚 Comparison**](#-why-this-slaps-other-methods)

</div>

---

**`repo-to-llm-context`** is the project manager your AI assistant wishes it had. Stop feeding your LLM random files and praying for a good answer. This tool acts like a pro developer, reading your entire project, intelligently selecting the most relevant files, and packaging them into a perfectly structured prompt so your AI can actually understand what the hell is going on.

<div align="center">
<table>
<tr>
<td align="center">
<h3>🧠</h3>
<b>Smart Filtering</b><br/>
<sub>Ditches node_modules & junk</sub>
</td>
<td align="center">
<h3>🎯</h3>
<b>Relevance Scoring</b><br/>
<sub>Puts the important code first</sub>
</td>
<td align="center">
<h3>📋</h3>
<b>Clipboard Ready</b><br/>
<sub>One command, ready to paste</sub>
</td>
</tr>
</table>
</div>

How it slaps:
-  **You:** `cd my-project && context`
-  **`context`:** Scans, filters, scores, formats, and copies.
-  **You:** `Cmd+V` into Claude/ChatGPT/Gemini.
-  **LLM:** "Ah, I see. A well-structured project. Here is your god-tier answer."

---

## 💥 Why This Slaps Other Methods

Manually prepping context is a vibe-killer. `repo-to-llm-context` makes other methods look ancient.

<table align="center">
<tr>
<td align="center"><b>❌ The Old Way (Pain)</b></td>
<td align="center"><b>✅ The `context` Way (Glory)</b></td>
</tr>
<tr>
<td>
<ol>
  <li>Open 15 files in VS Code.</li>
  <li>Frantically copy-paste into a text file.</li>
  <li>Realize you forgot the Dockerfile.</li>
  <li>Curse as you hit the token limit.</li>
  <li>Get a mediocre answer from a confused LLM.</li>
</ol>
</td>
<td>
<ol>
  <li><code>cd my-project</code></li>
  <li><code>context</code></li>
  <li>Paste.</li>
  <li>Receive genius-level insights.</li>
  <li>Go grab a coffee. ☕</li>
</ol>
</td>
</tr>
</table>

We're not just concatenating files. We're building a **high-signal, low-noise prompt** with a sophisticated scoring algorithm that knows a `README.md` is more important than a test utility, and a `main.py` is more critical than a config file deep in a subdirectory.

---

## 🚀 Get Started in 60 Seconds

The `context` command will be available in your terminal after installation.

### 🍎 macOS & 🐧 Linux: Homebrew (Recommended)
This is the cleanest, most native experience.

```bash
# 1. Add the Tap (a one-time setup)
brew tap yigitkonur/context
brew install context
```

### 🪟 Windows & Others: pipx (Recommended)
`pipx` is the gold standard for installing Python CLI tools. It keeps things tidy and isolated.

```bash
# 1. Install pipx if you don't have it
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# 2. Install the tool (from PyPI once published, or from GitHub for latest)
pipx install repo-to-llm-context
# OR for latest dev version: pipx install git+https://github.com/yigitkonur/code-to-clipboard-for-llms.git
```

> **✨ Zero Manual Setup:** After installation, the `context` command should be ready to go. If not, just restart your terminal!

---

## 🎮 Usage: Fire and Forget

The workflow is dead simple.

**1. Navigate to Your Project**
```bash
cd /path/to/your/killer-app
```

**2. Run the Command**
```bash
context
```
Your clipboard is now loaded with perfectly formatted Markdown.

**3. Paste & Prompt**
Go to your favorite LLM and paste the context. Now you can ask the real questions.

### Output Control 🕹️

Don't want it on your clipboard? No problem.

*   **Save to a file:**
    ```bash
    context --output project_context.md
    ```
*   **Print directly to your terminal (for piping or peeking):**
    ```bash
    context --stdout
    ```

---

## ✨ Feature Breakdown: The Secret Sauce

<div align="center">

| Feature | What It Does | Why You Care |
| :---: | :--- | :--- |
| **🧠 Smart Filtering**<br/>`No junk allowed` | Auto-excludes `node_modules`, `venv`, `builds`, `.git`, logs & more | Stops you from wasting tokens on garbage |
| **🎯 Relevance Scoring**<br/>`AI-optimized order` | Prioritizes files with a nuanced algorithm | Your LLM gets the most important info first |
| **🏗️ Project Tree**<br/>`Visual context` | Includes a `tree`-style view of what's included | The AI (and you) can see the project structure |
| **⚙️ Git-Aware**<br/>`Respects your repo` | Can read your `.gitignore` and check tracking status | Context matches your actual source code |
| **📋 Clipboard Ready**<br/>`Cmd+C on steroids` | Copies the entire formatted output in one go | Zero manual work between terminal and AI |
| **🔧 Hyper-Configurable**<br/>`You're the boss` | Flags to include/exclude anything you want | Fine-tune the context for any weird project |
| **🔒 Privacy First**<br/>`No path leaks` | Masks your local home directory path in the summary | Share your code, not your user folder |

</div>

---

## ⚙️ Advanced Usage & Customization

The defaults are great, but you can dial it in just right.

<details>
<summary><b>Expand for the full list of command-line flags</b></summary>

#### Filtering and Inclusion Control

*   `--include PATTERN`: Glob pattern to force inclusion of files/directories that might be excluded (e.g., `--include "config/**.yaml"`).
*   `--exclude PATTERN`: Glob pattern to add custom exclusions beyond the defaults (e.g., `--exclude "*.log"`).
*   `--include-only`: A powerful mode that includes *only* files matching `--include` patterns, excluding everything else.
*   `--exclude-extension EXT`: Exclude all files with a specific extension (e.g., `--exclude-extension .tmp`).
*   `--include-extension EXT`: Force include files with an extension that is normally excluded by default.

#### Override Default File Type Exclusions

*   `--include-json`: Include `.json` / `.jsonc` files.
*   `--include-yaml`: Include `.yaml` / `.yml` files.
*   `--include-xml`: Include `.xml` files.
*   `--include-html`: Include `.html` / `.htm` files.
*   `--include-css`: Include `.css` files.
*   `--include-sql`: Include `.sql` files.
*   `--include-csv`: Include `.csv` / `.tsv` files.
*   `--include-markdown`: Include all Markdown files, not just the root `README.md`.

#### Size and Content Control

*   `--max-size SIZE`: Exclude files larger than the specified size (e.g., `500k`, `10M`). Default is `2M`.
*   `--include-binary`: Attempt to include files detected as binary (default is to exclude them).
*   `--max-depth N`: Limit scanning to a maximum directory depth.

#### Git Integration Behavior

*   `--no-gitignore`: (Default) Ignore `.gitignore` rules and Git tracking status entirely.
*   `--gitignore-only`: Use `.gitignore` rules for exclusion but *don't* filter based on Git tracking status.
*   `--use-git`: Use both `.gitignore` rules and only include files that are tracked by Git.

#### Output and Execution Behavior

*   `--output FILE`: Write output to a file instead of the clipboard.
*   `--stdout`: Print the full output to the terminal.
*   `--no-clipboard`: Disable automatic copying to the clipboard (useful when using `--stdout` or `--output`).
*   `--preview`: Show a summary of what would be included without processing files or generating output.
*   `--dry-run`: Run the entire process but do not write any output to the clipboard, file, or stdout.
*   `--sort-alpha`: Override the relevance-based sorting and sort files alphabetically instead.

</details>

---

## 🆚 Why This Slaps Other Methods

<div align="center">

| Method | The Pain 😩 | The `context` Way 😎 |
| :--- | :--- | :--- |
| **Manual Copy/Paste** | You'll miss a file. You'll include junk. You'll hate your life. | One command. Perfect context. Every time. |
| **`cat file1 file2 > out.txt`** | Zero structure. No filtering. Still manual. Basically useless. | Auto-filters, adds a file tree, and formats beautifully. |
| **Sharing a GitHub Link** | LLM can't see local changes. Can't access private repos. | Works offline. Works on your latest, unpushed code. |
| **Simple `tree` command** | Shows structure but includes zero code content. | Gives you the full package: structure AND content. |

</div>

---

## 🛠️ For Developers & Tinkerers

### Running from Source

Want to hack on the code? Easy.

1.  **Clone the repo:**
    ```bash
    git clone https://github.com/yigitkonur/code-to-clipboard-for-llms.git
    cd code-to-clipboard-for-llms
    ```

2.  **Set up a virtual environment and install in editable mode:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -e .
    ```
    Now, any change you make to `llmcontext.py` will be live on your `context` command.

### Fork & Customize

If you fork the repo, you can permanently change the default filters by editing the constants at the top of `llmcontext.py`.

---

## 🔥 Common Issues & Quick Fixes

<details>
<summary><b>Expand for troubleshooting tips</b></summary>

| Problem | Solution |
| :--- | :--- |
| **`context: command not found`** | **Restart your terminal.** 99% of the time, this is the fix. If not, run `pipx ensurepath` (for pipx) or check your `PATH` environment variable. |
| **Clipboard isn't working** | **Linux users:** You might need a clipboard utility. Run `sudo apt install xclip` or `sudo pacman -S xclip`. For any OS, you can always use `--stdout` or `--output my_context.md` to bypass the clipboard. |
| **`.gitignore` is ignored** | By default, git integration is off for speed. Use the `--gitignore-only` or `--use-git` flag to turn it on. |
| **Script errors out** | Make sure you're on Python 3.8 or newer (`python3 --version`). |

</details>

---

<div align="center">

**Built with 🔥 because manually crafting LLM prompts is a soul-crushing waste of time.**

</div>