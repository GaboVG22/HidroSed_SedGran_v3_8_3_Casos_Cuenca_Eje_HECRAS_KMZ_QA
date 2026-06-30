# Hotfix SessionInfo Streamlit v3.7.6A

## Problema observado
Al abrir la aplicación Streamlit aparece el cuadro:
`Bad message format: Tried to use SessionInfo before it was initialized`.

## Diagnóstico
El error corresponde al runtime/frontend de Streamlit y a la gestión de mensajes websocket/sesión. No corresponde a los cálculos hidráulicos, sedimentológicos ni a los módulos de HidroSed.

## Corrección aplicada
1. Se fijó una versión estable de Streamlit:
   `streamlit==1.45.1`
2. Se desactivó la telemetría de navegador en `.streamlit/config.toml`:
   `[browser] gatherUsageStats = false`
3. Se mantuvo `showErrorDetails = true` para facilitar diagnóstico si aparece otro error real de Python.
4. Se ejecutó `compileall` sobre la aplicación.

## Instrucción de reinstalación
Eliminar dependencias anteriores o crear entorno limpio:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Si ya existía un entorno, ejecutar:
```bash
pip uninstall -y streamlit
pip install -r requirements.txt --force-reinstall
```
