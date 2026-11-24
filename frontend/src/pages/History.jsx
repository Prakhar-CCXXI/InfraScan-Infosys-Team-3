import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Download, TrendingUp, Plus } from 'lucide-react';
import { useAsync } from '../hooks/useAsync.js';
import { api } from '../services/api.js';
import { Card, Loading, Empty, ErrorBox, PageHead, Badge, ChartCanvas, downloadCSV, downloadJSON } from '../components/ui.jsx';
import CrackSvg from '../components/CrackSvg.jsx';
import { SEV_CLS, STATUS_CLS } from '../utils/helpers.js';
import { SEVERITIES } from '../services/mockData.js';

export default function History() {
  const { data, loading, error, reload } = useAsync(async () => {
    const [insps, assets] = await Promise.all([api.getInspections(), api.getAssets()]);
    return { insps: insps || [], assets: assets || [] };
  }, []);

  const [q, setQ] = useState('');
  const [selectedAsset, setSelectedAsset] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  const { insps, assets } = data;

  const filteredInsps = insps.filter((i) => {
    const matchesQ = (i.id + ' ' + (i.asset || i.assetId) + ' ' + i.inspector).toLowerCase().includes(q.toLowerCase());
    const matchesAsset = selectedAsset === 'All' || i.assetId === selectedAsset || i.asset === selectedAsset;
    const matchesStatus = statusFilter === 'All' || i.status === statusFilter;
    return matchesQ && matchesAsset && matchesStatus;
  });

  const handleExportCSV = () => {
    downloadCSV(
      'infrascan-inspection-history.csv',
      filteredInsps.map((i) => ({
        InspectionID: i.id,
        Asset: i.asset || i.assetId,
        Date: i.date,
        Inspector: i.inspector,
        Status: i.status,
        Severity: i.severity,
        Defects: i.defects,
      }))
    );
  };

  const handleExportJSON = () => {
    downloadJSON('infrascan-inspection-history.json', filteredInsps);
  };

  return (
    <>
      <PageHead
        title="Inspection History"
        sub="Comprehensive historical archive of completed, pending and assigned structural inspections"
      >
        <Link to="/inspections/new" className="btn">
          <Plus className="h-4 w-4" /> New Inspection
        </Link>
        <Link to="/inspections/progression" className="btn-ghost">
          <TrendingUp className="h-4 w-4" /> Damage Progression
        </Link>
        <button onClick={handleExportCSV} className="btn-ghost">
          <Download className="h-4 w-4" /> Export CSV
        </button>
      </PageHead>

      <Card
        title="Archived & Active Inspections"
        right={
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <input
                className="input w-52 pl-8"
                placeholder="Search ID, asset, inspector…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
            </div>

            <select
              className="input w-44"
              value={selectedAsset}
              onChange={(e) => setSelectedAsset(e.target.value)}
            >
              <option value="All">All Assets</option>
              {assets.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>

            <select
              className="input w-36"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="All">All Statuses</option>
              <option value="Completed">Completed</option>
              <option value="Pending Review">Pending Review</option>
              <option value="In Progress">In Progress</option>
              <option value="Assigned">Assigned</option>
            </select>
          </div>
        }
      >
        {!filteredInsps.length ? (
          <Empty text="No inspections match the selected filters." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th>Inspection ID</th>
                  <th>Infrastructure Asset</th>
                  <th>Inspection Date</th>
                  <th>Assigned Inspector</th>
                  <th>Status</th>
                  <th>Severity Finding</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredInsps.map((i) => (
                  <tr key={i.id} className="border-t">
                    <td className="font-mono text-xs font-semibold text-steel">
                      <Link to={`/inspections/${i.fullId || i.id}`} className="hover:underline">
                        {i.id}
                      </Link>
                    </td>
                    <td className="font-medium text-ink">{i.asset || i.assetId}</td>
                    <td className="text-slate-600">{i.date}</td>
                    <td>{i.inspector}</td>
                    <td>
                      <Badge cls={STATUS_CLS[i.status] || 'bg-slate-100 text-slate-700'}>
                        {i.status}
                      </Badge>
                    </td>
                    <td>
                      <Badge cls={SEV_CLS[i.severity] || 'bg-amber-100 text-amber-800'}>
                        {i.severity || 'Moderate Damage'}
                      </Badge>
                    </td>
                    <td>
                      <Link
                        to={i.status === 'Assigned' ? '/upload' : `/results/${i.fullId || i.id}`}
                        className="text-xs text-steel underline font-medium"
                      >
                        {i.status === 'Assigned' ? 'Upload Images' : 'View Analysis'}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
