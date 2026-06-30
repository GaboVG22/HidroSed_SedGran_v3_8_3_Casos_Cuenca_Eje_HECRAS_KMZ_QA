# Auditoría de producción · HidroSed SedGran v3.8.2

## Objetivo de la auditoría

Verificar que el selector de casos de aplicación, las alertas de respaldo topográfico, las imágenes referenciales y las nuevas salidas cartográficas estén correctamente enlazadas con la aplicación principal.

## Controles revisados

| Control | Resultado |
|---|---:|
| Compilación completa Python | OK |
| Pruebas unitarias existentes | OK |
| Pruebas nuevas de casos | OK |
| Pruebas nuevas de KMZ cuenca + eje | OK |
| Pruebas nuevas de KMZ cuenca + eje + curvas | OK |
| Imágenes referenciales incluidas en assets | OK |
| Fichas desplegables integradas | OK |
| Alertas para casos 2, 3 y 4 | OK |

## Resultado pytest

```text
43 passed, 10 warnings
```

Las advertencias corresponden a pruebas internas antiguas que devuelven tuplas en vez de `None`. No corresponden a fallas funcionales de la versión v3.8.2.

## Observación

No se ejecutó prueba visual con `streamlit run app.py` porque el sandbox no tiene instalado el paquete `streamlit`. La versión conserva `streamlit` declarado en `requirements.txt` para despliegue local, Streamlit Cloud o Hugging Face.
