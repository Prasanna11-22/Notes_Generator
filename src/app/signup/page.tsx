'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/store/useAppStore';
import { useTranslation } from '@/hooks/useTranslation';
import { GraduationCap, User, Building, BookOpen, Mail, Lock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function SignupPage() {
  const router = useRouter();
  const { setUser } = useAppStore();
  const { t } = useTranslation();
  const [name, setName] = useState('');
  const [institution, setInstitution] = useState('');
  const [department, setDepartment] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSignup = async (e: React.FormEvent) => {
    try {
      e.preventDefault();
      if (!name || !institution || !department || !email || !password || !confirmPassword) {
        setError('Please fill in all fields.');
        return;
      }
      if (password !== confirmPassword) {
        setError('Passwords do not match.');
        return;
      }

      // Pre-validate password criteria to match backend UserCreate constraints
      if (password.length < 8) {
        setError('Password must be at least 8 characters long.');
        return;
      }
      if (!/[A-Z]/.test(password)) {
        setError('Password must contain at least one uppercase letter.');
        return;
      }
      if (!/[0-9]/.test(password)) {
        setError('Password must contain at least one digit.');
        return;
      }

      setError('');
      setLoading(true);

      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

      const res = await fetch(`${API_URL}/api/v1/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          full_name: name,
          email: email,
          password: password,
          institution: institution || null,
          department: department || null,
          role: 'faculty',
        }),
      });

      const responseData = await res.json();

      if (!res.ok) {
        setLoading(false);
        setError(responseData.message || responseData.detail || 'Registration failed.');
        return;
      }

      // Automatically log in the user after successful registration
      const loginRes = await fetch(`${API_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const loginData = await loginRes.json();

      if (loginRes.ok) {
        const { access_token, refresh_token } = loginData.data;
        if (typeof window !== 'undefined') {
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', refresh_token);
        }
      }

      setUser({
        loggedIn: true,
        name,
        email,
        institution,
        department,
      });

      setLoading(false);
      window.location.href = '/dashboard';
    } catch (err: any) {
      setLoading(false);
      setError(err.message || 'Network error occurred during registration.');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-secondary p-6 transition-colors duration-300">
      <Card className="w-full max-w-lg shadow-lg rounded-2xl overflow-hidden bg-card border border-border-custom text-foreground">
        <CardHeader className="text-center pt-8">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm shadow-primary/25 mx-auto mb-4">
            <GraduationCap className="h-6 w-6" />
          </div>
          <CardTitle className="text-xl font-bold font-heading text-primary">{t('signup.title')}</CardTitle>
          <CardDescription className="text-xs text-muted-custom">
            {t('signup.subtitle')}
          </CardDescription>
        </CardHeader>

        <CardContent className="px-8 pb-8">
          {error && (
            <div className="mb-4 p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-600 dark:text-red-400 font-medium">
              {error}
            </div>
          )}

          <form onSubmit={handleSignup} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Full Name */}
            <div className="space-y-1.5 sm:col-span-2">
              <label className="text-xs font-semibold text-muted-custom">{t('signup.name')}</label>
              <div className="relative">
                <User className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-muted-custom/60" />
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full pl-10.5 pr-4 py-3 text-sm rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all placeholder:text-muted-custom/50 text-foreground"
                  placeholder="Dr. Jane Smith"
                  required
                />
              </div>
            </div>

            {/* Institution */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-custom">{t('signup.institution')}</label>
              <div className="relative">
                <Building className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-muted-custom/60" />
                <input
                  type="text"
                  value={institution}
                  onChange={(e) => setInstitution(e.target.value)}
                  className="w-full pl-10.5 pr-4 py-3 text-sm rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all placeholder:text-muted-custom/50 text-foreground"
                  placeholder="State University"
                  required
                />
              </div>
            </div>

            {/* Department */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-custom">{t('signup.department')}</label>
              <div className="relative">
                <BookOpen className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-muted-custom/60" />
                <input
                  type="text"
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  className="w-full pl-10.5 pr-4 py-3 text-sm rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all placeholder:text-muted-custom/50 text-foreground"
                  placeholder="Mechanical Eng."
                  required
                />
              </div>
            </div>

            {/* Email */}
            <div className="space-y-1.5 sm:col-span-2">
              <label className="text-xs font-semibold text-muted-custom">{t('signup.email')}</label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-muted-custom/60" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10.5 pr-4 py-3 text-sm rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all placeholder:text-muted-custom/50 text-foreground"
                  placeholder="j.smith@university.edu"
                  required
                />
              </div>
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-custom">{t('signup.password')}</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-muted-custom/60" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10.5 pr-4 py-3 text-sm rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all placeholder:text-muted-custom/50 text-foreground"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            {/* Confirm Password */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-custom">{t('signup.confirm_password')}</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-muted-custom/60" />
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full pl-10.5 pr-4 py-3 text-sm rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all placeholder:text-muted-custom/50 text-foreground"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            <div className="sm:col-span-2 mt-2">
              <Button type="submit" loading={loading} className="w-full">
                {t('signup.register')}
              </Button>
            </div>
          </form>

          <div className="mt-6 text-center text-xs text-muted-custom">
            {t('signup.have_account')}{' '}
            <Link href="/login" className="font-semibold text-primary hover:underline">
              {t('signup.login_here')}
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
