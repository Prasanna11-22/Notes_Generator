'use client';

import React from 'react';
import { useAppStore } from '@/store/useAppStore';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Sparkles,
  BookOpen,
  HelpCircle,
  FileSpreadsheet,
  PlusCircle,
  ArrowRight,
  TrendingUp,
  FileText,
  Clock,
  Lightbulb,
} from 'lucide-react';
import Link from 'next/link';

export default function DashboardHome() {
  const { user, history, isConfigured, selectedCourse, selectedTopic } = useAppStore();

  const stats = [
    { name: 'Active Courses', value: '4', icon: BookOpen, change: '+1 this sem', color: 'text-primary bg-primary/10' },
    { name: 'MCQs in Bank', value: '142', icon: HelpCircle, change: '+24 this week', color: 'text-secondary bg-secondary/10' },
    { name: 'Assignments Drafted', value: '18', icon: FileSpreadsheet, change: '6 formats', color: 'text-amber-600 bg-amber-500/10' },
    { name: 'Ingested Resources', value: '14 files', icon: FileText, change: '24.2 MB total', color: 'text-purple-600 bg-purple-500/10' },
  ];

  const quickActions = [
    { name: 'Configure Course', desc: 'Select department, unit, and topics', href: '/dashboard/courses', icon: PlusCircle, btnText: 'Configure' },
    { name: 'Generate Content', desc: 'Instantly run multi-agent drafts', href: '/dashboard/generate', icon: Sparkles, btnText: 'Generate', disabled: !isConfigured },
  ];

  const templates = [
    { name: 'Bloom-Balanced Assessment', desc: '40% Remember, 40% Apply, 20% Evaluate split quiz', count: '10 MCQs + 3 Short Qs' },
    { name: 'Case-Study Assignment', desc: 'Flipped classroom format with complete grading rubric', count: '2 Long Qs + Rubric' },
    { name: 'Socratic Concept Guide', desc: 'In-depth notes, worked examples, and discussion triggers', count: '5 Concepts + Examples' },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Welcome Banner */}
      <div className="relative overflow-hidden rounded-2xl border border-primary/10 bg-primary/5 dark:bg-primary/10 p-6 sm:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="absolute top-0 right-0 h-40 w-40 rounded-full bg-primary/10 dark:bg-primary/5 blur-3xl pointer-events-none" />
        <div className="space-y-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 text-primary dark:bg-primary/20 text-xs font-semibold">
            <Sparkles className="h-3.5 w-3.5 text-secondary" />
            System Ready
          </div>
          <h2 className="font-heading font-bold text-2xl tracking-tight">
            Welcome back, {user.name}
          </h2>
          <p className="text-sm text-muted-custom max-w-xl">
            {isConfigured ? (
              <>
                You are currently working on{' '}
                <strong className="text-foreground">{selectedCourse}</strong> &gt;{' '}
                <strong className="text-foreground">{selectedTopic}</strong>. Ready to generate.
              </>
            ) : (
              'Set up a department curriculum, upload files, and configure preferences to start generating cognitive materials.'
            )}
          </p>
        </div>
        <div className="shrink-0">
          <Link href={isConfigured ? '/dashboard/generate' : '/dashboard/courses'}>
            <Button className="shadow-xs cursor-pointer">
              {isConfigured ? 'Start Generation' : 'Configure Course'} <ArrowRight className="h-4 w-4 ml-1.5" />
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Widgets */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.name} className="p-6 bg-card border border-border-custom hover:shadow-xs transition-shadow">
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-semibold text-muted-custom uppercase tracking-wider">{stat.name}</span>
                <div className={`h-9 w-9 rounded-xl flex items-center justify-center ${stat.color}`}>
                  <Icon className="h-4.5 w-4.5" />
                </div>
              </div>
              <div className="space-y-1">
                <h3 className="font-heading font-extrabold text-2xl tracking-tight">{stat.value}</h3>
                <p className="text-[10px] text-muted-custom flex items-center gap-1">
                  <TrendingUp className="h-3 w-3 text-secondary" />
                  {stat.change}
                </p>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Main Grid: Left Side Recent/Actions, Right Side Activity/Tips */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left 2 Columns */}
        <div className="lg:col-span-2 space-y-8">
          {/* Quick Actions & Templates */}
          <Card className="border border-border-custom bg-card">
            <CardHeader>
              <CardTitle>Content Setup Tools</CardTitle>
              <CardDescription>Launch new curriculum sessions or continue editing drafts.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Action Buttons Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {quickActions.map((act) => {
                  const Icon = act.icon;
                  return (
                    <div
                      key={act.name}
                      className="p-4.5 rounded-xl border border-border-custom hover:border-primary/20 bg-bg-secondary/40 flex flex-col justify-between gap-4 transition-all"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <Icon className="h-4.5 w-4.5 text-primary" />
                          <h4 className="font-semibold text-sm">{act.name}</h4>
                        </div>
                        <p className="text-xs text-muted-custom leading-normal">{act.desc}</p>
                      </div>
                      <Link href={act.href} className="w-full">
                        <Button
                          variant={act.btnText === 'Generate' ? 'primary' : 'outline'}
                          size="sm"
                          disabled={act.disabled}
                          className="w-full text-xs"
                        >
                          {act.btnText}
                        </Button>
                      </Link>
                    </div>
                  );
                })}
              </div>

              {/* Templates */}
              <div className="space-y-3.5 pt-2">
                <h4 className="font-semibold text-xs text-muted-custom uppercase tracking-wider">Suggested Pedagogical Templates</h4>
                <div className="space-y-2.5">
                  {templates.map((tpl) => (
                    <div
                      key={tpl.name}
                      className="p-3.5 rounded-xl border border-border-custom/50 hover:bg-muted-bg flex items-center justify-between gap-4 transition-colors cursor-pointer"
                    >
                      <div className="space-y-0.5">
                        <h5 className="font-semibold text-xs">{tpl.name}</h5>
                        <p className="text-[11px] text-muted-custom">{tpl.desc}</p>
                      </div>
                      <span className="shrink-0 text-[10px] font-semibold bg-bg-secondary px-2.5 py-1 rounded-md text-muted-custom">
                        {tpl.count}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Recent History Table */}
          <Card className="border border-border-custom bg-card">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Recent Generated Files</CardTitle>
                <CardDescription>Access and download assessment materials created recently.</CardDescription>
              </div>
              <Link href="/dashboard/history" className="text-xs font-semibold text-primary hover:underline">
                View All
              </Link>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-border-custom/80 text-muted-custom font-semibold">
                      <th className="pb-3 pr-4">Date</th>
                      <th className="pb-3 px-4">Topic</th>
                      <th className="pb-3 px-4">Curriculum</th>
                      <th className="pb-3 pl-4 text-right">Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.slice(0, 3).map((item) => (
                      <tr key={item.id} className="border-b border-border-custom/40 hover:bg-muted-bg/30 transition-colors">
                        <td className="py-3.5 pr-4 text-muted-custom font-medium">{item.date}</td>
                        <td className="py-3.5 px-4 font-semibold">{item.topic}</td>
                        <td className="py-3.5 px-4 text-muted-custom">{item.courseName}</td>
                        <td className="py-3.5 pl-4 text-right">
                          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-green-500/10 text-green-600 dark:text-green-400 font-semibold text-[10px]">
                            {item.mcqCount} MCQs + {item.assignmentCount} Qs
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right 1 Column */}
        <div className="space-y-8">
          {/* AI Tip Card */}
          <Card className="border border-amber-500/10 bg-amber-500/5 dark:bg-amber-500/10 p-6 relative overflow-hidden">
            <div className="absolute -top-6 -right-6 h-16 w-16 bg-amber-500/10 rounded-full blur-xl" />
            <div className="flex gap-3">
              <div className="h-9 w-9 rounded-xl bg-amber-500/25 text-amber-700 dark:text-amber-400 flex items-center justify-center shrink-0">
                <Lightbulb className="h-4.5 w-4.5" />
              </div>
              <div className="space-y-2">
                <h3 className="font-heading font-semibold text-sm text-amber-700 dark:text-amber-400">AI Pedagogical Tip</h3>
                <p className="text-xs text-amber-900/80 dark:text-amber-300/80 leading-relaxed">
                  For topics like <strong>Data Structures</strong>, configuring a higher percentage on the <strong>Apply</strong> and <strong>Analyze</strong> Bloom level sliders triggers the generator to formulate tree-rotation diagrams and memory recursive trace rubrics, improving student performance.
                </p>
              </div>
            </div>
          </Card>

          {/* Recent Activity Timeline */}
          <Card className="border border-border-custom bg-card">
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>Track agent executions and audit trails.</CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="relative pl-6 border-l border-border-custom/80 space-y-6">
                {/* Activity 1 */}
                <div className="relative">
                  <span className="absolute -left-8.5 top-0.5 h-5 w-5 rounded-full border border-border-custom bg-card flex items-center justify-center text-primary">
                    <Clock className="h-3 w-3" />
                  </span>
                  <div className="space-y-0.5">
                    <p className="text-xs font-semibold">MCQ bank updated</p>
                    <p className="text-[11px] text-muted-custom">Generated 5 AVL tree questions at 12:44 PM</p>
                  </div>
                </div>

                {/* Activity 2 */}
                <div className="relative">
                  <span className="absolute -left-8.5 top-0.5 h-5 w-5 rounded-full border border-border-custom bg-card flex items-center justify-center text-secondary">
                    <Clock className="h-3 w-3" />
                  </span>
                  <div className="space-y-0.5">
                    <p className="text-xs font-semibold">Resource uploaded</p>
                    <p className="text-[11px] text-muted-custom">Added Textbook_Advanced_Algorithms.pdf at 11:20 AM</p>
                  </div>
                </div>

                {/* Activity 3 */}
                <div className="relative">
                  <span className="absolute -left-8.5 top-0.5 h-5 w-5 rounded-full border border-border-custom bg-card flex items-center justify-center text-amber-500">
                    <Clock className="h-3 w-3" />
                  </span>
                  <div className="space-y-0.5">
                    <p className="text-xs font-semibold">Course selected</p>
                    <p className="text-[11px] text-muted-custom">Configured Data Structures course at 11:15 AM</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

      </div>
    </div>
  );
}
