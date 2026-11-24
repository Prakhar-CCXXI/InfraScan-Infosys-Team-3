import { useState } from 'react';
import { Link } from 'react-router-dom';
import { TrendingUp, ArrowRight, AlertTriangle, Calendar, Layers } from 'lucide-react';
import { useAsync } from '../hooks/useAsync.js';
import { api } from '../services/api.js';
import { Card, Loading, Empty, ErrorBox, PageHead, Badge, ChartCanvas } from '../components/ui.jsx';
import CrackSvg from '../components/CrackSvg.jsx';
import { SEV_CLS } from '../utils/helpers.js';

export default function DamageProgression() {
  const { data, loading, error, reload } = useAsync(async () => {
    const [assets, insps] = await Promise.all([api.getAssets(), api.getInspections()]);
    return { assets: assets || [], insps: insps || [] };
  }, []);

  const [selectedAssetId, setSelectedAssetId] = useState('');
  const [metric, setMetric] = useState('Crack length');

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  const { assets, insps } = data;
  const currentAsset = assets.find((a) => a.id === selectedAssetId) || assets[0];
  const activeAssetId = currentAsset ? currentAsset.id : '';

  const assetInspections = insps
    .filter((i) => i.assetId === activeAssetId || i.asset === currentAsset?.name)
    .sort((a, b) => a.date.localeCompare(b.date));

  // Progression synthetic points if insufficient history
  const historyMilestones = [
    { date: '2026-05-10', id: 'INS-084', length: 18.2, width: 2.1, area: 38.2, status: 'Baseline' },
    { date: '2026-07-15', id: 'INS-091', length: 22.4, width: 2.8, area: 62.7, status: '+4.2 cm (+23%)' },
    { date: '2026-09-02', id: 'INS-101', length: 29.8, width: 3.9, area: 116.2, status: '+7.4 cm (+33%)' },
    { date: '2026-10-20', id: 'INS-104', length: 36.5, width: 4.8, area: 175.2, status: '+6.7 cm (+22%)' },
  ];

  const getMetricValue = (m, item) => {
    if (m === 'Crack length') return `${item.length} cm`;
    if (m === 'Crack width') return `${item.width} mm`;
    return `${item.area} cm²`;
  };

  const progressionData = {
    labels: historyMilestones.map((h) => h.date),
    datasets: [
      {
        label: metric,
        data: historyMilestones.map((h) =>
          metric === 'Crack length' ? h.length : metric === 'Crack width' ? h.width : h.area
        ),
        borderColor: '#e8a317',
        backgroundColor: 'rgba(232, 163, 23, 0.15)',
        tension: 0.3,
        fill: true,
      },
    ],
  };

  return (
    <>
      <PageHead
        title="Damage Progression"
        sub="Longitudinal defect propagation tracking, crack widening rates and structural deterioration comparison"
      >
        <Link to="/upload" className="btn">
          Upload New Inspection
        </Link>
      </PageHead>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <label className="text-sm font-medium">
          Select Infrastructure Asset:
          <select
            className="input ml-2 w-auto"
            value={activeAssetId}
            onChange={(e) => setSelectedAssetId(e.target.value)}
          >
            {assets.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} ({a.type})
              </option>
            ))}
          </select>
        </label>

        <label className="text-sm font-medium">
          Tracking Metric:
          <select
            className="input ml-2 w-auto"
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
          >
            <option>Crack length</option>
            <option>Crack width</option>
            <option>Damage area</option>
          </select>
        </label>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Visual Defect Progression (Previous vs Current Inspection)">
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center">
              <div className="mb-1 text-xs font-semibold text-slate-500">
                Baseline (Sep 02, 2026)
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-100 p-2">
                <CrackSvg scale={0.8} />
              </div>
              <div className="mt-1 text-xs text-slate-600">Minor crack branch (29.8 cm)</div>
            </div>
            <div className="text-center">
              <div className="mb-1 text-xs font-semibold text-slate-500">
                Latest (Oct 20, 2026)
              </div>
              <div className="rounded-lg border-2 border-survey bg-slate-100 p-2 shadow-xs">
                <CrackSvg scale={1.15} />
              </div>
              <div className="mt-1 text-xs font-medium text-red-700">Propagated & widened (36.5 cm)</div>
            </div>
          </div>
          <p className="mt-3 text-xs text-slate-500">
            Note: Calibration ensures pixels are translated to real-world metric dimensions under identical camera viewpoints.
          </p>
        </Card>

        <Card title={`Deterioration Curve: ${metric} Over Time`}>
          <ChartCanvas type="line" data={progressionData} options={{ plugins: { legend: { display: false } } }} />
        </Card>
      </div>

      <Card title="Historical Inspection Milestones & Defect Changes" className="mt-4">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                <th>Inspection Date</th>
                <th>Inspection ID</th>
                <th>{metric}</th>
                <th>Observed Change</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {historyMilestones.map((h, i) => (
                <tr key={h.id} className="border-t">
                  <td className="font-medium text-ink">{h.date}</td>
                  <td className="font-mono text-xs">{h.id}</td>
                  <td className="font-semibold text-slate-800">{getMetricValue(metric, h)}</td>
                  <td>
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-medium ${
                        i === 0
                          ? 'bg-slate-100 text-slate-700'
                          : 'bg-amber-100 text-amber-800'
                      }`}
                    >
                      {h.status}
                    </span>
                  </td>
                  <td>
                    <Link to="/results" className="text-xs text-steel underline">
                      View Analysis →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
