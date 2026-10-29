#!/usr/bin/env python3
"""Build an offline quiz using only the Python standard library."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "錯題重做-資安.html"


def normalize(text):
    if text is None:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"(?<=[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]) (?=[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff])", "", text)


def make_questions(source):
    questions = []
    for q in source:
        if q.get("multiple") is not False or len(q.get("answers", [])) != 1:
            continue
        match = re.fullmatch(r"資安題庫([ABC])\.pdf", q["pdf"])
        if not match:
            raise ValueError("Unknown question bank")
        if set(q["options"]) != set("ABCD") or q["answers"][0] not in q["options"]:
            raise ValueError("Invalid single-choice options")
        questions.append({
            "id": q["pdf"] + "::" + q["qid"],
            "bank": match.group(1), "pdf": q["pdf"], "qid": q["qid"],
            "page": q["page"], "number": q["number"],
            "multiple": False, "answers": q["answers"],
            "chosen_last": q.get("chosen_last", []),
            "stem": normalize(q["stem"]),
            "options": {letter: normalize(text) for letter, text in q["options"].items()},
            "explanation": normalize(q["explanation"]),
            "group_context": normalize(q.get("group_context")),
        })
    if len({q["id"] for q in questions}) != len(questions):
        raise ValueError("Duplicate question identifiers")
    return questions


TEMPLATE = r'''<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>錯題重做・資安</title>
<style>
:root { color-scheme:light; --ink:#20312f; --muted:#556663; --paper:#f4f7f4; --line:#ccd8d2; --green:#14633e; --red:#a92a32; }
* { box-sizing:border-box; }
body { margin:0; background:var(--paper); color:var(--ink); font-family:-apple-system,"PingFang TC","Noto Sans TC",sans-serif; font-size:19px; line-height:1.65; }
main { max-width:800px; margin:auto; padding:24px 20px 60px; overflow-wrap:anywhere; }
[hidden] { display:none !important; }
h1 { font-size:clamp(30px,6vw,40px); margin:12px 0; line-height:1.35; }
h2 { font-size:24px; line-height:1.6; margin:16px 0; }
h3 { font-size:21px; margin:0 0 8px; }
p { margin:10px 0; }
button,input { font:inherit; }
button { min-height:56px; padding:13px 18px; border:1px solid var(--line); border-radius:14px; background:#fff; color:var(--ink); cursor:pointer; touch-action:manipulation; white-space:normal; overflow-wrap:anywhere; }
button:disabled { cursor:default; opacity:.5; }
button:focus-visible,input:focus-visible { outline:3px solid #2866ba; outline-offset:4px; }
button.primary { background:var(--green); color:white; border-color:var(--green); font-weight:650; }
button.wide { width:100%; }
button.quiet { background:transparent; }
.eyebrow { color:var(--green); font-size:15px; font-weight:700; letter-spacing:.12em; }
.muted { color:var(--muted); }
.small { font-size:16px; }
.panel { padding:22px; background:#fff; border:1px solid var(--line); border-radius:20px; margin:20px 0; }
.stack { display:grid; gap:12px; }
.row { display:flex; gap:12px; flex-wrap:wrap; align-items:center; }
.row > * { flex:1 1 150px; min-width:0; }
fieldset { border:0; padding:0; margin:20px 0; min-width:0; }
legend { font-weight:650; margin-bottom:10px; }
.choice { display:flex; align-items:center; gap:10px; min-height:56px; padding:10px 12px; border:1px solid var(--line); border-radius:12px; cursor:pointer; background:#fff; }
.choice input { flex:none; width:23px; height:23px; accent-color:var(--green); margin:0; }
.choice:has(input:checked) { background:#eaf4ed; border-color:var(--green); }
.toolbar { display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:16px; }
.toolbar button { flex:none; font-size:16px; }
.progress-text { font-weight:650; font-size:20px; }
progress { display:block; width:100%; height:10px; margin:12px 0 20px; accent-color:var(--green); }
.source { color:var(--muted); font-size:17px; }
.context { background:#eaf0f7; border-left:4px solid #7b97b1; padding:16px 18px; border-radius:8px; margin:20px 0; }
.option { width:100%; display:flex; align-items:flex-start; gap:12px; text-align:left; font-size:20px; line-height:1.6; }
.letter { flex:none; font-weight:750; width:24px; }
.option-copy { min-width:0; flex:1; }
.option.correct { border:2px solid var(--green); background:#e4f3e8; color:#105334; }
.option.incorrect { border:2px solid var(--red); background:#fce8e8; color:#8e1f29; }
.option:disabled { opacity:1; }
.badge { display:block; font-weight:700; font-size:17px; margin-top:5px; }
.feedback { margin-top:22px; border:1px solid var(--line); border-radius:16px; padding:20px; background:#fff; }
.outcome { font-size:23px; font-weight:750; }
.outcome.good { color:var(--green); }
.outcome.bad { color:var(--red); }
.navigation { margin-top:24px; }
.rate { font-size:56px; line-height:1.2; font-weight:750; color:var(--green); margin:14px 0; }
.bank-stat { border-top:1px solid var(--line); padding:12px 0; }
.wrong-item { text-align:left; width:100%; }
.wrong-item .source { display:block; }
.notice { background:#fff4d9; border:1px solid #b9913d; padding:14px 18px; border-radius:12px; margin-bottom:20px; font-size:17px; }
@media(max-width:420px) { main { padding:18px 14px 40px; } .panel { padding:17px; } .toolbar { align-items:flex-start; } .toolbar button { padding:10px 12px; } h2 { font-size:22px; } }
@media(prefers-reduced-motion:no-preference) { button { transition:background-color .12s ease; } }
</style>
</head>
<body>
<main>
<div id="storage-notice" class="notice" role="status" hidden></div>
<section id="home" aria-labelledby="home-title">
  <div class="eyebrow">iPAS 資訊安全工程師初級</div>
  <h1 id="home-title" tabindex="-1">錯題，再練一次。</h1>
  <p class="muted">一次一題，選完就看解析。慢慢來，把觀念記牢。</p>
  <div class="panel">
    <h2>共 <span id="total-count"></span> 題單選題</h2>
    <p id="bank-counts" class="muted small"></p>
    <fieldset><legend>題目順序</legend><div class="stack">
      <label class="choice"><input type="radio" name="order" value="ordered" checked>照題庫順序</label>
      <label class="choice"><input type="radio" name="order" value="random">隨機順序</label>
    </div></fieldset>
    <button id="start-all" class="primary wide">全部重做</button>
    <fieldset><legend>只做指定題庫（可複選）</legend><div class="row">
      <label class="choice"><input type="checkbox" name="bank" value="A" checked>題庫 A</label>
      <label class="choice"><input type="checkbox" name="bank" value="B" checked>題庫 B</label>
      <label class="choice"><input type="checkbox" name="bank" value="C" checked>題庫 C</label>
    </div></fieldset>
    <button id="start-selected" class="wide"></button>
  </div>
  <div id="resume-area" class="panel" hidden>
    <p id="resume-summary"></p>
    <div class="stack"><button id="resume" class="primary">繼續上次</button><button id="clear-progress" class="quiet">清除進度</button></div>
    <p class="small muted">開始新一輪會取代上次進度。</p>
  </div>
  <p class="small muted">離線即可練習。桌機可按 1～4 作答。進度只儲存在目前的瀏覽器中。</p>
  <noscript><div class="notice">這個測驗需要 JavaScript。若目前只看到檔案預覽，請以支援 JavaScript 的瀏覽器開啟 HTML。</div></noscript>
</section>
<section id="quiz" aria-labelledby="question-title" hidden>
  <div class="toolbar"><div><div id="progress-text" class="progress-text"></div><div id="correct-count" class="small muted"></div></div><button id="go-home">回首頁</button></div>
  <progress id="progress-bar" value="0" max="1" aria-label="已作答進度"></progress>
  <p id="question-source" class="source"></p>
  <div id="question-context" class="context" hidden><h3>題組共用題幹</h3><p id="context-text"></p></div>
  <h2 id="question-title" tabindex="-1"></h2>
  <div id="options" class="stack" role="group" aria-labelledby="question-title"></div>
  <div id="feedback" class="feedback" aria-live="polite" hidden></div>
  <div class="row navigation"><button id="previous">上一題</button><button id="next" class="primary" hidden>下一題</button></div>
  <button id="back-results" class="wide quiet navigation" hidden>回到本次結果</button>
</section>
<section id="results" aria-labelledby="results-title" hidden>
  <div class="eyebrow">這一輪完成了</div><h1 id="results-title" tabindex="-1">看看這次的成果</h1>
  <div class="panel"><p>本次答對率</p><div id="result-rate" class="rate"></div><p id="result-summary"></p><div id="bank-results"></div></div>
  <div class="stack"><button id="retry-wrong" class="primary">只重做這次答錯的</button><button id="results-home">回首頁</button></div>
  <h2>這次答錯的題目</h2><p id="wrong-hint" class="muted"></p><div id="wrong-list" class="stack"></div>
</section>
</main>
<script id="quiz-data" type="application/json">__QUIZ_DATA__</script>
<script id="quiz-core">
'use strict';
globalThis.QuizCore = (() => {
  const VERSION = 1;
  function shuffle(items, random = Math.random) {
    const result = [...items];
    for (let i = result.length - 1; i > 0; i--) {
      const j = Math.floor(random() * (i + 1));
      [result[i], result[j]] = [result[j], result[i]];
    }
    return result;
  }
  function create(questions, fingerprint, banks, randomOrder, ids = null, random = Math.random) {
    const allowed = ids === null ? null : new Set(ids);
    let selected = questions.filter(q => banks.includes(q.bank) && (allowed === null || allowed.has(q.id)));
    selected = selected.slice().sort((a,b) => a.bank.localeCompare(b.bank) || a.page - b.page || a.number - b.number);
    let order = selected.map(q => q.id);
    if (randomOrder) order = shuffle(order, random);
    if (!order.length) throw new Error('請至少選擇一個有題目的題庫。');
    return {version: VERSION, fingerprint, order, responses: {}, index: 0, mode: 'quiz', randomOrder};
  }
  function grade(question, choice) { return question.answers[0] === choice; }
  function answer(state, byId, choice) {
    const id = state.order[state.index], question = byId.get(id);
    if (state.mode !== 'quiz' || !question || !Object.hasOwn(question.options, choice) || Object.hasOwn(state.responses,id)) return state;
    return {...state, responses: {...state.responses, [id]: choice}};
  }
  function score(state, byId) {
    const banks = Object.fromEntries(['A','B','C'].map(bank => [bank,{correct:0, wrong:0, total:0}]));
    const wrongIds = [];
    let correct = 0, answered = 0;
    for (const id of state.order) {
      const q = byId.get(id); banks[q.bank].total++;
      if (!Object.hasOwn(state.responses,id)) continue;
      answered++;
      if (grade(q,state.responses[id])) {correct++; banks[q.bank].correct++;}
      else {wrongIds.push(id); banks[q.bank].wrong++;}
    }
    return {correct, answered, total:state.order.length, wrongIds, banks};
  }
  function move(state, delta) {
    return {...state, index:Math.max(0,Math.min(state.order.length-1,state.index+delta)),mode:'quiz'};
  }
  function serialize(state) { return JSON.stringify(state); }
  function restore(raw, questions, fingerprint) {
    try {
      const s = JSON.parse(raw), byId = new Map(questions.map(q => [q.id,q]));
      if (!s || s.version !== VERSION || s.fingerprint !== fingerprint || !Array.isArray(s.order) || !s.order.length || new Set(s.order).size !== s.order.length || s.order.some(id => !byId.has(id))) return null;
      if (!Number.isInteger(s.index) || s.index < 0 || s.index >= s.order.length || !['quiz','results'].includes(s.mode) || typeof s.randomOrder !== 'boolean') return null;
      if (!s.responses || typeof s.responses !== 'object' || Array.isArray(s.responses)) return null;
      if (Object.entries(s.responses).some(([id,choice]) => !s.order.includes(id) || !Object.hasOwn(byId.get(id).options,choice))) return null;
      // A session always answers in sequence, with earlier questions available for review.
      const firstUnanswered = s.order.findIndex(id => !Object.hasOwn(s.responses,id));
      if (firstUnanswered !== -1 && (s.index > firstUnanswered || s.order.slice(firstUnanswered).some(id => Object.hasOwn(s.responses,id)) || s.mode === 'results')) return null;
      return {version:VERSION, fingerprint, order:s.order, responses:s.responses, index:s.index, mode:s.mode, randomOrder:s.randomOrder};
    } catch { return null; }
  }
  return {create, shuffle, grade, answer, score, move, serialize, restore};
})();
</script>
<script id="quiz-app">
'use strict';
(() => {
  const data = JSON.parse(document.getElementById('quiz-data').textContent);
  const questions = data.questions, byId = new Map(questions.map(q => [q.id,q]));
  const core = globalThis.QuizCore, KEY = 'wrong-quiz-infosec-v1';
  const $ = id => document.getElementById(id);
  let state = null, screen = 'home';
  function notice(message) { $('storage-notice').textContent = message; $('storage-notice').hidden = false; }
  function save() {
    try { localStorage.setItem(KEY,core.serialize(state)); }
    catch { notice('目前無法儲存進度。你仍可完成這一輪，但關閉或重新整理後可能需要重做。'); }
  }
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      state = core.restore(raw,questions,data.fingerprint);
      if (!state) notice('舊進度與目前題庫不相容或已損壞，請開始新一輪。');
    }
  } catch { notice('目前無法讀取進度。你仍可作答，但關閉後可能無法繼續上次。'); }
  function show(name, focusId) {
    screen = name;
    for (const id of ['home','quiz','results']) $(id).hidden = id !== name;
    if (focusId) { $(focusId).focus({preventScroll:true}); window.scrollTo(0,0); }
  }
  function source(q) { return `題庫 ${q.bank}・第 ${q.page} 頁・第 ${q.number} 題`; }
  function selectedBanks() { return [...document.querySelectorAll('input[name="bank"]:checked')].map(input => input.value); }
  function updateSelected() {
    const banks = selectedBanks(), count = questions.filter(q => banks.includes(q.bank)).length;
    $('start-selected').textContent = count ? `只做已選題庫（${count} 題）` : '請至少選擇一個題庫';
    $('start-selected').disabled = count === 0;
  }
  function home(focus = true) {
    $('resume-area').hidden = !state;
    if (state) {
      const s = core.score(state,byId);
      $('resume-summary').textContent = state.mode === 'results' ? `上次已完成 ${s.total} 題，可繼續查看結果。` : `上次停在第 ${state.index+1}／${s.total} 題，已作答 ${s.answered} 題。`;
    }
    show('home',focus ? 'home-title' : null);
  }
  function start(banks, ids = null, randomOrder = document.querySelector('input[name="order"]:checked').value === 'random') {
    state = core.create(questions,data.fingerprint,banks,randomOrder,ids);
    save(); renderQuestion();
  }
  function addText(parent, tag, text, className = '') {
    const node = document.createElement(tag); node.textContent = text;
    if (className) node.className = className;
    parent.appendChild(node); return node;
  }
  function renderQuestion(focus = true) {
    const q = byId.get(state.order[state.index]), chosen = state.responses[q.id];
    const answered = Object.hasOwn(state.responses,q.id), s = core.score(state,byId);
    $('progress-text').textContent = `第 ${state.index+1}／${s.total} 題`;
    $('correct-count').textContent = `目前答對 ${s.correct} 題・已作答 ${s.answered} 題`;
    $('progress-bar').max = s.total; $('progress-bar').value = s.answered;
    $('question-source').textContent = source(q);
    $('question-context').hidden = !q.group_context;
    $('context-text').textContent = q.group_context || '';
    $('question-title').textContent = q.stem;
    $('options').replaceChildren();
    for (const [letter,text] of Object.entries(q.options)) {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'option';
      button.dataset.letter = letter;
      addText(button,'span',letter,'letter');
      const copy = addText(button,'span',text,'option-copy');
      if (answered) {
        button.disabled = true;
        if (core.grade(q,letter)) {
          button.classList.add('correct');
          addText(copy,'span',letter === chosen ? '✓ 正確答案・你選的答案' : '✓ 正確答案','badge');
        } else if (letter === chosen) {
          button.classList.add('incorrect'); addText(copy,'span','✕ 你選的答案','badge');
        }
      }
      button.addEventListener('click',() => choose(letter)); $('options').appendChild(button);
    }
    // Remove old answer content entirely before rendering a new unanswered question.
    $('feedback').replaceChildren(); $('feedback').hidden = !answered;
    if (answered) {
      const correct = core.grade(q,chosen);
      addText($('feedback'),'p',correct ? '答對了！' : `這題再記一次，正確答案是 ${q.answers[0]}。`,`outcome ${correct ? 'good':'bad'}`);
      addText($('feedback'),'h3','解析');
      addText($('feedback'),'p',q.explanation || '此題未提供解析。','explanation');
      const last = Array.isArray(q.chosen_last) ? q.chosen_last.join('、') : q.chosen_last;
      addText($('feedback'),'p',`上次你選的是 ${last || '（未記錄）'}`,'muted');
    }
    $('previous').disabled = state.index === 0;
    $('next').hidden = !answered;
    $('next').textContent = state.index === state.order.length - 1 ? '查看結果' : '下一題';
    $('back-results').hidden = s.answered !== s.total;
    show('quiz',focus ? 'question-title' : null);
  }
  function choose(letter) {
    if (screen !== 'quiz') return;
    const next = core.answer(state,byId,letter);
    if (next === state) return;
    state = next; save(); renderQuestion(false); $('next').focus({preventScroll:true});
  }
  function results() {
    const s = core.score(state,byId);
    if (s.answered !== s.total) return;
    state = {...state,mode:'results'}; save();
    $('result-rate').textContent = `${Math.round(100*s.correct/s.total)}%`;
    $('result-summary').textContent = `${s.total} 題中，答對 ${s.correct} 題、答錯 ${s.wrongIds.length} 題。`;
    $('bank-results').replaceChildren();
    for (const [bank,stats] of Object.entries(s.banks)) {
      addText($('bank-results'),'p',`題庫 ${bank}：答對 ${stats.correct}／答錯 ${stats.wrong} 題${stats.total ? '' : '（本輪未作答）'}`,'bank-stat');
    }
    $('retry-wrong').hidden = !s.wrongIds.length;
    $('wrong-hint').textContent = s.wrongIds.length ? '點選題目，回看你的答案與解析。' : '全部答對！這次沒有需要重做的題目。';
    $('wrong-list').replaceChildren();
    for (const id of s.wrongIds) {
      const q = byId.get(id), button = document.createElement('button'); button.className = 'wrong-item';
      addText(button,'span',source(q),'source'); addText(button,'span',q.stem);
      button.addEventListener('click',() => { state = {...state,index:state.order.indexOf(id),mode:'quiz'}; save(); renderQuestion(); });
      $('wrong-list').appendChild(button);
    }
    show('results','results-title');
  }
  $('total-count').textContent = questions.length;
  $('bank-counts').textContent = ['A','B','C'].map(bank => `題庫 ${bank}：${questions.filter(q => q.bank === bank).length} 題`).join('　');
  document.querySelectorAll('input[name="bank"]').forEach(input => input.addEventListener('change',updateSelected));
  $('start-all').addEventListener('click',() => start(['A','B','C']));
  $('start-selected').addEventListener('click',() => start(selectedBanks()));
  $('resume').addEventListener('click',() => { if (state) state.mode === 'results' ? results() : renderQuestion(); });
  $('clear-progress').addEventListener('click',() => {
    if (!window.confirm('清除目前儲存的作答進度？題庫不會被刪除。')) return;
    try { localStorage.removeItem(KEY); state = null; home(); }
    catch { notice('目前無法清除儲存的進度。請允許瀏覽器使用本機儲存後再試。'); }
  });
  $('go-home').addEventListener('click',() => home());
  $('results-home').addEventListener('click',() => home());
  $('previous').addEventListener('click',() => { state = core.move(state,-1); save(); renderQuestion(); });
  $('next').addEventListener('click',() => {
    if (!Object.hasOwn(state.responses,state.order[state.index])) return;
    if (state.index === state.order.length-1) results();
    else { state = core.move(state,1); save(); renderQuestion(); }
  });
  $('back-results').addEventListener('click',results);
  $('retry-wrong').addEventListener('click',() => {
    const ids = core.score(state,byId).wrongIds;
    if (ids.length) start(['A','B','C'],ids,state.randomOrder);
  });
  document.addEventListener('keydown',event => {
    if (screen !== 'quiz' || event.repeat || event.altKey || event.ctrlKey || event.metaKey || event.isComposing || /INPUT|TEXTAREA|SELECT/.test(event.target.tagName)) return;
    if (/^[1-4]$/.test(event.key)) { event.preventDefault(); choose('ABCD'[Number(event.key)-1]); }
  });
  updateSelected(); home(false);
})();
</script>
</body>
</html>
'''


def main():
    source = json.loads((ROOT / "wrong_final.json").read_text(encoding="utf-8"))
    questions = make_questions(source)
    canonical = json.dumps(questions, ensure_ascii=False, sort_keys=True)
    fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    data = json.dumps({"fingerprint": fingerprint, "questions": questions}, ensure_ascii=False, separators=(",", ":"))
    data = data.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    html = TEMPLATE.replace("__QUIZ_DATA__", data)
    OUTPUT.write_text(html, encoding="utf-8")
    size = OUTPUT.stat().st_size
    if size >= 2_000_000:
        raise ValueError("HTML exceeds 2 MB")
    print(f"Built {OUTPUT.name}: {len(questions)} single-choice questions; {len(source)-len(questions)} excluded; {size:,} bytes")


if __name__ == "__main__":
    main()
