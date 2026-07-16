'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore, GeneratedAssignment } from '@/store/useAppStore';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  FileSpreadsheet,
  Download,
  Edit2,
  Trash2,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Award,
  Key,
  BookOpen,
  X,
} from 'lucide-react';

export default function AssignmentGeneratorPage() {
  const router = useRouter();
  const { generatedAssignments, updateAssignment, regenerateAssignment, deleteAssignment, isConfigured } = useAppStore();

  // Collapsed sections management
  const [collapsedStates, setCollapsedStates] = useState<Record<string, { rubric: boolean; key: boolean }>>({});

  // Editor modal state
  const [editingItem, setEditingItem] = useState<GeneratedAssignment | null>(null);
  const [editQuestion, setEditQuestion] = useState('');
  const [editRubric, setEditRubric] = useState('');
  const [editKey, setEditKey] = useState('');
  const [editMarks, setEditMarks] = useState(10);

  if (generatedAssignments.length === 0) {
    return (
      <Card className="border border-border-custom bg-card text-center p-12 animate-in fade-in duration-300">
        <CardContent className="space-y-4">
          <div className="mx-auto h-12 w-12 rounded-full bg-primary/10 text-primary flex items-center justify-center">
            <FileSpreadsheet className="h-6 w-6" />
          </div>
          <h3 className="font-heading font-bold text-lg">No Assignments Generated</h3>
          <p className="text-xs text-muted-custom max-w-sm mx-auto">
            You must configure your curriculum target and run the AI multi-agent generator to draft assignments.
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

  // Toggle Accordion Collapse state
  const toggleSection = (id: string, type: 'rubric' | 'key') => {
    setCollapsedStates((prev) => {
      const current = prev[id] || { rubric: true, key: true };
      return {
        ...prev,
        [id]: {
          ...current,
          [type]: !current[type],
        },
      };
    });
  };

  // Open Edit Modal
  const openEdit = (item: GeneratedAssignment) => {
    setEditingItem(item);
    setEditQuestion(item.question);
    setEditRubric(item.rubric);
    setEditKey(item.answerKey);
    setEditMarks(item.marks);
  };

  const closeEdit = () => {
    setEditingItem(null);
  };

  const handleSaveEdit = () => {
    if (!editingItem) return;
    updateAssignment(editingItem.id, {
      question: editQuestion,
      rubric: editRubric,
      answerKey: editKey,
      marks: editMarks,
    });
    closeEdit();
  };

  // Export homework
  const handleExport = () => {
    const dataStr = JSON.stringify(generatedAssignments, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Assignment_Sheet_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-heading font-bold text-2xl tracking-tight">Assignment Generator Sheets</h2>
          <p className="text-xs text-muted-custom">Review, grade rubrics, and finalize generated homework worksheets.</p>
        </div>

        <Button variant="outline" size="sm" className="text-xs shrink-0 cursor-pointer" onClick={handleExport}>
          <Download className="h-4 w-4 mr-1.5" /> Export Assignment File
        </Button>
      </div>

      {/* Assignment list grid */}
      <div className="space-y-6">
        {generatedAssignments.map((item, idx) => {
          const rubricCollapsed = collapsedStates[item.id]?.rubric !== false; // defaults to collapsed (true)
          const keyCollapsed = collapsedStates[item.id]?.key !== false; // defaults to collapsed (true)

          return (
            <Card key={item.id} className="border border-border-custom bg-card shadow-xs hover:border-primary/10 transition-all duration-200">
              {/* Card Header metadata */}
              <div className="p-6 pb-4 border-b border-border-custom/40 flex flex-wrap items-center justify-between gap-3 bg-bg-secondary/20">
                <div className="flex items-center gap-3">
                  <span className="text-xs font-semibold text-muted-custom uppercase">Question {idx + 1}</span>
                  <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-amber-500/15 text-amber-700 dark:text-amber-400 font-bold text-[10px]">
                    {item.marks} Marks
                  </span>
                  <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-primary/10 text-primary font-bold text-[10px]">
                    {item.bloomLevel}
                  </span>
                  <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-secondary/10 text-secondary font-semibold text-[10px] capitalize">
                    {item.questionType} Type
                  </span>
                </div>

                <div className="flex items-center gap-1.5">
                  <Button variant="ghost" className="h-8 w-8 p-0" onClick={() => openEdit(item)} title="Edit Question">
                    <Edit2 className="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="ghost" className="h-8 w-8 p-0" onClick={() => regenerateAssignment(item.id)} title="Regenerate Question">
                    <RefreshCw className="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="ghost" className="h-8 w-8 p-0 text-red-500 hover:bg-red-500/10 hover:text-red-600" onClick={() => deleteAssignment(item.id)} title="Delete Question">
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>

              {/* Card Content body */}
              <CardContent className="p-6 space-y-4">
                <p className="text-sm font-bold leading-relaxed">{item.question}</p>

                {/* Rubric Accordion */}
                <div className="border border-border-custom rounded-xl overflow-hidden">
                  <button
                    onClick={() => toggleSection(item.id, 'rubric')}
                    className="w-full flex items-center justify-between px-4 py-3 bg-bg-secondary/40 text-xs font-semibold text-left transition-colors"
                  >
                    <span className="flex items-center gap-2 text-muted-custom">
                      <Award className="h-4 w-4 text-primary" /> Grading Rubric Guide
                    </span>
                    {rubricCollapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
                  </button>
                  {!rubricCollapsed && (
                    <div className="p-4 bg-card text-xs leading-relaxed border-t border-border-custom/50 whitespace-pre-wrap">
                      {item.rubric}
                    </div>
                  )}
                </div>

                {/* Answer Key Accordion */}
                <div className="border border-border-custom rounded-xl overflow-hidden">
                  <button
                    onClick={() => toggleSection(item.id, 'key')}
                    className="w-full flex items-center justify-between px-4 py-3 bg-bg-secondary/40 text-xs font-semibold text-left transition-colors"
                  >
                    <span className="flex items-center gap-2 text-muted-custom">
                      <Key className="h-4 w-4 text-secondary" /> Evaluator Answer Key
                    </span>
                    {keyCollapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
                  </button>
                  {!keyCollapsed && (
                    <div className="p-4 bg-card text-xs leading-relaxed border-t border-border-custom/50 whitespace-pre-wrap font-mono">
                      {item.answerKey}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Inline Editor Dialog */}
      {editingItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 dark:bg-slate-950/60 backdrop-blur-xs">
          <div className="bg-card w-full max-w-xl rounded-2xl border border-border-custom shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="flex h-16 items-center justify-between px-6 border-b border-border-custom">
              <h3 className="font-heading font-semibold text-base">Edit Assignment Details</h3>
              <button onClick={closeEdit} className="h-8 w-8 rounded-lg hover:bg-muted-bg flex items-center justify-center text-muted-custom">
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
              {/* Question */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-custom">Question Text</label>
                <textarea
                  value={editQuestion}
                  onChange={(e) => setEditQuestion(e.target.value)}
                  className="w-full h-24 p-3 text-xs rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 text-foreground font-medium"
                />
              </div>

              {/* Marks */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-custom">Target Marks</label>
                <input
                  type="number"
                  value={editMarks}
                  onChange={(e) => setEditMarks(Number(e.target.value))}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-border-custom bg-bg-secondary font-medium text-foreground"
                />
              </div>

              {/* Rubric */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-custom">Grading Rubric</label>
                <textarea
                  value={editRubric}
                  onChange={(e) => setEditRubric(e.target.value)}
                  className="w-full h-24 p-3 text-xs rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 text-foreground"
                />
              </div>

              {/* Key */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-custom">Answer Key</label>
                <textarea
                  value={editKey}
                  onChange={(e) => setEditKey(e.target.value)}
                  className="w-full h-24 p-3 text-xs rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 text-foreground"
                />
              </div>
            </div>

            <div className="p-4 border-t border-border-custom flex gap-3">
              <Button variant="outline" className="flex-1 text-xs" onClick={closeEdit}>
                Cancel
              </Button>
              <Button className="flex-1 text-xs" onClick={handleSaveEdit}>
                Save Changes
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
