# Manual breve de uso · HidroSed SedGran v3.7.6

## Flujo recomendado
1. Ingresar punto de control, eje de cauce, DEM, cuenca, curvas y secciones v13.
2. Revisar secciones en 2D y 3D. Si hay secciones aplanadas, seleccionar tramo y generar secciones intermedias.
3. Calcular hidrología y caudales base.
4. Calcular hidráulica tipo HEC-RAS, sedimentos, desbordes y perfil 3D.
5. Abrir la pestaña **11 · Auditoría general** para revisar el proyecto como informe técnico integral.

## Pestaña 11 · Auditoría general

### Morfometría y Tc
Permite ingresar área, longitud, cotas, perímetro, drenaje y régimen. Calcula Tc por varios métodos y permite seleccionar el método rector.

### IDF regional
Permite editar P24(T) y Cd(t). Calcula intensidad mediante:

`i(T,t)=P24(T)*Cd(t)/t`

### Caudales y adopción
Calcula Método Racional, Verni-King Modificado, DGA-AC y SCS-CN preliminar. Genera tabla comparativa y audita el caudal adoptado.

### Aguas abajo / marea
Permite evaluar cota fija, marea normal, marea extrema, humedal, laguna, barra litoral y escenario combinado.

### Socavación / protección
Entrega revisión preliminar de socavación general, socavación local y predimensionamiento de protecciones fluviales.

### Auditoría externa / nota
Permite activar antecedentes presentes en un informe externo. La aplicación genera observaciones, severidad, recomendaciones y nota técnica global de 0 a 10.

### Exportar auditoría
Permite descargar Excel, Markdown, Word DOCX y PDF cuando las dependencias están instaladas.

## Advertencia
Los módulos de auditoría y predimensionamiento son herramientas de revisión técnica preliminar. Para diseño definitivo se debe verificar con topografía real, normativa vigente, criterios DOH/DGA/MOP/Manual de Carreteras y modelación oficial cuando corresponda.
