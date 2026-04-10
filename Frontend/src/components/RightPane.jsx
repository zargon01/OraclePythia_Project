import { useBackendStatus } from "../hooks/useBackendStatus";

export default function RightPane({
  langs,
  language,
  setLanguage,
  prompt,
  setPrompt,
  explanation,
  busy,
}) {

  const backendUp = useBackendStatus();

  return (
    <aside className="min-h-0 rounded-xl border border-zinc-800 bg-zinc-900 overflow-hidden flex flex-col">
      {/* Sidebar Header */}
      <div className="px-4 py-2 border-b border-zinc-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
                <span className="text-sm font-semibold">Agent Chat</span>

                {/* Status dot */}
                
                <span
                  title={backendUp ? "Backend running" : "Backend down"}
                  className={`h-2 w-2 rounded-full ${
                    backendUp ? "bg-green-500" : "bg-red-500"
                  }`}
                />

            </div>
        </div>

      {/* Content: use separators instead of nested cards */}
      <div className="flex-1 min-h-0 flex flex-col divide-y divide-zinc-800">
        {/* 1) Language (compact) */}
        <div className="px-3 py-2">
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            disabled={busy}
            className="
              w-full
              rounded-md
              bg-zinc-950
              px-3 py-2
              text-sm
              text-slate-100
              border border-zinc-800
              focus:outline-none
              focus:ring-2 focus:ring-[#FF5E4F]
            "
          >
            {langs.map((l) => (
              <option key={l.id} value={l.id}>
                {l.label}
              </option>
            ))}
          </select>
        </div>

        {/* 2) Prompt (no label, no inner card) */}
        <div className="px-3 py-2">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={busy}
            placeholder="Write instruction / prompt here..."
            className="
              w-full
              h-28
              resize-none
              rounded-md
              bg-zinc-950
              px-3 py-2
              text-sm
              text-slate-100
              border border-zinc-800
              placeholder:text-slate-500
              focus:outline-none
              focus:ring-2 focus:ring-[#FF5E4F]
            "
          />
        </div>

        {/* 3) Explanation (fills remaining height) */}
        <div className="px-3 py-2 flex-1 min-h-0 flex flex-col">
          <div className="text-xs text-slate-400 mb-2">Explanation</div>

          <div className="flex-1 min-h-0 overflow-auto rounded-md border border-zinc-800 bg-zinc-950 p-3">
            <pre className="whitespace-pre-wrap text-sm text-slate-100">
              {explanation?.trim()
                ? explanation
                : "AI explanation output will appear here..."}
            </pre>
          </div>
        </div>
      </div>
    </aside>
  );
}