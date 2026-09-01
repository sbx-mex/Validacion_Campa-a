# Validación Campaña · Fall 26

Recorrido ejecutivo para revisar una tienda en 25–30 minutos. Presenta una pregunta por pantalla, muestra una referencia oficial sólo cuando ayuda a decidir y genera una tasa de éxito con oportunidades claras.

Consulta el resumen de [10 mejoras implementadas](MEJORAS_IMPLEMENTADAS.md).

> **Información privada de la compañía.** No publiques este repositorio ni habilites un sitio público sin autorización corporativa. Consulta [PRIVACIDAD.md](PRIVACIDAD.md).

## Cómo funciona

1. Captura únicamente **Tienda** y **Quién valida**.
2. Responde los 36 controles en orden:
   - **Cumple = 1**
   - **No cumple = 0** y requiere una acción breve.
   - **No aplica** queda fuera del cálculo.
3. Revisa el resultado general, el desempeño por bloque y las oportunidades.
4. Descarga el JSON. Si necesitas un documento formal, conviértelo a PDF con Python.

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

Después de descargar el resultado desde la web:

```bash
python scripts/generate_store_report.py \
  --input exports/resultado_tienda.json \
  --output exports/Reporte_Fall26.pdf
```

El reporte incluye identidad de tienda, tasa de éxito, conteos, calificación por bloque y los puntos **No cumple** con su comentario.

## Referencias visuales

Las 30 referencias WebP incluidas provienen de recortes del consolidado y del comunicado fuente. No se generó ni sustituyó ninguna imagen de validación. Los archivos originales no se incluyen para evitar duplicación de material privado.

Para regenerarlas desde las láminas autorizadas:

```bash
python scripts/build_assets.py \
  --fall-dir "sources/Consolidado_Fall_v2ShowCase" \
  --w36-dir "sources/Comunicado de Operaciones W36" \
  --output-dir assets/reference
```

## Calidad y seguridad

```bash
python tests/validate_project.py
python -m unittest tests/test_scoring.py
node --check app.js
node --check service-worker.js
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
