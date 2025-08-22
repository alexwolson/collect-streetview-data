#!/bin/bash

echo "Installing Toronto StreetView Crawler..."
echo "========================================"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "🐍 Python version: $PYTHON_VERSION"

# Install the package in development mode
echo "📦 Installing package in development mode..."
python3 -m pip install -e .

if [ $? -eq 0 ]; then
    echo "✅ Package installed successfully!"
    echo ""
    echo "🎯 You can now use the following commands:"
    echo "   toronto-boundary    # Load Toronto boundary"
    echo "   toronto-panorama    # Get a single panorama"
    echo "   toronto-crawl       # Start crawling panoramas"
    echo ""
    echo "🧪 Test the installation with:"
    echo "   python3 test_package.py"
else
    echo "❌ Installation failed. Check the error messages above."
    exit 1
fi
