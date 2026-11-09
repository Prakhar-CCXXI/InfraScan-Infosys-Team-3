import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, Camera, X, Crop, CheckCircle, ShieldAlert, FileText, ExternalLink } from 'lucide-react';
import ImageEditor from '../components/ImageEditor.jsx';
import { useAsync } from '../hooks/useAsync.js';
import { api, isMock } from '../services/api.js';
import { Card, Field, PageHead, ErrorBox, Badge } from '../components/ui.jsx';

const OK = ['image/jpeg', 'image/png', 'image/webp'];
const MAX = 15 * 1024 * 1024; // 15 MB

export default function Upload() {
  const nav = useNavigate();
  const { data: assets } = useAsync(api.getAssets, []);
  const pick = useRef(), cam = useRef();
  
  const [files, setFiles] = useState([]);
  const [errs, setErrs] = useState([]);
  const [f, setF] = useState({ assetId: '', date: new Date().toISOString().split('T')[0], inspector: 'R. Kumar', notes: '' });
  const [fe, setFe] = useState({});
  const [ed, setEd] = useState(null);
  const [stage, setStage] = useState('idle');
  const [pct, setPct] = useState(0);
  const [msg, setMsg] = useState('');
  const [prediction, setPrediction] = useState(null);
  const [storedImages, setStoredImages] = useState([]);

  const add = (list) => {
    const bad = [], good = [];
    [...list].forEach((x) => {
      if (!OK.includes(x.type)) {
        bad.push(`${x.name}: only JPEG, PNG or WebP allowed.`);
      } else if (x.size > MAX) {
        bad.push(`${x.name}: larger than 15 MB.`);
      } else {
        good.push({ file: x, url: URL.createObjectURL(x) });
      }
    });
    setErrs(bad);
    setFiles((p) => [...p, ...good]);
  };

  const remove = (i) => {
    URL.revokeObjectURL(files[i].url);
    setFiles(files.filter((_, k) => k !== i));
  };

  const submit = async () => {
    const e = {};
    if (!f.assetId) e.assetId = 'Select an asset.';
    if (!f.date) e.date = 'Choose a date.';
    if (!f.inspector.trim()) e.inspector = 'Enter inspector name.';
    if (!files.length) e.files = 'Add at least one image.';
    setFe(e);
    if (Object.keys(e).length) return;

    setStage('sending');
    setMsg('');
    setPct(10);
    const t = setInterval(() => setPct((p) => Math.min(p + 15, 90)), 120);

    try {
      const fd = new FormData();
      files.forEach((x) => fd.append('images', x.file));
      Object.entries(f).forEach(([k, v]) => fd.append(k, v));

      const r = await api.uploadImages(fd);
      setPct(100);
      setStage('done');
      setMsg(r.message || 'Images stored in backend. AI analysis completed.');
      if (r.predictions && r.predictions.length > 0) {
        setPrediction(r.predictions[0]);
      }
      if (r.stored_images) {
        setStoredImages(r.stored_images);
      }
    } catch (x) {
      setStage('idle');
      setMsg(x.message || 'Image upload failed. Ensure backend server is running on port 8000.');
    } finally {
      clearInterval(t);
    }
  };

  return (
    <>
      <PageHead
        title="Image Upload & AI Crack Assessment"
        sub="Upload infrastructure inspection imagery directly to the backend for computer vision defect detection and database persistence"
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Inspection Images">
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              add(e.dataTransfer.files);
            }}
            className="flex flex-col items-center gap-2 rounded-lg border-2 border-dashed border-slate-300 p-8 text-center text-sm"
          >
            <UploadCloud className="h-8 w-8 text-steel" />
            <p className="font-medium text-slate-700">Drag and drop images here</p>
            <p className="text-xs text-slate-500">JPEG, PNG or WebP, up to 15 MB each</p>
            <div className="flex gap-2 mt-2">
              <button type="button" className="btn" onClick={() => pick.current.click()}>
                Browse files
              </button>
              <button type="button" className="btn-ghost" onClick={() => cam.current.click()}>
                <Camera className="h-4 w-4" /> Use camera
              </button>
            </div>
            <input
              ref={pick}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              hidden
              onChange={(e) => {
                add(e.target.files);
                e.target.value = '';
              }}
            />
            <input
              ref={cam}
              type="file"
              accept="image/*"
              capture="environment"
              hidden
              onChange={(e) => {
                add(e.target.files);
                e.target.value = '';
              }}
            />
          </div>

          {fe.files && <p role="alert" className="mt-2 text-xs text-red-600">{fe.files}</p>}
          {errs.map((x) => (
            <p key={x} role="alert" className="mt-1 text-xs text-red-600">{x}</p>
          ))}

          <div className="mt-3 grid grid-cols-3 gap-2">
            {files.map((x, i) => (
              <div key={x.url} className="relative group">
                <img src={x.url} alt={x.file.name} className="aspect-square w-full rounded object-cover border" />
                <button
                  type="button"
                  aria-label={`Remove ${x.file.name}`}
                  onClick={() => remove(i)}
                  className="absolute right-1 top-1 rounded-full bg-ink p-1 text-white hover:bg-red-600 transition"
                >
                  <X className="h-3 w-3" />
                </button>
                <button
                  type="button"
                  aria-label={`Crop or rotate ${x.file.name}`}
                  onClick={() => setEd(i)}
                  className="absolute bottom-1 right-1 rounded-full bg-ink p-1 text-white hover:bg-steel transition"
                >
                  <Crop className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>

          {ed !== null && files[ed] && (
            <ImageEditor
              item={files[ed]}
              onClose={() => setEd(null)}
              onApply={(nf) => {
                URL.revokeObjectURL(files[ed].url);
                setFiles(files.map((y, k) => (k === ed ? { file: nf, url: URL.createObjectURL(nf) } : y)));
                setEd(null);
              }}
            />
          )}
        </Card>

        <Card title="Inspection & Asset Metadata">
          <div className="space-y-3">
            <Field label="Infrastructure asset" error={fe.assetId}>
              <select
                className="input"
                value={f.assetId}
                onChange={(e) => setF({ ...f, assetId: e.target.value })}
              >
                <option value="">Select monitored asset…</option>
                {(assets || []).map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.id} · {a.name} ({a.type})
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Inspection date" error={fe.date}>
              <input
                type="date"
                className="input"
                value={f.date}
                onChange={(e) => setF({ ...f, date: e.target.value })}
              />
            </Field>

            <Field label="Inspector name" error={fe.inspector}>
              <input
                className="input"
                value={f.inspector}
                onChange={(e) => setF({ ...f, inspector: e.target.value })}
                placeholder="e.g. Dr. L. Venkat"
              />
            </Field>

            <Field label="Inspector notes (optional)">
              <textarea
                className="input"
                rows={3}
                value={f.notes}
                onChange={(e) => setF({ ...f, notes: e.target.value })}
                placeholder="Location details, visible cracks, ambient conditions..."
              />
            </Field>

            {stage === 'sending' && (
              <div className="space-y-1">
                <div className="h-2 rounded bg-slate-200 overflow-hidden">
                  <div
                    className="h-2 rounded bg-steel transition-all duration-300"
                    style={{ width: pct + '%' }}
                  />
                </div>
                <p className="text-xs text-slate-500">
                  Uploading to FastAPI backend and executing computer vision crack inference… ({pct}%)
                </p>
              </div>
            )}

            {stage === 'done' && (
              <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3 space-y-2">
                <div className="flex items-center gap-2 text-emerald-800 font-medium text-sm">
                  <CheckCircle className="h-5 w-5 text-emerald-600" />
                  <span>{msg}</span>
                </div>

                {storedImages.length > 0 && (
                  <div className="text-xs text-emerald-900 bg-white/70 p-2 rounded border border-emerald-100">
                    <p className="font-semibold">Backend Storage Location:</p>
                    {storedImages.map((img, i) => (
                      <p key={i} className="font-mono text-[11px] truncate text-slate-700">
                        {img.image_path}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            )}

            {stage === 'idle' && msg && <ErrorBox message={msg} />}

            <div className="flex gap-2 pt-2">
              <button
                type="button"
                className="btn"
                disabled={stage === 'sending'}
                onClick={submit}
              >
                {stage === 'sending' ? 'Uploading & Analyzing…' : 'Submit to Backend & Run AI'}
              </button>

              {stage === 'done' && (
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => nav('/results')}
                >
                  View full damage analysis
                </button>
              )}
            </div>
          </div>
        </Card>
      </div>

      {prediction && (
        <div className="mt-6">
          <Card title="Live AI Analysis Result (Persisted in PostgreSQL)">
            <div className="grid gap-4 md:grid-cols-4">
              <div className="p-3 bg-slate-50 rounded border">
                <p className="text-xs text-slate-500">Database Record ID</p>
                <p className="text-lg font-bold text-ink">Prediction #{prediction.id}</p>
                <p className="text-xs text-slate-600 mt-1">Asset ID: {prediction.asset_id}</p>
              </div>

              <div className="p-3 bg-slate-50 rounded border">
                <p className="text-xs text-slate-500">Damage Severity</p>
                <p className="text-base font-semibold text-amber-700">{prediction.severity_level}</p>
                <p className="text-xs text-slate-500 mt-1">
                  Confidence: <b>{Math.round(prediction.confidence_score * 100)}%</b>
                </p>
              </div>

              <div className="p-3 bg-slate-50 rounded border">
                <p className="text-xs text-slate-500">Defect Detection</p>
                <p className="text-sm font-medium text-slate-800">
                  {prediction.defect_details?.total_defects || 1} defect(s) localized
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Crack density: {prediction.defect_details?.crack_density_percentage || 0}%
                </p>
              </div>

              <div className="p-3 bg-slate-50 rounded border">
                <p className="text-xs text-slate-500">Forecasted Failure Date</p>
                <p className="text-sm font-semibold text-slate-800">
                  {prediction.predicted_failure_date ? prediction.predicted_failure_date.slice(0, 10) : 'N/A'}
                </p>
                <p className="text-xs text-emerald-600 mt-1">Active Monitoring</p>
              </div>
            </div>

            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded">
              <p className="text-xs font-semibold text-blue-900 uppercase tracking-wide">
                Prescriptive Engineering Recommendation
              </p>
              <p className="text-sm text-blue-950 mt-1">
                {prediction.recommended_action}
              </p>
            </div>
          </Card>
        </div>
      )}
    </>
  );
}
