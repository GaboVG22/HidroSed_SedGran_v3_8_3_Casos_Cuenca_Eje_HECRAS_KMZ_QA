Actúa como desarrollador senior Python/Streamlit, experto en hidrología, hidráulica fluvial, modelación tipo HEC-RAS, transporte de sedimentos, socavación, protección fluvial y normativa chilena DGA/MOP/Manual de Carreteras.

Debes mejorar la aplicación existente:

**HidroSed SedGran v3.7.5 · Secciones v13 · Hidrología · Sedimentos**

Archivo base:

`HidroSed_SedGran_v3_7_5_Intermedias_Overflow_CLEAN.zip`

Objetivo general:

Mejorar la aplicación para que sea válida para **cualquier proyecto hidrológico e hidráulico**, incluyendo estudios de puentes, modificación de cauces, defensas fluviales, quebradas, canales naturales, esteros, ríos, desembocaduras, humedales, obras de atravieso, alcantarillas, cajones, encauzamientos y obras de protección.

La aplicación debe permitir calcular, revisar, auditar y comparar datos, metodologías, parámetros y resultados de proyectos reales. Debe detectar inconsistencias técnicas, entregar recomendaciones, generar informes exportables y asignar una nota técnica objetiva.

No debes rehacer la app desde cero. Debes conservar la estructura, estilo, flujo de trabajo, módulos existentes, visualización de secciones v13, generación de secciones intermedias, detección de overflow/desbordes, módulos hidráulicos y sedimentológicos existentes. Solo debes mejorar, corregir, ampliar y robustecer.

---

# 1. Revisión inicial obligatoria

Antes de modificar:

1. Descomprimir el ZIP.
2. Identificar estructura completa de carpetas.
3. Revisar especialmente:

* `app.py`
* módulos de hidrología
* módulos de hidráulica
* módulos de secciones transversales
* módulos de sedimentos
* módulos de socavación
* módulos de visualización
* módulos de exportación
* archivos de prueba
* `requirements.txt`

4. Ejecutar auditoría inicial:

```bash
python -m compileall .
```

5. Ejecutar todos los tests existentes.
6. Levantar la app en modo local para verificar que abre sin errores.

No avanzar a entrega final si la aplicación no compila.

---

# 2. Mejoras hidrológicas generales

## 2.1. Módulo de morfometría de cuenca

Agregar o mejorar módulo de ingreso y cálculo de parámetros morfométricos:

* área de cuenca;
* longitud de cauce principal;
* desnivel;
* pendiente media de cuenca;
* pendiente media del cauce;
* altitud media;
* altitud máxima;
* altitud mínima;
* forma de cuenca;
* coeficiente de compacidad;
* factor de forma;
* densidad de drenaje, si existe información;
* régimen pluvial, nival o nivo-pluvial;
* porcentaje urbano, rural, agrícola, forestal o natural.

La app debe permitir ingresar estos datos manualmente o desde archivos:

* Excel;
* CSV;
* KMZ/KML;
* GeoJSON;
* SHP, si está disponible;
* DEM o curvas de nivel, si la app lo permite.

---

## 2.2. Tiempo de concentración

Agregar un selector de métodos de tiempo de concentración.

Debe permitir calcular y comparar:

1. California Highways / Manual de Carreteras.
2. Kirpich.
3. Témez.
4. Giandotti.
5. Ventura.
6. Bransby-Williams, si corresponde.
7. Método definido por el usuario.
8. Promedio de métodos.
9. Mediana de métodos.
10. Valor manual justificado.

La aplicación debe permitir definir un **método rector**, no solo entregar un promedio o mediana.

Debe mostrar:

* fórmula usada;
* variables;
* unidades;
* rango de validez;
* resultado;
* advertencia si el método no es aplicable;
* comparación entre métodos;
* diferencia porcentual entre métodos.

La app debe advertir cuando la diferencia entre métodos sea mayor al 25%.

---

## 2.3. Curvas IDF regionales

Crear un módulo IDF regional editable y reutilizable.

Debe permitir:

* ingresar precipitaciones máximas de 24 h por período de retorno;
* ingresar coeficientes de duración regionales;
* usar curvas IDF propias;
* cargar tablas IDF desde Excel;
* interpolar intensidades para duraciones intermedias;
* interpolar precipitaciones para períodos de retorno no tabulados;
* usar datos regionales DGA, MOP, DOH u otra fuente documentada;
* comparar varias estaciones pluviométricas;
* seleccionar estación representativa;
* ponderar estaciones por distancia, altitud o criterio técnico.

La intensidad debe calcularse como:

[
i(T,t) = \frac{P24(T) \cdot C_d(t)}{t}
]

donde:

* `P24(T)` es la precipitación máxima diaria para período de retorno T;
* `Cd(t)` es el coeficiente de duración;
* `t` es la duración en horas.

La app debe advertir cuando:

* se usa un período de retorno sin precipitación asociada;
* se extrapola fuera del rango de datos;
* se usa una estación no representativa;
* falta justificar la estación seleccionada;
* la duración usada no coincide con el tiempo de concentración.

Debe graficar curvas IDF para los períodos de retorno que el usuario seleccione.

---

# 3. Métodos de caudal de diseño

La aplicación debe calcular caudales máximos mediante varios métodos y permitir comparar resultados.

## 3.1. Método Racional

Mantener fórmula:

[
Q = \frac{C \cdot i \cdot A}{3,6}
]

Debe permitir:

* coeficiente C constante;
* coeficiente C variable por período de retorno;
* factor de ajuste por período de retorno;
* ajuste por urbanización;
* ajuste por pendiente;
* ajuste por suelo;
* ajuste por cobertura vegetal;
* ajuste por impermeabilización.

La aplicación debe advertir cuando:

* `C < 0,03`;
* `C > 0,80`;
* el valor de C no está justificado;
* el área de cuenca está fuera del rango recomendado;
* la cuenca tiene regulación, embalses, humedales, lagunas o zonas de laminación que afecten el método.

Debe mostrar:

* C base;
* factor aplicado;
* C final;
* intensidad usada;
* duración usada;
* área;
* caudal calculado;
* fórmula;
* unidades;
* observación técnica.

---

## 3.2. Método Verni-King Modificado

Agregar o corregir módulo específico para Verni-King Modificado DGA/MOP.

Implementar:

[
Q = C(T) \cdot 0,00618 \cdot P24(T)^{1,24} \cdot A^{0,88}
]

donde:

* `C(T)` es coeficiente empírico del período de retorno;
* `P24(T)` es precipitación diaria máxima del mismo período de retorno T;
* `A` es área pluvial en km²;
* `Q` es caudal en m³/s.

Debe incluir tabla editable de:

* zona o región hidrológica;
* `C(T=10)`;
* relación `C(T)/C(T=10)`;
* `C(T)` final;
* fuente normativa;
* observación técnica.

Debe permitir dos modos:

1. **Modo normativo estricto:** usa P24(T) correspondiente a cada período de retorno.
2. **Modo auditoría documental:** permite revisar informes que usen P24 constante, pero marca advertencia si eso no coincide con la fórmula declarada.

Debe mostrar:

* Q usando P24(T);
* Q usando P24 constante, solo si se activa auditoría;
* diferencia absoluta;
* diferencia porcentual;
* advertencia metodológica.

---

## 3.3. Método DGA-AC

Agregar selector formal de zona homogénea DGA.

Debe permitir:

* seleccionar zona homogénea;
* ingresar tabla regional editable;
* elegir curva media, máxima o mínima;
* ingresar Q10 calculado o estimado;
* aplicar factor de conversión de caudal medio diario máximo a caudal instantáneo;
* usar valores manuales justificados.

Debe calcular:

[
Q_{inst}(T) = \alpha \cdot Q_{med}(T)
]

donde:

* `Qmed(T)` es caudal medio diario máximo;
* `α` es factor de conversión a caudal instantáneo;
* `Qinst(T)` es caudal máximo instantáneo.

La app debe advertir cuando:

* se usa una zona homogénea no correspondiente;
* se extrapola fuera del rango normativo;
* se usa T mayor al rango recomendado del método;
* falta justificar `α`;
* falta justificar Q10.

---

## 3.4. Otros métodos hidrológicos

La app debe permitir incorporar otros métodos según tipo de proyecto:

* hidrograma triangular;
* método SCS-CN;
* método racional modificado;
* hidrograma unitario sintético;
* análisis de frecuencia de caudales, si existen datos fluviométricos;
* transposición de cuencas;
* regionalización;
* método DGA para cuencas sin información fluviométrica;
* métodos definidos por el usuario.

Cada método debe indicar:

* rango de validez;
* datos requeridos;
* limitaciones;
* fuente;
* nivel de confianza.

---

# 4. Selector y auditor de caudal de diseño

Crear un módulo de adopción de caudal de diseño.

Debe calcular simultáneamente los métodos disponibles y entregar una tabla comparativa:

| T | Q Método 1 | Q Método 2 | Q Método 3 | Promedio | Mediana | Máximo | Adoptado | Criterio |
| - | ---------: | ---------: | ---------: | -------: | ------: | -----: | -------: | -------- |

Debe permitir adoptar caudal por:

1. promedio aritmético;
2. mediana;
3. máximo o envolvente conservadora;
4. método racional;
5. método Verni-King;
6. método DGA-AC;
7. método definido por el usuario;
8. ponderación técnica editable;
9. valor manual justificado.

Debe agregar auditor automático.

La app debe detectar:

* si el criterio declarado no coincide con el valor adoptado;
* si se declara promedio pero se adopta el máximo;
* si se declara promedio pero se adopta un método específico;
* si se adopta valor manual sin justificación;
* si faltan períodos de retorno exigidos por el proyecto;
* si se mezclan caudales medios diarios con caudales instantáneos;
* si existen diferencias excesivas entre métodos;
* si falta justificar el método rector.

Debe mostrar alertas:

* alerta verde: consistente;
* alerta amarilla: requiere justificación;
* alerta roja: inconsistencia crítica.

---

# 5. Mejoras hidráulicas generales

## 5.1. Hidráulica tipo HEC-RAS

Mantener y mejorar el módulo hidráulico tipo HEC-RAS.

Para cada sección debe calcular y mostrar:

* km o distancia acumulada;
* cota mínima de fondo;
* cota de agua;
* tirante hidráulico;
* tirante normal;
* tirante crítico;
* energía específica;
* línea de energía;
* pendiente de energía;
* velocidad;
* área mojada;
* perímetro mojado;
* radio hidráulico;
* ancho superficial;
* número de Froude;
* régimen de escurrimiento;
* condición de desborde;
* revancha;
* borde izquierdo;
* borde derecho;
* observaciones.

Debe generar tabla tipo HEC-RAS y exportarla.

---

## 5.2. Plantilla hidráulica por sección

Agregar una plantilla por sección con:

* Yn;
* Yc;
* velocidad;
* energía específica;
* Froude;
* área mojada;
* perímetro mojado;
* radio hidráulico;
* ancho superficial;
* condición hidráulica;
* desborde;
* socavación;
* depositación, si corresponde.

Esta plantilla debe estar visible en pantalla, exportable a Excel y reportable en PDF/Word.

---

## 5.3. Perfil longitudinal 3D

Mantener y mejorar la visualización 3D del perfil longitudinal.

Debe permitir:

* seleccionar tramo;
* detectar secciones aplanadas;
* detectar secciones incoherentes;
* detectar cambios bruscos de pendiente;
* detectar cambios bruscos de ancho;
* generar secciones intermedias;
* suavizar transición geométrica;
* comparar sección original versus sección corregida;
* aprobar o rechazar secciones corregidas;
* mantener trazabilidad del cambio.

---

## 5.4. Desbordes

Mejorar módulo de desborde.

Debe mostrar:

* secciones con desborde;
* margen izquierdo afectado;
* margen derecho afectado;
* altura de sobrepaso;
* longitud del tramo desbordado;
* caudal asociado;
* período de retorno asociado;
* mapa o perfil de desborde;
* exportación KMZ/GeoJSON del tramo afectado, si existe geometría.

---

## 5.5. Sensibilidad hidráulica

Agregar análisis automático de sensibilidad.

Debe permitir variar:

* Manning bajo;
* Manning medio;
* Manning alto;
* condición aguas abajo por pendiente normal;
* condición aguas abajo por altura crítica;
* condición aguas abajo por cota fija;
* condición aguas abajo por marea;
* caudal bajo, medio y alto;
* geometría original y geometría corregida.

Debe mostrar variación de:

* cota de agua;
* tirante;
* velocidad;
* energía;
* Froude;
* desborde;
* revancha;
* condición de seguridad.

---

# 6. Módulo de desembocadura, marea, humedal y control aguas abajo

Crear módulo específico para proyectos con influencia aguas abajo.

Debe permitir ingresar:

* nivel medio del mar;
* pleamar máxima;
* pleamar de diseño;
* marejada;
* sobre-elevación meteorológica;
* nivel de laguna o humedal;
* embalsamiento por barra litoral;
* cota fija aguas abajo;
* pendiente normal;
* altura crítica;
* distancia al control aguas abajo;
* condición simultánea lluvia-marea.

Debe permitir correr escenarios:

1. sin influencia aguas abajo;
2. con cota fija;
3. con marea normal;
4. con marea extrema;
5. con humedal o laguna;
6. con barra litoral;
7. escenario combinado.

Debe graficar:

* perfil hidráulico base;
* perfil hidráulico con control aguas abajo;
* distancia de propagación de influencia;
* diferencia de cotas;
* secciones afectadas.

---

# 7. Sedimentos, transporte y socavación

## 7.1. Granulometría

La aplicación debe aceptar:

* curva granulométrica completa;
* d16;
* d35;
* d50;
* d65;
* d84;
* d90;
* d95;
* dm;
* porcentaje de finos;
* clasificación del material;
* densidad relativa;
* peso específico;
* cohesivo / no cohesivo.

Debe advertir cuando:

* se usa d50 pero el método exige d84, d90 o d95;
* existe arena fina con riesgo de suspensión;
* existe material cohesivo;
* existe granulometría extendida;
* hay posibilidad de acorazamiento;
* el número de muestras es insuficiente.

---

## 7.2. Transporte de sedimentos

Mejorar o agregar métodos de transporte:

* Meyer-Peter Müller;
* Engelund-Hansen;
* Ackers-White;
* Yang;
* Van Rijn, si es posible;
* Shields;
* transporte de fondo;
* transporte en suspensión;
* transporte total;
* método definido por el usuario.

Debe indicar aplicabilidad según:

* pendiente;
* tamaño de sedimento;
* régimen hidráulico;
* velocidad;
* esfuerzo cortante;
* tipo de cauce;
* profundidad;
* ancho;
* granulometría.

Debe graficar:

* capacidad de transporte;
* zonas de erosión;
* zonas de depositación;
* comparación entre métodos.

---

## 7.3. Socavación general

Agregar módulo de socavación general por:

1. Neill;
2. Lischtvan-Levediev;
3. Laursen;
4. método basado en esfuerzo cortante crítico;
5. método definido por usuario.

Debe permitir cálculo:

* global por sección;
* por franjas;
* por tramo;
* por período de retorno;
* con varias granulometrías;
* con sensibilidad hidráulica.

Debe graficar:

* sección original;
* línea de agua;
* sección socavada;
* profundidad de socavación;
* zonas críticas.

---

## 7.4. Socavación local

Agregar módulo de socavación local para:

* estribos;
* pilas;
* contracciones;
* alcantarillas;
* cajones;
* obras de encauzamiento;
* defensas fluviales;
* curvas o cambios bruscos de dirección.

Debe solicitar:

* geometría de la obra;
* ancho efectivo;
* contracción;
* velocidad;
* tirante;
* Froude;
* ángulo de ataque;
* tipo de fundación;
* tipo de lecho;
* protección existente.

Debe emitir advertencias cuando:

* no se evalúan estribos;
* no se evalúan pilas;
* no se evalúa contracción;
* se recomienda protección sin cálculo;
* la fundación queda dentro de la zona socavable.

---

# 8. Diseño de protección fluvial

Crear módulo de diseño preliminar de protección.

Debe incluir:

* gaviones;
* enrocados;
* colchones Reno;
* escollera;
* muros;
* geotextiles;
* protección de pie;
* protección de taludes;
* transición de entrada y salida;
* disipadores, si aplica.

Debe calcular o solicitar:

* velocidad de diseño;
* esfuerzo cortante;
* tamaño mínimo de piedra;
* espesor de protección;
* longitud aguas arriba;
* longitud aguas abajo;
* profundidad de enterramiento;
* filtro;
* geotextil;
* estabilidad al arrastre;
* estabilidad al volteo o deslizamiento, si corresponde;
* factor de seguridad.

Debe generar figuras conceptuales:

* planta;
* perfil longitudinal;
* sección transversal;
* línea de agua;
* línea de socavación;
* ubicación de obra;
* zona protegida.

---

# 9. Auditoría de informe externo

Agregar modo:

**“Auditoría de Informe Externo”**

Este modo debe permitir ingresar manualmente o mediante Excel:

* datos de cuenca;
* estaciones usadas;
* P24 por período de retorno;
* IDF;
* tiempos de concentración;
* caudales por método;
* caudal adoptado;
* criterio de adopción;
* rugosidad;
* secciones;
* resultados hidráulicos;
* granulometría;
* socavación;
* protección fluvial;
* conclusiones del informe.

La aplicación debe detectar:

* inconsistencias de unidades;
* fórmulas declaradas que no coinciden con resultados;
* tablas que declaran promedio pero adoptan otro criterio;
* uso de períodos de retorno sin precipitación asociada;
* uso de P24 constante donde corresponde P24(T);
* selección incorrecta de zona homogénea;
* coeficientes fuera de rango;
* ausencia de sensibilidad hidráulica;
* ausencia de análisis de estribos o pilas;
* falta de verificación de control aguas abajo;
* falta de verificación de desbordes;
* falta de trazabilidad;
* falta de respaldo de parámetros críticos;
* conclusiones no respaldadas por tablas.

Debe entregar:

* lista de observaciones;
* clasificación de cada observación;
* severidad baja, media, alta o crítica;
* recomendación de corrección;
* impacto en nota técnica.

---

# 10. Sistema de calificación técnica

Crear un sistema de puntaje de 0 a 10.

Componentes sugeridos:

| Componente                     | Ponderación |
| ------------------------------ | ----------: |
| Datos base y morfometría       |         10% |
| Precipitación e IDF            |         10% |
| Tiempo de concentración        |         10% |
| Caudales por métodos           |         15% |
| Selección del caudal de diseño |         15% |
| Modelación hidráulica          |         15% |
| Condición aguas abajo          |          5% |
| Sedimentos y socavación        |         10% |
| Protección fluvial             |          5% |
| QA y trazabilidad              |          5% |

La aplicación debe entregar:

* nota por módulo;
* nota global;
* observaciones críticas;
* recomendaciones;
* estado final.

Estados posibles:

1. Aprobado técnicamente.
2. Aprobado con observaciones menores.
3. Aprobado con observaciones relevantes.
4. Requiere corrección.
5. No recomendado técnicamente.

Reglas de bloqueo:

* Si hay contradicción entre criterio declarado y valor adoptado, la nota máxima posible será 8,4.
* Si hay error metodológico en caudales, la nota máxima posible será 8,0.
* Si falta modelación hidráulica del período de retorno exigido, la nota máxima posible será 7,8.
* Si falta análisis de socavación en una obra de puente, la nota máxima posible será 7,5.
* Si falta justificación de parámetros críticos, la nota máxima posible será 8,2.
* Si existen errores de unidades, la nota máxima posible será 7,8.
* Si no existe trazabilidad de datos, la nota máxima posible será 8,0.

La app debe indicar explícitamente si el proyecto supera o no un umbral definido por el usuario, por ejemplo:

[
8,7 / 10
]

---

# 11. Exportación de resultados

Agregar exportación a:

1. Excel;
2. Word;
3. PDF;
4. CSV;
5. GeoJSON;
6. KMZ/KML, si existen datos espaciales.

El informe debe incluir:

* portada;
* resumen ejecutivo;
* datos de entrada;
* metodología;
* fórmulas;
* parámetros;
* tablas;
* gráficos;
* secciones transversales;
* perfil longitudinal;
* resultados hidráulicos;
* resultados sedimentológicos;
* desbordes;
* socavación;
* protección fluvial;
* auditoría;
* nota técnica;
* recomendaciones;
* glosario;
* anexos;
* trazabilidad completa.

---

# 12. Pruebas internas obligatorias

Crear carpeta de pruebas:

`tests/`

Agregar pruebas genéricas:

1. `test_tc_methods.py`
2. `test_idf_module.py`
3. `test_rational_method.py`
4. `test_verni_king.py`
5. `test_dga_ac.py`
6. `test_flow_adoption_audit.py`
7. `test_hydraulic_sections.py`
8. `test_overflow_detection.py`
9. `test_tide_boundary.py`
10. `test_scour_methods.py`
11. `test_external_report_audit.py`
12. `test_score_system.py`

Cada prueba debe usar casos sintéticos simples con resultados conocidos.

No se deben dejar valores fijos de un proyecto específico como única validación. Los casos reales pueden agregarse como ejemplos, pero la app debe funcionar para cualquier proyecto.

---

# 13. QA final obligatorio

Antes de entregar la versión final:

1. Ejecutar:

```bash
python -m compileall .
```

2. Ejecutar todos los tests existentes.
3. Ejecutar todos los tests nuevos.
4. Revisar imports no usados.
5. Revisar funciones duplicadas.
6. Revisar errores silenciosos.
7. Revisar que la app abra en Streamlit.
8. Hacer tres corridas completas:

* proyecto sintético simple;
* proyecto con secciones transversales y desborde;
* proyecto con auditoría de informe externo.

9. No entregar la versión final si existen errores de compilación, errores de ejecución o resultados inconsistentes.

---

# 14. Entregables

Entregar un ZIP final con nombre:

`HidroSed_SedGran_v3_7_6_Auditoria_General_Hidraulica_Sedimentos_QA.zip`

Debe incluir:

* aplicación corregida;
* módulos nuevos;
* tests;
* ejemplos genéricos;
* changelog;
* README actualizado;
* manual breve de uso;
* reporte QA final.

El changelog debe indicar claramente:

* mejoras en tiempo de concentración;
* mejoras IDF;
* corrección Verni-King;
* selector DGA-AC;
* auditor de caudal adoptado;
* módulo condición aguas abajo;
* módulo marea/humedal;
* módulo Neill;
* módulo Lischtvan-Levediev;
* módulo socavación local;
* módulo protección fluvial;
* modo auditoría de informe externo;
* sistema de puntaje 0 a 10;
* exportación de informes;
* pruebas internas.

---

# 15. Criterio de éxito

La aplicación mejorada debe cumplir:

1. Funciona para distintos tipos de proyectos hidráulicos.
2. Permite ingresar datos manuales o desde archivos.
3. Calcula y compara varios métodos hidrológicos.
4. Permite seleccionar método rector de tiempo de concentración.
5. Calcula IDF regional editable.
6. Calcula caudales por varios métodos.
7. Audita el caudal adoptado.
8. Detecta contradicciones metodológicas.
9. Modela hidráulica por secciones.
10. Detecta desbordes.
11. Evalúa sensibilidad hidráulica.
12. Evalúa condición aguas abajo.
13. Calcula transporte de sedimentos.
14. Calcula socavación general y local.
15. Propone protección fluvial.
16. Audita informes externos.
17. Entrega nota técnica.
18. Indica si supera o no el umbral definido por el usuario.
19. Exporta informes completos.
20. Compila y corre sin errores.

No cambies el nombre conceptual de la aplicación ni elimines funcionalidades existentes.

Solo mejora, ordena, robustece, documenta y valida.
