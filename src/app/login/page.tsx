'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/store/useAppStore';
import { useTranslation } from '@/hooks/useTranslation';
import { GraduationCap, Sparkles, Eye, EyeOff, Lock, Mail } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function LoginPage() {
  const router = useRouter();
  const { setUser } = useAppStore();
  const { t } = useTranslation();
  const [email, setEmail] = useState('prasanna.k@academic.edu');
  const [password, setPassword] = useState('password123');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  React.useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('registeredUser');
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          if (parsed && parsed.email) {
            setEmail(parsed.email);
            setPassword(parsed.password || '');
          }
        } catch (e) {
          console.error(e);
        }
      }
    }
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    try {
      e.preventDefault();
      if (!email || !password) {
        setError(t('common.error'));
        return;
      }
      setError('');
      setLoading(true);

      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      
      const res = await fetch(`${API_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const responseData = await res.json();

      if (!res.ok) {
        setLoading(false);
        setError(responseData.message || responseData.detail || 'Login failed. Please verify academic credentials.');
        return;
      }

      const { access_token, refresh_token } = responseData.data;

      // Store JWT token pair in localStorage
      if (typeof window !== 'undefined') {
        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', refresh_token);
      }

      // Fetch verified user profile details from /me
      const profileRes = await fetch(`${API_URL}/api/v1/auth/me`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${access_token}`,
        },
      });

      if (profileRes.ok) {
        const profileData = await profileRes.json();
        const profile = profileData.data;
        setUser({
          loggedIn: true,
          name: profile.full_name,
          email: profile.email,
          institution: profile.institution || '',
          department: profile.department || '',
        });
      } else {
        // Fallback profile
        setUser({
          loggedIn: true,
          email,
          name: 'Faculty Instructor',
          institution: 'Institutional Academy',
          department: 'Academic Department',
        });
      }

      setLoading(false);
      window.location.href = '/dashboard';
    } catch (err: any) {
      setLoading(false);
      setError(err.message || 'Network error occurred during login. Please check server.');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-secondary p-6 transition-colors duration-300">
      {/* Container Card */}
      <Card className="w-full max-w-md shadow-lg rounded-2xl overflow-hidden bg-card border border-border-custom">
        <CardHeader className="text-center pt-8 text-foreground">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm shadow-primary/25 mx-auto mb-4">
            <GraduationCap className="h-6 w-6" />
          </div>
          <CardTitle className="text-xl font-bold font-heading text-primary">{t('login.welcome')}</CardTitle>
          <CardDescription className="text-xs text-muted-custom">
            {t('login.subtitle')}
          </CardDescription>
        </CardHeader>

        <CardContent className="px-8 pb-8 text-foreground">
          {error && (
            <div className="mb-4 p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-600 dark:text-red-400 font-medium">
              {error}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-5">
            {/* Email Field */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-custom">{t('login.email')}</label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-muted-custom/60" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10.5 pr-4 py-3 text-sm rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all placeholder:text-muted-custom/50 text-foreground"
                  placeholder="name@university.edu"
                  required
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <label className="text-xs font-semibold text-muted-custom">{t('login.password')}</label>
                <Link
                  href="/forgot-password"
                  className="text-[11px] font-medium text-primary hover:underline"
                >
                  Forgot Password?
                </Link>
              </div>
              <div className="relative">
                <Lock className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-muted-custom/60" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10.5 pr-10 py-3 text-sm rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all placeholder:text-muted-custom/50 text-foreground"
                  placeholder="••••••••"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-3.5 text-muted-custom hover:text-foreground transition-colors cursor-pointer"
                >
                  {showPassword ? <EyeOff className="h-4.5 w-4.5" /> : <Eye className="h-4.5 w-4.5" />}
                </button>
              </div>
            </div>

            {/* Remember Me */}
            <div className="flex items-center">
              <input
                type="checkbox"
                id="remember"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="h-4 w-4 rounded border-border-custom text-primary focus:ring-primary/20 bg-bg-secondary accent-primary"
              />
              <label htmlFor="remember" className="ml-2.5 text-xs font-medium text-muted-custom select-none cursor-pointer">
                Remember this device
              </label>
            </div>

            {/* Submit */}
            <Button type="submit" loading={loading} className="w-full">
              {t('login.signin')}
            </Button>
          </form>

          {/* Create Account Link */}
          <div className="mt-6 text-center text-xs text-muted-custom">
            {t('login.no_account')}{' '}
            <Link href="/signup" className="font-semibold text-primary hover:underline">
              {t('login.register_here')}
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
