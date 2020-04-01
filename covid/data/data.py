from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "datasets"
COARSE_INDEX = ("0-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+")

# Contact matrix information
CONTACT_MATRIX_COUNTRIES = [
    "Belgium",
    "Finland",
    "Germany",
    "Great Britain",
    "Italy",
    "Luxembourg",
    "Netherlands",
    "Poland",
]
CONTACT_MATRIX_IDS = [c.lower() for c in CONTACT_MATRIX_COUNTRIES]
