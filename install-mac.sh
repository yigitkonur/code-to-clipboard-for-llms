#!/usr/bin/env bash
set -e
set -o pipefail

# --- Configuration ---
ALIAS_NAME="context" # Safe alias
GITHUB_REPO="yigitkonur/code-to-clipboard-for-llms"
SCRIPT_FILENAME="copy.py"
INSTALL_DIR="$HOME/bin"          # Install location for the script itself
LOCAL_BIN_DIR="$HOME/.local/bin" # Standard location for pip --user executables
GIT_RAW_BASE_URL="https://raw.githubusercontent.com/${GITHUB_REPO}/main"
SCRIPT_URL="${GIT_RAW_BASE_URL}/${SCRIPT_FILENAME}"
SCRIPT_DEST="$INSTALL_DIR/$SCRIPT_FILENAME"
# Unique identifier comment for config changes
ADDED_BY_COMMENT="# Added by code-to-clipboard-for-llms installer ($ALIAS_NAME)"

# --- Color Definitions ---
COLOR_RESET="\033[0m"
COLOR_INFO="\033[34m"
COLOR_SUCCESS="\033[32m"
COLOR_WARN="\033[33m"
COLOR_ERROR="\033[31m"
COLOR_CMD="\033[36m"

# --- Helper Functions ---
log() {
    local level="$1" msg="$2" color_var="COLOR_$level"
    printf "${!color_var:-}[%s] %s${COLOR_RESET}\n" "$level" "$msg" >&2
    if [[ "$level" == "ERROR" ]]; then exit 1; fi
}
command_exists() { command -v "$1" >/dev/null 2>&1; }
marker_exists_in_file() { grep -qF -- "$1" "$2" 2>/dev/null; }

add_lines_once() {
    local marker="$1" config_file="$2"
    shift 2
    mkdir -p "$(dirname "$config_file")" && touch "$config_file"
    if marker_exists_in_file "$marker" "$config_file"; then
        log "INFO" "Configuration marker present in $config_file. Skipping add."
        return 1
    fi
    log "INFO" "Adding configuration to $config_file..."
    printf "\n%s\n" "$marker" >> "$config_file"
    for line_to_add in "$@"; do printf "%s\n" "$line_to_add" >> "$config_file"; done
    return 0
}

# --- 1. Prerequisite Checks ---
log "INFO" "Checking prerequisites..."
REQUIRED_CMDS=("curl" "python3" "pip3" "git" "pbcopy")
MISSING_CMDS=()
for cmd in "${REQUIRED_CMDS[@]}"; do
    if ! command_exists "$cmd"; then MISSING_CMDS+=("$cmd"); fi
done
if [[ ${#MISSING_CMDS[@]} -gt 0 ]]; then
    log "ERROR" "Missing required commands: ${MISSING_CMDS[*]}. Please install them (e.g., via Homebrew or Xcode Command Line Tools) and rerun."
fi
# Check Xcode CLT separately as it's a common macOS need for dev tools
if ! xcode-select -p >/dev/null 2>&1; then
    log "WARN" "Xcode Command Line Tools not found (xcode-select -p failed)."
    log "WARN" "These might be needed for 'pip' or 'git'. If errors occur later, run:"
    log "CMD" "xcode-select --install"
fi
log "SUCCESS" "Prerequisites checks passed."

# --- 2. Determine Python & Pip Executables ---
log "INFO" "Determining Python 3 and Pip 3 executables..."
PYTHON_EXEC=$(which python3)
PIP_EXEC=$(which pip3)
log "INFO" "Using Python 3: $PYTHON_EXEC"
log "INFO" "Using Pip 3: $PIP_EXEC"

# --- 3. Ensure Installation Directory ---
log "INFO" "Ensuring installation directory exists: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR" # set -e handles failure
log "SUCCESS" "Installation directory ready: $INSTALL_DIR"

# --- 4. Download Script ---
log "INFO" "Downloading $SCRIPT_FILENAME to $SCRIPT_DEST..."
if curl -fsSL "$SCRIPT_URL" -o "$SCRIPT_DEST"; then
    log "SUCCESS" "Download complete."
else
    rm -f "$SCRIPT_DEST" >/dev/null 2>&1 || true # Clean up partial download
    log "ERROR" "Download failed from $SCRIPT_URL."
fi

# --- 5. Make Script Executable ---
log "INFO" "Making script executable: $SCRIPT_DEST"
chmod +x "$SCRIPT_DEST" # set -e handles failure
log "SUCCESS" "Script is now executable."

# --- 6. Install Dependencies (using --user) ---
log "INFO" "Installing Python dependencies (pyperclip, gitignore-parser) using --user..."
PIP_INSTALL_CMD=("$PIP_EXEC" "install" "--upgrade" "--user" "pyperclip" "gitignore-parser")
log "CMD" "${PIP_INSTALL_CMD[*]}"
if "${PIP_INSTALL_CMD[@]}"; then
    log "SUCCESS" "Python dependencies installed/updated successfully (user-level)."
else
    log "ERROR" "Failed to install Python dependencies. Check pip output, network, and permissions."
fi

# --- 7. Configure Shell Environment (Bash / Zsh) ---
log "INFO" "Detecting shell and configuring environment..."
CURRENT_SHELL=$(basename "$SHELL")
CONFIG_FILE=""
CONFIG_UPDATED=false

case "$CURRENT_SHELL" in
  zsh) CONFIG_FILE="$HOME/.zshrc" ;;
  bash)
    # Prefer .bash_profile for login shells on macOS, ensure it sources .bashrc
    if [[ -f "$HOME/.bash_profile" ]]; then
        CONFIG_FILE="$HOME/.bash_profile"
        # Add reminder to source .bashrc if not already done
        if ! grep -qE 'source.*(\.bashrc|bashrc)' "$CONFIG_FILE" 2>/dev/null; then
             log "WARN" "$CONFIG_FILE does not seem to source '$HOME/.bashrc'. Consider adding: [[ -f ~/.bashrc ]] && source ~/.bashrc"
        fi
    elif [[ -f "$HOME/.bashrc" ]]; then
        CONFIG_FILE="$HOME/.bashrc" # Fallback if no .bash_profile
    else
        CONFIG_FILE="$HOME/.bash_profile" # Create .bash_profile if neither exists
    fi
    ;;
  *)
    log "WARN" "Unsupported shell: $CURRENT_SHELL. Skipping automatic PATH/alias setup."
    log "WARN" "Please manually add '$INSTALL_DIR' and '$LOCAL_BIN_DIR' to your PATH,"
    log "WARN" "and create an alias: alias $ALIAS_NAME='$PYTHON_EXEC $SCRIPT_DEST'"
    CONFIG_FILE="" # Prevent further processing
    ;;
esac

if [[ -n "$CONFIG_FILE" ]]; then
    log "INFO" "Using configuration file: $CONFIG_FILE"

    # 7a. Ensure necessary directories are in PATH
    PATH_MODIFIED=false
    PATH_LINE_BIN="export PATH=\"$INSTALL_DIR:\$PATH\""
    PATH_MARKER_BIN="$ADDED_BY_COMMENT (PATH for $INSTALL_DIR)"
    if add_lines_once "$PATH_MARKER_BIN" "$CONFIG_FILE" "$PATH_LINE_BIN"; then
        CONFIG_UPDATED=true PATH_MODIFIED=true
    fi

    # Add ~/.local/bin because we used --user
    if [[ -d "$LOCAL_BIN_DIR" && "$LOCAL_BIN_DIR" != "$INSTALL_DIR" ]]; then # Check if exists and differs from ~/bin
        PATH_LINE_LOCAL="export PATH=\"$LOCAL_BIN_DIR:\$PATH\""
        PATH_MARKER_LOCAL="$ADDED_BY_COMMENT (PATH for $LOCAL_BIN_DIR)"
        if add_lines_once "$PATH_MARKER_LOCAL" "$CONFIG_FILE" "$PATH_LINE_LOCAL"; then
            CONFIG_UPDATED=true PATH_MODIFIED=true
        fi
    fi
    if ! $PATH_MODIFIED; then log "INFO" "Required PATH entries seem already configured."; fi

    # 7b. Ensure alias is set
    ALIAS_LINE="alias $ALIAS_NAME='$PYTHON_EXEC $SCRIPT_DEST'"
    ALIAS_MARKER="$ADDED_BY_COMMENT (Alias for $ALIAS_NAME)"
    # Check if alias command exists *outside* our marker block first
    if ! marker_exists_in_file "$ALIAS_MARKER" "$CONFIG_FILE"; then
         if alias "$ALIAS_NAME" >/dev/null 2>&1 || declare -f "$ALIAS_NAME" >/dev/null 2>&1; then
             log "WARN" "Alias/function '$ALIAS_NAME' already exists (defined elsewhere?). Skipping automatic alias add."
         elif add_lines_once "$ALIAS_MARKER" "$CONFIG_FILE" "$ALIAS_LINE"; then
             CONFIG_UPDATED=true
         fi
    else
        log "INFO" "Alias '$ALIAS_NAME' seems already configured by this script."
    fi
else
    # This block executes if shell was unsupported or CONFIG_FILE determination failed
    if [[ "$CURRENT_SHELL" != "zsh" && "$CURRENT_SHELL" != "bash" ]]; then
        log "SUCCESS" "Script downloaded and dependencies installed. Manual shell configuration needed."
    else
        log "WARN" "Could not determine or modify shell config file. Manual setup required."
    fi
fi

# --- 8. Final Instructions ---
echo ""
log "SUCCESS" "--------------------------------------------------"
log "SUCCESS" " Installation complete!"
log "SUCCESS" "--------------------------------------------------"
log "INFO" "Script: $SCRIPT_DEST"
log "INFO" "Alias:  $ALIAS_NAME"
log "INFO" "Python Dependencies installed via --user method."
echo ""
if $CONFIG_UPDATED; then
  log "WARN" "ACTION REQUIRED: Your shell configuration file ($CONFIG_FILE) was modified."
  log "WARN" "Run the following command to apply changes to your current session:"
  log "CMD" "  source \"$CONFIG_FILE\""
  log "WARN" "Or, open a new terminal tab/window."
else
  log "INFO" "No changes made to shell configuration ($CONFIG_FILE)."
  log "INFO" "If the '$ALIAS_NAME' command doesn't work, try 'source \"$CONFIG_FILE\"' or open a new terminal."
fi
echo ""
log "INFO" "Usage: cd /path/to/project && $ALIAS_NAME"
log "SUCCESS" "--------------------------------------------------"

exit 0