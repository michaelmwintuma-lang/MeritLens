// Nominations. Managers see the ones they made; HR sees all of them and opens a waiting one to decide.
import { useEffect, useState } from "react";
import { ClipboardCheck } from "lucide-react";
import { api } from "../../api";
import { useAuth } from "../../auth";
import { PageHeader } from "../../components/ui";
import NominationsTable from "../../components/promotion/NominationsTable";

export default function Nominations() {
  const { user } = useAuth();
  const isHr = user.role === "hr";
  const [list, setList] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api("/promotion/nominations").then(setList).catch((err) => setError(err.message)); }, []);

  return (
    <>
      <PageHeader icon={ClipboardCheck} title={isHr ? "Nominations" : "My nominations"}
        subtitle={isHr
          ? "Managers' nominations. Review one to see the model's view and make the final decision."
          : "People you have nominated, and HR's decisions. To nominate someone, open them from My team."} />
      {error && <p className="alert alert-error">{error}</p>}
      {!list && !error && <p className="muted">Loading…</p>}
      {list && <NominationsTable nominations={list} isHr={isHr} title="Applications for promotion"
        subtitle={isHr ? "Waiting ones need your decision." : "HR decides; the model only advises."} />}
    </>
  );
}
