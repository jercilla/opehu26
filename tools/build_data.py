#!/usr/bin/env python3
"""
Procesa el JSON de preguntas y genera quiz/js/data.js con diffs precalculados.
Uso: python3 tools/build_data.py
"""
import json, re, os

def split_tokens(text):
    """Separa palabras y no-palabras (espacios, puntuacion) en tokens."""
    return re.findall(r'\w+|\W+', text)

def tokens_equal(a, b):
    """Compara tokens ignorando mayusculas y considerando espacios equivalentes."""
    if a.isspace() and b.isspace():
        return True
    return a.lower() == b.lower()

def lcs_tokens(a, b):
    """Longest Common Subsequence sobre listas de tokens."""
    dp = [[0]*(len(b)+1) for _ in range(len(a)+1)]
    for i in range(1, len(a)+1):
        for j in range(1, len(b)+1):
            if tokens_equal(a[i-1], b[j-1]):
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    i, j = len(a), len(b)
    res = []
    while i > 0 and j > 0:
        if tokens_equal(a[i-1], b[j-1]):
            res.append(('same', a[i-1]))
            i -= 1; j -= 1
        elif dp[i-1][j] >= dp[i][j-1]:
            res.append(('diff', a[i-1]))
            i -= 1
        else:
            j -= 1
    while i > 0:
        res.append(('diff', a[i-1]))
        i -= 1
    res.reverse()
    return res

def common_word_count(a, b):
    wa = set(re.findall(r'\b\w{3,}\b', a.lower()))
    wb = set(re.findall(r'\b\w{3,}\b', b.lower()))
    return len(wa & wb)

def escape_html(s):
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def highlight(text, other):
    a = split_tokens(text)
    b = split_tokens(other)
    diff = lcs_tokens(a, b)
    html = ''
    in_diff = False
    for typ, tok in diff:
        esc = escape_html(tok)
        if typ == 'diff' and not tok.isspace():
            if not in_diff:
                html += '<span class="diff-highlight">'
                in_diff = True
            html += esc
        else:
            if in_diff:
                html += '</span>'
                in_diff = False
            html += esc
    if in_diff:
        html += '</span>'
    return html

def process_question(q, threshold=15):
    opts = q['opciones']
    letters = list(opts.keys())
    texts = [opts[l] for l in letters]

    # Compute max similarity score between any pair of options
    max_score = 0
    for i in range(len(letters)):
        for j in range(i + 1, len(letters)):
            score = common_word_count(texts[i], texts[j])
            if score > max_score:
                max_score = score

    # Only generate diffs if options are sufficiently similar
    if max_score < threshold:
        if 'diffs' in q:
            del q['diffs']
        return q

    diffs = {}
    for i, li in enumerate(letters):
        best = -1
        best_score = -1
        for j, lj in enumerate(letters):
            if i == j:
                continue
            score = common_word_count(texts[i], texts[j])
            if score > best_score:
                best_score = score
                best = j
        if best == -1 or best_score < 3:
            diffs[li] = escape_html(texts[i])
        else:
            diffs[li] = highlight(texts[i], texts[best])
    q['diffs'] = diffs
    return q

QUIZ_SOURCES = [
    {
        'slug': 'administrativo_c1',
        'file': 'administrativo_c1.json',
        'label': 'Administrativo C1',
        'meta': '500 preguntas - OPE 2023-2024 UPV/EHU',
    },
]

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dst = os.path.join(root, 'quiz', 'js', 'data.js')

    quizzes = {}
    total = 0
    for src_cfg in QUIZ_SOURCES:
        src = os.path.join(root, src_cfg['file'])
        if not os.path.exists(src):
            print(f'[SKIP] {src} no encontrado')
            continue
        with open(src, encoding='utf-8') as f:
            questions = json.load(f)
        processed = [process_question(q) for q in questions]
        quizzes[src_cfg['slug']] = {
            'label': src_cfg['label'],
            'meta': src_cfg['meta'],
            'questions': processed,
        }
        total += len(processed)
        print(f'[OK] {src_cfg["slug"]}: {len(processed)} preguntas')

    with open(dst, 'w', encoding='utf-8') as f:
        f.write('const QUIZZES = ')
        json.dump(quizzes, f, ensure_ascii=False, indent=2)
        f.write(';\n')

    print(f'Generado {dst} con {total} preguntas totales y diffs precalculados.')

if __name__ == '__main__':
    main()
