'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAppStore } from '@/store/useAppStore';
import { useTranslation } from '@/hooks/useTranslation';
import {
  Settings,
  Cpu,
  Globe,
  Bell,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  Info,
} from 'lucide-react';

export default function SettingsPage() {
  const store = useAppStore();
  const { t } = useTranslation();

  const [model, setModel] = useState('qwen-2.5-7b');
  const [lang, setLangState] = useState(store.language || 'en');
  const [isMaintenanceActive, setIsMaintenanceActive] = useState(false);
  
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

    // Apply language instantly
    store.setLanguage(lang as 'en' | 'ta');

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
        <h2 className="font-heading font-bold text-2xl tracking-tight">{t('settings.title')}</h2>
        <p className="text-xs text-muted-custom">{t('settings.subtitle')}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Columns: Config Forms (2/3 columns) */}
        <div className="lg:col-span-2 space-y-8 text-foreground">
          <Card className="border border-border-custom bg-card">
            <CardHeader>
              <CardTitle>{t('settings.card_title')}</CardTitle>
              <CardDescription>{t('settings.card_desc')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6 text-xs">
              {savedSuccess && (
                <div className="p-3.5 rounded-xl bg-green-500/10 border border-green-500/20 text-xs text-green-600 dark:text-green-400 font-semibold flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 shrink-0" /> Settings saved successfully!
                </div>
              )}

              {/* LLM Model Selection */}
              <div className="space-y-2">
                <label className="font-semibold text-muted-custom flex items-center gap-1.5">
                  <Cpu className="h-4 w-4 text-primary" /> {t('settings.model')}
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
                  {t('settings.model_desc')}
                </p>
              </div>

              {/* Default Language */}
              <div className="space-y-2 pt-2">
                <label className="font-semibold text-muted-custom flex items-center gap-1.5">
                  <Globe className="h-4 w-4 text-secondary" /> {t('settings.language')}
                </label>
                <select
                  value={lang}
                  onChange={(e) => {
                    setLangState(e.target.value as 'en' | 'ta');
                    // Update instantly per requirement
                    store.setLanguage(e.target.value as 'en' | 'ta');
                  }}
                  className="w-full text-xs py-2.5 px-3 rounded-xl border border-border-custom bg-bg-secondary font-medium text-foreground focus:outline-hidden"
                >
                  <option value="en">English (US/UK)</option>
                  <option value="ta">Tamil (தமிழ்)</option>
                </select>
              </div>

              {/* Notification Toggles */}
              <div className="space-y-3 pt-4 border-t border-border-custom/50">
                <h4 className="font-semibold text-muted-custom flex items-center gap-1.5">
                  <Bell className="h-4 w-4 text-amber-500" /> {t('settings.notify')}
                </h4>
                
                <div className="space-y-3 pl-1">
                  {/* Toggle 1 */}
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <p className="font-semibold">{t('settings.notify_job')}</p>
                      <p className="text-[10px] text-muted-custom">{t('settings.notify_job_desc')}</p>
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
                      <p className="font-semibold">{t('settings.notify_verify')}</p>
                      <p className="text-[10px] text-muted-custom">{t('settings.notify_verify_desc')}</p>
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
                      <p className="font-semibold">{t('settings.notify_weekly')}</p>
                      <p className="text-[10px] text-muted-custom">{t('settings.notify_weekly_desc')}</p>
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
                  {t('settings.save_settings')}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Danger zone / Institutional Data controls (1/3 columns) */}
        <div className="space-y-8">
          {/* Maintenance Card */}
          <Card className={`p-6 space-y-4 border transition-all duration-300 ${
            isMaintenanceActive 
              ? 'border-red-500/15 bg-red-500/5 dark:bg-red-500/10' 
              : 'border-border-custom bg-card'
          }`}>
            <div className="flex gap-3 text-foreground">
              <div className={`h-9 w-9 rounded-xl flex items-center justify-center shrink-0 ${
                isMaintenanceActive 
                  ? 'bg-red-500/20 text-red-600 dark:text-red-500' 
                  : 'bg-green-500/15 text-green-600 dark:text-green-500'
              }`}>
                {isMaintenanceActive ? <AlertTriangle className="h-4.5 w-4.5" /> : <Info className="h-4.5 w-4.5" />}
              </div>
              <div className="space-y-1.5 text-xs">
                <div className="flex items-center justify-between">
                  <h3 className="font-heading font-semibold text-sm">
                    {t('settings.maintenance')}
                  </h3>
                  <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${
                    isMaintenanceActive 
                      ? 'bg-red-500/20 text-red-700 dark:text-red-400' 
                      : 'bg-green-500/10 text-green-700 dark:text-green-400'
                  }`}>
                    {isMaintenanceActive ? 'Active' : 'Offline'}
                  </span>
                </div>
                <p className="text-muted-custom font-semibold">
                  {isMaintenanceActive ? t('settings.maintenance_active') : t('settings.no_maintenance')}
                </p>
                <p className="text-muted-custom leading-relaxed">
                  {t('settings.maintenance_desc')}
                </p>
              </div>
            </div>

            {/* Test Toggle to switch between states manually for testing */}
            <div className="flex items-center justify-between pt-2 border-t border-border-custom/50 text-[10px] text-muted-custom">
              <span>Test Status Toggle</span>
              <input
                type="checkbox"
                checked={isMaintenanceActive}
                onChange={(e) => setIsMaintenanceActive(e.target.checked)}
                className="h-3.5 w-3.5 rounded bg-bg-secondary accent-primary"
              />
            </div>

            {purgeSuccess && (
              <div className="p-3 rounded-xl bg-green-500/10 border border-green-500/20 text-[10px] text-green-600 dark:text-green-400 font-semibold flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5" /> Data purged successfully!
              </div>
            )}

            <div className="pt-2 space-y-2 text-xs">
              <Button
                variant={isMaintenanceActive ? 'danger' : 'outline'}
                size="sm"
                className="w-full text-xs justify-center hover:bg-red-700/10"
                onClick={handlePurge}
                loading={purging}
              >
                {t('settings.clear_history')}
              </Button>
              <p className="text-[10px] text-muted-custom text-center leading-normal">
                {t('settings.clear_history_desc')}
              </p>
            </div>
          </Card>
        </div>

      </div>
    </div>
  );
}
