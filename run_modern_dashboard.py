#!/usr/bin/env python3
"""
Script to run the modern AI SEO Analyzer & Business Finder dashboard.
"""

import subprocess
import sys
import os

def main():
    """Run the modern dashboard."""
    try:
        # Check if streamlit is installed
        import streamlit
        print("🚀 Starting Modern AI SEO Analyzer & Business Finder Dashboard...")
        print("📱 The app will open in your default browser at http://localhost:8501")
        print("🔄 Press Ctrl+C to stop the server")
        print("-" * 60)
        
        # Run the modern dashboard
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "dashboard_app_modern.py",
            "--server.port", "8501",
            "--server.address", "localhost",
            "--browser.gatherUsageStats", "false"
        ])
        
    except ImportError:
        print("❌ Streamlit is not installed. Please install it first:")
        print("pip install streamlit")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped. Goodbye!")
    except Exception as e:
        print(f"❌ Error running dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 