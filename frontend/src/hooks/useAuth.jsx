import { createContext, useContext, useState } from 'react';
import { api, ROLE_MAP } from '../services/api.js';

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('infrascan_user');
      if (saved) {
        const u = JSON.parse(saved);
        return {
          ...u,
          name: u.full_name || u.name || u.email?.split('@')[0] || 'User',
          role: ROLE_MAP[u.role] || u.role || 'Civil Engineer',
        };
      }
      return null;
    } catch {
      return null;
    }
  });

  const finish = (data) => {
    if (!data) return;
    const token = data.access_token || data.token;
    const rawUser = data.user || {};
    const u = {
      ...rawUser,
      name: rawUser.full_name || rawUser.name || rawUser.email?.split('@')[0] || 'User',
      role: ROLE_MAP[rawUser.role] || rawUser.role || 'Civil Engineer',
      email: rawUser.email || '',
    };
    if (token) localStorage.setItem('infrascan_token', token);
    localStorage.setItem('infrascan_user', JSON.stringify(u));
    setUser(u);
  };

  const login = async (credentials) => {
    const res = await api.login(credentials);
    finish(res);
    return res;
  };

  const register = async (userData) => {
    const res = await api.register(userData);
    finish(res);
    return res;
  };

  const logout = () => {
    localStorage.removeItem('infrascan_token');
    localStorage.removeItem('infrascan_user');
    setUser(null);
  };

  const updateProfile = (p) => {
    const u = { ...user, ...p };
    localStorage.setItem('infrascan_user', JSON.stringify(u));
    setUser(u);
  };

  const setRole = (r) => {
    const u = { ...user, role: ROLE_MAP[r] || r };
    localStorage.setItem('infrascan_user', JSON.stringify(u));
    setUser(u);
  };

  return (
    <Ctx.Provider value={{ user, login, register, logout, updateProfile, setRole }}>
      {children}
    </Ctx.Provider>
  );
}
