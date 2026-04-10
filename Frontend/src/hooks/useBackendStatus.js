import { useEffect, useState } from "react";
import { checkBackendStatus } from "../api/backendStatus";

export function useBackendStatus(pollInterval = 5000) {
  const [backendUp, setBackendUp] = useState(false);

  useEffect(() => {
    let cancelled = false;


    async function poll() {
    try {
        const isUp = await checkBackendStatus();
        console.log("✅ Backend status:", isUp);
        if (!cancelled) setBackendUp(isUp);
    } catch (e) {
        console.error("❌ Backend check failed", e);
        if (!cancelled) setBackendUp(false);
    }
    }


    poll(); // initial check
    const id = setInterval(poll, pollInterval);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [pollInterval]);

  return backendUp;
}