# Reporte QA final · HidroSed SedGran v3.7.6

## Base revisada
Archivo base aplicado: `HidroSed_SedGran_v3_7_5_Intermedias_Overflow_CLEAN.zip`.

## Auditoría inicial
- Descompresión y revisión de estructura: OK.
- `python -m compileall .`: OK.
- `python test_supreme_internal.py`: 10/10 OK.

## Auditoría final
- `python -m compileall .`: OK.
- `python -m unittest discover -s tests`: 12/12 OK.
- `python test_supreme_internal.py`: 10/10 OK.
- Corrida sintética simple hidrología/IDF/caudales/adopción: OK.
- Corrida sintética con secciones/desborde: OK.
- Corrida sintética auditoría informe externo/nota: OK.

## Verificación Streamlit
En el entorno de generación no se pudo ejecutar `streamlit run app.py` porque el binario `streamlit` no está instalado en el sandbox. La dependencia permanece declarada en `requirements.txt` (`streamlit>=1.36,<1.42`) para ejecución en ambiente local o Streamlit Cloud.

## Observación técnica
La versión compila y las pruebas funcionales de módulos pasan correctamente. La apertura visual debe verificarse en el ambiente del usuario con:

```bash
pip install -r requirements.txt
streamlit run app.py
```
