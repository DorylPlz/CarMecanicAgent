"""
Mechanical agent configuration.
Defines vehicle data and file paths.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables automatically when config is imported
load_dotenv()


class VehicleConfig(BaseModel):
    """Vehicle configuration."""
    model: str
    year: int
    vin: str
    manual_pdf_path: str = os.getenv("VEHICLE_MANUAL_PDF_PATH", "service_manual.pdf")
    
    def __str__(self) -> str:
        return f"{self.model} {self.year} (VIN: {self.vin})"


class ManualPdfPathDescriptor:
    """Descriptor for MANUAL_PDF_PATH that calculates dynamically."""
    def __get__(self, obj, objtype=None):
        if objtype is None:
            objtype = type(obj)
        
        # If vehicle is configured, use its manual_pdf_path
        if objtype.vehicle and objtype.vehicle.manual_pdf_path:
            manual_path = objtype.vehicle.manual_pdf_path
            # If it's a relative path, make it relative to BASE_DIR
            if not Path(manual_path).is_absolute():
                return objtype.BASE_DIR / manual_path
            return Path(manual_path)
        
        # Otherwise, use .env or default
        default_path = os.getenv("VEHICLE_MANUAL_PDF_PATH", "service_manual.pdf")
        return objtype.BASE_DIR / default_path


class Config:
    """Global agent configuration."""
    
    # API Keys
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # LLM Model configuration (configurable via .env)
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    
    # Vehicle configuration (loaded from .env or can be configured manually)
    vehicle: Optional[VehicleConfig] = None
    
    @classmethod
    def load_vehicle_from_env(cls):
        """Loads vehicle configuration from environment variables."""
        model = os.getenv("VEHICLE_MODEL", "")
        year_str = os.getenv("VEHICLE_YEAR", "")
        vin = os.getenv("VEHICLE_VIN", "")
        manual_pdf_path = os.getenv("VEHICLE_MANUAL_PDF_PATH", None)
        
        if model and year_str and vin:
            try:
                year = int(year_str)
                cls.set_vehicle(
                    model=model,
                    year=year,
                    vin=vin,
                    manual_pdf_path=manual_pdf_path
                )
                return cls.vehicle
            except ValueError:
                raise ValueError(f"VEHICLE_YEAR must be an integer, received: {year_str}")
        return None
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent
    MANUAL_PDF_PATH = ManualPdfPathDescriptor()  # Dynamic path based on vehicle or .env
    VECTOR_STORE_PATH: Path = BASE_DIR / os.getenv("VECTOR_STORE_PATH", "vector_store")
    INDEX_PATH: Path = None  # Will be set dynamically
    METADATA_PATH: Path = None  # Will be set dynamically
    IMAGES_PATH: Path = None  # Will be set dynamically
    IMAGES_METADATA_PATH: Path = None  # Will be set dynamically
    
    @classmethod
    def _init_paths(cls):
        """Initialize paths that depend on VECTOR_STORE_PATH."""
        if cls.INDEX_PATH is None:
            cls.INDEX_PATH = cls.VECTOR_STORE_PATH / "faiss_index"
            cls.METADATA_PATH = cls.VECTOR_STORE_PATH / "metadata.json"
            cls.IMAGES_PATH = cls.VECTOR_STORE_PATH / "images"
            cls.IMAGES_METADATA_PATH = cls.VECTOR_STORE_PATH / "images_metadata.json"
    
    # Indexing configuration (configurable via .env)
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))  # Characters per chunk
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))  # Overlap between chunks
    EMBEDDING_MODEL: str = os.getenv(
        "EMBEDDING_MODEL", 
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    
    # Search configuration (configurable via .env)
    TOP_K_RESULTS: int = int(os.getenv("TOP_K_RESULTS", "10"))  # Number of results to return
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.5"))  # Minimum similarity threshold
    
    # Internet search now uses Gemini's integrated Google Search
    # No external API keys needed - only GOOGLE_API_KEY is required
    
    @classmethod
    def set_vehicle(cls, model: str, year: int, vin: str, manual_pdf_path: Optional[str] = None):
        """Configures vehicle data."""
        # Use provided path, .env value, or default
        if manual_pdf_path is None:
            manual_pdf_path = os.getenv("VEHICLE_MANUAL_PDF_PATH", "service_manual.pdf")
        
        cls.vehicle = VehicleConfig(
            model=model,
            year=year,
            vin=vin,
            manual_pdf_path=manual_pdf_path
        )
        return cls.vehicle
    
    @classmethod
    def get_vehicle_info(cls) -> str:
        """Returns vehicle information as a string."""
        if cls.vehicle is None:
            return "Vehicle not configured"
        return f"Vehicle: {cls.vehicle.model} {cls.vehicle.year}, VIN: {cls.vehicle.vin}"


# Initialize paths on module load
Config._init_paths()
