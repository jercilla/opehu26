const Stats = (() => {
  function record(user, quizSlug, idpregunta, correcta, elegida) {
    const acierto = elegida === correcta;

    // global per quiz
    const g = State.getGlobal(user, quizSlug);
    g.total_respondidas += 1;
    if (acierto) g.total_aciertos += 1; else g.total_fallos += 1;
    State.setGlobal(user, quizSlug, g);

    // per question per quiz
    const pp = State.getPorPregunta(user, quizSlug);
    const rec = pp[idpregunta] || { aciertos: 0, fallos: 0, ultimo_resultado: null };
    if (acierto) rec.aciertos += 1; else rec.fallos += 1;
    rec.ultimo_resultado = acierto ? 'acierto' : 'fallo';
    pp[idpregunta] = rec;
    State.setPorPregunta(user, quizSlug, pp);

    return acierto;
  }

  function getGlobal(user, quizSlug) { return State.getGlobal(user, quizSlug); }

  // Marca/desmarca una pregunta como "me cuesta" (estado intermedio, independiente
  // de acierto/fallo). Se guarda en el detalle por pregunta.
  function setCuesta(user, quizSlug, idpregunta, value) {
    const pp = State.getPorPregunta(user, quizSlug);
    const rec = pp[idpregunta] || { aciertos: 0, fallos: 0, ultimo_resultado: null };
    rec.cuesta = !!value;
    pp[idpregunta] = rec;
    State.setPorPregunta(user, quizSlug, pp);
    return rec.cuesta;
  }

  function isCuesta(user, quizSlug, idpregunta) {
    const pp = State.getPorPregunta(user, quizSlug);
    return !!(pp[idpregunta] && pp[idpregunta].cuesta);
  }

  function countCuesta(user, quizSlug) {
    const pp = State.getPorPregunta(user, quizSlug);
    return Object.values(pp).filter(r => r && r.cuesta).length;
  }

  function getRankingFallos(user, quizSlug, questions) {
    const pp = State.getPorPregunta(user, quizSlug);
    const arr = questions.map(q => {
      const r = pp[q.idpregunta] || { fallos: 0, aciertos: 0 };
      return { idpregunta: q.idpregunta, fallos: r.fallos, aciertos: r.aciertos, ratio: r.fallos - r.aciertos };
    });
    arr.sort((a, b) => b.ratio - a.ratio || b.fallos - a.fallos);
    return arr;
  }

  return { record, getGlobal, getRankingFallos, setCuesta, isCuesta, countCuesta };
})();
