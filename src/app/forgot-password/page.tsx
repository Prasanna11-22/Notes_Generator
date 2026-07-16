'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { GraduationCap, Mail, ArrowLeft, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setLoading(true);

    setTimeout(() => {
      setSubmitted(true);
      setLoading(false);
    }, 1200);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-secondary p-6 transition-colors duration-300">
      <Card className="w-full max-w-md shadow-lg rounded-2xl overflow-hidden bg-card border border-border-custom">
        <CardHeader className="text-center pt-8">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm shadow-primary/25 mx-auto mb-4">
            <GraduationCap className="h-6 w-6" />
          </div>
          <CardTitle className="text-xl font-bold font-heading text-primary">Recover Password</CardTitle>
          <CardDescription className="text-xs text-muted-custom">
            Enter your email and we'll send you recovery details.
          </CardDescription>
        </CardHeader>

        <CardContent className="px-8 pb-8">
          {submitted ? (
            <div className="text-center space-y-4 py-4">
              <div className="mx-auto h-12 w-12 bg-green-500/10 text-green-600 dark:text-green-400 flex items-center justify-center rounded-full">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <h3 className="font-heading font-semibold text-base">Check Your Inbox</h3>
              <p className="text-xs text-muted-custom leading-relaxed">
                We've sent recovery instructions to <strong>{email}</strong>. Please check your spam folder if you do not receive it shortly.
              </p>
              <div className="pt-4">
                <Link href="/login">
                  <Button variant="outline" className="w-full">
                    <ArrowLeft className="h-4 w-4 mr-2" /> Back to Sign In
                  </Button>
                </Link>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-custom">Academic Email Address</label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-muted-custom/60" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-10.5 pr-4 py-3 text-sm rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all placeholder:text-muted-custom/50"
                    placeholder="name@university.edu"
                    required
                  />
                </div>
              </div>

              <Button type="submit" loading={loading} className="w-full">
                Send Recovery Instructions
              </Button>

              <div className="text-center pt-2">
                <Link
                  href="/login"
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline"
                >
                  <ArrowLeft className="h-3.5 w-3.5" /> Back to Sign In
                </Link>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
