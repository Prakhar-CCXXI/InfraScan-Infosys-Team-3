import {createContext,useContext,useState} from 'react';
import {api} from '../services/api.js';
const Ctx=createContext(null);
export const useAuth=()=>useContext(Ctx);
export function AuthProvider({children}){
 const [user,setUser]=useState(()=>{try{return JSON.parse(localStorage.getItem('infrascan_user'))}catch{return null}});
 const finish=({token,user})=>{localStorage.setItem('infrascan_token',token);localStorage.setItem('infrascan_user',JSON.stringify(user));setUser(user);};
 const login=async c=>finish(await api.login(c));const register=async u=>finish(await api.register(u));
 const logout=()=>{localStorage.removeItem('infrascan_token');localStorage.removeItem('infrascan_user');setUser(null);};
 const updateProfile=p=>{const u={...user,...p};localStorage.setItem('infrascan_user',JSON.stringify(u));setUser(u);};
 return <Ctx.Provider value={{user,login,register,logout,updateProfile}}>{children}</Ctx.Provider>;}
