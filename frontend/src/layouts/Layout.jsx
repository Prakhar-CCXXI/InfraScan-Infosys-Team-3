import { useState } from 'react';
import { NavLink, Outlet, Link } from 'react-router-dom';
import {
  LayoutDashboard,
  Building2,
  ClipboardList,
  Upload,
  ScanSearch,
  History,
  TrendingUp,
  MapPin,
  Wrench,
  FileText,
  BarChart3,
  Cpu,
  Users,
  ShieldCheck,
  SlidersHorizontal,
  Bell,
  Menu,
  LogOut,
  HardHat,
  PlusCircle,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth.jsx';
import { useAsync } from '../hooks/useAsync.js';
import { api, isMock, ROLE_MAP } from '../services/api.js';

const ALL = [
  'Civil Engineer',
  'Infrastructure Inspector',
  'Maintenance Engineer',
  'Infrastructure Manager',
  'Administrator',
];

const NAV = [
  ['/dashboard', 'Dashboard', LayoutDashboard, ALL],
  ['/assets', 'Infrastructure Assets', Building2, ALL],
  ['/inspections', 'Inspections', ClipboardList, ALL],
  ['/inspections/new', 'New Inspection', PlusCircle, ['Civil Engineer', 'Infrastructure Inspector', 'Administrator']],
  ['/upload', 'Image Upload', Upload, ['Civil Engineer', 'Infrastructure Inspector', 'Administrator']],
  ['/results', 'Damage Analysis', ScanSearch, ['Civil Engineer', 'Infrastructure Inspector', 'Administrator']],
  ['/history', 'Inspection History', History, ALL],
  ['/inspections/progression', 'Damage Progression', TrendingUp, ALL],
  ['/map', 'Damage Map', MapPin, ALL],
  ['/maintenance', 'Maintenance', Wrench, ['Civil Engineer', 'Maintenance Engineer', 'Infrastructure Manager', 'Administrator']],
  ['/reports', 'Reports', FileText, ALL],
  ['/analytics', 'Analytics', BarChart3, ALL],
  ['/models', 'Model Management', Cpu, ['Civil Engineer', 'Administrator']],
  ['/users', 'User Management', Users, ['Administrator']],
  ['/audit', 'Audit Logs', ShieldCheck, ['Administrator', 'Infrastructure Manager']],
  ['/roles', 'Roles & RBAC', SlidersHorizontal, ALL],
];

export default function Layout() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const { data: notes } = useAsync(api.getNotifications, []);
  const unread = (notes || []).filter((n) => !n.read).length;

  const userRole = ROLE_MAP[user?.role] || user?.role || 'Civil Engineer';

  return (
    <div className="flex min-h-screen bg-concrete">
      {/* Sidebar navigation */}
      <aside
        className={`fixed inset-y-0 z-30 w-64 shrink-0 bg-ink p-3 text-slate-200 transition-transform md:static md:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        } overflow-y-auto`}
      >
        <div className="mb-5 flex items-center gap-2 px-2 py-2 text-lg font-bold text-white">
          <HardHat className="text-survey" />
          InfraScan
        </div>

        <nav className="space-y-1">
          {NAV.filter((n) => n[3].includes(userRole)).map(([to, label, Icon]) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-steel text-white shadow-xs'
                    : 'text-slate-300 hover:bg-white/10 hover:text-white'
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-20 bg-black/40 md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Main Content Area */}
      <div className="min-w-0 flex-1 flex flex-col">
        <header className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-2.5">
          <button
            className="md:hidden text-slate-600 hover:text-ink"
            aria-label="Open menu"
            onClick={() => setOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </button>

          <span className="hidden text-xs font-medium text-slate-500 sm:block">
            AI-Powered Crack &amp; Damage Assessment for Civil Infrastructure
          </span>

          <div className="ml-auto flex items-center gap-4">
            <Link
              to="/notifications"
              aria-label="Notifications"
              className="relative p-1 text-slate-600 hover:text-ink"
            >
              <Bell className="h-5 w-5" />
              {unread > 0 && (
                <span className="absolute -right-1 -top-1 rounded-full bg-red-600 px-1.5 text-[10px] font-bold text-white">
                  {unread}
                </span>
              )}
            </Link>

            <Link
              to="/profile"
              className="text-right text-xs leading-tight hover:underline"
            >
              <div className="font-semibold text-ink">{user?.name}</div>
              <div className="text-slate-500">{userRole}</div>
            </Link>

            <button
              onClick={logout}
              className="btn-ghost p-1.5 text-slate-600 hover:text-red-700"
              aria-label="Log out"
              title="Sign Out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </header>

        <div className="hazard" />

        {isMock && (
          <div className="bg-survey/20 px-4 py-1 text-xs text-amber-900 border-b border-survey/30">
            Demo mode: sample data and demo sign-in. Backend fallback active.
          </div>
        )}

        <main className="p-4 md:p-6 flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
