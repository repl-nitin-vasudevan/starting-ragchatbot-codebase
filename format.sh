#!/bin/bash
# Quick script to format code with black

echo "Formatting code with black..."
uv run black backend/ main.py

echo ""
echo "✓ Formatting complete!"
