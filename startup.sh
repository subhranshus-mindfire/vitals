#!/bin/bash
# Startup script for Azure App Service Linux
export PYTHONPATH="/home/site/wwwroot/.python_packages/lib/site-packages:/home/site/wwwroot:$PYTHONPATH"
python3 app.py
