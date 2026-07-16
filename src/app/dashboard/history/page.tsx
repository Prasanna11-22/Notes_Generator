'use client';

import React from 'react';
import { useAppStore } from '@/store/useAppStore';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { History, Calendar, CheckCircle2, FileText, Download, Play } from 'lucide-react';

export default function HistoryPage() {
  const { history } = useAppStore();

  const handleDownload = (topic: string) => {
    const mockData = {
      notes: 'Study notes on balancing rotations.',
      topic: topic,
      downloadedAt: new Date().toISOString(),
    };
    const dataStr = JSON.stringify(mockData, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${topic.toLowerCase().replace(/\s+/g, '_')}_history.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      
      {/* Header */}
      <div>
        <h2 className="font-heading font-bold text-2xl tracking-tight">Generation History Log</h2>
        <p className="text-xs text-muted-custom">Track previous multi-agent pipelines, metadata hashes, and review output history.</p>
      </div>

      {history.length === 0 ? (
        <Card className="border border-border-custom bg-card text-center p-12">
          <CardContent className="space-y-4">
            <div className="mx-auto h-12 w-12 rounded-full bg-primary/10 text-primary flex items-center justify-center">
              <History className="h-6 w-6" />
            </div>
            <h3 className="font-heading font-bold text-lg">No Generation History Found</h3>
            <p className="text-xs text-muted-custom">
              You haven't run any content generation pipelines yet.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="relative border-l border-border-custom/80 pl-6 ml-4 space-y-8">
          {history.map((item) => (
            <div key={item.id} className="relative">
              {/* Timeline Bullet icon */}
              <span className="absolute -left-9.5 top-0.5 h-7 w-7 rounded-full bg-card border border-border-custom flex items-center justify-center text-primary shadow-xs">
                <Calendar className="h-3.5 w-3.5" />
              </span>

              {/* Log Card */}
              <Card className="border border-border-custom bg-card shadow-xs hover:border-primary/10 transition-all duration-200">
                <CardHeader className="flex flex-row items-start justify-between pb-3 gap-3">
                  <div>
                    <span className="inline-flex items-center gap-1 text-[10px] text-muted-custom font-semibold uppercase tracking-wider mb-1 bg-bg-secondary px-2 py-0.5 rounded-md">
                      {item.date}
                    </span>
                    <CardTitle className="text-sm font-bold">{item.topic}</CardTitle>
                    <CardDescription>{item.courseName}</CardDescription>
                  </div>

                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-green-500/10 text-green-600 dark:text-green-400 font-semibold text-[10px]">
                    <CheckCircle2 className="h-3 w-3 stroke-[3]" />
                    {item.status}
                  </span>
                </CardHeader>

                <CardContent className="pt-0 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  {/* Generated quantities */}
                  <div className="flex items-center gap-4 text-xs">
                    {item.hasNotes && (
                      <span className="flex items-center gap-1.5 text-muted-custom">
                        <FileText className="h-4 w-4 text-primary" /> Lesson Guide
                      </span>
                    )}
                    {item.mcqCount > 0 && (
                      <span className="flex items-center gap-1.5 text-muted-custom">
                        <Play className="h-3.5 w-3.5 text-secondary rotate-90" /> {item.mcqCount} Quiz Questions
                      </span>
                    )}
                    {item.assignmentCount > 0 && (
                      <span className="flex items-center gap-1.5 text-muted-custom">
                        <Play className="h-3.5 w-3.5 text-amber-500 rotate-90" /> {item.assignmentCount} Assignments
                      </span>
                    )}
                  </div>

                  {/* Actions */}
                  <Button variant="outline" size="sm" className="text-xs w-full sm:w-auto h-8 px-3 shrink-0 cursor-pointer" onClick={() => handleDownload(item.topic)}>
                    <Download className="h-3.5 w-3.5 mr-1" /> Re-Download JSON
                  </Button>
                </CardContent>
              </Card>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
