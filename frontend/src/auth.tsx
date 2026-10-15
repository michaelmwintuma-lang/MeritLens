// Who is signed in, shared with every page. The session lives in an httpOnly cookie, so on page load the only way
// to know whether someone is signed in is to ask the server (/auth/me).
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { SESSION_ENDED, auth, type User } from "./api";

interface AuthState {
  user: User | null;
  setUser: (user: User | null) => void;
  loading: boolean;
  login: (username: string, password: string, code?: string) => Promise<void>;
  logout: () => void;
  notice: string; // why the user was signed out, shown on the sign-in page
}

const AuthContext = createContext<AuthState | null>(null);
export const useAuth = () => useContext(AuthContext) as AuthState;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");
  const signedIn = useRef(false);
  signedIn.current = Boolean(user);

  // The server stopped accepting the session: go back to the sign-in page with a reason, not a page of errors
  useEffect(() => {
    const ended = () => {
      if (!signedIn.current) return;
      setUser(null);
      setNotice("Your session has ended. Please sign in again.");
    };
    window.addEventListener(SESSION_ENDED, ended);
    return () => window.removeEventListener(SESSION_ENDED, ended);
  }, []);

  // On page load: is this browser still signed in?
  useEffect(() => {
    auth.me().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false));
  }, []);

  async function login(username: string, password: string, code?: string) {
    const res = await auth.login({ username, password, code: code || null });
    setNotice("");
    setUser(res.user);
  }

  function logout() {
    auth.logout().catch(() => {}); // the session stops working on the server, and the cookie is removed
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, setUser, loading, login, logout, notice }}>{children}</AuthContext.Provider>;
}
