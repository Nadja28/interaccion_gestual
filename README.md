# Interacción gestual - GMMJ

1. Clonar repositorio
- `git clone https://github.com/Nadja28/interaccion_gestual.git`

2. Crear y activar entorno virtual con miniconda
- `conda create -n gestual python=3.10`
- `conda activate gestual`

3. Instalar librerías necesarias para su aplicación (asegurar de estar dentro de la carpeta del proyecto)
- `pip install -r requirements.txt`

4. Levantar la aplicación
- `uvicorn app:app --reload`
