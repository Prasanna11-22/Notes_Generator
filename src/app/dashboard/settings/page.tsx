'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Settings,
  Cpu,
  Globe,
  Bell,
  Trash2,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';

export default function SettingsPage() {
  const [model, setModel] = useState('qwen-2.5-7b');
  const [lang, setLang] = useState('en');
  
  // Notification flags
  const [notifyJob, setNotifyJob] = useState(true);
  const [notifyVerify, setNotifyVerify] = useState(false);
  const [notifyWeekly, setNotifyWeekly] = useState(true);
  
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [purging, setPurging] = useState(false);
  const [purgeSuccess, setPurgeSuccess] = useState(false);

  const handleSave = () => {
    setSaving(true);
    setSavedSuccess(false);

    setTimeout(() => {
      setSaving(false);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    }, 800);
  };

  const handlePurge = () => {
    if (confirm('Are you sure you want to purge all historical generated question records? This action is irreversible.')) {
      setPurging(true);
      setPurgeSuccess(false);
      
      setTimeout(() => {
        setPurging(false);
        setPurgeSuccess(true);
        setTimeout(() => setPurgeSuccess(false), 3000);
      }, 1000);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      
      {/* Header */}
      <div>
        <h2 className="font-heading font-bold text-2xl tracking-tight">System Settings</h2>
        <p className="text-xs text-muted-custom">Configure model connections, UI languages, and notification schedules.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Columns: Config Forms (2/3 columns) */}
        <div className="lg:col-span-2 space-y-8">
          <Card className="border border-border-custom bg-card">
            <CardHeader>
              <CardTitle>System Configuration</CardTitle>
              <CardDescription>Adjust LLM parameters and UI properties.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6 text-xs">
              {savedSuccess && (
                <div className="p-3.5 rounded-xl bg-green-500/10 border border-green-500/20 text-xs text-green-600 dark:text-green-400 font-semibold flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 shrink-0" /> Configuration settings saved!
                </div>
              )}

              {/* LLM Model Selection */}
              <div className="space-y-2">
                <label className="font-semibold text-muted-custom flex items-center gap-1.5">
                  <Cpu className="h-4 w-4 text-primary" /> Active LLM Model Runtime
                </label>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full text-xs py-2.5 px-3 rounded-xl border border-border-custom bg-bg-secondary font-medium text-foreground focus:outline-hidden"
                >
                  <option value="qwen-2.5-7b">Qwen 2.5 7B GGUF (Quantized & CPU-optimized) [Recommended]</option>
                  <option value="phi-3.5-mini">Phi 3.5 3.8B GGUF (Ultra-lightweight, 4GB RAM)</option>
                  <option value="llama-3.1-8b">Llama 3.1 8B GGUF (Balanced reasoning runtime)</option>
                  <option value="gemini-flash">Gemini 1.5 Flash API (Cloud-hosted network fallback)</option>
                </select>
                <p className="text-[10px] text-muted-custom">
                  Local models run directly on your institution's CPU. Cloud APIs require a secondary network token config.
                </p>
              </div>

              {/* Default Language */}
              <div className="space-y-2 pt-2">
                <label className="font-semibold text-muted-custom flex items-center gap-1.5">
                  <Globe className="h-4 w-4 text-secondary" /> System Language
                </label>
                <select
                  value={lang}
                  onChange={(e) => setLang(e.target.value)}
                  className="w-full text-xs py-2.5 px-3 rounded-xl border border-border-custom bg-bg-secondary font-medium text-foreground focus:outline-hidden"
                >
                  <option value="en">English (US/UK)</option>
                  <option value="es">Spanish (Español)</option>
                  <option value="hi">Hindi (हिन्दी)</option>
                  <option value="fr">French (Français)</option>
                  <option value="ar">Arabic (العربية)</option>
                </select>
              </div>

              {/* Notification Toggles */}
              <div className="space-y-3 pt-4 border-t border-border-custom/50">
                <h4 className="font-semibold text-muted-custom flex items-center gap-1.5">
                  <Bell className="h-4 w-4 text-amber-500" /> Notifications & Alerts
                </h4>
                
                <div className="space-y-3 pl-1">
                  {/* Toggle 1 */}
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <p className="font-semibold text-foreground">Background Job Completions</p>
                      <p className="text-[10px] text-muted-custom">Send browser alerts once content generation completes.</p>
                    </div>
                    <input
                      type="checkbox"
                      checked={notifyJob}
                      onChange={(e) => setNotifyJob(e.target.checked)}
                      className="h-4.5 w-4.5 rounded border-border-custom text-primary focus:ring-primary/20 bg-bg-secondary accent-primary"
                    />
                  </div>

                  {/* Toggle 2 */}
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <p className="font-semibold text-foreground">Validation Failures</p>
                      <p className="text-[10px] text-muted-custom">Alert if validator agent rejects more than 3 consecutive drafts.</p>
                    </div>
                    <input
                      type="checkbox"
                      checked={notifyVerify}
                      onChange={(e) => setNotifyVerify(e.target.checked)}
                      className="h-4.5 w-4.5 rounded border-border-custom text-primary focus:ring-primary/20 bg-bg-secondary accent-primary"
                    />
                  </div>

                  {/* Toggle 3 */}
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <p className="font-semibold text-foreground">Weekly Digest Summaries</p>
                      <p className="text-[10px] text-muted-custom">Receive email logs listing question bank usage statistics.</p>
                    </div>
                    <input
                      type="checkbox"
                      checked={notifyWeekly}
                      onChange={(e) => setNotifyWeekly(e.target.checked)}
                      className="h-4.5 w-4.5 rounded border-border-custom text-primary focus:ring-primary/20 bg-bg-secondary accent-primary"
                    />
                  </div>
                </div>
              </div>

              {/* Submit */}
              <div className="pt-2">
                <Button onClick={handleSave} loading={saving} className="w-full sm:w-auto text-xs">
                  Save Settings
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Danger zone / Institutional Data controls (1/3 columns) */}
        <div className="space-y-8">
          <Card className="border border-red-500/15 bg-red-500/5 dark:bg-red-500/10 p-6 space-y-4">
            <div className="flex gap-3">
              <div className="h-9 w-9 rounded-xl bg-red-500/20 text-red-600 dark:text-red-500 flex items-center justify-center shrink-0">
                <Trash2 className="h-4.5 w-4.5" />
              </div>
              <div className="space-y-1.5 text-xs">
                <h3 className="font-heading font-semibold text-sm text-red-700 dark:text-red-400">Institutional Maintenance</h3>
                <p className="text-red-900/80 dark:text-red-300/80 leading-relaxed">
                  Purge cached curriculum indices, historical generation timelines, or reset local embedding indices.
                </p>
              </div>
            </div>

            {purgeSuccess && (
              <div className="p-3 rounded-xl bg-green-500/10 border border-green-500/20 text-[10px] text-green-600 dark:text-green-400 font-semibold flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5" /> Data purged successfully!
              </div>
            )}

            <div className="pt-2 space-y-2 text-xs">
              <Button
                variant="danger"
                size="sm"
                className="w-full text-xs justify-center hover:bg-red-700"
                onClick={handlePurge}
                loading={purging}
              >
                Clear History Logs
              </Button>
              <p className="text-[10px] text-red-800/60 dark:text-red-300/60 text-center leading-normal">
                * This will empty the database table generated_content and question_bank_history.
              </p>
            </div>
          </Card>
        </div>

      </div>
    </div>
  );
}
