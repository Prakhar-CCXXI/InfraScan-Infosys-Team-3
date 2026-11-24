import { useState } from 'react';
import { UserPlus, Search, ShieldCheck, CheckCircle2, UserX, AlertCircle } from 'lucide-react';
import { useAsync } from '../hooks/useAsync.js';
import { api } from '../services/api.js';
import { Card, Loading, ErrorBox, PageHead, Modal, Field, Badge } from '../components/ui.jsx';
import { ROLES } from '../services/mockData.js';

export default function Users() {
  const { data: users, loading, error, reload } = useAsync(api.getAdminUsers, []);
  const [q, setQ] = useState('');
  const [roleFilter, setRoleFilter] = useState('All');
  const [openModal, setOpenModal] = useState(false);
  const [feedback, setFeedback] = useState({ msg: '', type: 'info' });
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    role: 'Infrastructure Inspector',
    department: 'Civil Infrastructure Dept',
  });
  const [formErr, setFormErr] = useState({});

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;

  const filtered = (users || []).filter((u) => {
    const matchesQ = (u.name + ' ' + u.email).toLowerCase().includes(q.toLowerCase());
    const matchesRole = roleFilter === 'All' || u.role === roleFilter;
    return matchesQ && matchesRole;
  });

  const handleRoleChange = async (userId, newRole) => {
    try {
      await api.updateUserRole(userId, newRole);
      setFeedback({ msg: `Updated user role to ${newRole}.`, type: 'success' });
      reload();
    } catch (err) {
      setFeedback({ msg: `Failed to update role: ${err.message}`, type: 'error' });
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    const errors = {};
    if (!form.name.trim()) errors.name = 'Full name is required.';
    if (!form.email.trim() || !/^\S+@\S+\.\S+$/.test(form.email)) errors.email = 'Valid email is required.';
    if (!form.password || form.password.length < 6) errors.password = 'Minimum 6 characters.';

    setFormErr(errors);
    if (Object.keys(errors).length) return;

    try {
      await api.createUser(form);
      setFeedback({ msg: `User "${form.name}" created successfully.`, type: 'success' });
      setOpenModal(false);
      setForm({ name: '', email: '', password: '', role: 'Infrastructure Inspector', department: 'Civil Infrastructure Dept' });
      reload();
    } catch (err) {
      setFeedback({ msg: `Failed to create user: ${err.message}`, type: 'error' });
    }
  };

  return (
    <>
      <PageHead
        title="User Management"
        sub="Manage system personnel, assign RBAC roles and control access authorizations"
      >
        <button onClick={() => setOpenModal(true)} className="btn">
          <UserPlus className="h-4 w-4" /> Add User
        </button>
      </PageHead>

      {feedback.msg && (
        <div
          role="alert"
          className={`mb-4 flex items-center justify-between rounded-md p-3 text-sm ${
            feedback.type === 'error'
              ? 'border border-red-200 bg-red-50 text-red-800'
              : 'border border-emerald-200 bg-emerald-50 text-emerald-800'
          }`}
        >
          <span>{feedback.msg}</span>
          <button
            onClick={() => setFeedback({ msg: '', type: 'info' })}
            className="text-xs font-semibold hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      <Card
        title="Registered Personnel"
        right={
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <input
                className="input w-56 pl-8"
                placeholder="Search name or email…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
            </div>
            <select
              className="input w-48"
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
            >
              <option value="All">All Roles</option>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
        }
      >
        {!filtered.length ? (
          <p className="py-8 text-center text-sm text-slate-500">No users match your filters.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Current Role</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((u) => (
                  <tr key={u.id} className="border-t">
                    <td className="font-medium text-ink">{u.name}</td>
                    <td className="text-slate-600">{u.email}</td>
                    <td>
                      <select
                        className="input w-auto py-1 text-xs"
                        value={u.role}
                        onChange={(e) => handleRoleChange(u.id, e.target.value)}
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r}>
                            {r}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <Badge
                        cls={
                          u.status === 'Active'
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-slate-100 text-slate-700'
                        }
                      >
                        {u.status || 'Active'}
                      </Badge>
                    </td>
                    <td>
                      <button
                        onClick={() =>
                          handleRoleChange(
                            u.id,
                            u.role === 'Administrator' ? 'Civil Engineer' : 'Administrator'
                          )
                        }
                        className="btn-ghost py-1 text-xs"
                      >
                        {u.role === 'Administrator' ? 'Revoke Admin' : 'Make Admin'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {openModal && (
        <Modal title="Register New User" onClose={() => setOpenModal(false)}>
          <form onSubmit={handleCreateUser} className="space-y-3">
            <Field label="Full Name" error={formErr.name}>
              <input
                className="input"
                placeholder="e.g. David Miller"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </Field>
            <Field label="Email Address" error={formErr.email}>
              <input
                className="input"
                type="email"
                placeholder="e.g. david.miller@infrascan.gov"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </Field>
            <Field label="Initial Password" error={formErr.password}>
              <input
                className="input"
                type="password"
                placeholder="Minimum 6 characters"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
            </Field>
            <Field label="Assigned Role">
              <select
                className="input"
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Department">
              <input
                className="input"
                placeholder="e.g. Highways and Bridges Division"
                value={form.department}
                onChange={(e) => setForm({ ...form, department: e.target.value })}
              />
            </Field>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="btn-ghost"
                onClick={() => setOpenModal(false)}
              >
                Cancel
              </button>
              <button className="btn">Create Account</button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
