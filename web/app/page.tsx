"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Chart from "@/components/Chart";
import ResultTable from "@/components/ResultTable";
import { ask, examples as loadExamples, type Reply } from "@/lib/api";

type Turn = { id: number; question: string; reply: Reply | null };

const FALLBACK_EXAMPLES = [
  "Revenue by region last quarter",
  "Monthly revenue in 2026",
  "Top 5 products by revenue this year",
  "What share of 2026 revenue came from each channel?",
];
const REPO = "https://github.com/nc711-coder/tally";

export default function Home() {
  const [examples, setExamples] = useState<string[]>(FALLBACK_EXAMPLES);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadExamples().then((e) => e.length && setExamples(e));   // also wakes the server up
  }, []);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns]);

  async function submit(question: string) {
    question = question.trim();
    if (!question || busy) return;
    const history = turns
      .filter((t) => t.reply?.status === "answered" && t.reply.sql)
      .slice(-2)
      .map((t) => ({ question: t.question, sql: t.reply!.sql! }));
    const id = Date.now();
    setTurns((ts) => [...ts, { id, question, reply: null }]);
    setText("");
    setBusy(true);
    const reply = await ask(question, history);
    setTurns((ts) => ts.map((t) => (t.id === id ? { ...t, reply } : t)));
    setBusy(false);
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    submit(text);
  }

  return (
    <main className="page">
      <header className="masthead">
        <div className="brand">
          <span className="logo" aria-hidden="true">▤</span>
          <span className="wordmark">Tally</span>
        </div>
        <h1>Ask your data a question.</h1>
        <p className="lede">
          Plain-English questions about <strong>Fernwood Coffee Roasters</strong>, a fictional company with two
          years of sales, customers and subscriptions. You get the answer, a chart, and the exact SQL behind it.
        </p>
      </header>

      <section className="thread" aria-live="polite">
        {turns.length === 0 && (
          <div className="examples">
            <p className="examples-title">Try one of these</p>
            <div className="chips">
              {examples.map((e) => (
                <button key={e} className="chip" onClick={() => submit(e)} disabled={busy}>{e}</button>
              ))}
            </div>
          </div>
        )}

        {turns.map((t) => (
          <article key={t.id} className="turn">
            <p className="question">{t.question}</p>
            {!t.reply ? (
              <div className="card thinking"><span className="dot" /><span className="dot" /><span className="dot" /> Writing and checking the query…</div>
            ) : (
              <Answer reply={t.reply} onFollow={submit} busy={busy} />
            )}
          </article>
        ))}
        <div ref={endRef} />
      </section>

      <form className="ask" onSubmit={onSubmit}>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="e.g. Which region grew fastest this year?"
          maxLength={500}
          aria-label="Your question"
        />
        <button type="submit" disabled={busy || !text.trim()}>{busy ? "Thinking…" : "Ask"}</button>
      </form>

      <footer className="foot">
        <p>
          <strong>Read-only by design.</strong> The AI writes the query; code checks it before it runs (SELECT only,
          Fernwood&apos;s tables only, 5-second limit), and every number in the answer is checked against the result.
        </p>
        <p><a href={REPO}>Source code on GitHub</a> · Fictional data, no real customers.</p>
      </footer>
    </main>
  );
}

function Answer({ reply, onFollow, busy }: { reply: Reply; onFollow: (q: string) => void; busy: boolean }) {
  if (reply.status !== "answered") {
    const tone = reply.status === "clarify" ? "ask-back" : reply.status === "refused" ? "refused" : "failed";
    const title = { "ask-back": "Quick question first", refused: "Not something I can do", failed: "Something went wrong" }[tone];
    return (
      <div className={`card ${tone}`}>
        <p className="card-title">{title}</p>
        <p>{reply.message}</p>
      </div>
    );
  }
  const columns = reply.columns ?? [];
  const rows = reply.rows ?? [];
  const spec = reply.chart;
  const showTable = !spec || spec.type === "table";
  return (
    <div className="card">
      <p className="answer">{reply.answer}</p>
      {spec && <Chart spec={spec} columns={columns} rows={rows} />}
      {showTable && rows.length > 0 && <ResultTable columns={columns} rows={rows} spec={spec} truncated={reply.truncated} />}
      <div className="details">
        {!showTable && spec?.type !== "number" && rows.length > 0 && (
          <details>
            <summary>Show data ({rows.length} row{rows.length === 1 ? "" : "s"})</summary>
            <ResultTable columns={columns} rows={rows} spec={spec} truncated={reply.truncated} />
          </details>
        )}
        {reply.sql && (
          <details>
            <summary>Show query</summary>
            <pre><code>{reply.sql}</code></pre>
          </details>
        )}
      </div>
      {!!reply.follow_ups?.length && (
        <div className="chips follow">
          {reply.follow_ups.map((f) => (
            <button key={f} className="chip small" onClick={() => onFollow(f)} disabled={busy}>{f}</button>
          ))}
        </div>
      )}
      <p className="meta">
        Read-only query · {rows.length} row{rows.length === 1 ? "" : "s"}
        {reply.seconds?.total ? ` · ${reply.seconds.total.toFixed(1)}s` : ""}
      </p>
    </div>
  );
}
