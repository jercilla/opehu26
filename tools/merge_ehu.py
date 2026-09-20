#!/usr/bin/env python3
"""
Fusiona los trozos transcritos (chunk_*.json) con la clave de respuestas de LAB
(answers.json) y produce administrativo_c1.json listo para build_data.py.

- Fuente de enunciados+opciones: los chunk_*.json (transcripcion por vision).
- Fuente de la respuesta correcta: answers.json (clave de LAB).
- Reporta discrepancias entre el resaltado STEILAS ("marcada") y la clave LAB,
  numeros duplicados, huecos, y preguntas sin 4 opciones.

Uso: python3 tools/merge_ehu.py <dir_con_chunks>
     (por defecto busca chunk_*.json en el CWD)
Salida: administrativo_c1.json (array de 500 preguntas ordenado por num).
"""
import glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOTAL = 500
OUT = os.path.join(ROOT, 'administrativo_c1.json')
ANSWERS = os.path.join(ROOT, 'answers.json')

def main():
    chunk_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    chunk_files = sorted(glob.glob(os.path.join(chunk_dir, 'chunk_*.json')))
    if not chunk_files:
        sys.exit(f'No se encontraron chunk_*.json en {chunk_dir}')

    with open(ANSWERS, encoding='utf-8') as f:
        key = {int(k): v.upper() for k, v in json.load(f).items()}

    by_num = {}
    dups = []
    for cf in chunk_files:
        with open(cf, encoding='utf-8') as f:
            arr = json.load(f)
        for q in arr:
            n = int(q['num'])
            if n in by_num:
                dups.append((n, os.path.basename(cf)))
                continue
            by_num[n] = q
        print(f'[chunk] {os.path.basename(cf)}: {len(arr)} preguntas')

    faltan = [n for n in range(1, TOTAL + 1) if n not in by_num]
    extra = [n for n in by_num if not (1 <= n <= TOTAL)]
    sin4 = []
    sin_clave = []
    discrepancias = []

    result = []
    for n in range(1, TOTAL + 1):
        q = by_num.get(n)
        if not q:
            continue
        opts = q.get('opciones', {})
        letters = ['A', 'B', 'C', 'D']
        if sorted(opts.keys()) != letters or any(not str(opts.get(l, '')).strip() for l in letters):
            sin4.append(n)
        correcta = key.get(n)
        if not correcta:
            sin_clave.append(n)
        marcada = (q.get('marcada') or '').upper() or None
        if marcada and correcta and marcada != correcta:
            discrepancias.append((n, f'STEILAS={marcada} LAB={correcta}'))
        result.append({
            'num': n,
            'idpregunta': n,
            'pregunta': q.get('pregunta', '').strip(),
            'opciones': {l: str(opts.get(l, '')).strip() for l in letters},
            'correcta': correcta,
        })

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f'\n=== RESUMEN ===')
    print(f'Preguntas escritas: {len(result)} / {TOTAL}')
    if dups:
        print(f'[AVISO] Numeros duplicados entre chunks: {dups}')
    if extra:
        print(f'[AVISO] Numeros fuera de 1..500: {sorted(extra)}')
    if faltan:
        print(f'[AVISO] FALTAN {len(faltan)} preguntas: {faltan}')
    else:
        print('Numeracion 1..500 completa.')
    if sin4:
        print(f'[AVISO] Preguntas sin 4 opciones no vacias: {sin4}')
    if sin_clave:
        print(f'[AVISO] Sin clave de respuesta: {sin_clave}')
    if discrepancias:
        print(f'[REVISAR] Discrepancias resaltado STEILAS vs clave LAB '
              f'({len(discrepancias)}): {discrepancias}')
    else:
        print('Sin discrepancias STEILAS vs LAB (o sin resaltado anotado).')
    print(f'\nEscrito {OUT}')

if __name__ == '__main__':
    main()
