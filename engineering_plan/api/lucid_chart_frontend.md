# Frontend Functional Spec (tidied from Lucidchart CSV)

> Documento de referencia para implementar vistas, formularios y llamadas al backend. Usa los mismos nombres de campo del CSV para evitar confusiones con el equipo.

---

## 1) Autenticación & Cuenta

### Login

* **POST**: `mail`, `password`

### Registro

* **POST**: `nombre`, `apellido`, `mail`, `password`, `acepta tyc`

### Términos y condiciones

* **GET**: `tyc`

### Perfil de usuario (self-service)

* **GET**: `Correo`, `Rol`, `Nombre`, `etc`
* **PATCH**: `nombre`, `correo`, `contraseña`

---

## 2) Panel / Dashboard de Naves

### Listado de naves

* **GET**:
  `Nombre`, `Estado`, `Descripcion Estado`, `Coordenadas`, `Cantidad de Claros`, `Plantas`, `Superficie`, `NaveID`

### Detalle / Resumen por nave

* **GET**:
  `Nombre nave`, `Macetas Totales`, `Valor potencial`, `Movimiento ultimo mes`, `ultima actualizacion`, `Claros`

### Mapa / Vista geográfica

* **GET**:
  `Coordenadas`, `Nombre naves`, `Nombre claros (N y S)`, `plantas por claros`, `maceta por claros`, `Tipo de plantas`

### Crear nave

* **POST**:
  `Cordenadas`, `nombre`

---

## 3) Claros & Seguimiento

### Detalle de claro

* **GET**:
  `Ubicacion?`, `Nombre`, `cantidad de Plantas`, `Codigo Maceta`, `Valor estimado`, `Ultima actualizaciopn`, `Diferencia ultima actualizacion (+5,-2)`

### Acciones sobre claros (movimientos)

* **POST/INGRESO**: `Claro Destino`, `Tipo de planta`, `cantidad`, `maceta`, `observaciones`
* **POST/REPLANTE**: `Claro Destino`, `Tipo de planta`, `cantidad`, `maceta`, `observaciones`
* **POST/TRANSPLANTE**: `Claro Origen`, `Claro Destino`, `Tipo de planta`, `cantidad`, `maceta`, `observaciones`
* **POST/MUERTE**: `Claro Origen`, `Tipo de planta`, `cantidad`, `observaciones`

> **Nota UI**: Cada acción va como formulario modal sobre el detalle del claro, con historial de movimientos y balance (+/−) en la tarjeta del claro.

---

## 4) Catálogo de Macetas

### Listado

* **GET**: `macetas`, `precio`, `litros`

### Crear

* **POST**: `nombre`, `tamaño?`, `precio`, `Volumen`

### Editar

* **PATCH**: `nombre`, `tamaño?`, `precio`, `Volumen`

### Eliminar

* **DELETE**: *(sin campos adicionales en el CSV)*

---

## 5) Imágenes, Detecciones & Trazabilidad

### Subida de imagen

* **POST**: `IMAGEN`

### Métricas / Detalle por elemento (imagen/lote)

* **GET**:
  `Foto + historial_ID?`, `nro detecciones`, `nro ingreso manual`, `trazabilidad`, `COmparativa ultimo mes`

### Evolución visual

* **GET / UI idea**: “A medida que cambian las fotos mostrar la evolución”

  * **Gráfico sugerido**: diagrama de puntos con `cantidad de plantas` por fecha (historial_ID)

### Control de calidad / Correcciones

* **GET**: `Fotos`, `Estado`, `Info`
* **PATCH**: `nave`, `cantero`, `claro`, `descripcion error`
* **Vista comparativa**: “imagen con detecccion vs sin deteccion”

---

## 6) Jobs (procesos en background)

* **GET**: `Jobs`

> **UI**: tabla con estado, tipo de job, fecha de creación, duración, enlace a logs/resultados.

---

## 7) Administración

### Bandera de sección

* **ADMIN** (sección de navegación)

### Usuarios (listado y edición)

* **/GET** Usuarios: `nombre`, `email`, `rol`, `ultimo login`, `ultimo upload`
* **/PATCH** Usuarios: `nombre`, `email`, `rol`, `ultimo login`, `ultimo upload`
* **PATCH (admin)** usuario: `nombre`, `correo`, `contraseña`, `rol`

> **Flujo**: Admin lista → selecciona usuario → edita campos (incluye cambio de rol).

---

## 8) “Claros: ingreso manual por lote”

(Formulario masivo según CSV suelto)

* **POST**: `claroID (pueden ser varios)`, `Maceta`, `Tipo planta`

> **UI**: selector múltiple de `claroID`, dropdown de `Maceta` y `Tipo planta`, vista previa del impacto.

---

## 9) Observaciones de diseño (del CSV)

* Varias entradas marcadas como **GET/POST/PATCH** representan **vistas** y **formularios** junto a los **campos esperados**.
* Los “User Image” del CSV son **actores/avatares** sin datos adicionales: no requieren UI específica.
* Se suprimió contenido no profesional presente en el CSV original para mantener el documento técnico.

---

## 10) Navegación propuesta (resumen)

1. **Login / Registro / TYC**
2. **Dashboard de Naves**

   * Listado de naves
   * Detalle de nave (resumen + mapa)
   * Crear nave
3. **Claros**

   * Detalle de claro
   * Movimientos: Ingreso, Replante, Transplante, Muerte
   * Carga masiva por `claroID`
4. **Catálogo de Macetas** (CRUD)
5. **Imágenes & Detecciones**

   * Subir imagen
   * Métricas e historial
   * Correcciones y comparación (con/sin detección)
   * Evolución (gráfico de puntos)
6. **Jobs**
7. **Administración**

   * Usuarios (listado y edición)
   * Editar usuario (admin)

---

## 11) Componentes UI sugeridos (rápido)

* **Tablas**: naves, claros, usuarios, jobs, detecciones.
* **Tarjetas**: KPIs por nave (macetas totales, valor potencial, movimiento último mes).
* **Map/Plano**: `Coordenadas`, capas por claros/macetas/tipos de planta.
* **Form Modals**: movimientos (Ingreso/Replante/Transplante/Muerte), CRUD de macetas, crear nave.
* **Charts**: evolución de `cantidad de plantas` (scatter), comparativas mes a mes.

---

## 12) Checklist de implementación

* [ ] Rutas y vistas según navegación propuesta
* [ ] Formularios con validaciones según campos listados
* [ ] Tablas con filtros por `Nave`, `Claro`, `Tipo planta`, fecha
* [ ] Gráficos (evolución, comparativas)
* [ ] Módulo de subida de imágenes + preview
* [ ] Vista comparativa detección vs. original
* [ ] Gestión de usuarios (admin) y perfil (self)
* [ ] Jobs: listado y estados
* [ ] i18n de rótulos si aplica (mantener nombres de campos del CSV en backend)

---

> **Listo:** esto condensa y ordena todo lo que estaba en el CSV en una guía directa para el frontend. Si querés, lo paso a issues/epics con criterios de aceptación.
