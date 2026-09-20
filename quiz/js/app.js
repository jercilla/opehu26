const App = (() => {
  let currentUser = null;
  let selectedQuizSlug = null;

  const screens = {
    users: document.getElementById('screen-users'),
    menu: document.getElementById('screen-menu'),
    session: document.getElementById('screen-session'),
    quiz: document.getElementById('screen-quiz'),
    results: document.getElementById('screen-results'),
  };

  function show(name) {
    Object.values(screens).forEach(s => s.classList.add('hidden'));
    screens[name].classList.remove('hidden');
  }

  function renderUsers() {
    const list = document.getElementById('users-list');
    const users = Users.list();
    list.innerHTML = '';
    if (users.length === 0) {
      list.innerHTML = '<p style="color:#64748b;text-align:center;">No hay perfiles. Crea uno abajo.</p>';
      return;
    }
    users.forEach(u => {
      const div = document.createElement('div');
      div.className = 'user-item' + (u === currentUser ? ' active' : '');
      div.innerHTML = `<span class="user-item-name">${escapeHtml(u)}</span><span class="user-item-action">${u === currentUser ? 'activo' : 'usar'}</span>`;
      div.addEventListener('click', () => {
        currentUser = u;
        Users.setLast(u);
        goMenu();
      });
      list.appendChild(div);
    });
  }

  function getCollapsed() {
    try {
      return JSON.parse(localStorage.getItem(`quiz_user_${currentUser}_collapsed`)) || [];
    } catch { return []; }
  }
  function setCollapsed(slugs) {
    localStorage.setItem(`quiz_user_${currentUser}_collapsed`, JSON.stringify(slugs));
  }
  function toggleCollapsed(slug) {
    const arr = getCollapsed();
    const idx = arr.indexOf(slug);
    if (idx >= 0) arr.splice(idx, 1); else arr.push(slug);
    setCollapsed(arr);
  }

  function renderQuizzes() {
    const container = document.getElementById('quizzes-list');
    container.innerHTML = '';
    const collapsed = getCollapsed();
    Object.entries(QUIZZES).forEach(([slug, quiz]) => {
      const g = Stats.getGlobal(currentUser, slug);
      const isCollapsed = collapsed.includes(slug);
      const card = document.createElement('div');
      card.className = 'quiz-card' + (isCollapsed ? ' collapsed' : '');
      card.dataset.slug = slug;
      card.innerHTML = `
        <div class="quiz-card-header">
          <div>
            <h2>${escapeHtml(quiz.label)}</h2>
            <p class="quiz-meta">${escapeHtml(quiz.meta)}</p>
          </div>
          <span class="quiz-card-toggle">&#9662;</span>
        </div>
        <div class="quiz-card-body">
          <div class="stats-preview">
            <div class="stat"><span class="stat-value">${g.total_respondidas}</span><span class="stat-label">Respondidas</span></div>
            <div class="stat"><span class="stat-value">${g.total_aciertos}</span><span class="stat-label">Aciertos</span></div>
            <div class="stat"><span class="stat-value">${g.total_fallos}</span><span class="stat-label">Fallos</span></div>
            <div class="stat"><span class="stat-value">${Stats.countCuesta(currentUser, slug)}</span><span class="stat-label">Me cuestan</span></div>
          </div>
          <button class="btn btn-primary btn-block btn-open-session" data-slug="${escapeHtml(slug)}">Entrar</button>
        </div>
      `;
      container.appendChild(card);
    });

    container.querySelectorAll('.quiz-card-header').forEach(header => {
      header.addEventListener('click', () => {
        const card = header.closest('.quiz-card');
        const slug = card.dataset.slug;
        card.classList.toggle('collapsed');
        toggleCollapsed(slug);
      });
    });

    container.querySelectorAll('.btn-open-session').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        selectedQuizSlug = btn.dataset.slug;
        goSession(selectedQuizSlug);
      });
    });
  }

  function goSession(slug) {
    const quiz = QUIZZES[slug];
    document.getElementById('session-quiz-title').textContent = quiz.label;

    // Check saved session
    const saved = State.getSession(currentUser, slug);
    const resumeBox = document.getElementById('session-resume-box');
    if (saved && saved.order && saved.idx < saved.order.length) {
      document.getElementById('session-resume-text').textContent =
        `pregunta ${saved.idx + 1} de ${saved.order.length}`;
      resumeBox.classList.remove('hidden');
    } else {
      resumeBox.classList.add('hidden');
    }

    // Reset inputs defaults
    const qLen = quiz.questions.length;
    document.getElementById('seq-start').max = qLen;
    document.getElementById('seq-end').max = qLen;
    document.getElementById('rand-start').max = qLen;
    document.getElementById('rand-end').max = qLen;
    document.getElementById('diff-start').max = qLen;
    document.getElementById('diff-end').max = qLen;

    // Load last used ranges for this user/quiz
    const last = State.get(currentUser, 'last_ranges', {});
    const r = last[slug] || {};
    if (r.mode) {
      document.querySelector(`input[name="session-mode"][value="${r.mode}"]`).checked = true;
    }
    document.getElementById('seq-start').value = r.seqStart || 1;
    document.getElementById('seq-end').value = r.seqEnd || qLen;
    document.getElementById('rand-start').value = r.randStart || 1;
    document.getElementById('rand-end').value = r.randEnd || qLen;
    document.getElementById('diff-start').value = r.diffStart || 1;
    document.getElementById('diff-end').value = r.diffEnd || qLen;
    document.getElementById('chk-show-diffs').checked = r.showDiffs !== false;

    show('session');
  }

  function startSession(resume, practice) {
    const mode = document.querySelector('input[name="session-mode"]:checked').value;
    const seqStart = parseInt(document.getElementById('seq-start').value, 10) || 1;
    const seqEnd = parseInt(document.getElementById('seq-end').value, 10) || 1;
    const randStart = parseInt(document.getElementById('rand-start').value, 10) || 1;
    const randEnd = parseInt(document.getElementById('rand-end').value, 10) || 1;
    const diffStart = parseInt(document.getElementById('diff-start').value, 10) || 1;
    const diffEnd = parseInt(document.getElementById('diff-end').value, 10) || 1;
    const showDiffs = document.getElementById('chk-show-diffs').checked;

    // Save last used ranges
    const last = State.get(currentUser, 'last_ranges', {});
    last[selectedQuizSlug] = { mode, seqStart, seqEnd, randStart, randEnd, diffStart, diffEnd, showDiffs };
    State.set(currentUser, 'last_ranges', last);

    Quiz.start({ user: currentUser, slug: selectedQuizSlug, mode, seqStart, seqEnd, randStart, randEnd, diffStart, diffEnd, showDiffs, resume, practice });
    show('quiz');
  }

  function renderUserDropdown() {
    const dd = document.getElementById('user-dropdown');
    const users = Users.list();
    dd.innerHTML = '';
    users.forEach(u => {
      const div = document.createElement('div');
      div.className = 'dropdown-item' + (u === currentUser ? ' active' : '');
      div.innerHTML = `<span>${escapeHtml(u)}</span>${u === currentUser ? '<span class="dropdown-check">&#10003;</span>' : ''}`;
      div.addEventListener('click', () => {
        currentUser = u;
        Users.setLast(u);
        dd.classList.add('hidden');
        goMenu();
      });
      dd.appendChild(div);
    });
  }

  function toggleUserDropdown() {
    const dd = document.getElementById('user-dropdown');
    if (dd.classList.contains('hidden')) {
      renderUserDropdown();
      dd.classList.remove('hidden');
    } else {
      dd.classList.add('hidden');
    }
  }

  function goUsers() {
    renderUsers();
    show('users');
  }

  function goMenu() {
    currentUser = Users.ensureDefault();
    document.getElementById('current-user-name').textContent = currentUser;
    renderQuizzes();
    show('menu');
  }

  function showImportModal(conflicts) {
    const list = document.getElementById('import-conflicts-list');
    list.innerHTML = '';
    conflicts.forEach(c => {
      const item = document.createElement('div');
      item.className = 'import-conflict-item';
      const shortQ = c.pregunta.length > 80 ? c.pregunta.slice(0, 80) + '...' : c.pregunta;
      const shortO = c.opcion.length > 60 ? c.opcion.slice(0, 60) + '...' : c.opcion;
      item.innerHTML = `
        <input type="checkbox" checked data-user="${escapeHtml(c.user)}" data-quiz="${escapeHtml(c.quizSlug)}" data-qid="${escapeHtml(c.idpregunta)}" data-letter="${escapeHtml(c.letter)}" data-text="${escapeHtml(c.text)}">
        <div class="import-conflict-text">
          <span class="conf-q">${escapeHtml(shortQ)}</span>
          <span class="conf-opt">${escapeHtml(c.letter)}: ${escapeHtml(shortO)} — <em>${escapeHtml(c.text)}</em></span>
        </div>
      `;
      list.appendChild(item);
    });
    document.getElementById('import-modal').classList.remove('hidden');
  }

  function hideImportModal() {
    document.getElementById('import-modal').classList.add('hidden');
  }

  function init() {
    currentUser = Users.ensureDefault();
    goMenu();

    document.getElementById('btn-switch-user').addEventListener('click', goUsers);
    document.getElementById('menu-user-badge').addEventListener('click', (e) => {
      e.stopPropagation();
      toggleUserDropdown();
    });
    document.getElementById('btn-back-from-users').addEventListener('click', goMenu);

    document.addEventListener('click', () => {
      document.getElementById('user-dropdown').classList.add('hidden');
    });
    document.getElementById('user-dropdown').addEventListener('click', (e) => e.stopPropagation());

    document.getElementById('new-user-form').addEventListener('submit', e => {
      e.preventDefault();
      const input = document.getElementById('new-user-name');
      const res = Users.create(input.value);
      if (res.ok) {
        input.value = '';
        currentUser = res.user;
        Users.setLast(res.user);
        goMenu();
      } else {
        alert(res.error);
      }
    });

    document.getElementById('btn-clear-data').addEventListener('click', () => {
      if (!confirm('¿Seguro? Se borraran TODOS los perfiles, estadisticas y sesiones guardadas.')) return;
      // Remove all quiz-related keys
      for (let i = localStorage.length - 1; i >= 0; i--) {
        const k = localStorage.key(i);
        if (k && (k.startsWith('quiz_') || k === 'quiz_last_user')) {
          localStorage.removeItem(k);
        }
      }
      currentUser = null;
      Users.ensureDefault();
      renderUsers();
    });

    document.getElementById('btn-export-data').addEventListener('click', () => {
      const data = Users.exportData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ope_quiz_backup_${new Date().toISOString().slice(0,10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    });

    let pendingImportData = null;
    let pendingImportApply = null;

    document.getElementById('btn-import-data').addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        try {
          const data = JSON.parse(ev.target.result);
          const preview = Users.previewImport(data);
          if (preview.conflicts.length > 0) {
            pendingImportData = data;
            pendingImportApply = preview.apply;
            showImportModal(preview.conflicts);
          } else {
            if (!confirm('¿Importar datos? Se fusionaran con los existentes (stats se suman, subrayados se unen).')) return;
            preview.apply();
            currentUser = Users.ensureDefault();
            renderUsers();
            alert('Datos importados correctamente.');
          }
        } catch (err) {
          alert('Error al importar: ' + err.message);
        }
      };
      reader.readAsText(file);
      e.target.value = '';
    });

    document.getElementById('btn-import-cancel').addEventListener('click', () => {
      if (!pendingImportData || !pendingImportApply) return;
      // Apply without deletions
      pendingImportApply();
      pendingImportData = null;
      pendingImportApply = null;
      hideImportModal();
      currentUser = Users.ensureDefault();
      renderUsers();
      alert('Datos importados. Se mantuvieron todos los subrayados locales.');
    });

    document.getElementById('btn-import-confirm').addEventListener('click', () => {
      if (!pendingImportData || !pendingImportApply) return;
      const checked = Array.from(document.querySelectorAll('.import-conflict-item input:checked')).map(cb => ({
        user: cb.dataset.user, quizSlug: cb.dataset.quiz, idpregunta: cb.dataset.qid,
        letter: cb.dataset.letter, text: cb.dataset.text
      }));
      pendingImportApply(checked);
      pendingImportData = null;
      pendingImportApply = null;
      hideImportModal();
      currentUser = Users.ensureDefault();
      renderUsers();
      alert(`Import completado. ${checked.length} subrayados eliminados.`);
    });

    document.getElementById('btn-back-from-session').addEventListener('click', goMenu);
    document.getElementById('btn-start-session').addEventListener('click', () => startSession(false, false));
    document.getElementById('btn-practice-session').addEventListener('click', () => startSession(false, true));
    document.getElementById('btn-continue-session').addEventListener('click', () => startSession(true, false));

    document.getElementById('btn-validate').addEventListener('click', () => Quiz.validate());
    document.getElementById('btn-next').addEventListener('click', () => Quiz.next());
    document.getElementById('btn-cuesta').addEventListener('click', () => Quiz.toggleCuesta());
    document.getElementById('btn-quit-quiz').addEventListener('click', () => {
      goMenu();
    });
    document.getElementById('btn-back-menu').addEventListener('click', () => {
      goMenu();
    });

    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('sw.js').catch(() => {});
    }
  }

  function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  return { init };
})();

window.addEventListener('DOMContentLoaded', App.init);
