// Who is signed in, shared with every page.
import { createContext, useContext, useEffect, useState } from "react";
import { SESSION_ENDED, api, getToken, setToken } from "./api";
import { setKeyOwner } from "./keyStore";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUserState] = useState(null);
  // Saved report keys belong to the signed-in account on this device
  const setUser = (next) => { setKeyOwner(next?.id); setUserState(next); };
  const [loading, setLoading] = useState(Boolean(getToken()));
  const [notice, setNotice] = useState(""); // why the user was signed out, shown on the sign-in page

  // The server stopped accepting the login: go back to the sign-in page with a reason, not a page of errors
  useEffect(() => {
    const ended = () => {
      if (!getToken()) return;
      setToken(null);
      setUser(null);
      setNotice("Your session has ended. Please sign in again.");
    };
    window.addEventListener(SESSION_ENDED, ended);
    return () => window.removeEventListener(SESSION_ENDED, ended);
  }, []);

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
    setNotice("");
    setUser(res.user);
  }

  function logout() {
    api("/auth/logout", { method: "POST" }).catch(() => {}); // the token stops working on the server too
    setToken(null);
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, setUser, loading, login, logout, notice }}>{children}</AuthContext.Provider>;
}
