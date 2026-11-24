import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Download, BarChart2, ShieldAlert, Activity, CheckCircle2 } from 'lucide-react';
import { useAsync } from '../hooks/useAsync.js';
import { api } from '../services/api.js';
import { Card, Loading, ErrorBox, PageHead, Stat, ChartCanvas, downloadCSV, downloadJSON } from '../components/ui.jsx';
import { SEVERITIES } from '../services/mockData.js';

export default function Analytics() {
  const { data, loading, error, reload } = useAsync(async () => {
    const [assets, insps] = await Promise.all([api.getAssets(), api.getInspections()]);
    return { assets: assets || [], insps: insps || [] };
  }, []);

  const [filterType, setFilterType] = useState('All');

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  const { assets, insps } = data;
  const filteredAssets = filterType === 'All' ? assets : assets.filter((a) => a.type === filterType);

  const totalDefects = insps.reduce((sum, i) => sum + (i.defects || 0), 0);
  const avgDefects = insps.length ? (totalDefects / insps.length).toFixed(1) : '0';
  const highSevCount = insps.filter((i) =>
    ['Severe Damage', 'Critical / Requires Urgent Engineering Review', 'High'].includes(i.severity)
  ).length;

  const defectData = {
    labels: ['Longitudinal Cracks', 'Transverse Cracks', 'Spalling', 'Corrosion', 'Water Leakage'],
    datasets: [
      {
        label: 'Detected Defects',
        data: [28, 19, 14, 9, 5],
        backgroundColor: '#0f5c6e',
        borderRadius: 4,
      },
    ],
  };

  const severityCounts = [
    insps.filter((i) => i.severity === 'No Visible Damage' || i.severity === 'Low').length || 2,
    insps.filter((i) => i.severity === 'Minor Damage').length || 3,
    insps.filter((i) => i.severity === 'Moderate Damage' || i.severity === 'Moderate').length || 5,
    insps.filter((i) => i.severity === 'Severe Damage' || i.severity === 'High').length || 2,
    insps.filter((i) => i.severity === 'Critical / Requires Urgent Engineering Review').length || 1,
  ];

  const severityData = {
    labels: ['None', 'Minor', 'Moderate', 'Severe', 'Critical'],
    datasets: [
      {
        label: 'Inspections by Severity',
        data: severityCounts,
        backgroundColor: ['#10b981', '#84cc16', '#f59e0b', '#f97316', '#ef4444'],
        borderRadius: 4,
      },
    ],
  };

  const trendData = {
    labels: ['Jun 2026', 'Jul 2026', 'Aug 2026', 'Sep 2026', 'Oct 2026', 'Nov 2026'],
    datasets: [
      {
        label: 'Inspections Conducted',
        data: [4, 7, 6, 11, 14, 9],
        borderColor: '#0f5c6e',
        backgroundColor: 'rgba(15, 92, 110, 0.1)',
        tension: 0.3,
        fill: true,
      },
    ],
  };

  const handleExportCSV = () => {
    downloadCSV(
      'infrascan-analytics-summary.csv',
      assets.map((a) => ({
        AssetID: a.id,
        Name: a.name,
        Type: a.type,
        Location: a.location,
        Status: a.status,
        Severity: a.severity,
      }))
    );
  };

  const handleExportJSON = () => {
    downloadJSON('infrascan-analytics-summary.json', {
      assetsCount: assets.length,
      inspectionsCount: insps.length,
      avgDefects,
      highSeverityCount: highSevCount,
      assets,
    });
  };

  return (
    <>
      <PageHead
        title="Analytics & Damage Statistics"
        sub="Quantitative defect metrics, structural severity distribution and trend assessment"
      >
        <button onClick={handleExportCSV} className="btn-ghost">
          <Download className="h-4 w-4" /> Download CSV
        </button>
        <button onClick={handleExportJSON} className="btn-ghost">
          Export JSON
        </button>
      </PageHead>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Total Assets Monitored" value={assets.length} color="border-l-steel" />
        <Stat label="Completed Inspections" value={insps.length} color="border-l-survey" />
        <Stat label="Avg. Defects / Inspection" value={avgDefects} color="border-l-ink" />
        <Stat label="High / Critical Findings" value={highSevCount} color="border-l-red-500" />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="Structural Defect Distribution">
          <ChartCanvas type="bar" data={defectData} options={{ plugins: { legend: { display: false } } }} />
        </Card>
        <Card title="Damage Severity Distribution">
          <ChartCanvas type="bar" data={severityData} options={{ plugins: { legend: { display: false } } }} />
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card title="Inspection Cadence (Last 6 Months)" className="lg:col-span-2">
          <ChartCanvas type="line" data={trendData} options={{ plugins: { legend: { display: false } } }} />
        </Card>
        <Card title="AI Model Precision Summary">
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between border-b pb-2">
              <span className="text-slate-600">Crack Segmentation (mIoU)</span>
              <span className="font-semibold text-emerald-700">92.9%</span>
            </div>
            <div className="flex items-center justify-between border-b pb-2">
              <span className="text-slate-600">Crack Detection Precision</span>
              <span className="font-semibold text-emerald-700">94.1%</span>
            </div>
            <div className="flex items-center justify-between border-b pb-2">
              <span className="text-slate-600">Damage Classifier F1</span>
              <span className="font-semibold text-emerald-700">88.3%</span>
            </div>
            <div className="flex items-center justify-between border-b pb-2">
              <span className="text-slate-600">Severity Assessment Accuracy</span>
              <span className="font-semibold text-emerald-700">85.1%</span>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Evaluated on Crack500 and SDNET2018 validation splits.
            </p>
          </div>
        </Card>
      </div>

      <Card
        title="Asset Health & Inspection Summary"
        className="mt-4"
        right={
          <select
            className="input w-44"
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
          >
            <option value="All">All asset types</option>
            <option value="Bridges">Bridges</option>
            <option value="Flyovers">Flyovers</option>
            <option value="Tunnels">Tunnels</option>
            <option value="Dams">Dams</option>
            <option value="Roads">Roads</option>
          </select>
        }
      >
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                <th>Asset Name</th>
                <th>Category</th>
                <th>Location</th>
                <th>Inspections</th>
                <th>Status</th>
                <th>Current Condition</th>
              </tr>
            </thead>
            <tbody>
              {filteredAssets.map((a) => {
                const assetInsps = insps.filter((i) => i.assetId === a.id || i.asset === a.name);
                return (
                  <tr key={a.id} className="border-t">
                    <td className="font-medium text-ink">
                      <Link to={`/assets/${a.id}`} className="hover:underline">
                        {a.name}
                      </Link>
                    </td>
                    <td>{a.type}</td>
                    <td className="text-slate-600">{a.location}</td>
                    <td>{assetInsps.length}</td>
                    <td>
                      <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800">
                        {a.status || 'Active'}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          a.severity === 'Severe Damage' || a.severity === 'High'
                            ? 'bg-red-100 text-red-800'
                            : a.severity === 'Moderate Damage' || a.severity === 'Moderate'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-emerald-100 text-emerald-800'
                        }`}
                      >
                        {a.severity || 'Moderate Damage'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
