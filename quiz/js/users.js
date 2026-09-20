const Users = (() => {
  const KEY_USERS = 'quiz_users';
  const KEY_LAST = 'quiz_last_user';

  function list() {
    try { return JSON.parse(localStorage.getItem(KEY_USERS)) || []; } catch { return []; }
  }
  function save(users) { localStorage.setItem(KEY_USERS, JSON.stringify(users)); }

  function create(name) {
    const n = name.trim();
    if (!n) return { ok: false, error: 'El nombre no puede estar vacio' };
    const users = list();
    if (users.includes(n)) return { ok: false, error: 'Ya existe un perfil con ese nombre' };
    users.push(n);
    save(users);
    return { ok: true, user: n };
  }

  function remove(name) {
    const users = list().filter(u => u !== name);
    save(users);
    // also wipe their stats keys
    const prefix = `quiz_user_${name}_`;
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const k = localStorage.key(i);
      if (k && k.startsWith(prefix)) localStorage.removeItem(k);
    }
    const last = getLast();
    if (last === name) {
      localStorage.removeItem(KEY_LAST);
    }
  }

  function getLast() { return localStorage.getItem(KEY_LAST) || null; }
  function setLast(name) { localStorage.setItem(KEY_LAST, name); }

  function ensureDefault() {
    let users = list();
    if (users.length === 0) {
      create('User 1');
      users = list();
    }
    let last = getLast();
    if (!last || !users.includes(last)) {
      last = users[0];
      setLast(last);
    }
    return last;
  }

  function exportData() {
    const data = {};
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && (k.startsWith('quiz_') || k === 'quiz_last_user')) {
        data[k] = localStorage.getItem(k);
      }
    }
    return data;
  }

  function previewImport(data) {
    const conflicts = [];
    const existingUsers = list();
    const importedUsers = JSON.parse(data['quiz_users'] || '[]');

    // Detect deleted highlights that still exist locally
    for (const [key, value] of Object.entries(data)) {
      if (!key.endsWith('_deleted_highlights')) continue;
      const user = key.replace('quiz_user_', '').replace('_deleted_highlights', '');
      if (!existingUsers.includes(user)) continue;

      const importedDeletes = JSON.parse(value);
      const highlightsRaw = localStorage.getItem(`quiz_user_${user}_highlights`);
      if (!highlightsRaw) continue;
      const existingHighlights = JSON.parse(highlightsRaw);

      for (const [quizSlug, questions] of Object.entries(importedDeletes)) {
        if (!existingHighlights[quizSlug]) continue;
        for (const [qid, letters] of Object.entries(questions)) {
          if (!existingHighlights[quizSlug][qid]) continue;
          for (const [letter, texts] of Object.entries(letters)) {
            if (!existingHighlights[quizSlug][qid][letter]) continue;
            for (const text of texts) {
              if (existingHighlights[quizSlug][qid][letter].includes(text)) {
                const quizData = window.QUIZZES && window.QUIZZES[quizSlug];
                const question = quizData ? quizData.questions.find(q => String(q.idpregunta) === String(qid)) : null;
                conflicts.push({
                  user, quizSlug, idpregunta: qid, letter, text,
                  pregunta: question ? question.pregunta : `Pregunta ${qid}`,
                  opcion: question ? question.opciones[letter] : text,
                });
              }
            }
          }
        }
      }
    }

    return { conflicts, apply: () => applyImport(data, conflicts) };
  }

  function applyImport(data, conflictsToDelete) {
    // Merge users
    const existingUsers = list();
    const importedUsers = JSON.parse(data['quiz_users'] || '[]');
    const mergedUsers = [...new Set([...existingUsers, ...importedUsers])];
    save(mergedUsers);

    for (const [key, value] of Object.entries(data)) {
      if (key === 'quiz_users' || key === 'quiz_last_user') continue;
      const existing = localStorage.getItem(key);
      if (!existing) {
        localStorage.setItem(key, value);
        continue;
      }
      try {
        const existingObj = JSON.parse(existing);
        const importedObj = JSON.parse(value);
        const merged = mergeKey(existingObj, importedObj, key);
        localStorage.setItem(key, JSON.stringify(merged));
      } catch {
        localStorage.setItem(key, value);
      }
    }

    // Apply deletions
    if (conflictsToDelete && conflictsToDelete.length > 0) {
      for (const c of conflictsToDelete) {
        const h = JSON.parse(localStorage.getItem(`quiz_user_${c.user}_highlights`) || '{}');
        if (h[c.quizSlug] && h[c.quizSlug][c.idpregunta] && h[c.quizSlug][c.idpregunta][c.letter]) {
          const arr = h[c.quizSlug][c.idpregunta][c.letter];
          const idx = arr.indexOf(c.text);
          if (idx >= 0) {
            arr.splice(idx, 1);
            if (arr.length === 0) delete h[c.quizSlug][c.idpregunta][c.letter];
            localStorage.setItem(`quiz_user_${c.user}_highlights`, JSON.stringify(h));
          }
        }
      }
    }
  }

  function mergeKey(existing, imported, key) {
    if (key.endsWith('_global')) {
      for (const [quiz, stats] of Object.entries(imported)) {
        if (!existing[quiz]) existing[quiz] = stats;
        else {
          existing[quiz].total_respondidas += stats.total_respondidas;
          existing[quiz].total_aciertos += stats.total_aciertos;
          existing[quiz].total_fallos += stats.total_fallos;
        }
      }
      return existing;
    }
    if (key.endsWith('_por_pregunta')) {
      for (const [quiz, questions] of Object.entries(imported)) {
        if (!existing[quiz]) existing[quiz] = questions;
        else {
          for (const [qid, stats] of Object.entries(questions)) {
            if (!existing[quiz][qid]) existing[quiz][qid] = stats;
            else {
              existing[quiz][qid].aciertos += stats.aciertos;
              existing[quiz][qid].fallos += stats.fallos;
              existing[quiz][qid].ultimo_resultado = stats.ultimo_resultado;
            }
          }
        }
      }
      return existing;
    }
    if (key.endsWith('_highlights')) {
      for (const [quiz, questions] of Object.entries(imported)) {
        if (!existing[quiz]) existing[quiz] = questions;
        else {
          for (const [qid, letters] of Object.entries(questions)) {
            if (!existing[quiz][qid]) existing[quiz][qid] = letters;
            else {
              for (const [letter, texts] of Object.entries(letters)) {
                if (!existing[quiz][qid][letter]) existing[quiz][qid][letter] = texts;
                else {
                  existing[quiz][qid][letter] = [...new Set([...existing[quiz][qid][letter], ...texts])];
                }
              }
            }
          }
        }
      }
      return existing;
    }
    if (key.endsWith('_deleted_highlights')) {
      for (const [quiz, questions] of Object.entries(imported)) {
        if (!existing[quiz]) existing[quiz] = questions;
        else {
          for (const [qid, letters] of Object.entries(questions)) {
            if (!existing[quiz][qid]) existing[quiz][qid] = letters;
            else {
              for (const [letter, texts] of Object.entries(letters)) {
                if (!existing[quiz][qid][letter]) existing[quiz][qid][letter] = texts;
                else {
                  existing[quiz][qid][letter] = [...new Set([...existing[quiz][qid][letter], ...texts])];
                }
              }
            }
          }
        }
      }
      return existing;
    }
    // For other keys (collapsed, last_ranges, session): overwrite
    return imported;
  }

  return { list, create, remove, getLast, setLast, ensureDefault, exportData, previewImport };
})();
