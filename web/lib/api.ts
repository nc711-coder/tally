export type ChartSpec = {
  type: "number" | "line" | "bar" | "table";
  x: string | null;
  y: string[];
  formats: Record<string, "money" | "percent" | "number" | "text">;
  horizontal: boolean;
};

export type Reply = {
  status: "answered" | "clarify" | "refused" | "failed" | "limited";
  message: string;
  answer?: string;
  follow_ups?: string[];
  sql?: string;
  columns?: string[];
  rows?: (string | number | null)[][];
  truncated?: boolean;
  chart?: ChartSpec | null;
  seconds?: Record<string, number>;
  checks?: { answer_rewrites: number; answer_fallback: boolean; queries_blocked: number };
};

export const API = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export async function ask(question: string, history: { question: string; sql: string }[]): Promise<Reply> {
  try {
    const r = await fetch(`${API}/api/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, history }),
    });
    const data = await r.json().catch(() => null);
    if (data && data.status) return data as Reply;
    return { status: "failed", message: `The server answered with an error (${r.status}). Please try again.` };
  } catch {
    return {
      status: "failed",
      message: "Couldn't reach Tally's server. It may be waking up; try again in a few seconds.",
    };
  }
}

export async function examples(): Promise<string[]> {
  try {
    const r = await fetch(`${API}/api/examples`);
    return (await r.json()).examples ?? [];
  } catch {
    return [];
  }
}
