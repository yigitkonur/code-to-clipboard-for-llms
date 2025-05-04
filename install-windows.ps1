#!/bin/bash

GITHUB_REPO="yigitkonur/code-to-clipboard-for-llms"
SCRIPT_FILENAME="copy.py"
INSTALL_DIR="$HOME/bin"                     # Standard user script location
BIN_DIR_PIP="$HOME/.local/bin"              # Standard pip user install script location
ALIAS_NAME="context"                        # Command name for Mac/Linux
REQUIRED_PYTHON_VERSION="3.6"               # Minimum required Python version
SCRIPT_URL="https://raw.githubusercontent.com/${GITHUB_REPO}/main/${SCRIPT_FILENAME}"
SCRIPT_DEST="$INSTALL_DIR/$SCRIPT_FILENAME"
ADDED_BY_COMMENT="# Added by code-to-clipboard-for-llms installer"

# --- Helper Functions ---
info() { echo "[INFO] $1"; }
warn() { echo "[WARN] $1"; }
error() { echo "[ERROR] $1"; exit 1; }
success() { echo "[SUCCESS] $1"; }
attention() { echo "[ATTENTION] $1"; }
command_exists() { command -v "$1" >/dev/null 2>&1; }
pattern_exists_in_file() { grep -q F "$1" "$2" 2>/dev/null; } # Use -F for fixed string search

# --- Add Line Function (Simplified) ---
# Adds 'line_to_add' to 'config_file' if 'check_pattern' isn't found.
add_line_once() {
  local line_to_add="$1"
  local check_pattern="$2" # Simpler check pattern (often the line itself or key part)
  local config_file="$3"

  touch "$config_file" # Ensure file exists
  if pattern_exists_in_file "$check_pattern" "$config_file"; then
    info "'$check_pattern' found in $config_file. Skipping add."
  else
    info "Adding configuration to $config_file..."
    printf "\n%s\n%s\n" "$ADDED_BY_COMMENT" "$line_to_add" >> "$config_file"
    # Return 0 to indicate something was added
    return 0
  fi
  # Return 1 if skipped
  return 1
}

# --- Version Check Function ---
# Checks if version $1 is >= version $2
version_ge() {
    printf '%s\n%s' "$2" "$1" | sort -V -C # -V: version sort, -C: check if sorted
}

# --- Script Start ---
info "--- Starting code-to-clipboard-for-llms Installer for Linux ---"

# --- 1. Check Prerequisites: curl, python3, pip3 ---
info "Checking prerequisites..."
# Recommend packages for Debian/Ubuntu if missing
declare -a MISSING_PKGS
if ! command_exists curl; then MISSING_PKGS+=("curl"); fi
if ! command_exists python3; then MISSING_PKGS+=("python3"); fi
if ! command_exists pip3; then MISSING_PKGS+=("python3-pip"); fi # pip often separate package

if [ ${#MISSING_PKGS[@]} -ne 0 ]; then
    error <<EOF
Missing prerequisites: ${MISSING_PKGS[*]}
Please install them using your package manager.
For Debian/Ubuntu: sudo apt update && sudo apt install -y ${MISSING_PKGS[*]}
EOF
fi
PYTHON_EXEC=$(command -v python3)
PIP_EXEC=$(command -v pip3)
success "Prerequisites (curl, python3, pip3) found."

# --- 2. Check Python Version ---
info "Checking Python 3 version..."
PYTHON_VERSION=$($PYTHON_EXEC --version 2>&1 | awk '{print $2}')
if ! version_ge "$PYTHON_VERSION" "$REQUIRED_PYTHON_VERSION"; then
    error "Python version $PYTHON_VERSION is too old. Need $REQUIRED_PYTHON_VERSION+. Please upgrade."
fi
success "Python version $PYTHON_VERSION is compatible."

# --- 3. Ensure Installation Directory ---
info "Ensuring installation directory exists: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR" || error "Failed to create directory: $INSTALL_DIR"

# --- 4. Download Script ---
info "Checking for existing script: $SCRIPT_DEST"
if [[ -f "$SCRIPT_DEST" ]]; then
    info "Script already exists. Skipping download. (Delete $SCRIPT_DEST to force redownload)"
else
    info "Downloading $SCRIPT_FILENAME..."
    if curl -fsSL "$SCRIPT_URL" -o "$SCRIPT_DEST"; then
        success "Download complete."
    else
        rm -f "$SCRIPT_DEST" # Clean up partial download
        error "Download failed. Check network or URL: $SCRIPT_URL"
    fi
    info "Making script executable..."
    chmod +x "$SCRIPT_DEST" || error "Failed to set execute permission on $SCRIPT_DEST."
fi

# --- 5. Install Dependencies (--user) ---
info "Installing/updating Python dependencies (pyperclip, gitignore-parser)..."
if "$PIP_EXEC" install --user --upgrade pyperclip gitignore-parser; then
    success "Dependencies installed/updated successfully."
    # Check if ~/.local/bin is in PATH, as pip --user installs scripts there
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        warn "'$HOME/.local/bin' is not detected in your PATH."
        warn "Pip dependencies might install executables there."
        warn "Consider adding 'export PATH=\"\$HOME/.local/bin:\$PATH\"' to your shell config."
    fi
    # Check clipboard tools
    if ! command_exists xclip && ! command_exists xsel; then
         warn "'pyperclip' might need 'xclip' or 'xsel' on Linux X11 systems."
         warn "Install one if clipboard functionality fails: 'sudo apt install xclip' or 'sudo apt install xsel'"
    fi
else
    error "Failed to install Python dependencies using $PIP_EXEC. Check pip/network."
fi

# --- 6. Configure Shell (Bash/Zsh) ---
info "Detecting shell and configuring environment..."
CURRENT_SHELL=$(basename "$SHELL")
CONFIG_FILE=""
CONFIG_UPDATED=false

case "$CURRENT_SHELL" in
  zsh) CONFIG_FILE="$HOME/.zshrc" ;;
  bash) CONFIG_FILE="$HOME/.bashrc" ;; # Target .bashrc for simplicity
  *) warn "Unsupported shell: $CURRENT_SHELL. Cannot auto-configure PATH/alias."; CONFIG_FILE="UNSUPPORTED" ;;
esac

if [[ "$CONFIG_FILE" != "UNSUPPORTED" ]]; then
    info "Using config file: $CONFIG_FILE"

    # 6a. Ensure ~/bin is in PATH (for our script)
    PATH_LINE_BIN="export PATH=\"\$HOME/bin:\$PATH\""
    PATH_CHECK_BIN="\$HOME/bin:\$PATH"
    if add_line_once "$PATH_LINE_BIN" "$PATH_CHECK_BIN" "$CONFIG_FILE"; then
        CONFIG_UPDATED=true
    fi

    # 6b. Ensure ~/.local/bin is in PATH (for pip --user scripts, if not already warned about)
    # Only add if we didn't warn earlier (meaning it wasn't found)
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        PATH_LINE_LOCAL_BIN="export PATH=\"\$HOME/.local/bin:\$PATH\""
        PATH_CHECK_LOCAL_BIN="\$HOME/.local/bin:\$PATH"
        if add_line_once "$PATH_LINE_LOCAL_BIN" "$PATH_CHECK_LOCAL_BIN" "$CONFIG_FILE"; then
            CONFIG_UPDATED=true
            info "Also added \$HOME/.local/bin to PATH for pip user installs."
        fi
    fi

    # 6c. Ensure alias is set
    ALIAS_LINE="alias $ALIAS_NAME='$PYTHON_EXEC $SCRIPT_DEST'"
    ALIAS_CHECK_PATTERN="alias $ALIAS_NAME=" # Check if alias already defined
    if add_line_once "$ALIAS_LINE" "$ALIAS_CHECK_PATTERN" "$CONFIG_FILE"; then
        CONFIG_UPDATED=true
    fi
else
    attention "Manual setup needed:"
    attention "1. Add '$INSTALL_DIR' to your shell's PATH."
    attention "2. (Recommended) Add '$BIN_DIR_PIP' to your shell's PATH."
    attention "3. Create an alias: alias $ALIAS_NAME='$PYTHON_EXEC $SCRIPT_DEST'"
fi

# --- 7. Final Instructions ---
echo ""
success "--------------------------------------------------"
success "$SCRIPT_FILENAME Installation Complete!"
success "--------------------------------------------------"
info "Script installed at: $SCRIPT_DEST"
info "Alias '$ALIAS_NAME' configured to run it."
echo ""
if $CONFIG_UPDATED; then
  attention "Your shell configuration file ($CONFIG_FILE) was modified."
  attention "To apply changes, run:"
  attention "  source \"$CONFIG_FILE\""
  attention "Or open a NEW terminal window/tab."
else
  info "No changes needed in shell config ($CONFIG_FILE)."
  info "If the command doesn't work, try opening a new terminal anyway."
fi
echo ""
info "Usage: Open a NEW terminal, cd to your project, and run '$ALIAS_NAME'."
info "--- Finished ---"

exit 0