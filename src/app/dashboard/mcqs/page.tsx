'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore, GeneratedMCQ } from '@/store/useAppStore';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  HelpCircle,
  Filter,
  Download,
  Edit2,
  Trash2,
  RefreshCw,
  X,
  CheckCircle2,
  Search,
  Eye,
} from 'lucide-react';

export default function MCQGeneratorPage() {
  const router = useRouter();
  const { generatedMCQs, updateMCQ, regenerateMCQ, deleteMCQ, isConfigured } = useAppStore();

  // Search & Filter state
  const [searchTerm, setSearchTerm] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState('all');
  const [bloomFilter, setBloomFilter] = useState('all');

  // Preview / Editor drawer state
  const [selectedMCQ, setSelectedMCQ] = useState<GeneratedMCQ | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editQuestion, setEditQuestion] = useState('');
  const [editExplanation, setEditExplanation] = useState('');
  const [editOptions, setEditOptions] = useState<string[]>([]);
  const [editCorrectAnswer, setEditCorrectAnswer] = useState('');

  if (generatedMCQs.length === 0) {
    return (
      <Card className="border border-border-custom bg-card text-center p-12 animate-in fade-in duration-300">
        <CardContent className="space-y-4">
          <div className="mx-auto h-12 w-12 rounded-full bg-primary/10 text-primary flex items-center justify-center">
            <HelpCircle className="h-6 w-6" />
          </div>
          <h3 className="font-heading font-bold text-lg">No MCQs Generated</h3>
          <p className="text-xs text-muted-custom max-w-sm mx-auto">
            You must configure your curriculum target and run the AI multi-agent generator to compile quiz banks.
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

  // Filter MCQ list
  const filteredMCQs = generatedMCQs.filter((mcq) => {
    const matchesSearch = mcq.question.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesDifficulty = difficultyFilter === 'all' || mcq.difficulty === difficultyFilter;
    const matchesBloom = bloomFilter === 'all' || mcq.bloomLevel.toLowerCase() === bloomFilter.toLowerCase();
    return matchesSearch && matchesDifficulty && matchesBloom;
  });

  // Open Drawer and populate values
  const openDrawer = (mcq: GeneratedMCQ) => {
    setSelectedMCQ(mcq);
    setEditQuestion(mcq.question);
    setEditExplanation(mcq.explanation);
    setEditOptions([...mcq.options]);
    setEditCorrectAnswer(mcq.correctAnswer);
    setDrawerOpen(true);
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
    setSelectedMCQ(null);
  };

  const handleSaveDrawer = () => {
    if (!selectedMCQ) return;
    updateMCQ(selectedMCQ.id, {
      question: editQuestion,
      explanation: editExplanation,
      options: editOptions,
      correctAnswer: editCorrectAnswer,
    });
    closeDrawer();
  };

  const handleOptionChange = (idx: number, val: string) => {
    const updated = [...editOptions];
    updated[idx] = val;
    setEditOptions(updated);
  };

  // Mock export handler
  const handleExport = (format: string) => {
    const dataStr = JSON.stringify(filteredMCQs, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `MCQ_Bank_${Date.now()}.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300 relative">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-heading font-bold text-2xl tracking-tight">MCQ Generator Console</h2>
          <p className="text-xs text-muted-custom">Review, tag, and export generated Multiple Choice questions.</p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="text-xs shrink-0 cursor-pointer" onClick={() => handleExport('json')}>
            <Download className="h-4 w-4 mr-1.5" /> Export JSON
          </Button>
          <Button variant="outline" size="sm" className="text-xs shrink-0 cursor-pointer" onClick={() => handleExport('csv')}>
            <Download className="h-4 w-4 mr-1.5" /> Export Canvas CSV
          </Button>
        </div>
      </div>

      {/* Toolbar Filters */}
      <div className="flex flex-col md:flex-row gap-4 items-center justify-between p-4 bg-card border border-border-custom rounded-2xl">
        <div className="flex items-center gap-2 w-full md:w-auto">
          <Search className="h-4 w-4 text-muted-custom shrink-0" />
          <input
            type="text"
            placeholder="Search questions..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full md:w-60 bg-transparent border-0 text-xs focus:ring-0 focus:outline-hidden text-foreground placeholder:text-muted-custom/60"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto justify-end">
          {/* Difficulty */}
          <div className="flex items-center gap-1.5 text-xs">
            <Filter className="h-3.5 w-3.5 text-muted-custom" />
            <select
              value={difficultyFilter}
              onChange={(e) => setDifficultyFilter(e.target.value)}
              className="py-1 px-2 text-[11px] rounded-lg border border-border-custom bg-bg-secondary"
            >
              <option value="all">All Difficulties</option>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>

          {/* Bloom */}
          <div className="flex items-center gap-1.5 text-xs">
            <Filter className="h-3.5 w-3.5 text-muted-custom" />
            <select
              value={bloomFilter}
              onChange={(e) => setBloomFilter(e.target.value)}
              className="py-1 px-2 text-[11px] rounded-lg border border-border-custom bg-bg-secondary"
            >
              <option value="all">All Bloom Levels</option>
              <option value="remember">Remember</option>
              <option value="understand">Understand</option>
              <option value="apply">Apply</option>
              <option value="analyze">Analyze</option>
              <option value="evaluate">Evaluate</option>
              <option value="create">Create</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Table view */}
      <Card className="border border-border-custom bg-card">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-border-custom bg-bg-secondary/40 text-muted-custom font-semibold">
                  <th className="py-4 px-6 w-12 text-center">#</th>
                  <th className="py-4 px-4">Question Text</th>
                  <th className="py-4 px-4 w-32">Bloom Level</th>
                  <th className="py-4 px-4 w-28">Difficulty</th>
                  <th className="py-4 px-6 text-right w-44">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredMCQs.map((mcq, index) => (
                  <tr key={mcq.id} className="border-b border-border-custom/50 hover:bg-muted-bg/30 transition-colors">
                    <td className="py-4 px-6 text-center text-muted-custom font-semibold">{index + 1}</td>
                    <td className="py-4 px-4">
                      <div className="space-y-2">
                        <p className="font-bold text-sm leading-normal">{mcq.question}</p>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                          {mcq.options.map((opt) => (
                            <div
                              key={opt}
                              className={`px-3 py-1 rounded-lg text-[10px] flex items-center gap-1.5 ${
                                opt === mcq.correctAnswer
                                  ? 'bg-green-500/10 border border-green-500/20 text-green-600 dark:text-green-400 font-semibold'
                                  : 'bg-bg-secondary/50 text-muted-custom'
                              }`}
                            >
                              {opt === mcq.correctAnswer && <CheckCircle2 className="h-3 w-3 shrink-0" />}
                              <span className="truncate">{opt}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-primary/10 text-primary font-bold text-[10px]">
                        {mcq.bloomLevel}
                      </span>
                    </td>
                    <td className="py-4 px-4">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-md font-semibold text-[10px] ${
                        mcq.difficulty === 'easy'
                          ? 'bg-green-500/10 text-green-600'
                          : mcq.difficulty === 'medium'
                          ? 'bg-amber-500/10 text-amber-600'
                          : 'bg-red-500/10 text-red-600'
                      }`}>
                        {mcq.difficulty}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-right space-x-1 shrink-0">
                      <Button variant="ghost" className="h-8 w-8 p-0" onClick={() => openDrawer(mcq)} title="View Detail">
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" className="h-8 w-8 p-0" onClick={() => regenerateMCQ(mcq.id)} title="Regenerate Item">
                        <RefreshCw className="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" className="h-8 w-8 p-0 text-red-500 hover:bg-red-500/10 hover:text-red-600" onClick={() => deleteMCQ(mcq.id)} title="Delete Item">
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Slide-over Preview/Editor Drawer */}
      {drawerOpen && selectedMCQ && (
        <div className="fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-card border-l border-border-custom shadow-2xl flex flex-col justify-between animate-in slide-in-from-right duration-300">
          <div className="flex h-16 items-center justify-between px-6 border-b border-border-custom">
            <h3 className="font-heading font-semibold text-base">Edit Question Properties</h3>
            <button onClick={closeDrawer} className="h-8 w-8 rounded-lg hover:bg-muted-bg flex items-center justify-center text-muted-custom">
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="flex-1 p-6 space-y-5 overflow-y-auto">
            {/* Question Text */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-custom">Question Text</label>
              <textarea
                value={editQuestion}
                onChange={(e) => setEditQuestion(e.target.value)}
                className="w-full h-24 p-3 text-xs rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 text-foreground font-medium"
              />
            </div>

            {/* Options */}
            <div className="space-y-3">
              <label className="text-xs font-semibold text-muted-custom">Answer Options</label>
              {editOptions.map((opt, idx) => (
                <div key={idx} className="flex gap-2">
                  <input
                    type="radio"
                    name="correct"
                    checked={opt === editCorrectAnswer}
                    onChange={() => setEditCorrectAnswer(opt)}
                    className="mt-3.5 h-4 w-4 rounded-full border-border-custom text-primary focus:ring-primary/20 bg-bg-secondary accent-primary"
                  />
                  <input
                    type="text"
                    value={opt}
                    onChange={(e) => handleOptionChange(idx, e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-border-custom bg-bg-secondary text-foreground font-medium"
                  />
                </div>
              ))}
            </div>

            {/* Explanation */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-muted-custom">Correct Explanation</label>
              <textarea
                value={editExplanation}
                onChange={(e) => setEditExplanation(e.target.value)}
                className="w-full h-24 p-3 text-xs rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 text-foreground"
              />
            </div>
          </div>

          <div className="p-4 border-t border-border-custom flex gap-3">
            <Button variant="outline" className="flex-1 text-xs" onClick={closeDrawer}>
              Cancel
            </Button>
            <Button className="flex-1 text-xs" onClick={handleSaveDrawer}>
              Save Changes
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
