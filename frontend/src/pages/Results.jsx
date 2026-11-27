import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ZoomIn, Columns, Square, CheckCircle2, AlertTriangle, X } from 'lucide-react';
import { useAsync } from '../hooks/useAsync.js';
import { api, mediaUrl } from '../services/api.js';
import { Card, Loading, ErrorBox, PageHead, Badge, DemoTag, EngineerNotice } from '../components/ui.jsx';
import CrackSvg from '../components/CrackSvg.jsx';
import { SEV_CLS, PRI_CLS } from '../utils/helpers.js';

export default function Results() {
  const { id = 'latest' } = useParams();
  const { data, loading, error, reload } = useAsync(() => api.getAnalysis(id), [id]);
  const [activeTab, setActiveTab] = useState('detect');
  const [compareMode, setCompareMode] = useState(false);
  const [review, setReview] = useState(null);
  const [saving, setSaving] = useState(false);
  const [reviewErr, setReviewErr] = useState(null);
  const [zoomed, setZoomed] = useState(null);

  useEffect(() => {
    setActiveTab('detect');
    setCompareMode(false);
    setReview(null);
    setReviewErr(null);
    setZoomed(null);
  }, [id]);

  useEffect(() => {
    if (!zoomed) return;
    const onKeyDown = (e) => {
      if (e.key === 'Escape') setZoomed(null);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [zoomed]);

  if (loading || !data) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  const c = data.cracks?.[0] || null;
  const detections = data.detections || [];
  const unit = data.calibrated ? 'mm' : 'px';
  const images = data.images || {};
  const isSample = Boolean(data.sample);
  const isRoadScene = data.profile === 'road_scene';
  const rawConf = data.confidence ?? c?.confidence ?? 0;

  const isHairlineClassifier =
    !isRoadScene &&
    (String(c?.type || '').toLowerCase().includes('hairline') ||
      String(data.severity || '').toLowerCase().includes('hairline'));

  const isEmptyMask =
    !isRoadScene &&
    Number(c?.areaPx || 0) === 0 &&
    Number(data.crackDensityPct || 0) === 0;

  const isEmptyHairlineFallback = isHairlineClassifier && isEmptyMask;

  const views = isRoadScene
    ? [
        { key: 'detect', label: 'Detection / Overlay' },
        { key: 'original', label: 'Original' },
      ]
    : [
        { key: 'detect', label: 'Detection / Overlay' },
        { key: 'original', label: 'Original' },
        { key: 'mask', label: 'Segmentation Mask' },
        { key: 'heat', label: 'Grad-CAM' },
      ];

  const currentKey = views.some((v) => v.key === activeTab) ? activeTab : 'detect';
  const currentView = views.find((v) => v.key === currentKey) || views[0];
  const currentSrc = mediaUrl(images[currentKey]);
  const originalSrc = mediaUrl(images.original);

  const scorePct =
    data.severityScore != null ? Math.max(0, Math.min(100, Number(data.severityScore))) : null;
  const scoreBarCls =
    scorePct == null
      ? 'bg-slate-400'
      : scorePct >= 65
        ? 'bg-red-500'
        : scorePct >= 35
          ? 'bg-amber-500'
          : 'bg-emerald-500';

  const submitReview = async (status, localLabel) => {
    if (!data.predictionId) {
      setReview(localLabel);
      return;
    }
    setSaving(true);
    setReviewErr(null);
    try {
      const r = await api.updateReview(data.predictionId, status);
      setReview(r.reviewStatus);
    } catch (e) {
      setReviewErr(e.message || 'Could not save review status.');
    } finally {
      setSaving(false);
    }
  };

  const renderStageImage = (src, label, key, maxH = 'max-h-[440px]') => {
    if (key === 'mask' && isEmptyHairlineFallback) {
      return (
        <div className="flex h-72 w-full flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-amber-300 bg-amber-50/60 px-6 text-center">
          <AlertTriangle className="h-7 w-7 text-amber-600" />
          <div className="max-w-md space-y-1">
            <p className="text-sm font-semibold text-amber-950">
              No segmentation mask for hairline crack
            </p>
            <p className="text-xs leading-relaxed text-amber-800">
              This hairline crack was detected by the SDNET2018 ConvNeXt classifier rather than pixel-level U-Net segmentation, so no binary mask is generated.
            </p>
          </div>
          {images.heat && (
            <button
              type="button"
              onClick={() => {
                setActiveTab('heat');
                setCompareMode(false);
              }}
              className="inline-flex items-center rounded-md bg-amber-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-800"
            >
              View Grad-CAM heatmap
            </button>
          )}
        </div>
      );
    }

    if (src) {
      return (
        <div className="group relative flex items-center justify-center rounded-lg border border-slate-200 bg-slate-100/80 p-2">
          <img
            src={src}
            alt={label}
            onClick={() => setZoomed({ src, label })}
            className={`${maxH} w-auto max-w-full cursor-zoom-in rounded object-contain shadow-sm`}
          />
          <button
            type="button"
            onClick={() => setZoomed({ src, label })}
            aria-label={`Zoom ${label}`}
            className="absolute right-3 top-3 inline-flex items-center gap-1 rounded-md bg-white/90 px-2 py-1 text-xs font-medium text-slate-700 shadow-sm ring-1 ring-slate-200 backdrop-blur transition hover:bg-white"
          >
            <ZoomIn className="h-3.5 w-3.5" />
            Zoom
          </button>
        </div>
      );
    }
    if (isSample) {
      return (
        <div className="flex items-center justify-center rounded-lg border border-slate-200 bg-slate-100 p-4">
          <CrackSvg mode={key} />
        </div>
      );
    }
    return (
      <div className="flex h-72 w-full items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 text-center text-xs text-slate-400">
        {label} not generated for this inspection
      </div>
    );
  };

  return (
    <>
      <PageHead
        title="Damage analysis"
        sub={`Inspection ${data.inspectionId} · ${data.modelVersion}`}
      >
        {isSample && <DemoTag text="Sample results, not real AI output" />}
        <Link to="/upload" className="btn-ghost">New Upload</Link>
      </PageHead>

      <div className="grid items-start gap-5 lg:grid-cols-12">
        {/* LEFT: Interactive Visual Inspector */}
        <div className="space-y-3 lg:col-span-7">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            {/* Toolbar: View Switcher + Compare Toggle */}
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <div className="inline-flex flex-wrap gap-1 rounded-lg bg-slate-100 p-1">
                {views.map((v) => {
                  const active = currentKey === v.key;
                  return (
                    <button
                      key={v.key}
                      type="button"
                      onClick={() => setActiveTab(v.key)}
                      className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                        active
                          ? 'bg-white text-slate-900 shadow-sm'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      {v.label}
                    </button>
                  );
                })}
              </div>

              <button
                type="button"
                onClick={() => setCompareMode((m) => !m)}
                className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition ${
                  compareMode
                    ? 'border-slate-900 bg-slate-900 text-white'
                    : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                }`}
              >
                {compareMode ? <Square className="h-3.5 w-3.5" /> : <Columns className="h-3.5 w-3.5" />}
                {compareMode ? 'Single view' : 'Compare'}
              </button>
            </div>

            {/* Main Image Stage */}
            {compareMode ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="mb-1.5 text-xs font-medium text-slate-500">Original</p>
                  {renderStageImage(originalSrc, 'Original', 'original', 'max-h-[360px]')}
                </div>
                <div>
                  <p className="mb-1.5 text-xs font-medium text-slate-500">
                    {currentKey === 'original' ? 'Detection / Overlay' : currentView.label}
                  </p>
                  {renderStageImage(
                    currentKey === 'original' ? mediaUrl(images.detect) : currentSrc,
                    currentKey === 'original' ? 'Detection / Overlay' : currentView.label,
                    currentKey === 'original' ? 'detect' : currentKey,
                    'max-h-[360px]'
                  )}
                </div>
              </div>
            ) : (
              renderStageImage(currentSrc, currentView.label, currentKey, 'max-h-[460px]')
            )}

            {/* Compact Thumbnail Filmstrip */}
            <div className={`mt-3 grid grid-cols-2 gap-2 ${isRoadScene ? 'sm:grid-cols-2' : 'sm:grid-cols-4'}`}>
              {views.map((v) => {
                const hideMaskThumb = v.key === 'mask' && isEmptyHairlineFallback;
                const src = hideMaskThumb ? null : mediaUrl(images[v.key]);
                const active = currentKey === v.key;
                return (
                  <button
                    key={v.key}
                    type="button"
                    onClick={() => {
                      setActiveTab(v.key);
                      setCompareMode(false);
                    }}
                    className={`flex items-center gap-2 rounded-lg border p-1.5 text-left transition ${
                      active
                        ? 'border-slate-900 bg-slate-50 ring-1 ring-slate-900'
                        : 'border-slate-200 bg-white hover:border-slate-300'
                    }`}
                  >
                    {src ? (
                      <img
                        src={src}
                        alt={v.label}
                        className="h-11 w-11 shrink-0 rounded border border-slate-200 bg-slate-100 object-cover"
                      />
                    ) : (
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded border border-dashed border-slate-300 bg-slate-50 text-[10px] text-slate-400">
                        N/A
                      </div>
                    )}
                    <span className="truncate text-xs font-medium text-slate-700">
                      {v.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* RIGHT: Inspector Summary & Actions Rail */}
        <div className="space-y-4 lg:col-span-5">
          {/* Severity & Classification */}
          <Card title="Severity & Classification">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Badge cls={SEV_CLS[data.severity]}>{data.severity}</Badge>
              <Badge cls={PRI_CLS[data.priority]}>{data.priority}</Badge>
            </div>

            {scorePct != null && (
              <div className="mt-3">
                <div className="mb-1 flex items-baseline justify-between text-xs">
                  <span className="text-slate-500">Severity score</span>
                  <span className="font-semibold text-slate-900">{data.severityScore} / 100</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full rounded-full transition-all ${scoreBarCls}`}
                    style={{ width: `${scorePct}%` }}
                  />
                </div>
              </div>
            )}

            <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-2.5 text-sm">
              <span className="text-slate-500">Model confidence</span>
              <b className="text-slate-900">
                {rawConf > 0
                  ? `${Math.round(rawConf * 100)}%`
                  : isRoadScene
                    ? 'N/A (no detections)'
                    : 'N/A (pixel segmentation)'}
              </b>
            </div>

            {data.severityExplanation && (
              <p className="mt-3 rounded-lg bg-slate-50 p-2.5 text-xs leading-relaxed text-slate-600">
                {data.severityExplanation}
              </p>
            )}
          </Card>

          {/* Measurements (U-Net) or Detections (YOLO11s) */}
          <Card title={c ? 'Crack measurements' : 'Road detections (YOLO11s)'}>
            {c ? (
              isEmptyHairlineFallback ? (
                <div className="space-y-2 rounded-lg border border-amber-200 bg-amber-50/70 p-3 text-xs text-amber-900">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                    <div>
                      <p className="font-semibold">{c.type}</p>
                      <p className="mt-0.5 text-amber-800">
                        U-Net produced an empty mask on this low-contrast surface, so pixel length and width are unavailable. Inspect the Grad-CAM heatmap to localize the crack.
                      </p>
                    </div>
                  </div>
                  {images.heat && (
                    <button
                      type="button"
                      onClick={() => {
                        setActiveTab('heat');
                        setCompareMode(false);
                      }}
                      className="inline-flex items-center rounded-md bg-amber-900 px-2.5 py-1 text-xs font-medium text-white hover:bg-amber-800"
                    >
                      View Grad-CAM heatmap
                    </button>
                  )}
                </div>
              ) : (
                <>
                  <p className="mb-2.5 text-xs font-medium text-slate-600">{c.type}</p>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      ['Length', `${c.lengthPx} ${unit}`],
                      ['Avg width', `${c.avgWidthPx} ${unit}`],
                      ['Max width', `${c.maxWidthPx} ${unit}`],
                      ['Area', `${c.areaPx} ${unit}²`],
                      ['Crack density', `${data.crackDensityPct}%`],
                      ['Orientation', `${c.orientationDeg}°`],
                      ...(c.branchPoints != null ? [['Branch points', c.branchPoints]] : []),
                    ].map(([k, v]) => (
                      <div key={k} className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
                        <p className="text-[11px] text-slate-500">{k}</p>
                        <p className="text-sm font-semibold text-slate-900">{v}</p>
                      </div>
                    ))}
                  </div>
                  {!data.calibrated && (
                    <p className="mt-2.5 text-[11px] text-slate-500">
                      No scale calibration supplied — values are in pixels.
                    </p>
                  )}
                </>
              )
            ) : detections.length > 0 ? (
              <ul className="space-y-2.5 text-sm">
                {detections.map((d, idx) => {
                  const pct = Math.round((d.confidence || 0) * 100);
                  const label =
                    d.class && d.label && d.label !== d.class
                      ? `${d.class} · ${d.label}`
                      : d.class_name || d.label || d.class;
                  return (
                    <li key={idx} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium text-slate-800">{label}</span>
                        <span className="font-semibold text-slate-600">{pct}%</span>
                      </div>
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                        <div className="h-full rounded-full bg-slate-700" style={{ width: `${pct}%` }} />
                      </div>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">No defects localized in this image.</p>
            )}
          </Card>

          {/* Engineer Review */}
          <Card title="Engineer review">
            <div className="mb-3 flex items-center gap-2 text-sm">
              <CheckCircle2 className="h-4 w-4 text-slate-400" />
              <span className="text-slate-500">Status:</span>
              <b className="text-slate-900">{review || data.reviewStatus}</b>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                className="btn flex-1 justify-center"
                disabled={saving}
                onClick={() => submitReview('confirmed', 'Confirmed by engineer (local session)')}
              >
                {saving ? 'Saving…' : 'Confirm'}
              </button>
              <button
                className="btn-ghost flex-1 justify-center"
                disabled={saving}
                onClick={() => submitReview('review_requested', 'Engineering review requested (local session)')}
              >
                Request review
              </button>
            </div>
            {reviewErr && <p role="alert" className="mt-2 text-xs text-red-600">{reviewErr}</p>}
          </Card>
        </div>
      </div>

      <div className="mt-5">
        <EngineerNotice />
      </div>

      {/* Full-Screen Zoom Lightbox */}
      {zoomed && (
        <div
          role="dialog"
          aria-modal="true"
          onClick={() => setZoomed(null)}
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/85 p-4 backdrop-blur-sm"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="relative flex max-h-[92vh] max-w-[92vw] flex-col items-center rounded-xl bg-white p-3 shadow-2xl"
          >
            <div className="mb-2 flex w-full items-center justify-between gap-4 border-b border-slate-100 pb-2 text-xs text-slate-700">
              <span className="font-semibold">{zoomed.label}</span>
              <button
                type="button"
                onClick={() => setZoomed(null)}
                className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-200"
              >
                <X className="h-3.5 w-3.5" /> Close
              </button>
            </div>
            <img
              src={zoomed.src}
              alt={zoomed.label}
              className="max-h-[82vh] max-w-[88vw] rounded object-contain"
            />
          </div>
        </div>
      )}
    </>
  );
}