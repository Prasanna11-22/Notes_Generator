'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/store/useAppStore';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  BookOpen,
  Copy,
  Edit3,
  Check,
  RefreshCw,
  FileDown,
  Download,
  AlertCircle,
  HelpCircle,
  ListTodo,
} from 'lucide-react';

type TabKey = 'overview' | 'conceptExplanation' | 'workedExamples' | 'activities' | 'discussionQuestions' | 'summary' | 'revisionNotes';

interface TabItem {
  key: TabKey;
  label: string;
  icon: React.ComponentType<any>;
}

export default function LearningMaterialPage() {
  const router = useRouter();
  const { generatedNotes, updateNotesTab, isConfigured } = useAppStore();
  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState('');
  const [copied, setCopied] = useState(false);
  const [downloading, setDownloading] = useState<'pdf' | 'docx' | null>(null);

  const tabs: TabItem[] = [
    { key: 'overview', label: 'Overview', icon: BookOpen },
    { key: 'conceptExplanation', label: 'Concepts', icon: BookOpen },
    { key: 'workedExamples', label: 'Examples', icon: Check },
    { key: 'activities', label: 'Lab & Activities', icon: RefreshCw },
    { key: 'discussionQuestions', label: 'Discussions', icon: HelpCircle },
    { key: 'summary', label: 'Summary', icon: AlertCircle },
    { key: 'revisionNotes', label: 'Revision Checklist', icon: ListTodo },
  ];

  if (!generatedNotes) {
    return (
      <Card className="border border-border-custom bg-card text-center p-12 animate-in fade-in duration-300">
        <CardContent className="space-y-4">
          <div className="mx-auto h-12 w-12 rounded-full bg-primary/10 text-primary flex items-center justify-center">
            <BookOpen className="h-6 w-6" />
          </div>
          <h3 className="font-heading font-bold text-lg">No Learning Materials Generated</h3>
          <p className="text-xs text-muted-custom max-w-sm mx-auto">
            You must configure your curriculum target and run the AI multi-agent generator to draft study notes.
          </p>
          <div className="pt-2">
            <Button onClick={() => router.push(isConfigured ? '/dashboard/generate' : '/dashboard/courses')}>
              {isConfigured ? 'Go to Generator' : 'Configure Course'}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const activeContent = generatedNotes[activeTab];

  const handleCopy = () => {
    navigator.clipboard.writeText(activeContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleEditStart = () => {
    setEditText(activeContent);
    setIsEditing(true);
  };

  const handleEditSave = () => {
    updateNotesTab(activeTab, editText);
    setIsEditing(false);
  };

  const handleDownload = (format: 'pdf' | 'docx') => {
    setDownloading(format);
    setTimeout(() => {
      setDownloading(null);
      // Simulate file download trigger
      const blob = new Blob([activeContent], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Lecture_Notes_${activeTab}_${Date.now()}.${format === 'pdf' ? 'pdf' : 'docx'}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 1200);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header and export buttons */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-heading font-bold text-2xl tracking-tight">Lecture Notes & Concepts</h2>
          <p className="text-xs text-muted-custom">Access formatted concept explainers, lab worksheets, and revision points.</p>
        </div>
        
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="text-xs shrink-0 cursor-pointer"
            loading={downloading === 'pdf'}
            onClick={() => handleDownload('pdf')}
          >
            <FileDown className="h-4 w-4 mr-1.5" /> PDF
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="text-xs shrink-0 cursor-pointer"
            loading={downloading === 'docx'}
            onClick={() => handleDownload('docx')}
          >
            <Download className="h-4 w-4 mr-1.5" /> DOCX
          </Button>
        </div>
      </div>

      {/* Main Tabbed Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        
        {/* Left Side: Tabs Selector Sidebar (1/4 columns) */}
        <div className="lg:col-span-1 space-y-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => {
                  setActiveTab(tab.key);
                  setIsEditing(false);
                }}
                className={`w-full flex items-center gap-3 px-4 py-3 text-xs font-semibold rounded-xl text-left border transition-all ${
                  isActive
                    ? 'bg-primary border-primary text-primary-foreground shadow-sm shadow-primary/10'
                    : 'bg-card border-border-custom hover:bg-muted-bg text-muted-custom hover:text-foreground'
                }`}
              >
                <Icon className="h-4.5 w-4.5 shrink-0" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Right Side: Content Area (3/4 columns) */}
        <div className="lg:col-span-3">
          <Card className="border border-border-custom bg-card h-full min-h-[450px] flex flex-col justify-between">
            <CardHeader className="flex flex-row items-center justify-between border-b border-border-custom/40 pb-4">
              <div>
                <CardTitle className="capitalize">{activeTab.replace(/([A-Z])/g, ' $1')}</CardTitle>
                <CardDescription>Generated text grounding citation models.</CardDescription>
              </div>

              {/* Utility actions */}
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0 cursor-pointer" onClick={handleCopy} title="Copy Content">
                  {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                </Button>
                {isEditing ? (
                  <Button size="sm" className="text-xs h-8" onClick={handleEditSave}>
                    Save Changes
                  </Button>
                ) : (
                  <Button variant="outline" size="sm" className="text-xs h-8" onClick={handleEditStart}>
                    <Edit3 className="h-3.5 w-3.5 mr-1" /> Edit
                  </Button>
                )}
              </div>
            </CardHeader>

            <CardContent className="flex-1 p-6">
              {isEditing ? (
                <textarea
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  className="w-full h-96 p-4 rounded-xl border border-border-custom bg-bg-secondary text-sm font-mono focus:outline-hidden focus:ring-2 focus:ring-primary/20"
                />
              ) : (
                <div className="prose prose-sm dark:prose-invert max-w-none text-sm leading-relaxed whitespace-pre-wrap">
                  {activeContent}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

      </div>
    </div>
  );
}
