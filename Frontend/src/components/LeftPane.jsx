import Editor from "@monaco-editor/react";

export default function LeftPane({
  code,
  setCode,
  output,
  clearOutput,
  activeLang,
  busy,
  onGenerate,
  onCopySuccess,
  onToggleSidebar
}) {
  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(code ?? "");
      onCopySuccess?.();   // ✅ notify parent
    } catch {
      try {
        const ta = document.createElement("textarea");
        ta.value = code ?? "";
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        onCopySuccess?.(); // ✅ fallback success
      } catch (err) {
        console.error("Copy failed", err);
      }
    }
  }

  return (
    <div className="min-h-0 grid grid-rows-[1fr_220px] gap-2">
      <div className="min-h-0 rounded-xl border border-zinc-800 bg-zinc-950 overflow-hidden flex flex-col">
        <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800">
          {/* <div className="flex items-center gap-3">
            <img src="/LTM-Logo.svg" alt="LTM Logo" className="h-6 w-auto" />
            <span className="text-sm font-semibold tracking-wide">
              Oracle Code Assistant
            </span>
          </div> */}
          <div className="flex items-center gap-3">
            {/* Hamburger */}
            <button
              onClick={onToggleSidebar}
              className="
                p-1.5 rounded-md
                hover:bg-zinc-800
                text-zinc-300
                hover:text-white
              "
              title="Open settings"
            >
              ☰
            </button>

            <img
              src="/LTM-Logo.svg"
              alt="LTM Logo"
              className="h-6 w-auto"
            />

            <span className="text-sm font-semibold tracking-wide">
              Oracle Code Assistant
            </span>
          </div>

          <div className="flex gap-2">
            {/* ✅ Copy Code */}
            <button
              onClick={handleCopy}
              disabled={busy || !code.trim()}
              className="
                px-3 py-1.5 rounded-md
                border border-zinc-700
                bg-zinc-800
                hover:bg-zinc-700
                disabled:opacity-50
              "
            >
              Copy Code
            </button>

            <button
              onClick={onGenerate}
              disabled={busy}
              className="
                px-3 py-1.5 rounded-md
                bg-[#FF5E4F]
                text-white
                font-semibold
                hover:opacity-90
                disabled:opacity-50
              "
            >
              Generate
            </button>
          </div>
        </div>

        <div className="flex-1 min-h-0">
          <Editor
            height="100%"
            theme="vs-dark"
            language={activeLang.monaco}
            value={code}
            onChange={(v) => setCode(v ?? "")}
            options={{
              minimap: { enabled: false },
              fontSize: 13,
              wordWrap: "on",
              automaticLayout: true,
            }}
          />
        </div>
      </div>

      {/* Console */}
      <div className="min-h-0 rounded-xl border border-zinc-800 bg-zinc-950 overflow-hidden flex flex-col">
        <div className="flex items-center justify-between px-3 py-2 border-b border-slate-800">
          <div className="font-semibold">Console</div>
          <button
            onClick={clearOutput}
            className="px-3 py-1.5 rounded-md border border-zinc-700 bg-zinc-800 hover:bg-[#FF5E4F]"
          >
            Clear
          </button>
        </div>

        <div className="p-3 flex-1 min-h-0 overflow-auto bg-zinc-900">
          <pre className="whitespace-pre-wrap text-xs leading-5 text-sky-200">
            {output}
          </pre>
        </div>
      </div>
    </div>
  );
}