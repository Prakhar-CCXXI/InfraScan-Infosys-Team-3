import { useState } from 'react';
import { ShieldCheck, UserCheck, HardHat, Wrench, Building2, UserCog, CheckCircle } from 'lucide-react';
import { useAuth } from '../hooks/useAuth.jsx';
import { Card, PageHead, Badge } from '../components/ui.jsx';
import { ROLES } from '../services/mockData.js';

export default function Roles() {
  const { user, setRole } = useAuth();
  const [selectedRole, setSelectedRole] = useState(user?.role || 'Civil Engineer');
  const [savedMsg, setSavedMsg] = useState(false);

  const roleDetails = [
    {
      role: 'Infrastructure Inspector',
      icon: HardHat,
      color: 'border-l-amber-500',
      description:
        'Conducts field surveys, captures on-site photographs of cracks and surface distress, tags asset locations, and uploads visual data for AI analysis.',
      permissions: [
        'Upload high-resolution inspection imagery',
        'Record field observations and camera orientations',
        'View assigned inspection schedules',
        'Flag urgent hazards for engineer review',
      ],
    },
    {
      role: 'Civil Engineer',
      icon: UserCheck,
      color: 'border-l-steel',
      description:
        'Validates AI damage segmentations, reviews crack width/length measurements, assesses structural integrity impacts, and confirms engineering recommendations.',
      permissions: [
        'Review AI crack segmentation and confidence masks',
        'Confirm or adjust severity classifications',
        'Request structural follow-up or core sampling',
        'View technical damage progression analytics',
        'Inspect and configure deployed AI models',
      ],
    },
    {
      role: 'Maintenance Engineer',
      icon: Wrench,
      color: 'border-l-emerald-600',
      description:
        'Executes structural repairs, plans crack injection, resurfacing, joint replacement, and updates maintenance task statuses and remediation logs.',
      permissions: [
        'Manage maintenance task queue and work orders',
        'Update task completion status (In Progress / Done)',
        'Schedule follow-up physical inspections',
        'View asset historical repair log',
      ],
    },
    {
      role: 'Infrastructure Manager',
      icon: Building2,
      color: 'border-l-indigo-600',
      description:
        'Oversees regional infrastructure assets, tracks safety trends across bridges and tunnels, evaluates critical damage alerts, and generates executive reports.',
      permissions: [
        'Regional asset condition overview and risk heatmaps',
        'Export compliance reports in PDF, CSV, and JSON',
        'Monitor severe damage notifications and escalations',
        'Inspect operational audit logs',
      ],
    },
    {
      role: 'Administrator',
      icon: UserCog,
      color: 'border-l-red-600',
      description:
        'Full administrative authority over platform configuration, user account creation, RBAC authorization role assignments, and security audit logs.',
      permissions: [
        'User management and RBAC role assignment',
        'AI model deployment to production and benchmark tracking',
        'Review complete system security audit logs',
        'Full read and write access across all modules',
      ],
    },
  ];

  const handleApplyRole = (r) => {
    setSelectedRole(r);
    setRole(r);
    setSavedMsg(true);
    setTimeout(() => setSavedMsg(false), 3000);
  };

  const matrix = [
    { feature: 'Dashboard & Asset Overview', inspector: true, civil: true, maint: true, mgr: true, admin: true },
    { feature: 'Infrastructure Asset Directory', inspector: false, civil: true, maint: true, mgr: true, admin: true },
    { feature: 'Image Upload & Field Capture', inspector: true, civil: true, maint: false, mgr: false, admin: true },
    { feature: 'AI Damage Analysis & Review', inspector: true, civil: true, maint: false, mgr: false, admin: true },
    { feature: 'Damage Progression & Map', inspector: true, civil: true, maint: true, mgr: true, admin: true },
    { feature: 'Maintenance Work Orders', inspector: false, civil: true, maint: true, mgr: true, admin: true },
    { feature: 'Reports & Data Exports', inspector: true, civil: true, maint: true, mgr: true, admin: true },
    { feature: 'Analytics Dashboard', inspector: true, civil: true, maint: true, mgr: true, admin: true },
    { feature: 'AI Model Registry & Deploy', inspector: false, civil: true, maint: false, mgr: false, admin: true },
    { feature: 'User Management & Roles', inspector: false, civil: false, maint: false, mgr: false, admin: true },
    { feature: 'System Audit Logs', inspector: false, civil: false, maint: false, mgr: true, admin: true },
  ];

  return (
    <>
      <PageHead
        title="Role & Permission Reference"
        sub="Role-Based Access Control (RBAC) security framework and responsibility matrix"
      >
        <span className="text-xs text-slate-500">
          Currently logged in as: <b className="text-ink">{user?.name}</b> ({user?.role})
        </span>
      </PageHead>

      {savedMsg && (
        <div className="mb-4 flex items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
          <CheckCircle className="h-4 w-4 shrink-0" />
          Active role switched to <b>{user?.role}</b> for this session. Navigation and feature access updated.
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {roleDetails.map((r) => {
          const Icon = r.icon;
          const isCurrent = user?.role === r.role;
          return (
            <div
              key={r.role}
              className={`rounded-lg border bg-white p-4 transition-all border-l-4 ${r.color} ${
                isCurrent ? 'ring-2 ring-steel shadow-md' : 'border-slate-200'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Icon className="h-5 w-5 text-steel" />
                  <h3 className="font-semibold text-ink">{r.role}</h3>
                </div>
                {isCurrent ? (
                  <span className="rounded-full bg-steel px-2.5 py-0.5 text-xs font-semibold text-white">
                    Current Active Role
                  </span>
                ) : (
                  <button
                    onClick={() => handleApplyRole(r.role)}
                    className="btn-ghost py-1 text-xs"
                  >
                    Switch to Role
                  </button>
                )}
              </div>
              <p className="mt-2 text-sm text-slate-600">{r.description}</p>
              <div className="mt-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Key Permissions:
                </h4>
                <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-slate-600">
                  {r.permissions.map((p) => (
                    <li key={p}>{p}</li>
                  ))}
                </ul>
              </div>
            </div>
          );
        })}
      </div>

      <Card title="RBAC Authorization Matrix Across Features" className="mt-6">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b">
                <th className="py-2 text-left font-semibold">Feature / Module</th>
                <th className="text-center font-semibold">Inspector</th>
                <th className="text-center font-semibold">Civil Eng.</th>
                <th className="text-center font-semibold">Maint. Eng.</th>
                <th className="text-center font-semibold">Infra Mgr.</th>
                <th className="text-center font-semibold">Admin</th>
              </tr>
            </thead>
            <tbody>
              {matrix.map((row) => (
                <tr key={row.feature} className="border-t">
                  <td className="py-2 font-medium text-ink">{row.feature}</td>
                  <td className="text-center">{row.inspector ? '✅' : '—'}</td>
                  <td className="text-center">{row.civil ? '✅' : '—'}</td>
                  <td className="text-center">{row.maint ? '✅' : '—'}</td>
                  <td className="text-center">{row.mgr ? '✅' : '—'}</td>
                  <td className="text-center">{row.admin ? '✅' : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
