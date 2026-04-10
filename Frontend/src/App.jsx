import { useMemo, useState } from "react";
import LeftPane from "./components/LeftPane";
import RightPane from "./components/RightPane";
import { sendChat } from "./api/chatApi";
import TokenSidebar from "./components/TokenSidebar";

const LANGS = [
  { id: "groovy", label: "Groovy (Fusion)", monaco: "java" },
  { id: "fast_formula", label: "Fast Formula (HCM)", monaco: "plaintext" },
  { id: "jde_bsf", label: "JDE Business Function", monaco: "c" },
];

export default function App() {
  const [language, setLanguage] = useState("groovy");
  const [prompt, setPrompt] = useState("");
  const [explanation, setExplanation] = useState("");
  const [code, setCode] = useState("// Start here...\n");
  const [output, setOutput] = useState("Console ready.\n");
  const [busy, setBusy] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [primaryToken, setPrimaryToken] = useState("");
  const [fallbackToken, setFallbackToken] = useState("");



  const activeLang = useMemo(
    () => LANGS.find((l) => l.id === language) ?? LANGS[0],
    [language]
  );

  const API_BASE = import.meta.env?.VITE_API_BASE || "http://localhost:8000";
  const log = (msg) => setOutput((prev) => prev + msg + "\n");

  async function handleGenerate() {
    setBusy(true);
    log("[generate] sending prompt to /chat...");

    try {
      const payload = {
        type: language,                       // "groovy" | "fast_formula" | "jde_bsf"
        query: prompt,                        // from RightPane
        current_code: code?.trim() ? code : ""// from LeftPane editor
      };

      const data = await sendChat(payload);

      // FastAPI returns: { status, code, explanation, model, response_time, backend_time }
      if (data?.code !== undefined) setCode(data.code);
      setExplanation(data?.explanation ?? "");

      log(`[generate] done. model=${data?.model ?? "unknown"} time=${data?.response_time ?? "?"}s`);
    } catch (e) {
      log(`[generate] ERROR: ${e.message}`);
    } finally {
      setBusy(false);
    }
  }

  async function saveTokens() {
    try {
      if (primaryToken.trim()) {
        await fetch(`${API_BASE}/token1`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: primaryToken }),
        });
      }

      if (fallbackToken.trim()) {
        await fetch(`${API_BASE}/token2`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: fallbackToken }),
        });
      }

      log("[auth] tokens saved successfully");
      setIsSidebarOpen(false);
    } catch (e) {
      log(`[auth] ERROR saving tokens: ${e.message}`);
    }
  }


  return (
    <div className="h-screen bg-zinc-950 text-slate-100 p-2">
      <div className="h-full grid grid-cols-[1fr_360px] gap-2 min-h-0">
        <LeftPane
          code={code}
          setCode={setCode}
          output={output}
          clearOutput={() => setOutput("Console cleared.\n")}
          activeLang={activeLang}
          busy={busy}
          onGenerate={handleGenerate}
          onCopySuccess={() => log("code copied successfully")}
          onToggleSidebar={() => setIsSidebarOpen(true)}
        />

        <RightPane
          langs={LANGS}
          language={language}
          setLanguage={setLanguage}
          prompt={prompt}
          setPrompt={setPrompt}
          explanation={explanation}
          busy={busy}
        />
      </div>
      {isSidebarOpen && (
        <TokenSidebar
          primaryToken={primaryToken}
          fallbackToken={fallbackToken}
          setPrimaryToken={setPrimaryToken}
          setFallbackToken={setFallbackToken}
          onSave={saveTokens}
          onClose={() => setIsSidebarOpen(false)}
        />
      )}
    </div>

    
  );
}

