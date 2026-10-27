"""
Configuración de pytest: añade el directorio raíz del proyecto a sys.path
para que los tests puedan importar el paquete nkdem sin instalarlo.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
