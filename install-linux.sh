#!/usr/bin/env bash

set -e # Exit on error
set -u # Treat unset variables as error
set -o pipefail # Pipesi failures count as errors

# --- Configuration ---
GITHUB_REPO="yigitkonur/code-to-clipboard-for-llms"
SCRIPT_FILENAME="copy.py"
INSTALL_BASE_DIR="$HOME/.local/share"
APP_NAME="llmcontext" # Short, safe name for dirs/files
VENV_DIR="${INSTALL_BASE_DIR}/${APP_NAME}/venv"
APP_DIR="${VENV_DIR}/app" # Where the actual script will live inside the venv dir
SCRIPT_URL="https://raw.githubusercontent.com/${GITHUB_REPO}/main/${SCRIPT_FILENAME}"
TARGET_BIN_DIR="$HOME/.local/bin" # Use standard location
COMMAND_NAME="context"
WRAPPER_SCRIPT_DEST="${TARGET_BIN_DIR}/${COMMAND_NAME}"
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=6
INSTALLER_MARKER="# Added by code-to-clipboard-for-llms (llmcontext) installer" # For idempotency

# --- Helper Functions (Colors & Interaction) ---
if command -v tput >/dev/null && tput setaf 1 >/dev/null 2>&1; then
    color_reset=$(tput sgr0); color_red=$(tput setaf 1); color_green=$(tput setaf 2)
    color_yellow=$(tput setaf 3); color_blue=$(tput setaf 4); color_bold=$(tput bold)
else
    color_reset=""; color_red=""; color_green=""; color_yellow=""; color_blue=""; color_bold=""
fi
info() { echo "${color_blue}${color_bold}[INFO]${color_reset} $1"; }
warn() { echo "${color_yellow}${color_bold}[WARN]${color_reset} $1"; }
error() { echo "${color_red}${color_bold}[ERROR]${color_reset} $1" >&2; exit 1; }
success() { echo "${color_green}${color_bold}[SUCCESS]${color_reset} $1"; }
ask() {
    local prompt="$1" response
    while true; do
        read -p "${color_yellow}${color_bold}[PROMPT]${color_reset} ${prompt} [Y/n] " -n 1 -r response
        echo ""; response=${response,,}
        if [[ -z "$response" || "$response" == "y" ]]; then return 0; # Yes
        elif [[ "$response" == "n" ]]; then return 1; # No
        else echo "Please answer 'y' or 'n'."; fi
    done
}
command_exists() { command -v "$1" >/dev/null 2>&1; }

# --- Sanity Check: Running as root? ---
if [[ "$(id -u)" -eq 0 ]]; then
    error "This script should not be run as root. Please run as a regular user."
fi

# --- 1. Detect Distro & Package Manager ---
info "Detecting Linux distribution..."
PKG_MANAGER=""
PKG_INSTALL_CMD_PREFIX=() # Array to hold sudo + command
PKG_UPDATE_CMD=()
PKG_PYTHON="python3"; PKG_PIP="python3-pip"; PKG_VENV="python3-venv";
PKG_CURL="curl"; PKG_GIT="git"; PKG_XCLIP="xclip"; PKG_XSEL="xsel"; PKG_WL_CLIPBOARD="wl-clipboard"

if command_exists lsb_release; then DISTRO=$(lsb_release -si);
elif [ -f /etc/os-release ]; then DISTRO=$(grep -oP '^ID=\K\w+' /etc/os-release);
else warn "Cannot determine Linux distribution automatically."; DISTRO="unknown"; fi
DISTRO=${DISTRO,,}

case "$DISTRO" in
    ubuntu|debian|mint)
        PKG_MANAGER="apt-get"
        PKG_UPDATE_CMD=(sudo $PKG_MANAGER update)
        PKG_INSTALL_CMD_PREFIX=(sudo $PKG_MANAGER install -y)
        info "Detected Debian/Ubuntu based system."
        ;;
    arch|manjaro)
        PKG_MANAGER="pacman"
        PKG_PIP="python-pip"; PKG_VENV="python-venv"
        # No separate update needed, -Syu does it
        PKG_INSTALL_CMD_PREFIX=(sudo $PKG_MANAGER -Syu --noconfirm)
        info "Detected Arch Linux based system."
        ;;
    *)
        warn "Unsupported distribution '$DISTRO'. Prerequisite installation must be done manually."
        PKG_MANAGER="your_package_manager"
        ;;
esac

# --- 2. Check Sudo Capability ---
SUDO_ACCESS=false
if command_exists sudo; then
    if sudo -n true >/dev/null 2>&1; then
        info "Passwordless sudo detected."
        SUDO_ACCESS=true
    elif sudo -v >/dev/null 2>&1; then
        info "Sudo access requires password."
        SUDO_ACCESS=true
    else
        warn "User does not seem to have sudo privileges or 'sudo' command is misconfigured."
    fi
else
    warn "'sudo' command not found."
fi

# Helper function to run install commands
install_packages() {
    if ! $SUDO_ACCESS; then
        error "Cannot install packages without working sudo access. Please install manually: $*"
    fi
    if [[ ${#PKG_UPDATE_CMD[@]} -gt 0 ]]; then
        info "Running package list update (${PKG_UPDATE_CMD[*]})..."
        if ! "${PKG_UPDATE_CMD[@]}"; then
            warn "Package list update failed. Continuing installation attempt..."
        fi
    fi
    info "Attempting installation of: $*"
    if "${PKG_INSTALL_CMD_PREFIX[@]}" "$@"; then
        success "Successfully installed: $*"
    else
        error "Failed to install packages: $*. Please install them manually and re-run."
    fi
}

# --- 3. Check Prerequisites ---
info "Checking prerequisites..."
REQUIRED_PKGS=("$PKG_PYTHON" "$PKG_PIP" "$PKG_VENV" "$PKG_CURL" "$PKG_GIT")
MISSING_PKGS=()
for pkg in "${REQUIRED_PKGS[@]}"; do
    cmd_to_check="$pkg"; py_module=""
    case "$pkg" in
        python3-pip|python-pip) cmd_to_check="pip3" ;;
        python3-venv|python-venv) py_module="venv" ;; # Check as python module
    esac

    if [[ -n "$py_module" ]]; then
        if ! python3 -c "import $py_module" >/dev/null 2>&1; then MISSING_PKGS+=("$pkg"); fi
    elif ! command_exists "$cmd_to_check"; then MISSING_PKGS+=("$pkg"); fi
done

if [ ${#MISSING_PKGS[@]} -ne 0 ]; then
    warn "The following required packages seem to be missing: ${color_yellow}${MISSING_PKGS[*]}${color_reset}"
    if [[ "$PKG_MANAGER" == "your_package_manager" ]]; then
        error "Please install them manually using your system's package manager and re-run the script."
    fi
    if ask "Do you want to attempt automatic installation using '$PKG_MANAGER'?"; then
        install_packages "${MISSING_PKGS[@]}"
    else
        error "Prerequisites missing. Aborting installation."
    fi
else
    success "Core prerequisites seem installed."
fi

# --- 4. Check Python Version ---
info "Checking Python version..."
PYTHON_EXEC=$(command -v python3)
if ! "$PYTHON_EXEC" -c "import sys; exit(not (sys.version_info >= ($MIN_PYTHON_MAJOR, $MIN_PYTHON_MINOR)))"; then
    PYTHON_VERSION=$($PYTHON_EXEC --version)
    error "Python version $PYTHON_VERSION is too old. Version $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR or higher required."
fi
success "Python version check passed ($($PYTHON_EXEC --version))."

# --- 5. Check Clipboard Utilities ---
info "Checking for clipboard utilities..."
CLIPBOARD_TOOL_FOUND=false
CLIPBOARD_TOOL_PKG=""
if command_exists $PKG_XCLIP; then CLIPBOARD_TOOL_FOUND=true; CLIPBOARD_TOOL_PKG=$PKG_XCLIP;
elif command_exists $PKG_XSEL; then CLIPBOARD_TOOL_FOUND=true; CLIPBOARD_TOOL_PKG=$PKG_XSEL;
elif command_exists wl-copy && command_exists wl-paste; then CLIPBOARD_TOOL_FOUND=true; CLIPBOARD_TOOL_PKG=$PKG_WL_CLIPBOARD; fi

if $CLIPBOARD_TOOL_FOUND; then
    success "Found clipboard utility ('$CLIPBOARD_TOOL_PKG')."
else
    warn "No common clipboard utility (xclip, xsel, wl-clipboard) found."
    warn "The '$COMMAND_NAME' script needs one of these to copy to clipboard."
    CLIPBOARD_CHOICES=("$PKG_XCLIP" "$PKG_XSEL" "$PKG_WL_CLIPBOARD")
    PKG_TO_INSTALL=$PKG_XCLIP # Default suggestion
    if [[ "$XDG_SESSION_TYPE" == "wayland" ]]; then PKG_TO_INSTALL="$PKG_WL_CLIPBOARD"; fi

    if [[ "$PKG_MANAGER" != "your_package_manager" ]]; then
        if ask "Do you want to install '$PKG_TO_INSTALL'? (Recommended for clipboard functionality)"; then
            install_packages "$PKG_TO_INSTALL"
        else
            warn "Skipping clipboard utility installation. The '--stdout' or '--output' flags will be needed."
        fi
    else
        warn "Please manually install a clipboard utility like ${CLIPBOARD_CHOICES[*]} for clipboard functionality."
    fi
fi

# --- 6. Setup Directories & Python Virtual Environment ---
info "Ensuring directories and Python virtual environment..."
mkdir -p "$TARGET_BIN_DIR" || error "Failed to create script directory: $TARGET_BIN_DIR"
mkdir -p "$APP_DIR" || error "Failed to create application directory: $APP_DIR" # Creates base dir too

VENV_PYTHON="${VENV_DIR}/bin/python"
if [ -f "$VENV_PYTHON" ]; then
    info "Virtual environment already exists ($VENV_DIR)."
else
    info "Creating Python virtual environment in $VENV_DIR..."
    if "$PYTHON_EXEC" -m venv "$VENV_DIR"; then
        success "Virtual environment created."
    else
        error "Failed to create virtual environment in $VENV_DIR. Check permissions or disk space."
    fi
fi

# --- 7. Install Dependencies into Venv ---
info "Installing dependencies (pyperclip, gitignore-parser) into virtual environment..."
VENV_PIP="${VENV_DIR}/bin/pip"
# Use --disable-pip-version-check for cleaner output, handle errors with set -e
if "$VENV_PIP" install --upgrade --disable-pip-version-check pip >/dev/null && \
   "$VENV_PIP" install --upgrade --disable-pip-version-check pyperclip gitignore-parser; then
    success "Dependencies installed successfully in virtual environment."
else
    error "Failed to install dependencies into virtual environment. Check network or $VENV_PIP logs."
fi

# --- 8. Download the Script ---
SCRIPT_DEST_IN_VENV="${APP_DIR}/${SCRIPT_FILENAME}"
info "Downloading $SCRIPT_FILENAME to $SCRIPT_DEST_IN_VENV..."
if curl --fail --silent --show-error --location "$SCRIPT_URL" --output "$SCRIPT_DEST_IN_VENV"; then
    chmod +x "$SCRIPT_DEST_IN_VENV" || warn "Could not make $SCRIPT_DEST_IN_VENV executable."
    success "Script downloaded."
else
    rm -f "$SCRIPT_DEST_IN_VENV" # Clean up partial download
    error "Download failed from $SCRIPT_URL. Check URL or network connection."
fi

# --- 9. Create Wrapper Script ---
info "Creating wrapper script at $WRAPPER_SCRIPT_DEST..."
read -r -d '' WRAPPER_CONTENT << EOM
#!/usr/bin/env bash
# Wrapper for ${COMMAND_NAME}, activates venv and runs the script.
# ${INSTALLER_MARKER}
exec "${VENV_DIR}/bin/python" "${SCRIPT_DEST_IN_VENV}" "\$@"
EOM
echo "$WRAPPER_CONTENT" > "$WRAPPER_SCRIPT_DEST"
chmod +x "$WRAPPER_SCRIPT_DEST" || error "Failed to make wrapper script executable: $WRAPPER_SCRIPT_DEST"
success "Wrapper script created."

# --- 10. Configure Shell Environment (Simplified PATH Check) ---
info "Configuring shell environment for PATH..."
CURRENT_SHELL=$(basename "$SHELL")
CONFIG_FILE=""
CONFIG_UPDATED=false

case "$CURRENT_SHELL" in
  zsh) CONFIG_FILE="$HOME/.zshrc" ;;
  bash) CONFIG_FILE="$HOME/.bashrc" ;;
  *) warn "Unsupported shell: $CURRENT_SHELL. Cannot automatically configure PATH.";;
esac

if [[ -n "$CONFIG_FILE" ]]; then
    info "Checking shell configuration file: $CONFIG_FILE"
    touch "$CONFIG_FILE" # Ensure file exists

    # Simple Check: Add PATH entry ONLY if our specific marker isn't already present
    if grep -q F -- "$INSTALLER_MARKER" "$CONFIG_FILE"; then
        info "$TARGET_BIN_DIR seems already configured by this installer in $CONFIG_FILE."
    else
        info "Adding $TARGET_BIN_DIR to PATH in $CONFIG_FILE..."
        # Add a blank line for separation if file isn't empty and doesn't end with newline
        [[ -s "$CONFIG_FILE" && "$(tail -c 1 "$CONFIG_FILE")" != "" ]] && printf "\n" >> "$CONFIG_FILE"
        printf "\n%s\n" "$INSTALLER_MARKER" >> "$CONFIG_FILE"
        printf "export PATH=\"%s:\$PATH\"\n" "$TARGET_BIN_DIR" >> "$CONFIG_FILE"
        success "$TARGET_BIN_DIR added to PATH configuration."
        CONFIG_UPDATED=true
    fi
else
    warn "Please add '$TARGET_BIN_DIR' to your shell's PATH manually."
fi

# --- 11. Final Instructions ---
echo ""
success "Installation process complete!"
echo "--------------------------------------------------"
info "Installed '${COMMAND_NAME}' command script to: ${WRAPPER_SCRIPT_DEST}"
info "Python script and dependencies are isolated in: ${VENV_DIR}"
echo ""
if $CONFIG_UPDATED; then
    warn "Your shell configuration file ($CONFIG_FILE) was modified."
    warn "To apply the changes for the current session, run:"
    warn "${color_yellow}  source \"$CONFIG_FILE\"${color_reset}"
    warn "Or simply open a new terminal window/tab."
elif [[ -n "$CONFIG_FILE" ]]; then
    info "No changes needed in shell configuration file ($CONFIG_FILE)."
    info "If '$TARGET_BIN_DIR' was already in your PATH, the command should be available."
fi
info "If the command is not found, try opening a new terminal first."
echo ""
info "You can now navigate to any project folder and run:"
info "${color_green}  context${color_reset}"
echo "--------------------------------------------------"

exit 0