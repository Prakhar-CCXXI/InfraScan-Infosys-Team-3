import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAsync } from '../hooks/useAsync.js';
import { api, mediaUrl } from '../services/api.js';
import { Card, Loading, ErrorBox, PageHead, Badge, DemoTag, EngineerNotice } from '../components/ui.jsx';
import CrackSvg from '../components/CrackSvg.jsx';
import { SEV_CLS, PRI_CLS } from '../utils/helpers.js';

export default function Results() {
  const { id = 'latest' } = useParams();
  const { data, loading, error, reload } = useAsync(() => api.getAnalysis(id), [id]);
  const [review, setReview] = useState(null);
  const [saving, setSaving] = useState(false);
  const [reviewErr, setReviewErr] = useState(null);

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  const c = data.cracks?.[0] || null;
  const detections = data.detections || [];
  const unit = data.calibrated ? 'mm' : 'px';
  const images = data.images || {};
  const isSample = Boolean(data.sample);
  const rawConf = data.confidence ?? c?.confidence ?? 0;

  const submitReview = async (status, localLabel) => {
    if (!data.predictionId) {
      setReview(localLabel); // sample/mock data has no DB record
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

  const steps = [
    ['Original image', 'original'],
    ['Preprocessed image', 'pre'],
    ['Detection / overlay', 'detect'],
    ['Segmentation mask', 'mask'],
    ['Grad-CAM / explainability', 'heat'],
  ];

  return (
    <>
      <PageHead
        title="Damage analysis"
        sub={`Inspection ${data.inspectionId} · model ${data.modelVersion}`}
      >
        {isSample && <DemoTag text="Sample results, not real AI output" />}
        <Link to="/upload" className="btn-ghost">New Upload</Link>
      </PageHead>

      <Card title="Comparison view: Original ↔ Preprocessed ↔ Detection ↔ Segmentation mask ↔ Grad-CAM">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          {steps.map(([label, key], i) => {
            const imgSrc = mediaUrl(images[key]);
            return (
              <figure key={key} className="flex flex-col">
                {imgSrc ? (
                  <img
                    src={imgSrc}
                    alt={label}
                    className="h-40 w-full rounded border border-slate-200 bg-slate-900 object-contain"
                  />
                ) : isSample ? (
                  <CrackSvg mode={key} />
                ) : (
                  <div className="flex h-40 w-full items-center justify-center rounded border border-dashed border-slate-300 bg-slate-50 px-2 text-center text-xs text-slate-400">
                    {key === 'heat' && data.profile === 'road_scene'
                      ? 'Not applicable for road_scene mode'
                      : `Not generated for ${data.profile || 'this'} mode`}
                  </div>
                )}
                <figcaption className="mt-1 text-center text-xs text-slate-600">
                  {i + 1}. {label}
                </figcaption>
              </figure>
            );
          })}
        </div>
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card title={c ? 'Crack measurements (U-Net)' : 'Road detections (YOLO11s)'}>
          {c ? (
            <>
              <table className="w-full text-sm">
                <tbody>
                  {[
                    ['Type', c.type],
                    ['Length', `${c.lengthPx} ${unit}`],
                    ['Average width', `${c.avgWidthPx} ${unit}`],
                    ['Maximum width', `${c.maxWidthPx} ${unit}`],
                    ['Area', `${c.areaPx} ${unit}²`],
                    ['Orientation', `${c.orientationDeg}°`],
                    ['Crack density', `${data.crackDensityPct}%`],
                    ...(c.branchPoints != null ? [['Branch points', c.branchPoints]] : []),
                  ].map(([k, v]) => (
                    <tr key={k} className="border-t">
                      <td className="py-1 text-slate-500">{k}</td>
                      <td className="py-1 font-medium">{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!data.calibrated && (
                <p className="mt-2 text-xs text-slate-500">
                  No scale calibration available, so values are in pixels, not physical units.
                </p>
              )}
            </>
          ) : detections.length > 0 ? (
            <ul className="space-y-2 text-sm">
              {detections.map((d, idx) => (
                <li key={idx} className="flex items-center justify-between border-t pt-1">
                  <span className="font-medium">
                    {d.class && d.label && d.label !== d.class
                      ? `${d.class} · ${d.label}`
                      : d.class_name || d.label || d.class}
                  </span>
                  <span className="text-slate-600">
                    {Math.round((d.confidence || 0) * 100)}%
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">No defects localized in this image.</p>
          )}
        </Card>

        <Card title="Severity & Classification">
          <ul className="space-y-2 text-sm">
            <li>
              Confidence:{' '}
              <b>
              {rawConf > 0
                ? `${Math.round(rawConf * 100)}%`
                : data.profile === 'road_scene'
                  ? 'N/A (no detections)'
                  : 'N/A (pixel segmentation)'}
              </b>
            </li>
            {data.severityScore != null && (
              <li>
                Severity score: <b>{data.severityScore} / 100</b>
              </li>
            )}
            <li>
              Severity: <Badge cls={SEV_CLS[data.severity]}>{data.severity}</Badge>
            </li>
            <li>
              Suggested priority: <Badge cls={PRI_CLS[data.priority]}>{data.priority}</Badge>
            </li>
            {data.severityExplanation && (
              <li className="border-t pt-2 text-xs text-slate-600">
                {data.severityExplanation}
              </li>
            )}
          </ul>
        </Card>

        <Card title="Engineer review">
          <p className="mb-2 text-sm">
            Status: <b>{review || data.reviewStatus}</b>
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              className="btn"
              disabled={saving}
              onClick={() => submitReview('confirmed', 'Confirmed by engineer (local session)')}
            >
              Confirm
            </button>
            <button
              className="btn-ghost"
              disabled={saving}
              onClick={() => submitReview('review_requested', 'Engineering review requested (local session)')}
            >
              Request review
            </button>
          </div>
          {reviewErr && <p role="alert" className="mt-2 text-xs text-red-600">{reviewErr}</p>}
        </Card>
      </div>

      <div className="mt-4">
        <EngineerNotice />
      </div>
    </>
  );
}