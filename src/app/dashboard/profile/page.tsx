'use client';

import React, { useState } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { User, Building, BookOpen, Mail, Lock, ShieldAlert, CheckCircle2 } from 'lucide-react';

export default function ProfilePage() {
  const { user, setUser } = useAppStore();
  const [name, setName] = useState(user.name);
  const [institution, setInstitution] = useState(user.institution);
  const [department, setDepartment] = useState(user.department);
  const [email, setEmail] = useState(user.email);
  
  const [passCurrent, setPassCurrent] = useState('');
  const [passNew, setPassNew] = useState('');
  const [passConfirm, setPassConfirm] = useState('');

  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [secSuccess, setSecSuccess] = useState(false);

  const handleProfileSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSavedSuccess(false);

    setTimeout(() => {
      setUser({ name, institution, department, email });
      setSaving(false);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    }, 1000);
  };

  const handlePasswordSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSecSuccess(false);
    if (!passCurrent || !passNew || !passConfirm) return;
    if (passNew !== passConfirm) return;

    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      setSecSuccess(true);
      setPassCurrent('');
      setPassNew('');
      setPassConfirm('');
      setTimeout(() => setSecSuccess(false), 3000);
    }, 1000);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div>
        <h2 className="font-heading font-bold text-2xl tracking-tight">Faculty Profile Settings</h2>
        <p className="text-xs text-muted-custom">Manage your academic credentials, departmental context, and security credentials.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Profile form (2/3 columns) */}
        <div className="lg:col-span-2 space-y-8">
          <Card className="border border-border-custom bg-card">
            <CardHeader>
              <CardTitle>Institutional Identity</CardTitle>
              <CardDescription>Update your public faculty credentials and university affiliation.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {savedSuccess && (
                <div className="p-3.5 rounded-xl bg-green-500/10 border border-green-500/20 text-xs text-green-600 dark:text-green-400 font-semibold flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 shrink-0" /> Settings updated successfully!
                </div>
              )}

              <form onSubmit={handleProfileSave} className="space-y-4 text-xs">
                {/* Full Name */}
                <div className="space-y-1.5">
                  <label className="font-semibold text-muted-custom">Full Name</label>
                  <div className="relative">
                    <User className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-muted-custom/60" />
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="w-full pl-10.5 pr-4 py-3 rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all font-medium text-foreground"
                      required
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Institution */}
                  <div className="space-y-1.5">
                    <label className="font-semibold text-muted-custom">University / Institution</label>
                    <div className="relative">
                      <Building className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-muted-custom/60" />
                      <input
                        type="text"
                        value={institution}
                        onChange={(e) => setInstitution(e.target.value)}
                        className="w-full pl-10.5 pr-4 py-3 rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all font-medium text-foreground"
                        required
                      />
                    </div>
                  </div>

                  {/* Department */}
                  <div className="space-y-1.5">
                    <label className="font-semibold text-muted-custom">Department</label>
                    <div className="relative">
                      <BookOpen className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-muted-custom/60" />
                      <input
                        type="text"
                        value={department}
                        onChange={(e) => setDepartment(e.target.value)}
                        className="w-full pl-10.5 pr-4 py-3 rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all font-medium text-foreground"
                        required
                      />
                    </div>
                  </div>
                </div>

                {/* Email */}
                <div className="space-y-1.5">
                  <label className="font-semibold text-muted-custom">Academic Email Address</label>
                  <div className="relative">
                    <Mail className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-muted-custom/60" />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full pl-10.5 pr-4 py-3 rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all font-medium text-foreground"
                      required
                    />
                  </div>
                </div>

                <div className="pt-2">
                  <Button type="submit" loading={saving} className="w-full sm:w-auto text-xs">
                    Save Profile Changes
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Security/Password updates (1/3 columns) */}
        <div className="space-y-8">
          <Card className="border border-border-custom bg-card">
            <CardHeader className="flex flex-row items-center gap-3">
              <div className="h-9 w-9 rounded-xl bg-red-500/10 text-red-600 dark:text-red-500 flex items-center justify-center shrink-0">
                <ShieldAlert className="h-4.5 w-4.5" />
              </div>
              <div>
                <CardTitle>Account Credentials</CardTitle>
                <CardDescription>Update password codes.</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {secSuccess && (
                <div className="p-3.5 rounded-xl bg-green-500/10 border border-green-500/20 text-xs text-green-600 dark:text-green-400 font-semibold flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 shrink-0" /> Password updated!
                </div>
              )}

              <form onSubmit={handlePasswordSave} className="space-y-4 text-xs">
                {/* Current */}
                <div className="space-y-1.5">
                  <label className="font-semibold text-muted-custom">Current Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-muted-custom/60" />
                    <input
                      type="password"
                      value={passCurrent}
                      onChange={(e) => setPassCurrent(e.target.value)}
                      className="w-full pl-10.5 pr-4 py-3 rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all font-medium text-foreground"
                      placeholder="••••••••"
                      required
                    />
                  </div>
                </div>

                {/* New */}
                <div className="space-y-1.5">
                  <label className="font-semibold text-muted-custom">New Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-muted-custom/60" />
                    <input
                      type="password"
                      value={passNew}
                      onChange={(e) => setPassNew(e.target.value)}
                      className="w-full pl-10.5 pr-4 py-3 rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all font-medium text-foreground"
                      placeholder="••••••••"
                      required
                    />
                  </div>
                </div>

                {/* Confirm */}
                <div className="space-y-1.5">
                  <label className="font-semibold text-muted-custom">Confirm Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-3.5 h-4.5 w-4.5 text-muted-custom/60" />
                    <input
                      type="password"
                      value={passConfirm}
                      onChange={(e) => setPassConfirm(e.target.value)}
                      className="w-full pl-10.5 pr-4 py-3 rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all font-medium text-foreground"
                      placeholder="••••••••"
                      required
                    />
                  </div>
                </div>

                <Button type="submit" variant="outline" loading={saving} className="w-full text-xs hover:bg-muted-bg text-foreground">
                  Change Password
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>

      </div>
    </div>
  );
}
