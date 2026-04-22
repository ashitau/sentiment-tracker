import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mail, ArrowRight, CheckCircle, AlertCircle, Loader } from "lucide-react";

interface Props {
  onRequestLink: (email: string) => Promise<string>;
  onVerifyToken: (token: string) => Promise<boolean>;
  verifyTokenFromUrl: string | null;
}

type Stage = "email" | "sent" | "verifying" | "error";

export default function LoginPage({ onRequestLink, onVerifyToken, verifyTokenFromUrl }: Props) {
  const [email, setEmail] = useState("");
  const [stage, setStage] = useState<Stage>("email");
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Auto-verify if token is in the URL
  useEffect(() => {
    if (!verifyTokenFromUrl) return;
    setStage("verifying");
    onVerifyToken(verifyTokenFromUrl).then(ok => {
      if (!ok) {
        setStage("error");
        setMessage("This login link has expired or already been used. Please request a new one.");
      }
      // If ok, the parent will re-render and show the main app
    });
  }, [verifyTokenFromUrl, onVerifyToken]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    setIsLoading(true);
    try {
      const msg = await onRequestLink(email.trim().toLowerCase());
      setMessage(msg);
      setStage("sent");
    } catch {
      setStage("error");
      setMessage("Something went wrong. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-brand-bg flex items-center justify-center p-4">
      {/* Subtle background glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-blue-500/5 rounded-full blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative w-full max-w-sm"
      >
        {/* Logo mark */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 mb-4">
            <div className="w-5 h-5 rounded-full border-2 border-blue-400" />
          </div>
          <h1 className="text-white text-xl font-semibold">ET Now</h1>
          <p className="text-gray-500 text-sm mt-1">Sentiment Tracker</p>
        </div>

        <div className="bg-brand-panel border border-brand-border rounded-2xl p-6">
          <AnimatePresence mode="wait">
            {stage === "email" && (
              <motion.div key="email" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <h2 className="text-white font-medium mb-1">Sign in</h2>
                <p className="text-gray-500 text-sm mb-5">
                  Enter your Times Group email address. We'll send you a one-click login link.
                </p>
                <form onSubmit={handleSubmit} className="flex flex-col gap-3">
                  <div className="relative">
                    <Mail size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                    <input
                      type="email"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      placeholder="you@timesgroup.com"
                      required
                      className="w-full bg-brand-bg border border-brand-border rounded-lg pl-9 pr-4 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 transition-colors"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={isLoading || !email.trim()}
                    className="flex items-center justify-center gap-2 w-full py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
                  >
                    {isLoading ? <Loader size={14} className="animate-spin" /> : <ArrowRight size={14} />}
                    {isLoading ? "Sending…" : "Send login link"}
                  </button>
                </form>
              </motion.div>
            )}

            {stage === "sent" && (
              <motion.div key="sent" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="text-center py-2"
              >
                <CheckCircle size={32} className="text-green-400 mx-auto mb-3" />
                <h2 className="text-white font-medium mb-2">Check your inbox</h2>
                <p className="text-gray-400 text-sm leading-relaxed">{message}</p>
                <p className="text-gray-500 text-xs mt-2">Sent to <span className="text-gray-300">{email}</span></p>
                <button
                  onClick={() => { setStage("email"); setEmail(""); }}
                  className="mt-5 text-xs text-gray-500 hover:text-gray-300 transition-colors"
                >
                  Use a different address
                </button>
              </motion.div>
            )}

            {stage === "verifying" && (
              <motion.div key="verifying" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="text-center py-4"
              >
                <Loader size={28} className="text-blue-400 animate-spin mx-auto mb-3" />
                <p className="text-gray-400 text-sm">Verifying your link…</p>
              </motion.div>
            )}

            {stage === "error" && (
              <motion.div key="error" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="text-center py-2"
              >
                <AlertCircle size={32} className="text-red-400 mx-auto mb-3" />
                <h2 className="text-white font-medium mb-2">Link expired</h2>
                <p className="text-gray-400 text-sm leading-relaxed">{message}</p>
                <button
                  onClick={() => setStage("email")}
                  className="mt-5 flex items-center gap-1.5 mx-auto text-xs text-blue-400 hover:text-blue-300 transition-colors"
                >
                  <ArrowRight size={12} />
                  Request a new link
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <p className="text-center text-gray-600 text-xs mt-5">
          Access restricted to authorised ET Now research team members.
        </p>
      </motion.div>
    </div>
  );
}
