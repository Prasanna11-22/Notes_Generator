'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/store/useAppStore';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Sparkles,
  Play,
  XCircle,
  FileText,
  HelpCircle,
  FileSpreadsheet,
  CheckCircle,
  Loader2,
  Clock,
  ChevronRight,
  GraduationCap,
  Sliders,
} from 'lucide-react';

export default function GenerationPage() {
  const router = useRouter();
  const {
    isConfigured,
    selectedCourse,
    selectedTopic,
    uploadedFiles,
    mcqCount,
    assignmentCount,
    bloomDistribution,
    isGenerating,
    generationStep,
    generationStatusText,
    estimatedSecondsLeft,
    startGeneration,
    cancelGeneration,
    generatedNotes,
  } = useAppStore();

  const handleStartEverything = () => {
    startGeneration();
  };

  const steps = [
    { label: 'Planner Agent', desc: 'Syllabus alignment & Bloom mapping' },
    { label: 'Retrieval Agent', desc: 'Dense + BM25 Qdrant search & rerank' },
    { label: 'Generator Agent', desc: 'LLM drafting of questions & notes' },
    { label: 'Validator Agent', desc: 'Bloom checks & syllabus grounding' },
    { label: 'Deduplication Agent', desc: 'Embedding semantic distance check' },
    { label: 'Formatter Agent', desc: 'DOCX, PDF & JSON structure exports' },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <div>
        <h2 className="font-heading font-bold text-2xl tracking-tight">AI Multi-Agent Content Generation</h2>
        <p className="text-xs text-muted-custom">Trigger parallel agent workers to planning, research, generate, validate, and format cognitive items.</p>
      </div>

      {!isConfigured ? (
        <Card className="border border-border-custom bg-card text-center p-12">
          <CardContent className="space-y-4">
            <div className="mx-auto h-12 w-12 rounded-full bg-amber-500/10 text-amber-500 flex items-center justify-center">
              <XCircle className="h-6 w-6" />
            </div>
            <h3 className="font-heading font-bold text-lg">Curriculum Configuration Missing</h3>
            <p className="text-xs text-muted-custom max-w-sm mx-auto">
              Please select a course topic and establish preferences before running the content generator.
            </p>
            <div className="pt-2">
              <Button onClick={() => router.push('/dashboard/courses')}>
                Go to Configuration
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left Column: Configuration Blueprint (1/3 columns) */}
          <div className="space-y-8">
            <Card className="border border-border-custom bg-card">
              <CardHeader>
                <CardTitle>Session Configuration</CardTitle>
                <CardDescription>Target parameters saved for this session.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-5 text-xs">
                
                {/* Course Nodes */}
                <div className="p-3.5 rounded-xl bg-bg-secondary space-y-1.5">
                  <div className="flex items-center gap-2">
                    <GraduationCap className="h-4 w-4 text-primary" />
                    <span className="font-semibold text-muted-custom">Course Target</span>
                  </div>
                  <p className="font-bold text-sm leading-normal">{selectedCourse}</p>
                  <p className="text-muted-custom text-[11px] font-semibold">{selectedTopic}</p>
                </div>

                {/* Ingested counts */}
                <div className="flex items-center justify-between py-2 border-b border-border-custom/50">
                  <span className="text-muted-custom font-medium">Reference Materials</span>
                  <span className="font-bold">{uploadedFiles.length} files</span>
                </div>

                {/* Targets */}
                <div className="space-y-2 py-2 border-b border-border-custom/50">
                  <div className="flex justify-between">
                    <span className="text-muted-custom font-medium">MCQ Target</span>
                    <span className="font-bold">{mcqCount} Questions</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-custom font-medium">Assignment Target</span>
                    <span className="font-bold">{assignmentCount} Tasks</span>
                  </div>
                </div>

                {/* Bloom breakdown */}
                <div className="space-y-2 py-2">
                  <div className="flex items-center gap-2 mb-1.5 text-muted-custom font-semibold">
                    <Sliders className="h-3.5 w-3.5" />
                    <span>Bloom Targets (%)</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[10px]">
                    <div className="flex justify-between bg-bg-secondary/40 px-2 py-1 rounded-md">
                      <span className="text-muted-custom">Remember:</span>
                      <span className="font-bold">{bloomDistribution.remember}%</span>
                    </div>
                    <div className="flex justify-between bg-bg-secondary/40 px-2 py-1 rounded-md">
                      <span className="text-muted-custom">Understand:</span>
                      <span className="font-bold">{bloomDistribution.understand}%</span>
                    </div>
                    <div className="flex justify-between bg-bg-secondary/40 px-2 py-1 rounded-md">
                      <span className="text-muted-custom">Apply:</span>
                      <span className="font-bold">{bloomDistribution.apply}%</span>
                    </div>
                    <div className="flex justify-between bg-bg-secondary/40 px-2 py-1 rounded-md">
                      <span className="text-muted-custom">Analyze:</span>
                      <span className="font-bold">{bloomDistribution.analyze}%</span>
                    </div>
                    <div className="flex justify-between bg-bg-secondary/40 px-2 py-1 rounded-md">
                      <span className="text-muted-custom">Evaluate:</span>
                      <span className="font-bold">{bloomDistribution.evaluate}%</span>
                    </div>
                    <div className="flex justify-between bg-bg-secondary/40 px-2 py-1 rounded-md">
                      <span className="text-muted-custom">Create:</span>
                      <span className="font-bold">{bloomDistribution.create}%</span>
                    </div>
                  </div>
                </div>

              </CardContent>
            </Card>

            {/* Quick Actions (Trigger separate generations) */}
            {!isGenerating && !generatedNotes && (
              <Card className="border border-border-custom bg-card">
                <CardHeader>
                  <CardTitle>Manual Triggers</CardTitle>
                  <CardDescription>Generate individual content items independently.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2.5">
                  <Button variant="outline" size="sm" className="w-full text-xs justify-start" onClick={handleStartEverything}>
                    <FileText className="h-4 w-4 mr-2 text-primary" /> Generate Notes Only
                  </Button>
                  <Button variant="outline" size="sm" className="w-full text-xs justify-start" onClick={handleStartEverything}>
                    <HelpCircle className="h-4 w-4 mr-2 text-secondary" /> Generate Quiz MCQs Only
                  </Button>
                  <Button variant="outline" size="sm" className="w-full text-xs justify-start" onClick={handleStartEverything}>
                    <FileSpreadsheet className="h-4 w-4 mr-2 text-amber-600" /> Generate Assignment Sheet Only
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Column: Execution timeline & Animations (2/3 columns) */}
          <div className="lg:col-span-2 space-y-8">
            <Card className="border border-border-custom bg-card">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Agent Execution Pipeline</CardTitle>
                  <CardDescription>Review running workers and validation loops.</CardDescription>
                </div>
                {isGenerating && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-600 dark:text-amber-500 font-semibold text-[10px] animate-pulse">
                    <Clock className="h-3 w-3" />
                    ~{estimatedSecondsLeft}s left
                  </span>
                )}
              </CardHeader>
              <CardContent className="space-y-6">
                
                {/* Status Trigger Banner */}
                {!isGenerating && !generatedNotes ? (
                  <div className="p-8 border border-dashed border-border-custom rounded-2xl text-center space-y-4 bg-bg-secondary/40">
                    <div className="h-12 w-12 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto shadow-sm shadow-primary/5">
                      <Sparkles className="h-6 w-6 animate-pulse" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold">Ready to Generate Content</p>
                      <p className="text-[10px] text-muted-custom max-w-xs mx-auto">Click "Generate Everything" to start the full multi-agent layout.</p>
                    </div>
                    <Button onClick={handleStartEverything} className="shadow-xs cursor-pointer">
                      <Play className="h-4 w-4 mr-1.5 fill-current" /> Generate Everything
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {/* Stepper Timeline */}
                    <div className="relative pl-6 border-l-2 border-border-custom/80 space-y-6">
                      {steps.map((st, idx) => {
                        const stepNum = idx + 1;
                        const isCompleted = generationStep > stepNum;
                        const isCurrent = generationStep === stepNum;
                        const isUpcoming = generationStep < stepNum;

                        return (
                          <div key={st.label} className="relative">
                            {/* Step Bullet */}
                            <span className={`absolute -left-9 top-0.5 h-6 w-6 rounded-full border flex items-center justify-center transition-all ${
                              isCompleted
                                ? 'bg-green-500 border-green-500 text-white shadow-sm shadow-green-500/25'
                                : isCurrent
                                ? 'bg-primary border-primary text-primary-foreground animate-pulse shadow-sm shadow-primary/25'
                                : 'bg-card border-border-custom text-muted-custom'
                            }`}>
                              {isCompleted ? (
                                <CheckCircle className="h-3.5 w-3.5 stroke-[3]" />
                              ) : isCurrent ? (
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                              ) : (
                                <span className="text-[10px] font-bold">{stepNum}</span>
                              )}
                            </span>

                            {/* Label */}
                            <div className="space-y-0.5">
                              <h4 className={`text-xs font-semibold ${
                                isCompleted ? 'text-green-600 dark:text-green-400 font-semibold' : isCurrent ? 'text-primary' : 'text-muted-custom'
                              }`}>
                                {st.label}
                              </h4>
                              <p className="text-[10px] text-muted-custom">{st.desc}</p>
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Progress details */}
                    {isGenerating && (
                      <div className="p-4 rounded-xl bg-bg-secondary space-y-2 border border-border-custom/50">
                        <div className="flex justify-between items-center text-[10px]">
                          <span className="font-semibold text-primary">Running Pipeline</span>
                          <span className="text-muted-custom font-semibold">{Math.round((generationStep / 6) * 100)}%</span>
                        </div>
                        <div className="h-1.5 w-full bg-border-custom/60 rounded-full overflow-hidden">
                          <div className="h-full bg-primary transition-all duration-500" style={{ width: `${(generationStep / 6) * 100}%` }} />
                        </div>
                        <p className="text-[10px] text-muted-custom leading-normal">{generationStatusText}</p>
                      </div>
                    )}

                    {/* Completion action buttons */}
                    {generatedNotes && !isGenerating && (
                      <div className="p-4 rounded-xl border border-green-500/10 bg-green-500/5 dark:bg-green-500/10 space-y-4">
                        <div className="flex items-center gap-3 text-green-700 dark:text-green-400">
                          <CheckCircle className="h-5 w-5 shrink-0" />
                          <div className="space-y-0.5">
                            <h4 className="font-semibold text-xs">Generation Successful!</h4>
                            <p className="text-[10px] text-muted-custom">Generated notes, {mcqCount} MCQs, and {assignmentCount} assignments.</p>
                          </div>
                        </div>

                        {/* Navigation Actions */}
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2 border-t border-border-custom/40">
                          <Button size="sm" variant="outline" className="text-xs" onClick={() => router.push('/dashboard/learning-material')}>
                            View Notes <ChevronRight className="h-3 w-3 ml-1" />
                          </Button>
                          <Button size="sm" variant="outline" className="text-xs" onClick={() => router.push('/dashboard/mcqs')}>
                            View MCQs <ChevronRight className="h-3 w-3 ml-1" />
                          </Button>
                          <Button size="sm" variant="outline" className="text-xs" onClick={() => router.push('/dashboard/assignments')}>
                            View Homework <ChevronRight className="h-3 w-3 ml-1" />
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* Cancel action */}
                    {isGenerating && (
                      <Button variant="outline" size="sm" className="w-full text-xs text-red-600 hover:bg-red-500/10" onClick={cancelGeneration}>
                        Cancel Generation
                      </Button>
                    )}
                  </div>
                )}

              </CardContent>
            </Card>
          </div>

        </div>
      )}
    </div>
  );
}
