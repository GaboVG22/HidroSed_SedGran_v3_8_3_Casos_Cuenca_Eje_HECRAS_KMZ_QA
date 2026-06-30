# Changelog · HidroSed SedGran v3.7.6 Auditoría General Hidráulica Sedimentos QA

## Mejoras principales

### Tiempo de concentración
- Nuevo comparador de métodos: California Highways / Manual de Carreteras, Kirpich, Témez, Giandotti, Ventura, Bransby-Williams, promedio, mediana y valor manual justificado.
- Selector de método rector.
- Advertencia automática cuando la dispersión entre métodos supera 25%.

### IDF regional editable
- Nuevo módulo IDF con P24(T), coeficientes de duración Cd(t), interpolación de intensidades y advertencias por extrapolación.
- Gráfico IDF por período de retorno.

### Caudales de diseño
- Método racional robustecido con C base, factor y advertencias de rango.
- Módulo Verni-King Modificado con modo normativo estricto P24(T) y modo auditoría documental con P24 constante.
- Selector DGA-AC con Q10, ratios por período y factor instantáneo alpha.
- SCS-CN preliminar opcional.

### Auditor de caudal adoptado
- Tabla comparativa por período de retorno.
- Adopción por promedio, mediana, máximo/envolvente, método específico, ponderación o manual.
- Semáforo automático por contradicción entre criterio declarado y valor adoptado.

### Hidráulica y desbordes
- Se mantiene motor tipo HEC-RAS 1D, secciones v13, QA de secciones, generación de secciones intermedias y control de tirante irreal.
- Perfil hidráulico enriquecido con pendiente de energía, desborde, revancha y tabla tipo HEC-RAS.
- Módulo de condición aguas abajo, marea, humedal, laguna y barra litoral.

### Sedimentos y socavación
- Comparador de socavación general: Neill preliminar, Lischtvan-Levediev preliminar, Laursen preliminar y esfuerzo cortante crítico.
- Socavación local preliminar para pilas, estribos, contracciones, alcantarillas/cajones y defensas.
- Diseño preliminar de protección: enrocado/escollera, gaviones y colchón Reno.

### Auditoría de informe externo
- Nuevo modo “Auditoría general” para revisar datos de cuenca, IDF, Tc, caudales, hidráulica, aguas abajo, sedimentos, protección y trazabilidad.
- Observaciones con severidad baja/media/alta/crítica y recomendación de corrección.

### Sistema de puntaje 0 a 10
- Ponderación por módulo.
- Reglas de bloqueo por contradicciones, errores metodológicos, ausencia de hidráulica, ausencia de socavación local en puentes, errores de unidades y falta de trazabilidad.
- Estados: aprobado técnicamente, aprobado con observaciones menores/relevantes, requiere corrección o no recomendado técnicamente.

### Exportación
- Excel de auditoría general.
- Informe Markdown.
- Informe Word DOCX si está instalado python-docx.
- Informe PDF si está instalado reportlab.

### Pruebas internas
- Carpeta tests/ con 12 pruebas genéricas solicitadas.
- Casos sintéticos simples, no dependientes de un proyecto específico.
