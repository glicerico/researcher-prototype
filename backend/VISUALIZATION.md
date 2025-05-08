# LangGraph Visualization with Graphviz

This document explains how to visualize the LangGraph topology using Graphviz.

## Prerequisites

The visualization script requires Graphviz and the same dependencies as the backend application:

```bash
# Install Graphviz and its development headers
sudo apt-get install graphviz graphviz-dev

# Navigate to the project root
cd /path/to/researcher-prototype

# Activate the virtual environment
source backend/venv/bin/activate
```

The script will automatically attempt to install pygraphviz in your virtual environment if it's not already installed. If this fails due to missing development headers, the script will fall back to direct source parsing.

## Usage

The script generates a PNG visualization of your LangGraph structure:

```bash
# Generate a PNG visualization (default output: graph.png)
./visualize_graph.sh

# Specify an output file
./visualize_graph.sh --output my_graph.png

# Use direct source parsing (most reliable)
./visualize_graph.sh --direct-parse
```

## Visualization Method

The script uses Graphviz to generate high-quality PNG images:

1. Extracts the graph structure from your LangGraph code
2. Generates a DOT file representation
3. Uses the Graphviz 'dot' command to render the PNG image
4. Saves the image to a file (default: graph.png)

This approach produces professional-quality vector-based visualizations that can be used in documentation and presentations.

## Fallback Mode

If pygraphviz installation fails, the script automatically falls back to direct source code parsing mode, which:

1. Still generates a proper visualization
2. Doesn't require Python bindings for Graphviz
3. Works as long as the 'dot' command is available

This ensures you can still get a visualization even without the full development environment.

## Troubleshooting

### LangGraph Version Issues

If you encounter errors related to LangGraph versions or missing methods, you have several options:

#### Option 1: Use the --direct-parse flag (Most Reliable)

The visualization script can bypass importing the LangGraph module altogether and extract the graph structure directly from the source code:

```bash
./visualize_graph.sh --direct-parse
```

This option:
- Works regardless of LangGraph version compatibility
- Doesn't require any module imports
- Extracts the graph structure directly from the Python source code
- Is the most reliable method if you're experiencing issues

#### Option 2: Use the --update flag

The visualization script includes an `--update` flag that will automatically update LangGraph and related packages:

```bash
./visualize_graph.sh --update
```

This will update `langgraph`, `langchain-core`, and `langchain-community` packages to their latest versions.

#### Option 3: Manual Update

If you prefer to update packages manually:

```bash
# Activate the virtual environment
source backend/venv/bin/activate

# Update LangGraph and related packages
pip install -U langgraph langchain-core langchain-community
```

### Graphviz Issues

If you encounter problems with the Graphviz installation:

1. Ensure Graphviz is properly installed: `sudo apt-get install --reinstall graphviz`
2. Make sure the required development libraries are available: `sudo apt-get install graphviz-dev`
3. If pygraphviz installation fails with compilation errors, you can install it with specific options:
   ```bash
   pip install pygraphviz --install-option="--include-path=/usr/include/graphviz" --install-option="--library-path=/usr/lib/graphviz/"
   ```
4. If all else fails, use the direct parsing mode: `./visualize_graph.sh --direct-parse`

## Integration with Development Workflow

You can use this visualization to:
1. Understand the flow of your application
2. Debug issues with the graph structure
3. Document your application architecture
4. Track changes to the graph structure over time

## Example: Embedding in Documentation

To include the Mermaid diagram in your Markdown documentation:

```