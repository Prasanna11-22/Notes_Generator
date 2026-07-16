'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore, UploadedFile } from '@/store/useAppStore';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  GraduationCap,
  UploadCloud,
  FileText,
  Trash2,
  AlertTriangle,
  Sliders,
  CheckCircle,
  HelpCircle,
} from 'lucide-react';

export default function CourseConfigPage() {
  const router = useRouter();
  const store = useAppStore();

  // Cascading drop-down state
  const [dept, setDept] = useState(store.selectedDept || 'Computer Science & Engineering');
  const [sem, setSem] = useState(store.selectedSemester || 'Semester V');
  const [course, setCourse] = useState(store.selectedCourse || 'Data Structures (CS-301)');
  const [unit, setUnit] = useState(store.selectedUnit || 'Unit I: Basics & Trees');
  const [topic, setTopic] = useState(store.selectedTopic || 'Binary Search Trees & Balancing');

  // Preferences local state
  const [style, setStyle] = useState(store.teachingStyle);
  const [pedagogy, setPedagogy] = useState(store.pedagogy);
  const [difficulty, setDifficulty] = useState(store.difficulty);
  const [mcqCount, setMcqCount] = useState(store.mcqCount);
  const [assignmentCount, setAssignmentCount] = useState(store.assignmentCount);

  // Bloom taxonomy local sliders
  const [bloom, setBloom] = useState(store.bloomDistribution);

  // Uploading state simulator
  const [dragging, setDragging] = useState(false);

  // Validate Bloom sum
  const bloomTotal =
    Number(bloom.remember) +
    Number(bloom.understand) +
    Number(bloom.apply) +
    Number(bloom.analyze) +
    Number(bloom.evaluate) +
    Number(bloom.create);
  const isBloomValid = bloomTotal === 100;

  // Handle slider changes
  const handleBloomChange = (key: keyof typeof bloom, val: number) => {
    setBloom((prev) => ({
      ...prev,
      [key]: val,
    }));
  };

  // Drag and drop simulator
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = () => {
    setDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      simulateFileUpload(files[0].name, files[0].size);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      simulateFileUpload(files[0].name, files[0].size);
    }
  };

  const simulateFileUpload = (filename: string, sizeInBytes: number) => {
    const sizeStr = (sizeInBytes / (1024 * 1024)).toFixed(1) + ' MB';
    const id = 'f_' + Date.now();
    
    const newFile: UploadedFile = {
      id,
      name: filename,
      size: sizeStr === '0.0 MB' ? '0.8 MB' : sizeStr,
      status: 'uploading',
      progress: 0,
    };
    
    store.addUploadedFile(newFile);

    let progress = 0;
    const interval = setInterval(() => {
      progress += 20;
      if (progress <= 100) {
        store.updateFileProgress(id, progress, progress === 100 ? 'completed' : 'uploading');
      } else {
        clearInterval(interval);
      }
    }, 400);
  };

  // Submit and save configuration
  const handleSave = () => {
    if (!isBloomValid) return;

    // Save configuration
    store.setConfig({
      dept,
      sem,
      course,
      unit,
      topic,
    });

    // Save preferences
    store.setPreferences({
      teachingStyle: style,
      pedagogy,
      difficulty,
      mcqCount,
      assignmentCount,
      bloomDistribution: bloom,
    });

    // Navigate to generation step
    router.push('/dashboard/generate');
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-heading font-bold text-2xl tracking-tight">Curriculum & Preferences Configuration</h2>
          <p className="text-xs text-muted-custom">Align syllabus elements, ingest resource materials, and establish target Bloom distributions.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        
        {/* Left Side: Setup and Upload (3/5 columns) */}
        <div className="lg:col-span-3 space-y-8">
          
          {/* Step 1: Cascading Dropdowns */}
          <Card className="border border-border-custom bg-card">
            <CardHeader className="flex flex-row items-center gap-3">
              <div className="h-9 w-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                <GraduationCap className="h-4.5 w-4.5" />
              </div>
              <div>
                <CardTitle>Curriculum Selection</CardTitle>
                <CardDescription>Pinpoint target curriculum nodes from departmental courses.</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Department */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-custom">Department</label>
                  <select
                    value={dept}
                    onChange={(e) => setDept(e.target.value)}
                    className="w-full text-xs py-2.5 px-3 rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="Computer Science & Engineering">Computer Science & Engineering</option>
                    <option value="Information Technology">Information Technology</option>
                    <option value="Electrical Engineering">Electrical Engineering</option>
                  </select>
                </div>

                {/* Semester */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-custom">Semester</label>
                  <select
                    value={sem}
                    onChange={(e) => setSem(e.target.value)}
                    className="w-full text-xs py-2.5 px-3 rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="Semester III">Semester III</option>
                    <option value="Semester IV">Semester IV</option>
                    <option value="Semester V">Semester V</option>
                    <option value="Semester VI">Semester VI</option>
                  </select>
                </div>
              </div>

              {/* Course */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-custom">Course</label>
                <select
                  value={course}
                  onChange={(e) => setCourse(e.target.value)}
                  className="w-full text-xs py-2.5 px-3 rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20"
                >
                  <option value="Data Structures (CS-301)">Data Structures (CS-301)</option>
                  <option value="Design & Analysis of Algorithms (CS-401)">Design & Analysis of Algorithms (CS-401)</option>
                  <option value="Computer Networks (CS-402)">Computer Networks (CS-402)</option>
                  <option value="Database Management Systems (CS-302)">Database Management Systems (CS-302)</option>
                </select>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Unit */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-custom">Target Unit</label>
                  <select
                    value={unit}
                    onChange={(e) => setUnit(e.target.value)}
                    className="w-full text-xs py-2.5 px-3 rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="Unit I: Basics & Trees">Unit I: Basics & Trees</option>
                    <option value="Unit II: Balancing & Graphs">Unit II: Balancing & Graphs</option>
                    <option value="Unit III: Advanced Indexing">Unit III: Advanced Indexing</option>
                  </select>
                </div>

                {/* Topic */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-custom">Target Topic</label>
                  <select
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    className="w-full text-xs py-2.5 px-3 rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20"
                  >
                    <option value="Binary Search Trees & Balancing">Binary Search Trees & Balancing</option>
                    <option value="Red-Black Tree Insertion rules">Red-Black Tree Insertion rules</option>
                    <option value="B/B+ Trees structure">B/B+ Trees structure</option>
                  </select>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Step 2: File Uploader */}
          <Card className="border border-border-custom bg-card">
            <CardHeader className="flex flex-row items-center gap-3">
              <div className="h-9 w-9 rounded-xl bg-secondary/10 text-secondary flex items-center justify-center">
                <UploadCloud className="h-4.5 w-4.5" />
              </div>
              <div>
                <CardTitle>Resource Ingestion</CardTitle>
                <CardDescription>Drag and drop text references, notes, or curriculum guidelines.</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Drag Zone */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all ${
                  dragging ? 'border-primary bg-primary/5' : 'border-border-custom bg-bg-secondary/40 hover:bg-bg-secondary/60'
                }`}
              >
                <input
                  type="file"
                  id="file-select"
                  onChange={handleFileSelect}
                  className="hidden"
                  accept=".pdf,.doc,.docx,.txt"
                />
                <label htmlFor="file-select" className="cursor-pointer space-y-3 block">
                  <UploadCloud className="h-10 w-10 text-muted-custom mx-auto" />
                  <div>
                    <p className="text-sm font-semibold">Drag and drop file here, or <span className="text-primary hover:underline">browse</span></p>
                    <p className="text-[10px] text-muted-custom">Supports PDF, DOCX, TXT up to 15MB</p>
                  </div>
                </label>
              </div>

              {/* Uploaded List */}
              {store.uploadedFiles.length > 0 && (
                <div className="space-y-3">
                  <h4 className="font-semibold text-xs text-muted-custom uppercase tracking-wider">Ingested Reference Materials</h4>
                  <div className="space-y-2">
                    {store.uploadedFiles.map((file) => (
                      <div
                        key={file.id}
                        className="p-3.5 rounded-xl border border-border-custom/60 hover:border-border-custom bg-card flex items-center justify-between gap-4 transition-all"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <FileText className="h-5 w-5 text-primary shrink-0" />
                          <div className="min-w-0">
                            <p className="text-xs font-semibold truncate">{file.name}</p>
                            <p className="text-[10px] text-muted-custom">{file.size} &bull; {file.status === 'uploading' ? `Uploading ${file.progress}%` : 'Ready'}</p>
                          </div>
                        </div>
                        {file.status === 'uploading' ? (
                          <div className="h-1.5 w-16 bg-bg-secondary rounded-full overflow-hidden shrink-0">
                            <div className="h-full bg-primary transition-all duration-300" style={{ width: `${file.progress}%` }} />
                          </div>
                        ) : (
                          <button
                            onClick={() => store.deleteFile(file.id)}
                            className="h-8 w-8 rounded-lg flex items-center justify-center text-muted-custom hover:text-red-500 hover:bg-red-500/10 transition-colors"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Side: Preferences and Bloom Sliders (2/5 columns) */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* Step 3: Pedagogy & Sliders */}
          <Card className="border border-border-custom bg-card">
            <CardHeader className="flex flex-row items-center gap-3">
              <div className="h-9 w-9 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-500 flex items-center justify-center">
                <Sliders className="h-4.5 w-4.5" />
              </div>
              <div>
                <CardTitle>Faculty Preferences</CardTitle>
                <CardDescription>Configure styles, question volume, and target Bloom taxonomy.</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              
              {/* Teaching Style & Difficulty */}
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-muted-custom">Teaching Style</label>
                    <select
                      value={style}
                      onChange={(e) => setStyle(e.target.value)}
                      className="w-full text-xs py-2 px-2.5 rounded-xl border border-border-custom bg-bg-secondary"
                    >
                      <option value="socratic">Socratic</option>
                      <option value="example-driven">Example Driven</option>
                      <option value="interactive">Interactive</option>
                      <option value="standard">Standard/Academic</option>
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-muted-custom">Difficulty</label>
                    <select
                      value={difficulty}
                      onChange={(e) => setDifficulty(e.target.value as any)}
                      className="w-full text-xs py-2 px-2.5 rounded-xl border border-border-custom bg-bg-secondary"
                    >
                      <option value="easy">Easy</option>
                      <option value="medium">Medium</option>
                      <option value="hard">Hard</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-muted-custom">MCQ Count</label>
                    <input
                      type="number"
                      value={mcqCount}
                      min="1"
                      max="30"
                      onChange={(e) => setMcqCount(Number(e.target.value))}
                      className="w-full text-xs py-2 px-2.5 rounded-xl border border-border-custom bg-bg-secondary"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-muted-custom">Assignment Count</label>
                    <input
                      type="number"
                      value={assignmentCount}
                      min="1"
                      max="10"
                      onChange={(e) => setAssignmentCount(Number(e.target.value))}
                      className="w-full text-xs py-2 px-2.5 rounded-xl border border-border-custom bg-bg-secondary"
                    />
                  </div>
                </div>
              </div>

              {/* Bloom Taxonomy Sliders */}
              <div className="space-y-4 pt-4 border-t border-border-custom/50">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-xs text-muted-custom uppercase tracking-wider">Bloom Distribution (%)</h4>
                  <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md font-bold text-[10px] ${
                    isBloomValid ? 'bg-green-500/10 text-green-600 dark:text-green-400' : 'bg-red-500/10 text-red-600 dark:text-red-400'
                  }`}>
                    {isBloomValid ? <CheckCircle className="h-3 w-3" /> : <AlertTriangle className="h-3 w-3 animate-bounce" />}
                    Sum: {bloomTotal}% / 100%
                  </span>
                </div>

                {!isBloomValid && (
                  <p className="text-[10px] text-red-500 dark:text-red-400 font-medium">
                    * The total percentage must equal exactly 100% before you can generate content.
                  </p>
                )}

                <div className="space-y-3.5">
                  {/* Remember */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs font-medium">
                      <span>Remember</span>
                      <span className="text-muted-custom">{bloom.remember}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      step="5"
                      value={bloom.remember}
                      onChange={(e) => handleBloomChange('remember', Number(e.target.value))}
                      className="w-full h-1 bg-bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
                    />
                  </div>

                  {/* Understand */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs font-medium">
                      <span>Understand</span>
                      <span className="text-muted-custom">{bloom.understand}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      step="5"
                      value={bloom.understand}
                      onChange={(e) => handleBloomChange('understand', Number(e.target.value))}
                      className="w-full h-1 bg-bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
                    />
                  </div>

                  {/* Apply */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs font-medium">
                      <span>Apply</span>
                      <span className="text-muted-custom">{bloom.apply}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      step="5"
                      value={bloom.apply}
                      onChange={(e) => handleBloomChange('apply', Number(e.target.value))}
                      className="w-full h-1 bg-bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
                    />
                  </div>

                  {/* Analyze */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs font-medium">
                      <span>Analyze</span>
                      <span className="text-muted-custom">{bloom.analyze}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      step="5"
                      value={bloom.analyze}
                      onChange={(e) => handleBloomChange('analyze', Number(e.target.value))}
                      className="w-full h-1 bg-bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
                    />
                  </div>

                  {/* Evaluate */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs font-medium">
                      <span>Evaluate</span>
                      <span className="text-muted-custom">{bloom.evaluate}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      step="5"
                      value={bloom.evaluate}
                      onChange={(e) => handleBloomChange('evaluate', Number(e.target.value))}
                      className="w-full h-1 bg-bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
                    />
                  </div>

                  {/* Create */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs font-medium">
                      <span>Create</span>
                      <span className="text-muted-custom">{bloom.create}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      step="5"
                      value={bloom.create}
                      onChange={(e) => handleBloomChange('create', Number(e.target.value))}
                      className="w-full h-1 bg-bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
                    />
                  </div>
                </div>
              </div>

              {/* Submit Config */}
              <div className="pt-4">
                <Button
                  onClick={handleSave}
                  disabled={!isBloomValid}
                  className="w-full shadow-xs cursor-pointer"
                >
                  Save & Continue to Generation
                </Button>
              </div>

            </CardContent>
          </Card>
        </div>

      </div>
    </div>
  );
}
