import logging
from .ui import StreamlitUI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the Sports Marketing Video Generator application"""
    ui = StreamlitUI()
    ui.run()

if __name__ == "__main__":
    main()