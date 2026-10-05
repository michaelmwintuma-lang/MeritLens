// Photos and videos as evidence for a report: choosing them (with previews and a privacy reminder), uploading them
// with progress, and showing the ones already added. Hidden details (location, phone, time) are removed by the
// server before anything is saved; what can be seen or heard is up to the reporter, so they're reminded to check.
import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Film, ImagePlus, Loader2, Paperclip, ShieldCheck, Trash2, TriangleAlert, Volume2, VolumeX } from "lucide-react";
import { apiBlob, uploadFile } from "../../api";

export const MAX_FILES = 6;
const PHOTO_TYPES = ["image/jpeg", "image/png", "image/webp"];
const VIDEO_TYPES = ["video/mp4", "video/quicktime", "video/webm"];
const MB = 1024 * 1024;
const LIMITS = { photo: 15 * MB, video: 100 * MB };

export function sizeText(bytes) {
  return bytes >= MB ? `${(bytes / MB).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

/** What is and isn't removed from a photo or video, shown wherever evidence is added. */
export function EvidencePrivacy() {
  return (
    <div className="evidence-privacy">
      <p><ShieldCheck size={16} aria-hidden="true" /> <span><strong>Removed automatically:</strong> where a photo or video was taken, the
        phone or camera, its owner's name, the time it was taken, and the file name.</span></p>
      <p><TriangleAlert size={16} aria-hidden="true" /> <span><strong>Not removed, so please check:</strong> faces (yours too, in
        reflections), your desk or the view from where you sit, screens showing your name, and your voice in videos.</span></p>
    </div>
  );
}

/** Choose photos and videos before sending. `files` is [{ id, file, kind, url, keepSound }]. */
export function EvidencePicker({ files, setFiles, already = 0 }) {
  const input = useRef(null);
  const [problems, setProblems] = useState([]);
  const room = MAX_FILES - already - files.length;

  // Previews stay available after this step (the upload list shows them too); each is freed when its file is removed,
  // and the rest when the tab closes

  function add(list) {
    const found = [];
    const added = [];
    for (const file of list) {
      const kind = PHOTO_TYPES.includes(file.type) ? "photo" : VIDEO_TYPES.includes(file.type) ? "video" : null;
      if (!kind) found.push(`${file.name}: only photos (JPEG, PNG, WebP) and videos (MP4, MOV, WebM) can be added.`);
      else if (file.size > LIMITS[kind]) found.push(`${file.name}: ${kind === "photo" ? "photos" : "videos"} can be up to ${LIMITS[kind] / MB} MB.`);
      else if (added.length >= room) found.push(`${file.name}: a report can have up to ${MAX_FILES} files.`);
      else {
        const url = URL.createObjectURL(file);
        added.push({ id: `${file.name}-${file.size}-${file.lastModified}-${Math.random()}`, file, kind, url, keepSound: true });
      }
    }
    setProblems(found);
    if (added.length) setFiles([...files, ...added]);
  }

  function remove(item) {
    URL.revokeObjectURL(item.url);
    setFiles(files.filter((f) => f.id !== item.id));
  }

  return (
    <div className="evidence">
      <div className={`drop-zone ${room <= 0 ? "full" : ""}`}
        onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add("over"); }}
        onDragLeave={(e) => e.currentTarget.classList.remove("over")}
        onDrop={(e) => { e.preventDefault(); e.currentTarget.classList.remove("over"); if (room > 0) add([...e.dataTransfer.files]); }}>
        <span className="drop-icon"><ImagePlus size={22} aria-hidden="true" /></span>
        <div>
          <strong>Add photos or videos</strong> <span className="muted">(optional)</span>
          <div className="muted small">Drag them here or choose files · photos up to 15 MB, videos up to 100 MB · up to {MAX_FILES} files</div>
        </div>
        <button type="button" className="btn btn-plain" disabled={room <= 0} onClick={() => input.current?.click()}>
          <Paperclip size={16} aria-hidden="true" />Choose files
        </button>
        <input ref={input} type="file" multiple hidden accept={[...PHOTO_TYPES, ...VIDEO_TYPES].join(",")}
          onChange={(e) => { add([...e.target.files]); e.target.value = ""; }} />
      </div>
      {problems.length > 0 && <div className="alert alert-error" role="alert"><ul>{problems.map((p) => <li key={p}>{p}</li>)}</ul></div>}
      {files.length > 0 && (
        <ul className="evidence-grid">
          {files.map((item) => (
            <li key={item.id} className="evidence-tile">
              <div className="evidence-media">
                {item.kind === "photo" ? <img src={item.url} alt="Your photo" /> : <video src={item.url} muted={!item.keepSound} controls preload="metadata" />}
              </div>
              <div className="evidence-meta">
                <span className="small">{item.kind === "photo" ? "Photo" : "Video"} · {sizeText(item.file.size)}</span>
                <button type="button" className="icon-btn" onClick={() => remove(item)} aria-label="Remove this file" title="Remove"><Trash2 size={16} /></button>
              </div>
              {item.kind === "video" && (
                <label className="check small">
                  <input type="checkbox" checked={!item.keepSound}
                    onChange={(e) => setFiles(files.map((f) => (f.id === item.id ? { ...f, keepSound: !e.target.checked } : f)))} />
                  {item.keepSound ? <Volume2 size={15} aria-hidden="true" /> : <VolumeX size={15} aria-hidden="true" />} Remove the sound (your voice could identify you)
                </label>
              )}
            </li>
          ))}
        </ul>
      )}
      <EvidencePrivacy />
    </div>
  );
}

/**
 * Upload chosen files to a case one by one, showing each one's progress. Calls onDone(evidenceList) after each
 * success. Returns nothing; failures are shown next to the file.
 */
export function EvidenceUploader({ caseId, secret, files, onDone, onFinished }) {
  const [state, setState] = useState(() => Object.fromEntries(files.map((f) => [f.id, { progress: 0, status: "waiting" }])));
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    (async () => {
      for (const item of files) {
        setState((s) => ({ ...s, [item.id]: { progress: 0, status: "uploading" } }));
        try {
          const res = await uploadFile("/reports/evidence", { case_id: caseId, key: secret, keep_sound: item.keepSound }, item.file,
            (p) => setState((s) => ({ ...s, [item.id]: { progress: p, status: p >= 1 ? "cleaning" : "uploading" } })));
          setState((s) => ({ ...s, [item.id]: { progress: 1, status: "done" } }));
          onDone?.(res.evidence);
        } catch (err) {
          setState((s) => ({ ...s, [item.id]: { progress: 0, status: "failed", error: err.message } }));
        }
      }
      onFinished?.();
    })();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <ul className="upload-list">
      {files.map((item) => {
        const s = state[item.id];
        return (
          <li key={item.id} className={`upload-row ${s.status}`}>
            <span className="upload-thumb">{item.kind === "photo" ? <img src={item.url} alt="" /> : <Film size={18} aria-hidden="true" />}</span>
            <div className="upload-body">
              <div className="row spread small">
                <span>{item.kind === "photo" ? "Photo" : "Video"} · {sizeText(item.file.size)}</span>
                <span className="upload-status">
                  {s.status === "waiting" && "Waiting…"}
                  {s.status === "uploading" && <><Loader2 size={14} className="spin" aria-hidden="true" /> Uploading {Math.round(s.progress * 100)}%</>}
                  {s.status === "cleaning" && <><Loader2 size={14} className="spin" aria-hidden="true" /> Removing hidden details…</>}
                  {s.status === "done" && <><CheckCircle2 size={14} aria-hidden="true" /> Added, hidden details removed</>}
                  {s.status === "failed" && <><TriangleAlert size={14} aria-hidden="true" /> Not added</>}
                </span>
              </div>
              <div className="upload-bar" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(s.progress * 100)}>
                <span style={{ width: `${Math.round((s.status === "done" ? 1 : s.progress) * 100)}%` }} />
              </div>
              {s.error && <div className="field-problem">{s.error}</div>}
            </div>
          </li>
        );
      })}
    </ul>
  );
}

/** One saved file: fetched with the right permission, then shown from memory. */
function SavedFile({ item, load, onRemove, removing }) {
  const [url, setUrl] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let made = null;
    let alive = true;
    load(item).then((blob) => { if (alive) { made = URL.createObjectURL(blob); setUrl(made); } })
      .catch((err) => { if (alive) setError(err.message); });
    return () => { alive = false; if (made) URL.revokeObjectURL(made); };
  }, [item.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const label = `${item.kind === "photo" ? "Photo" : "Video"} ${item.number}`;
  return (
    <li className="evidence-tile">
      <div className="evidence-media">
        {error ? <span className="field-problem">{error}</span>
          : !url ? <Loader2 size={20} className="spin" aria-label="Loading" />
          : item.kind === "photo" ? <a href={url} target="_blank" rel="noreferrer" title="Open full size"><img src={url} alt={label} /></a>
          : <video src={url} controls preload="metadata" aria-label={label} />}
      </div>
      <div className="evidence-meta">
        <span className="small"><strong>{label}</strong> · {sizeText(item.size)} · added {item.added_on}</span>
        {onRemove && (
          <button type="button" className="icon-btn" onClick={() => onRemove(item)} disabled={removing === item.id}
            aria-label={`Remove ${label}`} title="Remove">{removing === item.id ? <Loader2 size={16} className="spin" /> : <Trash2 size={16} />}</button>
        )}
      </div>
    </li>
  );
}

/** The files already added to a case. `load(item)` returns a Blob; `onRemove` is only given to the reporter. */
export function EvidenceGallery({ items, load, onRemove, removing }) {
  if (!items.length) return <p className="muted">No photos or videos have been added.</p>;
  return <ul className="evidence-grid">{items.map((item) => <SavedFile key={item.id} item={item} load={load} onRemove={onRemove} removing={removing} />)}</ul>;
}

/** Load a saved file as the reporter (with the case ID and key) or as HR. */
export const loadAsReporter = (caseId, secret) => (item) =>
  apiBlob(`/reports/evidence/${item.id}/view`, { method: "POST", body: { case_id: caseId, key: secret } });
export const loadAsHr = (caseId) => (item) => apiBlob(`/hr/reports/${caseId}/evidence/${item.id}`);
