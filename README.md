# OPE Administración EHU — PWA de test

Aplicación web (PWA) para practicar la batería de preguntas de la **OPE 2023-2024
de la UPV/EHU, Grupo C1 (Escala Administrativa), Turno Libre** — 500 preguntas tipo
test con 4 opciones y respuesta única.

Es una réplica de la PWA de estudio de Osakidetza: HTML/CSS/JS **vanilla**, sin build
ni dependencias. Todo el progreso se guarda en `localStorage` del navegador.

## Uso

```bash
cd quiz
python3 -m http.server 8080
# abrir http://localhost:8080
```

O abrir `quiz/index.html` directamente por `file://`.

### Funcionalidad
- Perfiles locales (multiusuario, sin registro).
- Tres modos de sesión con rango de preguntas configurable:
  **Secuencial**, **Aleatorio** y **Por dificultad**.
- Modo "Probar" (práctica sin registrar estadísticas).
- Validación pregunta a pregunta con feedback y resaltado de diferencias entre
  opciones similares.
- Marcado "Esta me cuesta", subrayados de usuario y estadísticas persistentes.
- Exportar / importar datos (backup JSON).

## Estructura

```
quiz/                  La PWA completa (esto es lo que se despliega)
  index.html
  css/style.css
  js/{data,users,state,stats,quiz,app}.js
  manifest.json  sw.js
tools/                 Generación de datos (Python)
  parse_answers.py     Extrae la clave de respuestas del PDF de LAB -> answers.json
  merge_ehu.py         Fusiona la transcripción + la clave -> administrativo_c1.json
  build_data.py        Genera quiz/js/data.js (con diffs precalculados)
administrativo_c1.json Dataset de 500 preguntas (fuente de data.js)
answers.json           Clave de respuestas 1-500
*.pdf                  Material original (batería STEILAS + clave LAB)
```

## Origen de los datos

- **Enunciados y opciones**: transcritos del PDF escaneado
  `bateria_de_preguntas_CON RESPUESTAS_ADMINISTRATIVO_1.pdf` (respuestas propuestas
  por STEILAS, marcadas en amarillo).
- **Respuestas correctas**: extraídas del PDF de texto `erantzunak-ADM_LAB.pdf`
  (clave publicada por LAB-EHU), usado como fuente fiable.

Notas:
- Preguntas **impugnables** según LAB (respuesta doble): **22** (a/b), **378** (c/d),
  **409** (b/d). Se toma la primera letra como correcta.
- Divergencia entre sindicatos revisada manualmente: **P267** → se usa la de LAB (D).

### Regenerar `data.js`

```bash
python3 tools/parse_answers.py      # -> answers.json
python3 tools/merge_ehu.py <dir>    # chunks transcritos + answers.json -> administrativo_c1.json
python3 tools/build_data.py         # -> quiz/js/data.js
```

Ni STEILAS ni LAB garantizan el 100% de acierto de sus claves; conviene cotejar.
