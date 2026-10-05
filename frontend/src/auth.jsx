// Who is signed in, shared with every page.
import { createContext, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "./api";
import { setKeyOwner } from "./keyStore";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUserState] = useState(null);
  // Saved report keys belong to the signed-in account on this device
  const setUser = (next) => { setKeyOwner(next?.id); setUserState(next); };
  const [loading, setLoading] = useState(Boolean(getToken()));

  // On page load, a saved token is checked with the backend; if it's no longer valid, the user signs in again
  useEffect(() => {
    if (!getToken()) return;
    api("/auth/me")
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, []);

  async function login(username, password) {
    const res = await api("/auth/login", { method: "POST", body: { username, password } });
    setToken(res.access_token);
    setUser(res.user);
  }

  function logout() {
    setToken(null);
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, setUser, loading, login, logout }}>{children}</AuthContext.Provider>;
}
