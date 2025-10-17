#!/bin/bash

# Script de configuración para Fanpage Automation Suite

echo "🚀 Configurando Fanpage Automation Suite..."

# Crear directorios necesarios
echo "📁 Creando directorios..."
mkdir -p data/media
mkdir -p data/templates
mkdir -p logs
mkdir -p config

# Copiar archivo de configuración de ejemplo
if [ ! -f ".env" ]; then
    echo "📄 Creando archivo .env..."
    cp .env.example .env
    echo "✏️  Por favor, edita el archivo .env con tus credenciales"
fi

# Crear entorno virtual si no existe
if [ ! -d ".venv" ]; then
    echo "🐍 Creando entorno virtual..."
    python3 -m venv .venv
fi

# Activar entorno virtual
echo "🔧 Activando entorno virtual..."
source .venv/bin/activate

# Actualizar pip
echo "⬆️ Actualizando pip..."
.venv/bin/python -m pip install --upgrade pip

# Instalar dependencias
echo "📦 Instalando dependencias..."
.venv/bin/python -m pip install -r requirements.txt

# Verificar instalación
echo "✅ Verificando instalación..."
.venv/bin/python verify_setup.py

echo ""
echo "🎉 ¡Configuración completada!"
echo ""
echo "📋 Próximos pasos:"
echo "1. Editar el archivo .env con tus credenciales de redes sociales"
echo "2. Revisar la configuración en config/config.yaml"
echo "3. Ejecutar la aplicación:"
echo "   source .venv/bin/activate"
echo "   python main.py --mode scheduler"
echo ""
echo "📚 Modos disponibles:"
echo "   --mode scheduler    # Modo programador (por defecto)"
echo "   --mode interactive  # Modo interactivo"
echo "   --mode api         # Servidor API"
echo ""
echo "🔧 Configuración de plataformas:"
echo "   --platform facebook"
echo "   --platform instagram"
echo "   --platform twitter"
echo "   --platform all     # Todas las plataformas (por defecto)"