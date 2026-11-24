import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowRight, ClipboardList, ShieldAlert, CheckCircle2 } from 'lucide-react';
import { useAsync } from '../hooks/useAsync.js';
import { api } from '../services/api.js';
import { Card, Loading, ErrorBox, PageHead, Field } from '../components/ui.jsx';

export default function CreateInspection() {
  const nav = useNavigate();
  const { data, loading, error, reload } = useAsync(async () => {
    const [assets, users] = await Promise.all([api.getAssets(), api.getUsers()]);
    return { assets: assets || [], users: users || [] };
  }, []);

  const [form, setForm] = useState({
    assetId: '',
    inspector: '',
    date: new Date().toISOString().slice(0, 10),
    time: '09:00',
    priority: 'Medium Priority',
    team: 'North Zone Inspection Team',
    description: '',
  });

  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState('');

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  const { assets, users } = data;
  const inspectors = users.filter((u) => u.role === 'Infrastructure Inspector' || u.role === 'Civil Engineer');

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const validate = () => {
    const errs = {};
    if (!form.assetId && assets.length) form.assetId = assets[0].id;
    if (!form.assetId) errs.assetId = 'Please select a target infrastructure asset.';
    if (!form.inspector.trim()) errs.inspector = 'Inspector name or assignment is required.';
    if (!form.date) errs.date = 'Inspection date is required.';
    if (form.description.trim().length < 5) errs.description = 'Provide a brief scope or description (min 5 chars).';
    return errs;
  };

  const handleNext = async (e) => {
    e.preventDefault();
    setSubmitError('');
    const errs = validate();
    setErrors(errs);
    if (Object.keys(errs).length) return;

    setBusy(true);
    try {
      // Store draft for upload step
      localStorage.setItem('is_draft', JSON.stringify(form));
      // Call backend to create initial inspection record
      await api.createInspection({
        assetId: form.assetId,
        date: form.date,
        inspector: form.inspector,
        description: form.description,
        priority: form.priority,
      });
      // Navigate to Step 2 (Upload)
      nav('/upload');
    } catch (err) {
      setSubmitError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHead
        title="Schedule Inspection (Step 1 of 2)"
        sub="Specify target civil infrastructure, inspector assignment, and inspection objectives"
      >
        <Link to="/inspections" className="btn-ghost">
          Back to Inspections
        </Link>
      </PageHead>

      <div className="mx-auto max-w-2xl">
        <Card title="Inspection Specifications">
          {submitError && <ErrorBox message={submitError} />}
          <form onSubmit={handleNext} className="mt-3 space-y-4">
            <Field label="Infrastructure Asset" error={errors.assetId}>
              <select
                className="input"
                value={form.assetId || (assets[0]?.id || '')}
                onChange={set('assetId')}
              >
                {assets.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name} ({a.type}) · {a.location}
                  </option>
                ))}
              </select>
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Assigned Inspector" error={errors.inspector}>
                <input
                  className="input"
                  placeholder="e.g. R. Kumar"
                  value={form.inspector}
                  onChange={set('inspector')}
                  list="inspectors-list"
                />
                <datalist id="inspectors-list">
                  {inspectors.map((u) => (
                    <option key={u.id || u.name} value={u.name} />
                  ))}
                </datalist>
              </Field>

              <Field label="Assigned Team">
                <select className="input" value={form.team} onChange={set('team')}>
                  <option>North Zone Inspection Team</option>
                  <option>Metro Structures Team</option>
                  <option>Remote Asset & Drone Team</option>
                  <option>Emergency Response Division</option>
                </select>
              </Field>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Inspection Date" error={errors.date}>
                <input
                  type="date"
                  className="input"
                  value={form.date}
                  onChange={set('date')}
                />
              </Field>

              <Field label="Scheduled Time">
                <input
                  type="time"
                  className="input"
                  value={form.time}
                  onChange={set('time')}
                />
              </Field>
            </div>

            <Field label="Maintenance & Inspection Priority">
              <select className="input" value={form.priority} onChange={set('priority')}>
                <option>Routine Monitoring</option>
                <option>Low Priority</option>
                <option>Medium Priority</option>
                <option>High Priority</option>
                <option>Urgent Engineering Review</option>
              </select>
            </Field>

            <Field label="Scope & Description" error={errors.description}>
              <textarea
                rows="3"
                className="input"
                placeholder="Describe scope, known defect locations, pier numbers, or special equipment required…"
                value={form.description}
                onChange={set('description')}
              />
            </Field>

            <div className="flex items-center justify-between pt-2">
              <Link to="/inspections" className="btn-ghost">
                Cancel
              </Link>
              <button className="btn" disabled={busy}>
                {busy ? 'Saving Draft…' : 'Proceed to Image Upload →'}
              </button>
            </div>
          </form>
        </Card>
      </div>
    </>
  );
}
