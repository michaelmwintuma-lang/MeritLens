// Load something when a page opens (and again when `deps` change), with its error and a way to try again.
//   const { data, error, reload } = useLoad(() => api("/promotion/decisions"), []);
// A newer load always wins: an answer that arrives after a newer request was made is ignored.
import { useCallback, useEffect, useRef, useState } from "react";

export function useLoad(loader, deps) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const latest = useRef(0);

  const reload = useCallback(() => {
    const ticket = ++latest.current;
    setError("");
    return Promise.resolve()
      .then(loader)
      .then((result) => { if (ticket === latest.current) setData(result); })
      .catch((err) => { if (ticket === latest.current) setError(err.message || "Something went wrong."); });
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { reload(); }, [reload]);
  return { data, error, reload, setData };
}
