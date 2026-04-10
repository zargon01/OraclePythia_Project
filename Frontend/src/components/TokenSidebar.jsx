import { useState } from "react";

export default function TokenSidebar({
  primaryToken,
  fallbackToken,
  setPrimaryToken,
  setFallbackToken,
  onSave,
  onClose,
}) {
  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />

      {/* Sidebar */}
      <div className="
        fixed top-0 left-0 h-full w-80
        bg-zinc-900 border-r border-zinc-800
        z-50 flex flex-col animate-slide-in
      ">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
          <span className="font-semibold text-sm">Configuration</span>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-white"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4 flex-1">
          {/* Primary Token */}
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">
              Primary Bearer Token
            </label>
            <textarea
              value={primaryToken}
              onChange={(e) => setPrimaryToken(e.target.value)}
              placeholder="Paste primary token..."
              className="
                w-full h-24 resize-none rounded-md
                bg-zinc-950 border border-zinc-800
                px-3 py-2 text-sm text-white
                placeholder:text-zinc-500
                focus:outline-none focus:ring-2 focus:ring-[#FF5E4F]
              "
            />
          </div>

          {/* Fallback Token */}
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">
              Fallback Bearer Token
            </label>
            <textarea
              value={fallbackToken}
              onChange={(e) => setFallbackToken(e.target.value)}
              placeholder="Paste fallback token..."
              className="
                w-full h-24 resize-none rounded-md
                bg-zinc-950 border border-zinc-800
                px-3 py-2 text-sm text-white
                placeholder:text-zinc-500
                focus:outline-none focus:ring-2 focus:ring-[#FF5E4F]
              "
            />
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-zinc-800">
          <button
            onClick={onSave}
            className="
              w-full py-2 rounded-md
              bg-[#FF5E4F] text-white font-semibold
              hover:opacity-90
            "
          >
            Save Tokens
          </button>
        </div>
      </div>
    </>
  );
}