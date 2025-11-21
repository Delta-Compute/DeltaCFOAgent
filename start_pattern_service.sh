#!/bin/bash
# Start the automatic pattern validation background service

echo "=========================================="
echo "Starting Pattern Validation Service"
echo "=========================================="
echo ""
echo "This service will automatically:"
echo "1. Listen for new pattern suggestions"
echo "2. Validate them with Claude LLM"
echo "3. Create classification patterns if approved"
echo "4. Send notifications to the UI"
echo ""
echo "Press Ctrl+C to stop"
echo "=========================================="
echo ""

cd "$(dirname "$0")"
python3 web_ui/pattern_validation_service.py
