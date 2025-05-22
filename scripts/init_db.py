import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from ai_client_acquisition.database.connection import init_db
from ai_client_acquisition.database.models import Base
from sqlalchemy import create_engine
from dotenv import load_dotenv

def main():
    """
    Initialize the database by creating all tables.
    """
    # Load environment variables
    load_dotenv()
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL", "sqlite:///./client_acquisition.db")
    
    # Create engine
    engine = create_engine(database_url)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    print("Database initialized successfully!")

if __name__ == "__main__":
    main() 