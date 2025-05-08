#!/bin/bash

# Simple script to visualize LangGraph as PNG for debugging

# Check if graphviz is installed
if ! command -v dot &> /dev/null; then
    echo "Error: Graphviz not installed. Run: sudo apt-get install graphviz"
    exit 1
fi

# Generate a temporary DOT file
cat > graph.dot << 'EOL'
digraph LangGraph {
    rankdir=TB;
    node [shape=box, style=filled, fontname="Arial"];
    orchestrator [label="🔄 orchestrator", fillcolor="#f9d5e5"];
    router [label="🔀 router", fillcolor="#eeeeee"];
    chat [label="💬 chat", fillcolor="#d5f9e8"];
    search [label="🔍 search", fillcolor="#e5f9d5"];
    analyzer [label="📊 analyzer", fillcolor="#d5e5f9"];
    END [label="END", shape=oval, fillcolor="#f5f5f5"];
    orchestrator -> router;
    router -> chat [label=" chat "];
    router -> search [label=" search "];
    router -> analyzer [label=" analyzer "];
    chat -> END;
    search -> END;
    analyzer -> END;
}
EOL

# Generate PNG from DOT file
dot -Tpng graph.dot -o graph.png

echo "Graph visualization created: graph.png" 