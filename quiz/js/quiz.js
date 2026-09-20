const Quiz = (() => {
  let user = null;
  let quizSlug = null;
  let questions = [];
  let order = [];
  let idx = 0;
  let session = { aciertos: 0, fallos: 0, falladas: [], cuesta: [] };
  let current = null;
  let validated = false;
  let practice = false;
  let showDiffs = true;

  const els = {
    progress: document.getElementById('quiz-progress'),
    score: document.getElementById('quiz-score'),
    label: document.getElementById('quiz-label'),
    text: document.getElementById('question-text'),
    options: document.getElementById('options-list'),
    validate: document.getElementById('btn-validate'),
    next: document.getElementById('btn-next'),
    cuesta: document.getElementById('btn-cuesta'),
    feedback: document.getElementById('feedback'),
    feedbackText: document.getElementById('feedback-text'),
  };

  function shuffle(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  // Orden por dificultad dentro del rango [start,end] (por numero de pregunta).
  // Criterios (prioridad alta -> baja):
  //   1) menos intentos (aciertos+fallos) primero
  //   2) mayor tasa de fallo (fallos/intentos, 0 si nunca respondida)
  //   3) marcadas 'me cuesta' primero
  //   4) orden de pregunta (estable)
  function buildDifficultyOrder(start, end) {
    const dStart = Math.max(0, (start || 1) - 1);
    const dEnd = Math.min(questions.length, end || questions.length);
    const pp = State.getPorPregunta(user, quizSlug);
    const pool = [];
    for (let i = dStart; i < dEnd; i++) pool.push(i);
    pool.sort((a, b) => {
      const ra = pp[questions[a].idpregunta] || {};
      const rb = pp[questions[b].idpregunta] || {};
      const ia = (ra.aciertos || 0) + (ra.fallos || 0);
      const ib = (rb.aciertos || 0) + (rb.fallos || 0);
      if (ia !== ib) return ia - ib;
      const fa = ia ? (ra.fallos || 0) / ia : 0;
      const fb = ib ? (rb.fallos || 0) / ib : 0;
      if (fa !== fb) return fb - fa;
      const ca = ra.cuesta ? 1 : 0, cb = rb.cuesta ? 1 : 0;
      if (ca !== cb) return cb - ca;
      return a - b;
    });
    return pool;
  }

  function start(config) {
    user = config.user;
    quizSlug = config.slug;
    questions = QUIZZES[quizSlug].questions;
    practice = config.practice || false;
    showDiffs = config.showDiffs !== false;
    els.label.textContent = QUIZZES[quizSlug].label + (practice ? ' (Prueba)' : '');

    if (config.resume) {
      const saved = State.getSession(user, quizSlug);
      if (saved) {
        order = saved.order;
        idx = saved.idx;
        session = saved.session || { aciertos: 0, fallos: 0, falladas: [], cuesta: [] };
        if (!session.cuesta) session.cuesta = [];
        validated = saved.validated || false;
        selectedLetter = saved.selectedLetter || null;
        if (saved.showDiffs !== undefined) showDiffs = saved.showDiffs;
        renderQuestion();
        return;
      }
    }

    if (!practice) {
      State.clearSession(user, quizSlug);
    }
    session = { aciertos: 0, fallos: 0, falladas: [], cuesta: [] };
    validated = false;
    selectedLetter = null;

    if (config.mode === 'random') {
      const rStart = Math.max(0, (config.randStart || 1) - 1);
      const rEnd = Math.min(questions.length, config.randEnd || questions.length);
      const pool = questions.map((_, i) => i).slice(rStart, rEnd);
      order = shuffle(pool);
    } else if (config.mode === 'difficulty') {
      order = buildDifficultyOrder(config.diffStart, config.diffEnd);
    } else {
      const sStart = Math.max(0, (config.seqStart || 1) - 1);
      const sEnd = Math.min(questions.length, config.seqEnd || questions.length);
      order = [];
      for (let i = sStart; i < sEnd; i++) order.push(i);
    }

    idx = 0;
    if (order.length === 0) {
      showResults();
      return;
    }
    if (!practice) saveProgress();
    renderQuestion();
  }

  function saveProgress() {
    if (practice) return;
    State.setSession(user, quizSlug, { order, idx, session, validated, selectedLetter, showDiffs });
  }

  function renderQuestion() {
    current = questions[order[idx]];
    document.getElementById('screen-quiz').classList.toggle('validated', validated);
    els.progress.textContent = `${idx + 1} / ${order.length}`;
    els.score.innerHTML = `&#9989; ${session.aciertos} - &#10060; ${session.fallos}`;
    els.options.innerHTML = '';

    if (validated) {
      // Post-validar: texto plano + highlights, botones deshabilitados
      els.text.innerHTML = applyHighlights(escapeHtml(current.pregunta), 'Q');
      const correct = current.correcta;
      ['A','B','C','D'].forEach(letter => {
        const txt = current.opciones[letter];
        if (txt === undefined) return;
        const btn = document.createElement('div');
        btn.className = 'option';
        btn.setAttribute('role', 'button');
        btn.setAttribute('tabindex', '-1');
        btn.dataset.letter = letter;
        if (letter === correct) btn.classList.add('correct');
        else if (letter === selectedLetter && letter !== correct) btn.classList.add('wrong');
        renderOptionText(btn, letter);
        els.options.appendChild(btn);
      });
      els.validate.classList.add('hidden');
      els.next.classList.remove('hidden');
      els.feedback.classList.remove('hidden');
      if (session.lastResult) {
        const lr = session.lastResult;
        els.feedback.className = 'feedback ' + (lr.acierto ? 'correct' : 'wrong');
        els.feedbackText.textContent = lr.acierto ? 'Correcto!' : `La correcta era la ${lr.correct}`;
      }
    } else {
      // Pre-validar: diffs como están ahora
      els.text.textContent = current.pregunta;
      ['A','B','C','D'].forEach(letter => {
        const txt = current.opciones[letter];
        if (txt === undefined) return;
        const btn = document.createElement('div');
        btn.className = 'option';
        btn.setAttribute('role', 'button');
        btn.setAttribute('tabindex', '0');
        btn.dataset.letter = letter;
        let html = (showDiffs && current.diffs && current.diffs[letter]) ? current.diffs[letter] : escapeHtml(txt);
        btn.innerHTML = `<span class="option-letter">${letter}</span><span class="option-text">${html}</span>`;
        btn.addEventListener('click', () => selectOption(letter));
        btn.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectOption(letter); }
        });
        els.options.appendChild(btn);
      });
      els.validate.classList.remove('hidden');
      els.validate.disabled = true;
      els.next.classList.add('hidden');
      els.feedback.classList.add('hidden');
      els.feedback.className = 'feedback hidden';
    }
    updateCuestaButton();
  }

  function renderOptionText(btn, letter) {
    const txt = current.opciones[letter];
    if (txt === undefined) return;
    let html = escapeHtml(txt);
    html = applyHighlights(html, letter);
    btn.innerHTML = `<span class="option-letter">${letter}</span><span class="option-text">${html}</span>`;
  }

  let selectedLetter = null;
  function selectOption(letter) {
    if (validated) return;
    selectedLetter = letter;
    Array.from(els.options.children).forEach(btn => {
      btn.classList.toggle('selected', btn.dataset.letter === letter);
    });
    els.validate.disabled = false;
    const rect = els.validate.getBoundingClientRect();
    if (rect.bottom > window.innerHeight) {
      els.validate.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  function validate() {
    if (validated || !selectedLetter) return;
    validated = true;
    document.getElementById('screen-quiz').classList.add('validated');
    const correct = current.correcta;
    const acierto = selectedLetter === correct;
    if (acierto) session.aciertos++; else {
      session.fallos++;
      session.falladas.push({
        num: current.num,
        pregunta: current.pregunta,
        opciones: current.opciones,
        correcta: correct,
        elegida: selectedLetter,
      });
    }

    if (!practice) {
      Stats.record(user, quizSlug, current.idpregunta, correct, selectedLetter);
    }
    session.lastResult = { correct, selectedLetter, acierto };
    saveProgress();

    Array.from(els.options.children).forEach(btn => {
      const l = btn.dataset.letter;
      btn.setAttribute('tabindex', '-1');
      if (l === correct) btn.classList.add('correct');
      else if (l === selectedLetter && l !== correct) btn.classList.add('wrong');
      // Reemplazar diffs por texto plano + highlights
      renderOptionText(btn, l);
    });
    els.text.innerHTML = applyHighlights(escapeHtml(current.pregunta), 'Q');

    els.validate.classList.add('hidden');
    els.next.classList.remove('hidden');
    els.feedback.classList.remove('hidden');
    els.feedback.className = 'feedback ' + (acierto ? 'correct' : 'wrong');
    els.feedbackText.textContent = acierto ? 'Correcto!' : `La correcta era la ${correct}`;
    els.score.innerHTML = `&#9989; ${session.aciertos} - &#10060; ${session.fallos}`;
    // Mostrar el boton 'me cuesta' ANTES de medir el scroll: al aparecer empuja
    // 'Siguiente' hacia abajo, y queremos desplazar hasta su posicion final.
    updateCuestaButton();
    const nextRect = els.next.getBoundingClientRect();
    if (nextRect.bottom > window.innerHeight) {
      els.next.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  // Estado "me cuesta": marcable tras validar (solo modo Empezar). Persiste en
  // el detalle por pregunta y se cuenta en los resultados de la sesion.
  function updateCuestaButton() {
    if (!els.cuesta) return;
    const show = validated && !practice && current;
    els.cuesta.classList.toggle('hidden', !show);
    if (!show) return;
    const marked = Stats.isCuesta(user, quizSlug, current.idpregunta);
    els.cuesta.classList.toggle('marked', marked);
    els.cuesta.textContent = marked ? '✓ Me cuesta' : 'Esta me cuesta';
  }

  function toggleCuesta() {
    if (!validated || practice || !current) return;
    const idp = current.idpregunta;
    const marked = Stats.setCuesta(user, quizSlug, idp, !Stats.isCuesta(user, quizSlug, idp));
    if (!session.cuesta) session.cuesta = [];
    const i = session.cuesta.indexOf(idp);
    if (marked && i === -1) session.cuesta.push(idp);
    else if (!marked && i !== -1) session.cuesta.splice(i, 1);
    updateCuestaButton();
    saveProgress();
  }

  function next() {
    idx++;
    selectedLetter = null;
    validated = false;
    session.lastResult = null;
    saveProgress();
    if (idx >= order.length) {
      if (!practice) {
        State.clearSession(user, quizSlug);
      }
      showResults();
      return;
    }
    renderQuestion();
    els.text.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function showResults() {
    document.getElementById('screen-quiz').classList.add('hidden');
    document.getElementById('screen-results').classList.remove('hidden');
    document.getElementById('result-aciertos').textContent = session.aciertos;
    document.getElementById('result-fallos').textContent = session.fallos;
    document.getElementById('result-detail').textContent = `${session.aciertos + session.fallos} de ${order.length} preguntas`;

    const nCuesta = (session.cuesta || []).length;
    const cuestaEl = document.getElementById('result-cuesta');
    if (nCuesta > 0) {
      cuestaEl.textContent = `Marcaste ${nCuesta} como "me cuesta"`;
      cuestaEl.classList.remove('hidden');
    } else {
      cuestaEl.classList.add('hidden');
    }

    const container = document.getElementById('result-falladas');
    container.innerHTML = '';
    if (!session.falladas || session.falladas.length === 0) return;

    const title = document.createElement('h3');
    title.className = 'result-falladas-title';
    title.textContent = `Preguntas falladas (${session.falladas.length})`;
    container.appendChild(title);

    session.falladas.forEach((f, i) => {
      const card = document.createElement('div');
      card.className = 'result-fallada-card collapsed';

      const header = document.createElement('div');
      header.className = 'result-fallada-header';
      header.innerHTML = `<h4>${escapeHtml(f.pregunta)}</h4><span class="result-fallada-toggle">&#9662;</span>`;
      header.addEventListener('click', () => card.classList.toggle('collapsed'));
      card.appendChild(header);

      const body = document.createElement('div');
      body.className = 'result-fallada-body';

      ['A','B','C','D'].forEach(letter => {
        const txt = f.opciones[letter];
        if (txt === undefined) return;
        const isCorrect = letter === f.correcta;
        const isWrong = letter === f.elegida && !isCorrect;
        const row = document.createElement('div');
        row.className = 'result-fallada-opt' + (isCorrect ? ' correct' : '') + (isWrong ? ' wrong' : '');
        row.innerHTML = `<span class="result-fallada-opt-letter">${letter}</span><span class="result-fallada-opt-text">${escapeHtml(txt)}</span>`;
        body.appendChild(row);
      });

      card.appendChild(body);
      container.appendChild(card);
    });
  }

  function applyHighlights(html, letter) {
    const h = State.getHighlights(user, quizSlug);
    const list = h[current.idpregunta] && h[current.idpregunta][letter] ? h[current.idpregunta][letter] : [];
    if (list.length === 0) return html;
    const sorted = list.slice().sort((a, b) => b.length - a.length);
    const spans = {};
    sorted.forEach((text, i) => {
      const escaped = escapeHtml(text);
      const marker = `___HL_${i}___`;
      spans[marker] = `<span class="user-highlight" data-letter="${letter}">${escaped}<span class="hl-x">&#10005;</span></span>`;
      // Solo primera ocurrencia (replace, no replaceAll)
      html = html.replace(escaped, marker);
    });
    for (const [marker, span] of Object.entries(spans)) {
      html = html.replaceAll(marker, span);
    }
    return html;
  }

  // ---------- highlight interaction (post-validate only) ----------
  const highlightMenu = document.createElement('div');
  highlightMenu.id = 'highlight-menu';
  highlightMenu.className = 'hidden';
  document.body.appendChild(highlightMenu);

  function showHighlightMenu(x, y, text, letter, isRemove) {
    highlightMenu.innerHTML = isRemove
      ? `Eliminar subrayado: "${escapeHtml(text)}"`
      : `Subrayar: "${escapeHtml(text)}"`;
    highlightMenu.style.left = x + 'px';
    highlightMenu.style.top = y + 'px';
    highlightMenu.classList.remove('hidden');
    highlightMenu.onclick = () => {
      if (isRemove) {
        State.removeHighlight(user, quizSlug, current.idpregunta, letter, text);
      } else {
        State.addHighlight(user, quizSlug, current.idpregunta, letter, text);
      }
      hideHighlightMenu();
      if (letter === 'Q') {
      els.text.innerHTML = applyHighlights(escapeHtml(current.pregunta), 'Q');
      } else {
        const btn = els.options.querySelector(`[data-letter="${letter}"]`);
        if (btn) renderOptionText(btn, letter);
      }
    };
  }

  function hideHighlightMenu() {
    highlightMenu.classList.add('hidden');
    highlightMenu.onclick = null;
  }

  let ignoreNextClick = false;

  document.addEventListener('click', (e) => {
    if (ignoreNextClick) {
      ignoreNextClick = false;
      return;
    }
    if (!highlightMenu.contains(e.target)) hideHighlightMenu();
  });

  // Suppress native context menu on highlightable text when validated
  document.addEventListener('contextmenu', (e) => {
    if (validated && (e.target.closest('.option-text') || e.target.closest('.question-text'))) {
      e.preventDefault();
    }
  });

  // PC: mouseup after selection -> show menu
  document.addEventListener('mouseup', () => {
    if (!validated) return;
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0 || sel.isCollapsed) return;
    const text = sel.toString().trim();
    if (!text) return;
    const range = sel.getRangeAt(0);
    const container = range.commonAncestorContainer;
    const optionText = container.nodeType === Node.TEXT_NODE
      ? container.parentElement.closest('.option-text')
      : container.closest('.option-text');
    const questionText = container.nodeType === Node.TEXT_NODE
      ? container.parentElement.closest('.question-text')
      : container.closest('.question-text');
    let letter, rect;
    if (optionText) {
      const btn = optionText.closest('.option');
      if (!btn) return;
      letter = btn.dataset.letter;
      rect = range.getBoundingClientRect();
    } else if (questionText) {
      letter = 'Q';
      rect = range.getBoundingClientRect();
    } else {
      return;
    }
    ignoreNextClick = true;
    showHighlightMenu(rect.left + window.scrollX, rect.bottom + window.scrollY + 4, text, letter, false);
  });

  // Click on X to remove (both PC and tablet)
  function handleXClick(e) {
    if (!validated) return;
    const x = e.target.closest('.hl-x');
    if (!x) return;
    e.stopPropagation();
    const hl = x.closest('.user-highlight');
    if (!hl) return;
    // Leer texto del primer nodo de texto del span (antes del X)
    const text = hl.childNodes[0] ? hl.childNodes[0].textContent : '';
    const letter = hl.dataset.letter;
    State.removeHighlight(user, quizSlug, current.idpregunta, letter, text);
    if (letter === 'Q') {
      els.text.innerHTML = applyHighlights(escapeHtml(current.pregunta), 'Q');
    } else {
      const btn = els.options.querySelector(`[data-letter="${letter}"]`);
      if (btn) renderOptionText(btn, letter);
    }
  }
  els.options.addEventListener('click', handleXClick);
  els.text.addEventListener('click', handleXClick);

  // Mobile: unified touch handling via event delegation on #screen-quiz
  let longPressTimer = null;
  let touchStartPos = null;

  document.getElementById('screen-quiz').addEventListener('touchstart', (e) => {
    if (!validated) return;
    const touch = e.touches[0];
    touchStartPos = { x: touch.clientX, y: touch.clientY };
    longPressTimer = setTimeout(() => { longPressTimer = null; }, 500);
  }, { passive: true });

  document.getElementById('screen-quiz').addEventListener('touchend', (e) => {
    if (!validated) return;
    const wasLongPress = longPressTimer === null;
    if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; }

    // 1. Prefer native text selection
    const sel = window.getSelection();
    if (sel && !sel.isCollapsed) {
      const text = sel.toString().trim();
      if (text) {
        const range = sel.getRangeAt(0);
        const container = range.commonAncestorContainer;
        const parent = container.nodeType === Node.TEXT_NODE ? container.parentElement : container;
        const optionText = parent.closest('.option-text');
        const questionText = parent.closest('.question-text');
        const rect = range.getBoundingClientRect();
        if (optionText) {
          const btn = optionText.closest('.option');
          if (btn) { showHighlightMenu(rect.left + window.scrollX, rect.bottom + window.scrollY + 4, text, btn.dataset.letter, false); return; }
        } else if (questionText) {
          showHighlightMenu(rect.left + window.scrollX, rect.bottom + window.scrollY + 4, text, 'Q', false); return;
        }
      }
    }

    // 2. Long-press: single word under finger
    if (wasLongPress) {
      const touch = e.changedTouches[0];
      let target = document.elementFromPoint(touch.clientX, touch.clientY);
      const textEl = target && (target.closest('.option-text') || target.closest('.question-text'));
      if (!textEl) { touchStartPos = null; return; }
      while (target && target !== els.options && target !== els.text) {
        if (target.classList && target.classList.contains('user-highlight')) { touchStartPos = null; return; }
        target = target.parentElement;
      }
      const pos = getTextNodeAtPoint(touch.clientX, touch.clientY);
      if (!pos) { touchStartPos = null; return; }
      const word = getWordAtPosition(pos.node, pos.offset);
      if (!word) { touchStartPos = null; return; }
      const optText = pos.node.nodeType === Node.TEXT_NODE ? pos.node.parentElement.closest('.option-text') : null;
      if (optText) {
        const btn = optText.closest('.option');
        if (btn) showHighlightMenu(touch.clientX + window.scrollX, touch.clientY + window.scrollY + 4, word, btn.dataset.letter, false);
      } else {
        showHighlightMenu(touch.clientX + window.scrollX, touch.clientY + window.scrollY + 4, word, 'Q', false);
      }
      touchStartPos = null;
      return;
    }

    // 3. Short tap: ignore
    touchStartPos = null;
  });

  function getTextNodeAtPoint(x, y) {
    if (document.caretPositionFromPoint) {
      const pos = document.caretPositionFromPoint(x, y);
      return pos ? { node: pos.offsetNode, offset: pos.offset } : null;
    } else if (document.caretRangeFromPoint) {
      const range = document.caretRangeFromPoint(x, y);
      return range ? { node: range.startContainer, offset: range.startOffset } : null;
    }
    return null;
  }

  function getWordAtPosition(node, offset) {
    if (node.nodeType !== Node.TEXT_NODE) return null;
    const text = node.textContent;
    if (offset < 0 || offset > text.length) return null;
    let start = offset;
    let end = offset;
    while (start > 0 && /\S/.test(text[start - 1])) start--;
    while (end < text.length && /\S/.test(text[end])) end++;
    const word = text.substring(start, end);
    return word.length > 0 ? word : null;
  }

  function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  return { start, validate, next, toggleCuesta };
})();
