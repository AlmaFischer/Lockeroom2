#!/usr/bin/env bash
# Exit on error
set -o errexit

# Modify this line as needed for your package manager (pip, poetry, etc.)
pip install -r requirements.txt

# Convert static asset files
python manage.py collectstatic --no-input

# Apply any outstanding database migrations
python manage.py migrate

#if [[ "$CREATE_SUPERUSER" == "true" ]]; then
#    echo "Creando superusuario..."
#    python manage.py createsuperuser --no-input
#else
#    echo "Variable CREATE_SUPERUSER no definida o no es 'true'. Saltando la creación de superusuario."
#fi