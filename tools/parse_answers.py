#!/usr/bin/env python3
"""
Extrae la clave de respuestas de erantzunak-ADM_LAB.pdf a un JSON {num: letra}.

La plantilla es una rejilla en texto con entradas tipo "n - letra", donde letra
puede ser doble/impugnable, p.ej. "22 - a/b". En esos casos se toma como
respuesta la PRIMERA letra y se registra la pregunta como impugnable.

Uso: python3 tools/parse_answers.py
Salida: answers.json  (dict "num" -> "LETRA" en mayuscula, A-D)
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(ROOT, 'erantzunak-ADM_LAB.pdf')
OUT = os.path.join(ROOT, 'answers.json')

TOTAL = 500

def main():
    txt = subprocess.run(
        ['pdftotext', '-layout', PDF, '-'],
        capture_output=True, text=True, check=True,
    ).stdout

    answers = {}
    impugnables = {}
    # n - a   |  n-a  |  n - a/b
    for m in re.finditer(r'(\d{1,3})\s*-\s*([a-dA-D])(?:\s*/\s*([a-dA-D]))?', txt):
        num = int(m.group(1))
        if not (1 <= num <= TOTAL):
            continue
        primary = m.group(1 + 1).upper()
        answers[num] = primary
        if m.group(3):
            impugnables[num] = f"{primary}/{m.group(3).upper()}"

    faltan = [n for n in range(1, TOTAL + 1) if n not in answers]
    print(f'Respuestas parseadas: {len(answers)} / {TOTAL}')
    if impugnables:
        print(f'Impugnables (respuesta doble, se toma la 1a): '
              + ', '.join(f'{n}={v}' for n, v in sorted(impugnables.items())))
    if faltan:
        print(f'[AVISO] Faltan {len(faltan)} numeros: {faltan}', file=sys.stderr)
    else:
        print('Numeracion 1..500 completa, sin huecos.')

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({str(k): v for k, v in sorted(answers.items())},
                  f, ensure_ascii=False, indent=2)
    print(f'Escrito {OUT}')

if __name__ == '__main__':
    main()
