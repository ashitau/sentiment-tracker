import { useState, useEffect, useCallback } from "react";
import axios from "axios";

const SESSION_KEY = "et_tracker_session";
const EMAIL_KEY = "et_tracker_email";

interface AuthState {
  token: string | null;
  email: string | null;
  status: "checking" | "authenticated" | "unauthenticated";
}

export function useAuth() {
  const [auth, setAuth] = useState<AuthState>({ token: null, email: null, status: "checking" });

  // On mount, validate stored token
  useEffect(() => {
    const token = localStorage.getItem(SESSION_KEY);
    const email = localStorage.getItem(EMAIL_KEY);
    if (!token || !email) {
      setAuth({ token: null, email: null, status: "unauthenticated" });
      return;
    }
    // Quick /auth/me check to confirm token is still valid
    axios
      .get("/auth/me", { headers: { Authorization: `Bearer ${token}` } })
      .then(() => setAuth({ token, email, status: "authenticated" }))
      .catch(() => {
        localStorage.removeItem(SESSION_KEY);
        localStorage.removeItem(EMAIL_KEY);
        setAuth({ token: null, email: null, status: "unauthenticated" });
      });
  }, []);

  const requestLink = useCallback(async (email: string): Promise<string> => {
    await axios.post("/auth/request", { email });
    return "Check your inbox — link expires in 15 minutes.";
  }, []);

  const verifyToken = useCallback(async (token: string): Promise<boolean> => {
    try {
      const { data } = await axios.get(`/auth/verify?token=${token}`);
      localStorage.setItem(SESSION_KEY, data.session_token);
      localStorage.setItem(EMAIL_KEY, data.email);
      setAuth({ token: data.session_token, email: data.email, status: "authenticated" });
      return true;
    } catch {
      return false;
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem(EMAIL_KEY);
    setAuth({ token: null, email: null, status: "unauthenticated" });
  }, []);

  // Inject token into all axios requests automatically
  useEffect(() => {
    const id = axios.interceptors.request.use(config => {
      const token = localStorage.getItem(SESSION_KEY);
      if (token) config.headers.Authorization = `Bearer ${token}`;
      return config;
    });
    return () => axios.interceptors.request.eject(id);
  }, []);

  return { ...auth, requestLink, verifyToken, logout };
}
