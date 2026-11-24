import { useState } from 'react';
import { Search, Download, Shield, Clock, FileText } from 'lucide-react';
import { useAsync } from '../hooks/useAsync.js';
import { api } from '../services/api.js';
import { Card, Loading, ErrorBox, PageHead, downloadCSV } from '../components/ui.jsx';

export default function AuditLog() {
  const { data: logs, loading, error, reload } = useAsync(api.getAuditLogs, []);
  const [q, setQ] = useState('');
  const [localLogs, setLocalLogs] = useState(null);

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  const displayLogs = localLogs !== null ? localLogs : (logs || []);
  const filtered = displayLogs.filter((l) =>
    (l.user + ' ' + l.action + ' ' + l.target).toLowerCase().includes(q.toLowerCase())
  );

  const handleExport = () => {
    downloadCSV(
      'infrascan-audit-logs.csv',
      filtered.map((l) => ({
        Timestamp: l.time,
        User: l.user,
        Action: l.action,
        Target: l.target,
      }))
    );
  };

  const handleClear = () => {
    setLocalLogs([]);
  };

  return (
    <>
      <PageHead
        title="Audit Logs"
        sub="System-wide audit trail, RBAC authorization activities and security-sensitive events"
      >
        <button onClick={handleExport} className="btn-ghost">
          <Download className="h-4 w-4" /> Export CSV
        </button>
        <button onClick={handleClear} className="btn-ghost">
          Clear Local View
        </button>
      </PageHead>

      <Card
        title="Operational Activity History"
        right={
          <div className="relative">
            <input
              className="input w-64 pl-8"
              placeholder="Filter by action, user or target…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
          </div>
        }
      >
        {!filtered.length ? (
          <p className="py-8 text-center text-sm text-slate-500">No audit logs matching this search filter.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Actor / User</th>
                  <th>Action</th>
                  <th>Target Resource</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((l) => (
                  <tr key={l.id} className="border-t">
                    <td className="whitespace-nowrap font-mono text-xs text-slate-500">
                      {l.time}
                    </td>
                    <td className="font-medium text-ink">{l.user}</td>
                    <td>
                      <span className="font-mono text-xs font-semibold uppercase text-steel">
                        {l.action}
                      </span>
                    </td>
                    <td className="text-slate-600">{l.target}</td>
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
