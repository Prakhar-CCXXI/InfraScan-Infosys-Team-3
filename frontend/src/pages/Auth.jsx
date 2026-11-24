import { useState } from 'react';
import { Link, useNavigate, Navigate } from 'react-router-dom';
import { Eye, EyeOff, HardHat, ShieldCheck, Key } from 'lucide-react';
import { useAuth } from '../hooks/useAuth.jsx';
import { Field } from '../components/ui.jsx';
import { ROLES } from '../services/mockData.js';
import Hero from '../components/Hero.jsx';

export default function Auth({ mode }) {
  const reg = mode === 'register';
  const { user, login, register } = useAuth();
  const nav = useNavigate();

  const [f, setF] = useState({
    id: '1',
    name: '',
    email: '',
    password: '',
    confirm: '',
    role: ROLES[1],
    department: 'Civil Infrastructure Dept',
  });

  const [show, setShow] = useState(false);
  const [err, setErr] = useState({});
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/dashboard" replace />;

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const validate = () => {
    const e = {};
    if (reg && !f.name.trim()) e.name = 'Full name is required.';
    if (!f.email) e.email = 'Email is required.';
    else if (!/^\S+@\S+\.\S+$/.test(f.email)) e.email = 'Enter a valid email address.';
    if (!f.password) e.password = 'Password is required.';
    else if (f.password.length < 6) e.password = 'Use at least 6 characters.';
    if (reg && f.confirm !== f.password) e.confirm = 'Passwords do not match.';
    return e;
  };

  const submit = async (ev) => {
    ev.preventDefault();
    setMsg('');
    const e = validate();
    setErr(e);
    if (Object.keys(e).length) return;
    setBusy(true);
    try {
      if (reg) {
        await register({ ...f, full_name: f.name });
      } else {
        await login({ email: f.email, password: f.password, id: Number(f.id) || 1, role: f.role });
      }
      nav('/dashboard');
    } catch (x) {
      setMsg(x.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setBusy(false);
    }
  };

  const fillAdmin = () => {
    setF({
      ...f,
      email: 'admin@infrascan.gov',
      password: 'Admin@Secure2026!',
      role: 'Administrator',
    });
  };

  const fillDemo = () => {
    setF({
      ...f,
      email: 'demo@infrascan.test',
      password: 'demo123',
      role: 'Infrastructure Inspector',
    });
  };

  return (
    <div className="flex min-h-screen bg-ink">
      <Hero />
      <div className="flex flex-1 items-center justify-center p-4">
        <form onSubmit={submit} noValidate className="w-full max-w-md space-y-3 rounded-lg bg-white p-6 shadow-xl">
          <div className="flex items-center gap-2 text-xl font-bold text-ink">
            <HardHat className="text-steel" />
            InfraScan
          </div>
          <p className="text-sm text-slate-500">
            {reg ? 'Create your operational account' : 'Sign in to access AI inspection platform'}
          </p>

          {!reg && (
            <div className="space-y-1 rounded border border-survey/40 bg-survey/10 p-2 text-xs text-amber-950">
              <div className="font-semibold text-amber-900">Quick Login Profiles:</div>
              <div className="flex flex-wrap gap-2 pt-1">
                <button
                  type="button"
                  onClick={fillAdmin}
                  className="rounded bg-white px-2 py-0.5 border border-slate-300 font-medium hover:bg-slate-50 text-[11px]"
                >
                  🔑 Backend Admin (admin@infrascan.gov)
                </button>
                <button
                  type="button"
                  onClick={fillDemo}
                  className="rounded bg-white px-2 py-0.5 border border-slate-300 font-medium hover:bg-slate-50 text-[11px]"
                >
                  🧪 Demo Inspector (demo@infrascan.test)
                </button>
              </div>
            </div>
          )}

          {msg && (
            <p role="alert" className="rounded bg-red-50 p-2.5 text-sm text-red-700 border border-red-200">
              {msg}
            </p>
          )}

          {reg && (
            <Field label="Full Name" error={err.name}>
              <input
                className="input"
                placeholder="e.g. Priya Sharma"
                value={f.name}
                onChange={set('name')}
              />
            </Field>
          )}

          <Field label="Email Address" error={err.email}>
            <input
              className="input"
              type="email"
              placeholder="name@infrascan.gov"
              value={f.email}
              onChange={set('email')}
            />
          </Field>

          <Field label="Password" error={err.password}>
            <div className="relative">
              <input
                className="input pr-10"
                type={show ? 'text' : 'password'}
                placeholder="••••••••"
                value={f.password}
                onChange={set('password')}
              />
              <button
                type="button"
                onClick={() => setShow(!show)}
                aria-label="Toggle password visibility"
                className="absolute right-2 top-2 text-slate-500 hover:text-slate-800"
              >
                {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </Field>

          {reg && (
            <Field label="Confirm Password" error={err.confirm}>
              <input
                className="input"
                type={show ? 'text' : 'password'}
                value={f.confirm}
                onChange={set('confirm')}
              />
            </Field>
          )}

          <Field label="Role Designation">
            <select className="input" value={f.role} onChange={set('role')}>
              {ROLES.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
          </Field>

          {reg && (
            <Field label="Department / Operational Unit">
              <input
                className="input"
                placeholder="Highways and Bridges Division"
                value={f.department}
                onChange={set('department')}
              />
            </Field>
          )}

          <button className="btn w-full justify-center" disabled={busy}>
            {busy ? 'Verifying Credentials…' : reg ? 'Create Account' : 'Sign In'}
          </button>

          <div className="flex items-center justify-between pt-1 text-xs text-slate-500">
            <Link to="/roles" className="hover:underline text-steel">
              View Role Matrix
            </Link>
            <div>
              {reg ? (
                <>
                  Have an account?{' '}
                  <Link className="text-steel underline font-medium" to="/login">
                    Sign in
                  </Link>
                </>
              ) : (
                <>
                  Need an account?{' '}
                  <Link className="text-steel underline font-medium" to="/register">
                    Register
                  </Link>
                </>
              )}
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
