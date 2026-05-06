#!/usr/bin/env python3
"""
verify_setup.py - Script de verificación rápida del setup
Comprueba que todas las dependencias y configuraciones necesarias están en lugar.
"""

import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Verifica que Python 3.10+ esté instalado."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(f"❌ Python 3.10+ requerido (tienes {version.major}.{version.minor})")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_package(package_name, import_name=None):
    """Verifica que un paquete esté instalado."""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        print(f"✅ {package_name}")
        return True
    except ImportError:
        print(f"❌ {package_name} no instalado")
        return False

def check_directory(path, name):
    """Verifica que un directorio exista."""
    if Path(path).exists():
        print(f"✅ {name}")
        return True
    print(f"❌ {name} no encontrado")
    return False

def main():
    print("=" * 60)
    print("🔍 VERIFICACIÓN DEL SETUP – QA Agent")
    print("=" * 60)

    all_ok = True

    # Python
    print("\n📦 Python:")
    all_ok &= check_python_version()

    # Dependencias principales
    print("\n📚 Dependencias:")
    all_ok &= check_package("selenium")
    all_ok &= check_package("streamlit")
    all_ok &= check_package("webdriver-manager", "webdriver_manager")
    all_ok &= check_package("python-dotenv", "dotenv")

    # Estructura del proyecto
    print("\n📁 Estructura:")
    all_ok &= check_directory("agent", "Módulo: agent/")
    all_ok &= check_directory("dashboard", "Módulo: dashboard/")
    all_ok &= check_directory("results", "Directorio: results/")

    # Archivos clave
    print("\n📄 Archivos clave:")
    all_ok &= check_directory("main.py", "main.py")
    all_ok &= check_directory("requirements.txt", "requirements.txt")
    all_ok &= check_directory(".env.example", ".env.example")

    # Resumen
    print("\n" + "=" * 60)
    if all_ok:
        print("✅ TODO LISTO – Puedes ejecutar:")
        print("   python main.py \"prueba el login\"")
        print("   streamlit run dashboard/app.py")
    else:
        print("❌ Hay problemas. Ejecuta: pip install -r requirements.txt")
    print("=" * 60)

    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
