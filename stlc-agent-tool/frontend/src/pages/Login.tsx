import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, User, Lock, Server, CheckCircle, XCircle } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { useAppContext } from '../context/AppContext';

const PASSWORD_POLICY = {
  minLen: 8,
  maxLen: 12,
  // at least 1 uppercase
  hasUpper: (p: string) => /[A-Z]/.test(p),
  // at least 1 digit
  hasDigit: (p: string) => /[0-9]/.test(p),
  // at least 1 allowed special char
  hasSpecial: (p: string) => /[@#$%]/.test(p),
  // only allowed chars: letters, digits, @#$%
  onlyAllowed: (p: string) => /^[A-Za-z0-9@#$%]+$/.test(p),
};

function validatePassword(p: string): string | null {
  if (
    p.length < PASSWORD_POLICY.minLen || 
    p.length > PASSWORD_POLICY.maxLen ||
    !PASSWORD_POLICY.hasUpper(p) ||
    !PASSWORD_POLICY.hasDigit(p) ||
    !PASSWORD_POLICY.hasSpecial(p) ||
    !PASSWORD_POLICY.onlyAllowed(p)
  ) {
    return "Password must have min 8 max 12 char with atleast 1 caps + Alphanumeric + allowed special char (@#$%)";
  }
  return null;
}

function PasswordStrengthHints({ password }: { password: string }) {
  const rules = [
    { label: '8–12 characters', ok: password.length >= 8 && password.length <= 12 },
    { label: 'At least 1 uppercase (A-Z)', ok: PASSWORD_POLICY.hasUpper(password) },
    { label: 'At least 1 digit (0-9)', ok: PASSWORD_POLICY.hasDigit(password) },
    { label: 'At least 1 special char (@#$%)', ok: PASSWORD_POLICY.hasSpecial(password) },
  ];

  return (
    <div className="mt-2 space-y-1 text-xs">
      {rules.map(r => (
        <div key={r.label} className={`flex items-center gap-1.5 ${r.ok ? 'text-green-400' : 'text-secondary'}`}>
          {r.ok
            ? <CheckCircle className="h-3 w-3 shrink-0" />
            : <XCircle className="h-3 w-3 shrink-0" />
          }
          {r.label}
        </div>
      ))}
    </div>
  );
}

export function Login() {
  const { login } = useAppContext();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) return;

    setError('');
    setSuccess('');

    // Client-side password policy validation for registration
    if (isRegistering) {
      const policyError = validatePassword(password);
      if (policyError) {
        setError(policyError);
        return;
      }
    }

    setLoading(true);

    try {
      if (isRegistering) {
        const res = await fetch('/api/auth/register-initial-admin', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password })
        });

        const data = await res.json();
        if (res.ok) {
          setIsRegistering(false);
          setPassword('');
          setSuccess('Admin account created successfully. You may now login.');
        } else {
          setError(data.detail || 'Failed to bootstrap admin');
        }
      } else {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: formData.toString()
        });

        const data = await res.json();
        if (res.ok) {
          const meRes = await fetch('/api/users/me', {
            headers: { 'Authorization': `Bearer ${data.access_token}` }
          });
          const meData = await meRes.json();
          if (meRes.ok) {
            login(data.access_token, meData.username, meData.role_name, meData.assigned_projects);
            navigate('/');
          } else {
            setError('Failed to fetch user profile.');
          }
        } else {
          setError(data.detail || 'Invalid credentials');
        }
      }
    } catch (err) {
      // Backend unreachable — activate Demo Mode with hardcoded credentials
      if (!isRegistering && username === 'admin' && password === 'Changeme@123') {
        const demoToken = 'demo-mode-token';
        login(demoToken, 'admin', 'Admin', ['Test']);
        localStorage.setItem('stlc_demo_mode', 'true');
        navigate('/');
        return;
      }
      setError('Backend unavailable. Use admin / Changeme@123 to enter Demo Mode.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-main flex items-center justify-center p-4">
      <div className="bg-card border border-border rounded-xl p-8 max-w-md w-full shadow-2xl">
        <div className="flex flex-col items-center mb-8">
          <div className="h-12 w-12 bg-primary/20 text-primary rounded-full flex items-center justify-center mb-4">
            <Shield className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold text-primary text-center">STLC Agentic Platform</h1>
          <p className="text-secondary text-sm mt-2 text-center">
            {isRegistering ? 'Bootstrap Initial Admin Account' : 'Secure Database Login'}
          </p>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500 text-red-400 p-3 rounded-md mb-4 text-sm flex items-start gap-2">
            <XCircle className="h-4 w-4 shrink-0 mt-0.5" />
            {error}
          </div>
        )}

        {success && (
          <div className="bg-green-500/10 border border-green-500 text-green-400 p-3 rounded-md mb-4 text-sm flex items-start gap-2">
            <CheckCircle className="h-4 w-4 shrink-0 mt-0.5" />
            {success}
          </div>
        )}

        <form onSubmit={handleAuth} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-secondary mb-1">Username</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <User className="h-4 w-4 text-secondary" />
              </div>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                className="w-full bg-main border border-border rounded-md pl-10 pr-3 py-2 text-primary focus:outline-none focus:border-primary"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-secondary mb-1">Password</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Lock className="h-4 w-4 text-secondary" />
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={isRegistering ? 'Min 8, Max 12 chars' : 'Enter password'}
                className="w-full bg-main border border-border rounded-md pl-10 pr-3 py-2 text-primary focus:outline-none focus:border-primary"
                required
              />
            </div>
            {/* Show live password strength hints only on registration */}
            {isRegistering && password.length > 0 && (
              <PasswordStrengthHints password={password} />
            )}
            {isRegistering && password.length === 0 && (
              <p className="mt-1.5 text-xs text-secondary">
                Password must have min 8 max 12 char with atleast 1 caps + Alphanumeric + allowed special char (@#$%)
              </p>
            )}
          </div>

          <Button type="submit" className="w-full mt-6" disabled={loading}>
            {loading ? 'Processing...' : (isRegistering ? 'Register Admin' : 'Sign In')}
          </Button>
        </form>

        <div className="mt-6 border-t border-border pt-4 text-center">
          <button
            type="button"
            onClick={() => { setIsRegistering(!isRegistering); setError(''); setSuccess(''); setPassword(''); }}
            className="text-primary text-sm hover:underline flex items-center justify-center w-full gap-2"
          >
            <Server className="h-4 w-4" />
            {isRegistering ? 'Back to Login' : 'First Time Setup? Bootstrap Admin'}
          </button>
        </div>
      </div>
    </div>
  );
}
