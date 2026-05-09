"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, ChevronDown, Send, Sparkles, X } from "lucide-react";
import { sendChatMessage, type ChatSource } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────────

type Role = "user" | "assistant" | "error";

interface Message {
  id: string;
  role: Role;
  content: string;
  sources?: ChatSource[];
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatAmount(amount: number) {
  const abs = Math.abs(amount);
  const sign = amount < 0 ? "-" : "+";
  return `${sign}₹${abs.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

const SUGGESTIONS = [
  "What is my total spending?",
  "Which category did I spend the most on?",
  "Show my largest transactions",
  "How much did I spend on food?",
];

// ── Sub-components ─────────────────────────────────────────────────────────────

function SourceTag({ source }: { source: ChatSource }) {
  const isDebit = source.amount < 0;
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium"
      style={{
        borderColor: isDebit
          ? "rgba(251,113,133,0.25)"
          : "rgba(52,211,153,0.25)",
        background: isDebit
          ? "rgba(251,113,133,0.08)"
          : "rgba(52,211,153,0.08)",
        color: isDebit ? "#fb7185" : "#34d399",
      }}
    >
      {source.category} · {formatAmount(source.amount)}
    </span>
  );
}

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";
  const isError = msg.role === "error";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      {!isUser && (
        <div
          className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-xl"
          style={{
            background:
              "linear-gradient(135deg,rgba(56,189,248,0.9),rgba(129,140,248,0.8))",
          }}
        >
          <Bot className="h-3.5 w-3.5 text-slate-950" />
        </div>
      )}

      <div className={`flex max-w-[80%] flex-col gap-2 ${isUser ? "items-end" : "items-start"}`}>
        {/* Bubble */}
        <div
          className="rounded-2xl px-4 py-3 text-sm leading-relaxed"
          style={
            isUser
              ? {
                  background:
                    "linear-gradient(135deg,rgba(56,189,248,0.22),rgba(129,140,248,0.18))",
                  border: "1px solid rgba(56,189,248,0.2)",
                  color: "#f4f7fb",
                  borderRadius: "1rem 1rem 0.25rem 1rem",
                }
              : isError
                ? {
                    background: "rgba(251,113,133,0.1)",
                    border: "1px solid rgba(251,113,133,0.2)",
                    color: "#fb7185",
                    borderRadius: "1rem 1rem 1rem 0.25rem",
                  }
                : {
                    background: "rgba(255,255,255,0.05)",
                    border: "1px solid rgba(255,255,255,0.08)",
                    color: "#f4f7fb",
                    borderRadius: "1rem 1rem 1rem 0.25rem",
                  }
          }
        >
          {msg.content}
        </div>

        {/* Sources */}
        {msg.sources && msg.sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 px-1">
            {msg.sources.slice(0, 6).map((s) => (
              <SourceTag key={s.id} source={s} />
            ))}
            {msg.sources.length > 6 && (
              <span className="text-[11px] text-[var(--color-mist)]">
                +{msg.sources.length - 6} more
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-3">
      <div
        className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-xl"
        style={{
          background:
            "linear-gradient(135deg,rgba(56,189,248,0.9),rgba(129,140,248,0.8))",
        }}
      >
        <Bot className="h-3.5 w-3.5 text-slate-950" />
      </div>
      <div
        className="flex items-center gap-1.5 rounded-2xl px-4 py-3"
        style={{
          background: "rgba(255,255,255,0.05)",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: "1rem 1rem 1rem 0.25rem",
        }}
      >
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-1.5 w-1.5 rounded-full bg-[var(--color-mist)]"
            style={{
              animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
            }}
          />
        ))}
      </div>
    </div>
  );
}

// ── Main Panel ─────────────────────────────────────────────────────────────────

export function ChatPanel() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Focus input when panel opens
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [open]);

  async function handleSend(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || loading) return;

    setInput("");
    setMessages((prev) => [
      ...prev,
      { id: uid(), role: "user", content: msg },
    ]);
    setLoading(true);

    try {
      const res = await sendChatMessage(msg);
      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: "assistant",
          content: res.answer,
          sources: res.sources,
        },
      ]);
    } catch (e: unknown) {
      const errMsg =
        e instanceof Error ? e.message : "Something went wrong. Try again.";
      setMessages((prev) => [
        ...prev,
        { id: uid(), role: "error", content: errMsg },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {/* Bounce animation keyframes */}
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
          40% { transform: translateY(-5px); opacity: 1; }
        }
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(16px) scale(0.97); }
          to   { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
      `}</style>

      {/* FAB Trigger */}
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label="Open AI chat"
        className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full shadow-2xl transition-all duration-200 hover:scale-105 active:scale-95"
        style={{
          background:
            "linear-gradient(135deg,rgba(56,189,248,0.95),rgba(129,140,248,0.85))",
          boxShadow:
            "0 0 0 1px rgba(56,189,248,0.3), 0 8px 32px rgba(56,189,248,0.35)",
        }}
      >
        {open ? (
          <ChevronDown className="h-6 w-6 text-slate-950" />
        ) : (
          <Sparkles className="h-6 w-6 text-slate-950" />
        )}
      </button>

      {/* Panel */}
      {open && (
        <div
          className="fixed bottom-24 right-6 z-50 flex w-[400px] max-w-[calc(100vw-3rem)] flex-col overflow-hidden rounded-3xl"
          style={{
            height: "580px",
            background: "rgba(9,13,22,0.96)",
            border: "1px solid rgba(255,255,255,0.1)",
            backdropFilter: "blur(24px)",
            boxShadow:
              "0 0 0 1px rgba(56,189,248,0.12), 0 24px 64px rgba(0,0,0,0.7)",
            animation: "slideUp 0.22s ease-out",
          }}
        >
          {/* Header */}
          <div
            className="flex items-center gap-3 px-5 py-4"
            style={{
              borderBottom: "1px solid rgba(255,255,255,0.07)",
              background:
                "linear-gradient(135deg,rgba(56,189,248,0.08),rgba(129,140,248,0.06),transparent)",
            }}
          >
            <div
              className="flex h-9 w-9 items-center justify-center rounded-xl"
              style={{
                background:
                  "linear-gradient(135deg,rgba(56,189,248,0.9),rgba(129,140,248,0.8))",
              }}
            >
              <Sparkles className="h-4 w-4 text-slate-950" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-white">
                Finance Assistant
              </p>
              <p className="text-[11px] text-[var(--color-mist)]">
                Ask anything about your transactions
              </p>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-[var(--color-mist)] transition-colors hover:bg-white/8 hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-4 py-4">
            {messages.length === 0 && !loading && (
              <div
                className="flex flex-col items-center gap-4 py-6 text-center"
                style={{ animation: "fadeIn 0.3s ease-out" }}
              >
                <div
                  className="flex h-14 w-14 items-center justify-center rounded-2xl"
                  style={{
                    background:
                      "linear-gradient(135deg,rgba(56,189,248,0.15),rgba(129,140,248,0.1))",
                    border: "1px solid rgba(56,189,248,0.2)",
                  }}
                >
                  <Bot className="h-6 w-6 text-[var(--color-cyan)]" />
                </div>
                <div>
                  <p className="text-sm font-medium text-white">
                    Ask me about your finances
                  </p>
                  <p className="mt-1 text-xs text-[var(--color-mist)]">
                    I can search across all your uploaded statements
                  </p>
                </div>
                <div className="flex w-full flex-col gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => handleSend(s)}
                      className="rounded-xl border px-3 py-2.5 text-left text-xs text-[var(--color-mist-strong)] transition-all duration-150 hover:border-[rgba(56,189,248,0.3)] hover:bg-[rgba(56,189,248,0.06)] hover:text-white"
                      style={{ borderColor: "rgba(255,255,255,0.08)" }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}

            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div
            className="px-4 py-4"
            style={{ borderTop: "1px solid rgba(255,255,255,0.07)" }}
          >
            <div
              className="flex items-center gap-2 rounded-2xl px-4 py-2.5"
              style={{
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.1)",
                transition: "border-color 0.15s",
              }}
              onFocus={() => {}}
            >
              <input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="Ask about your transactions…"
                disabled={loading}
                className="flex-1 bg-transparent text-sm text-white placeholder:text-[var(--color-mist)] focus:outline-none disabled:opacity-50"
              />
              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || loading}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl transition-all duration-150 disabled:opacity-30"
                style={{
                  background: input.trim()
                    ? "linear-gradient(135deg,rgba(56,189,248,0.9),rgba(129,140,248,0.8))"
                    : "rgba(255,255,255,0.08)",
                }}
              >
                <Send className="h-3.5 w-3.5 text-slate-950" />
              </button>
            </div>
            <p className="mt-2 text-center text-[10px] text-[var(--color-mist)]">
              Answers grounded in your transaction data via RAG
            </p>
          </div>
        </div>
      )}
    </>
  );
}
