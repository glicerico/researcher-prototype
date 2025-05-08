#!/bin/bash

# Script to visualize the LangGraph topology using Graphviz
# This wrapper automatically activates the virtual environment

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Path to the virtual environment
VENV_PATH="$SCRIPT_DIR/backend/venv"
VISUALIZATION_SCRIPT="$SCRIPT_DIR/backend/visualize_graph.py"

# Check if the --update flag is provided
UPDATE_LANGGRAPH=false
DIRECT_PARSE=false
ARGS=()

for arg in "$@"; do
    if [ "$arg" == "--update" ]; then
        UPDATE_LANGGRAPH=true
    elif [ "$arg" == "--direct-parse" ]; then
        DIRECT_PARSE=true
        ARGS+=("--direct-parse")
    else
        ARGS+=("$arg")
    fi
done

# Check if graphviz is installed
if ! command -v dot &> /dev/null; then
    echo "Error: Graphviz is not installed. Install it with:"
    echo "sudo apt-get install graphviz"
    exit 1
fi

# Check if the virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    echo "Make sure you have set up the backend environment correctly."
    echo "Run: cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if the visualization script exists
if [ ! -f "$VISUALIZATION_SCRIPT" ]; then
    echo "Error: Visualization script not found at $VISUALIZATION_SCRIPT"
    exit 1
fi

# Make the script executable if it isn't already
chmod +x "$VISUALIZATION_SCRIPT"

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Update LangGraph if requested
if [ "$UPDATE_LANGGRAPH" = true ]; then
    echo "Updating LangGraph and related packages..."
    pip install -U langgraph langchain-core langchain-community
    echo "Update completed."
fi

# Attempt to install pygraphviz if not already installed
if ! pip show pygraphviz &> /dev/null; then
    echo "Attempting to install pygraphviz..."
    # Try the normal installation first
    if pip install pygraphviz 2>/dev/null; then
        echo "pygraphviz installed successfully."
    else
        echo "Standard pygraphviz installation failed."
        echo "This is likely due to missing graphviz development headers."
        echo ""
        echo "INFO: You can install the required development headers with:"
        echo "sudo apt-get install graphviz-dev"
        echo ""
        echo "Then you can install pygraphviz with:"
        echo "pip install pygraphviz --install-option=\"--include-path=/usr/include/graphviz\" --install-option=\"--library-path=/usr/lib/graphviz/\""
        echo ""
        echo "Continuing with direct source parsing instead..."
        # Add direct-parse to arguments if not already present
        if ! [[ " ${ARGS[*]} " =~ " --direct-parse " ]]; then
            ARGS+=("--direct-parse")
        fi
    fi
fi

# Run the visualization script
python "$VISUALIZATION_SCRIPT" "${ARGS[@]}"

# Deactivate the virtual environment
deactivate 