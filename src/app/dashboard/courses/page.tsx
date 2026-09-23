'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore, UploadedFile } from '@/store/useAppStore';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useTranslation } from '@/hooks/useTranslation';
import {
  GraduationCap,
  UploadCloud,
  FileText,
  Trash2,
  AlertTriangle,
  Sliders,
  CheckCircle,
  Plus,
  X,
} from 'lucide-react';

interface DeptItem {
  id: string;
  name: string;
  code: string;
}

interface SemItem {
  id: string;
  number: number;
  program_id: string;
}

interface CourseItem {
  id: string;
  course_code: string;
  course_title: string;
  semester_id: string;
  credits: number;
}

interface UnitItem {
  id: string;
  unit_number: number;
  title: string;
}

interface TopicItem {
  id: string;
  topic_name: string;
}

function romanize(num: number): string {
  const lookup: Record<string, number> = { V: 5, IV: 4, I: 1 };
  let roman = '';
  let n = num;
  // Handle basic semesters 1-8
  if (n === 8) return 'VIII';
  if (n === 7) return 'VII';
  if (n === 6) return 'VI';
  if (n === 5) return 'V';
  if (n === 4) return 'IV';
  if (n === 3) return 'III';
  if (n === 2) return 'II';
  if (n === 1) return 'I';
  return String(num);
}

export default function CourseConfigPage() {
  const router = useRouter();
  const store = useAppStore();
  const { t, lang } = useTranslation();

  // Dynamic dropdown lists
  const [departments, setDepartments] = useState<DeptItem[]>([]);
  const [semesters, setSemesters] = useState<SemItem[]>([]);
  const [courses, setCourses] = useState<CourseItem[]>([]);
  const [units, setUnits] = useState<UnitItem[]>([]);
  const [topics, setTopics] = useState<TopicItem[]>([]);

  // Selection states
  const [dept, setDept] = useState(store.selectedDept || '');
  const [sem, setSem] = useState(store.selectedSemester || '');
  const [course, setCourse] = useState(store.selectedCourse || '');
  const [unit, setUnit] = useState(store.selectedUnit || '');
  const [topic, setTopic] = useState(store.selectedTopic || '');

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

  // Add Course Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newCode, setNewCode] = useState('');
  const [newCredits, setNewCredits] = useState(3);
  const [newDesc, setNewDesc] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Validate Bloom sum
  const bloomTotal =
    Number(bloom.remember) +
    Number(bloom.understand) +
    Number(bloom.apply) +
    Number(bloom.analyze) +
    Number(bloom.evaluate) +
    Number(bloom.create);
  const isBloomValid = bloomTotal === 100;

  // Fetch helper
  const fetchWithAuth = async (url: string, options: RequestInit = {}) => {
    const token = localStorage.getItem('access_token');
    const headers = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    };
    const res = await fetch(url, { ...options, headers });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.message || `API error: ${res.status}`);
    }
    return res.json();
  };

  // Initial fetch
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const deptsRes = await fetchWithAuth('http://127.0.0.1:8000/api/v1/departments?limit=100');
        const deptsData: DeptItem[] = deptsRes.data || [];
        setDepartments(deptsData);

        const semsRes = await fetchWithAuth('http://127.0.0.1:8000/api/v1/semesters?limit=100');
        const semsData: SemItem[] = semsRes.data || [];
        setSemesters(semsData);

        const coursesRes = await fetchWithAuth('http://127.0.0.1:8000/api/v1/courses?limit=1000');
        const coursesData: CourseItem[] = coursesRes.data || [];
        setCourses(coursesData);

        // Resolve default or restored selections
        let initialDept = store.selectedDept;
        if (!initialDept && deptsData.length > 0) {
          initialDept = deptsData[0].name;
        }
        setDept(initialDept);

        let initialSem = store.selectedSemester;
        if (!initialSem && semsData.length > 0) {
          initialSem = `Semester ${romanize(semsData[0].number)}`;
        }
        setSem(initialSem);

        // Find course matching selection
        let selectedCourseObj = coursesData.find(c => c.course_title === store.selectedCourse);
        if (!selectedCourseObj && coursesData.length > 0) {
          // Filter courses for currently selected semester
          const currentSemObj = semsData.find(s => `Semester ${romanize(s.number)}` === initialSem);
          if (currentSemObj) {
            const filtered = coursesData.filter(c => c.semester_id === currentSemObj.id);
            if (filtered.length > 0) selectedCourseObj = filtered[0];
          }
          if (!selectedCourseObj) selectedCourseObj = coursesData[0];
        }

        if (selectedCourseObj) {
          setCourse(selectedCourseObj.course_title);
          // Fetch units
          const unitsRes = await fetchWithAuth(`http://127.0.0.1:8000/api/v1/units?course_id=${selectedCourseObj.id}&limit=100`);
          const unitsData: UnitItem[] = unitsRes.data || [];
          setUnits(unitsData);

          let selectedUnitObj = unitsData.find(u => u.title === store.selectedUnit);
          if (!selectedUnitObj && unitsData.length > 0) {
            selectedUnitObj = unitsData[0];
          }

          if (selectedUnitObj) {
            setUnit(selectedUnitObj.title);
            // Fetch topics
            const topicsRes = await fetchWithAuth(`http://127.0.0.1:8000/api/v1/topics?unit_id=${selectedUnitObj.id}&limit=100`);
            const topicsData: TopicItem[] = topicsRes.data || [];
            setTopics(topicsData);

            let selectedTopicObj = topicsData.find(t => t.topic_name === store.selectedTopic);
            if (!selectedTopicObj && topicsData.length > 0) {
              selectedTopicObj = topicsData[0];
            }
            if (selectedTopicObj) {
              setTopic(selectedTopicObj.topic_name);
            }
          }
        }
      } catch (e) {
        console.error('Failed to load initial curriculum structures', e);
      }
    };
    loadInitialData();
  }, []);

  // Update courses when semester changes
  useEffect(() => {
    if (!sem || semesters.length === 0 || courses.length === 0) return;
    const semNum = Number(sem.replace(/\D/g, ''));
    const currentSemObj = semesters.find(s => s.number === semNum || `Semester ${romanize(s.number)}` === sem);
    if (!currentSemObj) return;

    const filteredCourses = courses.filter(c => c.semester_id === currentSemObj.id);
    if (filteredCourses.length > 0) {
      const match = filteredCourses.find(c => c.course_title === course) || filteredCourses[0];
      setCourse(match.course_title);
    } else {
      setCourse('');
      setUnits([]);
      setUnit('');
      setTopics([]);
      setTopic('');
    }
  }, [sem, semesters, courses]);

  // Update units/topics when course changes
  useEffect(() => {
    if (!course || courses.length === 0) return;
    const selectedCourseObj = courses.find(c => c.course_title === course);
    if (!selectedCourseObj) return;

    const loadUnits = async () => {
      try {
        const unitsRes = await fetchWithAuth(`http://127.0.0.1:8000/api/v1/units?course_id=${selectedCourseObj.id}&limit=100`);
        const unitsData: UnitItem[] = unitsRes.data || [];
        setUnits(unitsData);

        if (unitsData.length > 0) {
          const match = unitsData.find(u => u.title === unit) || unitsData[0];
          setUnit(match.title);
        } else {
          setUnit('');
          setTopics([]);
          setTopic('');
        }
      } catch (e) {
        console.error(e);
      }
    };
    loadUnits();
  }, [course, courses]);

  // Update topics when unit changes
  useEffect(() => {
    if (!unit || units.length === 0) return;
    const selectedUnitObj = units.find(u => u.title === unit);
    if (!selectedUnitObj) return;

    const loadTopics = async () => {
      try {
        const topicsRes = await fetchWithAuth(`http://127.0.0.1:8000/api/v1/topics?unit_id=${selectedUnitObj.id}&limit=100`);
        const topicsData: TopicItem[] = topicsRes.data || [];
        setTopics(topicsData);

        if (topicsData.length > 0) {
          const match = topicsData.find(t => t.topic_name === topic) || topicsData[0];
          setTopic(match.topic_name);
        } else {
          setTopic('');
        }
      } catch (e) {
        console.error(e);
      }
    };
    loadTopics();
  }, [unit, units]);

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

  const handleAddCourseSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newCode.trim()) {
      setErrorMsg(lang === 'ta' ? 'பாடத்தின் பெயர் மற்றும் குறியீடு கட்டாயமாகும்.' : 'Course Title and Code are required.');
      return;
    }
    setErrorMsg('');
    setIsSubmitting(true);
    try {
      // Find current selected semester ID
      const semNum = Number(sem.replace(/\D/g, ''));
      const selectedSemObj = semesters.find(s => s.number === semNum || `Semester ${romanize(s.number)}` === sem);
      if (!selectedSemObj) {
        throw new Error(lang === 'ta' ? 'தயவுசெய்து சரியான பருவத்தைத் தேர்ந்தெடுக்கவும்.' : 'Please select a valid semester first.');
      }

      // Create course
      const coursePayload = {
        semester_id: selectedSemObj.id,
        course_code: newCode.trim(),
        course_title: newTitle.trim(),
        credits: newCredits,
        description: newDesc.trim() || undefined,
      };

      const courseRes = await fetchWithAuth('http://127.0.0.1:8000/api/v1/courses', {
        method: 'POST',
        body: JSON.stringify(coursePayload),
      });

      const newCourse = courseRes.data;

      // To keep relationships with units and topics intact,
      // create a default unit and topic for this course
      const unitPayload = {
        course_id: newCourse.id,
        unit_number: 1,
        title: 'Unit I: Basics & Introduction',
      };
      const unitRes = await fetchWithAuth('http://127.0.0.1:8000/api/v1/units', {
        method: 'POST',
        body: JSON.stringify(unitPayload),
      });
      const newUnit = unitRes.data;

      const topicPayload = {
        unit_id: newUnit.id,
        topic_name: 'Introduction and Foundational Concepts',
        description: `Overview of ${newTitle}`,
      };
      await fetchWithAuth('http://127.0.0.1:8000/api/v1/topics', {
        method: 'POST',
        body: JSON.stringify(topicPayload),
      });

      // Refresh list of courses
      const freshCoursesRes = await fetchWithAuth('http://127.0.0.1:8000/api/v1/courses?limit=1000');
      const freshData = freshCoursesRes.data || [];
      setCourses(freshData);

      // Auto-select newly created course
      setCourse(newCourse.course_title);
      
      // Fetch units/topics for the new course
      setUnits([newUnit]);
      setUnit(newUnit.title);
      setTopics([{ id: 'default-t', topic_name: 'Introduction and Foundational Concepts' }]);
      setTopic('Introduction and Foundational Concepts');

      setShowAddModal(false);
      setNewTitle('');
      setNewCode('');
      setNewCredits(3);
      setNewDesc('');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to create course.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-heading font-bold text-2xl tracking-tight">{t('courses.title')}</h2>
          <p className="text-xs text-muted-custom">{t('courses.subtitle')}</p>
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
                <CardTitle>{t('courses.card_title')}</CardTitle>
                <CardDescription>{t('courses.card_desc')}</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Department */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-custom">{t('courses.dept')}</label>
                  <select
                    value={dept}
                    onChange={(e) => setDept(e.target.value)}
                    className="w-full text-xs py-2.5 px-3 rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 text-foreground"
                  >
                    {departments.map((d) => (
                      <option key={d.id} value={d.name}>{d.name}</option>
                    ))}
                    {departments.length === 0 && (
                      <option value="Computer Science & Engineering">Computer Science & Engineering</option>
                    )}
                  </select>
                </div>

                {/* Semester */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-custom">{t('courses.sem')}</label>
                  <select
                    value={sem}
                    onChange={(e) => setSem(e.target.value)}
                    className="w-full text-xs py-2.5 px-3 rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 text-foreground"
                  >
                    {semesters.map((s) => (
                      <option key={s.id} value={`Semester ${romanize(s.number)}`}>{`Semester ${romanize(s.number)}`}</option>
                    ))}
                    {semesters.length === 0 && (
                      <>
                        <option value="Semester III">Semester III</option>
                        <option value="Semester IV">Semester IV</option>
                        <option value="Semester V">Semester V</option>
                        <option value="Semester VI">Semester VI</option>
                      </>
                    )}
                  </select>
                </div>
              </div>

              {/* Course Selector with Add Course button */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-muted-custom">{t('courses.course')}</label>
                  <button
                    onClick={() => setShowAddModal(true)}
                    className="text-[10px] text-primary hover:underline font-bold flex items-center gap-0.5"
                  >
                    <Plus className="h-3 w-3" /> {t('courses.add_course')}
                  </button>
                </div>
                <select
                  value={course}
                  onChange={(e) => setCourse(e.target.value)}
                  className="w-full text-xs py-2.5 px-3 rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 text-foreground"
                >
                  {courses
                    .filter((c) => {
                      const semNum = Number(sem.replace(/\D/g, ''));
                      const currentSemObj = semesters.find(s => s.number === semNum || `Semester ${romanize(s.number)}` === sem);
                      return currentSemObj ? c.semester_id === currentSemObj.id : true;
                    })
                    .map((c) => (
                      <option key={c.id} value={c.course_title}>{c.course_title}</option>
                    ))}
                  {courses.length === 0 && (
                    <option value="">-- No Courses Created --</option>
                  )}
                </select>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Unit */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-custom">{t('courses.unit')}</label>
                  <select
                    value={unit}
                    onChange={(e) => setUnit(e.target.value)}
                    className="w-full text-xs py-2.5 px-3 rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 text-foreground"
                  >
                    {units.map((u) => (
                      <option key={u.id} value={u.title}>{u.title}</option>
                    ))}
                    {units.length === 0 && (
                      <option value="">-- No Units Created --</option>
                    )}
                  </select>
                </div>

                {/* Topic */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-custom">{t('courses.topic')}</label>
                  <select
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    className="w-full text-xs py-2.5 px-3 rounded-xl border border-border-custom bg-bg-secondary focus:outline-hidden focus:ring-2 focus:ring-primary/20 text-foreground"
                  >
                    {topics.map((t) => (
                      <option key={t.id} value={t.topic_name}>{t.topic_name}</option>
                    ))}
                    {topics.length === 0 && (
                      <option value="">-- No Topics Created --</option>
                    )}
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
                <CardTitle>{t('courses.ingestion')}</CardTitle>
                <CardDescription>{t('courses.ingestion_desc')}</CardDescription>
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
                    <p className="text-sm font-semibold">{t('courses.drop_prompt')}</p>
                    <p className="text-[10px] text-muted-custom">{t('courses.drop_info')}</p>
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
                <CardTitle>{t('courses.preferences')}</CardTitle>
                <CardDescription>{t('courses.preferences_desc')}</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              
              {/* Teaching Style & Difficulty */}
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-muted-custom">{t('courses.style')}</label>
                    <select
                      value={style}
                      onChange={(e) => setStyle(e.target.value)}
                      className="w-full text-xs py-2 px-2.5 rounded-xl border border-border-custom bg-bg-secondary text-foreground"
                    >
                      <option value="socratic">Socratic</option>
                      <option value="example-driven">Example Driven</option>
                      <option value="interactive">Interactive</option>
                      <option value="standard">Standard/Academic</option>
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-muted-custom">{t('courses.difficulty')}</label>
                    <select
                      value={difficulty}
                      onChange={(e) => setDifficulty(e.target.value as any)}
                      className="w-full text-xs py-2 px-2.5 rounded-xl border border-border-custom bg-bg-secondary text-foreground"
                    >
                      <option value="easy">Easy</option>
                      <option value="medium">Medium</option>
                      <option value="hard">Hard</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-muted-custom">{t('courses.mcqs')}</label>
                    <input
                      type="number"
                      value={mcqCount}
                      min="1"
                      max="30"
                      onChange={(e) => setMcqCount(Number(e.target.value))}
                      className="w-full text-xs py-2 px-2.5 rounded-xl border border-border-custom bg-bg-secondary text-foreground"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-muted-custom">{t('courses.assignments')}</label>
                    <input
                      type="number"
                      value={assignmentCount}
                      min="1"
                      max="10"
                      onChange={(e) => setAssignmentCount(Number(e.target.value))}
                      className="w-full text-xs py-2 px-2.5 rounded-xl border border-border-custom bg-bg-secondary text-foreground"
                    />
                  </div>
                </div>
              </div>

              {/* Bloom Taxonomy Sliders */}
              <div className="space-y-4 pt-4 border-t border-border-custom/50">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-xs text-muted-custom uppercase tracking-wider">{t('courses.bloom')}</h4>
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

                <div className="space-y-3.5 text-foreground">
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
                  disabled={!isBloomValid || !course}
                  className="w-full shadow-xs cursor-pointer"
                >
                  {t('courses.save_continue')}
                </Button>
              </div>

            </CardContent>
          </Card>
        </div>

      </div>

      {/* Add Course Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 dark:bg-slate-950/60 backdrop-blur-xs">
          <div className="bg-card w-full max-w-md rounded-2xl border border-border-custom shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="flex h-16 items-center justify-between px-6 border-b border-border-custom">
              <h3 className="font-heading font-semibold text-base">{t('courses.add_course_title')}</h3>
              <button onClick={() => setShowAddModal(false)} className="h-8 w-8 rounded-lg hover:bg-muted-bg flex items-center justify-center text-muted-custom">
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleAddCourseSubmit} className="p-6 space-y-4">
              {errorMsg && (
                <div className="p-3 text-[11px] bg-red-500/10 border border-red-500/20 text-red-600 rounded-lg font-medium">
                  {errorMsg}
                </div>
              )}

              {/* Course Title */}
              <div className="space-y-1.5 text-xs">
                <label className="font-semibold text-muted-custom">{t('courses.course_name')}</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Artificial Intelligence"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border-custom bg-bg-secondary text-foreground focus:outline-hidden"
                />
              </div>

              {/* Course Code */}
              <div className="space-y-1.5 text-xs">
                <label className="font-semibold text-muted-custom">{t('courses.course_code')}</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. CS-403"
                  value={newCode}
                  onChange={(e) => setNewCode(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-border-custom bg-bg-secondary text-foreground focus:outline-hidden"
                />
              </div>

              {/* Credits */}
              <div className="space-y-1.5 text-xs">
                <label className="font-semibold text-muted-custom">{t('courses.credits')}</label>
                <input
                  type="number"
                  min="1"
                  max="6"
                  required
                  value={newCredits}
                  onChange={(e) => setNewCredits(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-lg border border-border-custom bg-bg-secondary text-foreground focus:outline-hidden"
                />
              </div>

              {/* Description */}
              <div className="space-y-1.5 text-xs">
                <label className="font-semibold text-muted-custom">{t('courses.description')}</label>
                <textarea
                  placeholder="Course Overview..."
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  className="w-full h-20 px-3 py-2 rounded-lg border border-border-custom bg-bg-secondary text-foreground focus:outline-hidden resize-none"
                />
              </div>

              <div className="pt-2 flex gap-3">
                <Button type="button" variant="outline" className="flex-1 text-xs" onClick={() => setShowAddModal(false)}>
                  {t('common.cancel')}
                </Button>
                <Button type="submit" loading={isSubmitting} className="flex-1 text-xs">
                  {t('common.save')}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
