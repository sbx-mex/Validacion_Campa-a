# Validación Campaña · Fall 26

Recorrido ejecutivo de una pregunta por pantalla. Muestra una referencia oficial cuando ayuda a decidir y genera una tasa de éxito con acciones claras.

Consulta el resumen de [10 mejoras implementadas](MEJORAS_IMPLEMENTADAS.md).

> **Información privada de la compañía.** No publiques este repositorio ni habilites un sitio público sin autorización corporativa. Consulta [PRIVACIDAD.md](PRIVACIDAD.md).

## Experiencia Fall 26

- Estética cálida Starbucks + Peanuts basada en la referencia oficial ya incluida en el proyecto.
- Portada, mensajes y paleta controlados desde `config/settings.json`.
- Navegación por cinco momentos del Customer Journey: Prepara, Llega, Elige, Vive y Disfruta.
- **Cumple** y **No aplica** avanzan automáticamente; **No cumple** se detiene para definir una acción.
- Corrección inmediata sugerida al seleccionar **No cumple** y reconocimiento al seleccionar **Cumple**.
- Confirmación cálida antes de exportar y agradecimiento posterior con enfoque en la ruta de mejora.
- Aviso de responsabilidad obligatorio al iniciar o reanudar.
- Retención local máxima de 24 horas y botón para borrar el recorrido del dispositivo.
- Cero servicios externos: la aplicación no transmite los datos capturados.

## Cómo funciona

1. Captura únicamente **Tienda** y **Quién valida**.
2. Responde cada control; puedes cambiar de momento desde el navegador superior:
   - **Cumple = 1**
   - **No cumple = 0** y requiere una acción breve.
   - **No aplica** queda fuera del cálculo.
3. Revisa primero los puntos a favor y después la ruta de mejora.
4. Ajusta cualquier acuerdo desde el resumen y confirma la revisión antes de exportar.
5. El PDF propone automáticamente el nombre `Tienda_Fall.pdf` y muestra un cierre de agradecimiento.

La tasa de éxito se calcula así:

`Cumple / (Cumple + No cumple) × 100`

## Inicio rápido

```bash
python -m http.server 8000
```

Abre `http://localhost:8000`. El servidor es necesario para cargar los archivos JSON y habilitar el modo offline.

## Reporte PDF de tienda

Instala las dependencias una vez:

```bash
python -m pip install -r requirements.txt
```

Para validar el motor y generar el reporte ejecutivo de ejemplo:

```bash
python scripts/generate_store_report.py \
  --input sample/ejemplo_resultado.json
```

El reporte se entrega en **dos páginas**: la primera resume la tasa de éxito, las categorías evaluadas y los puntos a favor; la segunda concentra todas las oportunidades y deja campos para responsable, fecha, corrección y revalidación en tienda.

La portada y los dos momentos de exportación se construyen desde la referencia oficial proporcionada:

```bash
python scripts/prepare_campaign_ui.py \
  --source "Referencia oficial de campaña.jpeg" \
  --output-dir assets/ui
```

## iPhone y iPad

La aplicación respeta las áreas seguras de iOS, usa controles táctiles de al menos 48 px y puede agregarse a la pantalla de inicio. Los iconos se regeneran sin dependencias externas con:

```bash
python scripts/build_ios_assets.py
```

## Referencias visuales

Las 34 referencias WebP incluidas provienen de materiales autorizados. Las 16 referencias sustituidas se normalizan con Python: orientación, escalado controlado, nitidez suave y conversión WebP de alta calidad. Los originales no se incluyen para evitar duplicación de material privado.

Para regenerarlas desde las láminas autorizadas:

```bash
python scripts/build_assets.py \
  --fall-dir "sources/Consolidado_Fall_v2ShowCase" \
  --w36-dir "sources/Comunicado de Operaciones W36" \
  --output-dir assets/reference
```

Para preparar los dos lotes de sustitución y el paquete combinado:

```bash
python scripts/optimize_validation_images.py \
  --source Imagenes_Validacion.zip \
  --package-dir ../paquetes_imagenes
```

## Calidad y seguridad

```bash
python tests/validate_project.py
python -m unittest tests/test_scoring.py
node --check app.js
node --check service-worker.js
node tests/test_app_logic.js
```

El workflow de GitHub ejecuta esas revisiones en cada `push` y `pull_request`. No existe despliegue automático: es una protección deliberada porque el contenido es privado.

Para crear un paquete limpio con manifiesto SHA-256:

```bash
python scripts/build_release.py --output ../Validacion_Campana_Fall26_GitHub.zip
python scripts/verify_integrity.py
```

## Estructura

```text
Validacion_Campana/
├── assets/                 # Icono y referencias WebP autorizadas
├── config/settings.json    # Reglas de estado y configuración
├── data/fall26_checklist.json
├── scripts/                # Recortes, scoring y reporte PDF
├── tests/                  # Contratos de contenido y cálculo
├── .github/workflows/quality.yml
├── app.js
├── index.html
├── manifest.webmanifest
├── service-worker.js
└── styles.css
```

## Publicación controlada

El proyecto funciona como sitio estático. Puede alojarse en infraestructura interna o en un repositorio privado con los controles de acceso aprobados. **GitHub Pages puede exponer públicamente el contenido**, incluso cuando el repositorio tenga otras restricciones; valida el modelo de acceso antes de activarlo.

JUNTÉMONOS MÁS · Menos texto, decisiones claras y seguimiento visible.
