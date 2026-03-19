/**
 * context/AuthContext.jsx
 * Global auth state — consumed by every page that needs user info or login check.
 */

import { createContext, useContext, useState, useCallback } from "react";
import { setToken, setUser, clearAuth, getToken, getUser } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setTokenState] = useState(() => getToken());
  const [user,  setUserState]  = useState(() => getUser());

  const login = useCallback((tokenVal, userData) => {
    setToken(tokenVal);
    setUser(userData);
    setTokenState(tokenVal);
    setUserState(userData);
  }, []);

  const logout = useCallback(() => {
    clearAuth();
    setTokenState(null);
    setUserState(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, user, login, logout, isLoggedIn: !!token }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
};
