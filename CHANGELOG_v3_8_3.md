# Changelog v3.8.3

- Se rehízo la mejora de casos cuenca-eje usando el documento correcto.
- Se incorporó exportación KMZ HidroSed consolidada para evitar desorden por múltiples archivos.
- Se corrigió la descarga del eje: ya no depende de que exista eje manual; intenta eje automático y, si no puede, exporta puntos y README sin fallar.
- Se agregó carga de cuenca corregida y prioridad de `cuenca_corregida` sobre `cuenca_preliminar`.
- Se añadió plantilla Excel HEC-RAS y validador de secciones.
- Se añadió generación de curvas de apoyo del eje en corredor/buffer.
- Se añadió panel de diagnóstico técnico del proyecto.
- Se incorporaron pruebas unitarias específicas v3.8.3.
