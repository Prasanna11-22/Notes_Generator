'use client';

import React from 'react';
import Link from 'next/link';
import { useAppStore } from '@/store/useAppStore';
import {
  GraduationCap,
  Sparkles,
  ArrowRight,
  BookOpen,
  CheckCircle,
  ShieldCheck,
  Zap,
  Globe,
  Sliders,
  ChevronRight,
  Sun,
  Moon,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

export default function LandingPage() {
  const { theme, setTheme } = useAppStore();

  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-300">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-background/80 backdrop-blur-md border-b border-border-custom/50 px-6 lg:px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm shadow-primary/25">
            <GraduationCap className="h-5.5 w-5.5" />
          </div>
          <span className="font-heading font-bold text-base tracking-tight text-primary">
            CampusBot <span className="text-secondary font-medium">AI</span>
          </span>
        </div>

        {/* Navigation */}
        <nav className="hidden md:flex items-center gap-6 lg:gap-8 text-sm font-medium text-muted-custom">
          <a href="#features" className="hover:text-foreground transition-colors">Features</a>
          <a href="#workflow" className="hover:text-foreground transition-colors">Workflow</a>
          <a href="#benefits" className="hover:text-foreground transition-colors">Benefits</a>
          <a href="#testimonials" className="hover:text-foreground transition-colors">Testimonials</a>
        </nav>

        {/* Action buttons */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
            className="h-10 w-10 flex items-center justify-center rounded-xl border border-border-custom hover:bg-muted-bg text-muted-custom transition-all"
          >
            {theme === 'light' ? <Moon className="h-4.5 w-4.5" /> : <Sun className="h-4.5 w-4.5" />}
          </button>
          
          <Link href="/login">
            <Button variant="ghost" size="sm" className="hidden sm:inline-flex">
              Sign In
            </Button>
          </Link>
          
          <Link href="/signup">
            <Button size="sm">
              Get Started
            </Button>
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative py-20 lg:py-32 px-6 lg:px-8 max-w-6xl mx-auto text-center">
        {/* Subtle Background Accent */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-72 h-72 rounded-full bg-primary/10 dark:bg-primary/5 blur-3xl pointer-events-none" />
        
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-primary/10 text-primary dark:bg-primary/20 text-xs font-semibold tracking-wide mb-6">
          <Sparkles className="h-3.5 w-3.5 animate-pulse text-secondary" />
          Next-Generation Academic Assistant
        </div>

        <h1 className="font-heading font-extrabold text-4xl sm:text-5xl lg:text-6xl tracking-tight leading-tight max-w-4xl mx-auto mb-6">
          Supercharge Academic Content & Assessment Generation
        </h1>
        
        <p className="text-base sm:text-lg text-muted-custom max-w-2xl mx-auto mb-10 leading-relaxed">
          Ingest textbooks, syllabus grids, and notes. Instantly compile lecture guides, assignment sheets, and validated Bloom-aligned question banks utilizing local and CPU-efficient AI orchestration.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link href="/signup">
            <Button size="lg" className="w-full sm:w-auto">
              Start Generating for Free <ArrowRight className="h-4.5 w-4.5 ml-1" />
            </Button>
          </Link>
          <a href="#features">
            <Button variant="outline" size="lg" className="w-full sm:w-auto">
              Explore Features
            </Button>
          </a>
        </div>
      </section>

      {/* Feature Grid Section */}
      <section id="features" className="py-20 bg-bg-secondary/40 border-t border-border-custom/50 px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="font-heading font-bold text-3xl tracking-tight mb-4">
              Designed Specifically for Academic Rigor
            </h2>
            <p className="text-sm text-muted-custom">
              Unlike generic AI writers, CampusBot AI respects your syllabus structure, target Course Outcomes (COs), and rigorous cognitive standards.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <Card hoverable className="p-6">
              <div className="h-12 w-12 rounded-xl bg-primary/15 text-primary flex items-center justify-center mb-5">
                <BookOpen className="h-6 w-6" />
              </div>
              <h3 className="font-heading font-semibold text-lg mb-2">Smart Resource Ingestion</h3>
              <p className="text-xs text-muted-custom leading-relaxed">
                Upload PDFs, textbooks, or faculty raw notes. The system parses, tags, and registers documents down to unit, topic, and page mapping details.
              </p>
            </Card>

            <Card hoverable className="p-6">
              <div className="h-12 w-12 rounded-xl bg-secondary/15 text-secondary flex items-center justify-center mb-5">
                <Sliders className="h-6 w-6" />
              </div>
              <h3 className="font-heading font-semibold text-lg mb-2">Bloom Taxonomy Controls</h3>
              <p className="text-xs text-muted-custom leading-relaxed">
                Precisely direct difficulty levels and Bloom distribution ratios (Remember, Apply, Create) with strict multi-agent validation loops.
              </p>
            </Card>

            <Card hoverable className="p-6">
              <div className="h-12 w-12 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-500 flex items-center justify-center mb-5">
                <ShieldCheck className="h-6 w-6" />
              </div>
              <h3 className="font-heading font-semibold text-lg mb-2">Multi-Agent Verification</h3>
              <p className="text-xs text-muted-custom leading-relaxed">
                State-machine workflows route draft questions to validator and deduplication agents, ensuring factual grounding and zero near-duplicates.
              </p>
            </Card>

            <Card hoverable className="p-6">
              <div className="h-12 w-12 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center mb-5">
                <Zap className="h-6 w-6" />
              </div>
              <h3 className="font-heading font-semibold text-lg mb-2">CPU-Efficient Local AI</h3>
              <p className="text-xs text-muted-custom leading-relaxed">
                Engineered to run locally on mid-range institution hardware, utilizing lightweight, quantized models like Qwen 2.5 and Phi 3.5 GGUF.
              </p>
            </Card>

            <Card hoverable className="p-6">
              <div className="h-12 w-12 rounded-xl bg-green-500/10 text-green-600 dark:text-green-400 flex items-center justify-center mb-5">
                <Globe className="h-6 w-6" />
              </div>
              <h3 className="font-heading font-semibold text-lg mb-2">Curriculum Integrations</h3>
              <p className="text-xs text-muted-custom leading-relaxed">
                Synchronizes with standard departmental curricula, syllabus targets, and question banking policies out of the box.
              </p>
            </Card>

            <Card hoverable className="p-6">
              <div className="h-12 w-12 rounded-xl bg-rose-500/10 text-rose-600 dark:text-rose-400 flex items-center justify-center mb-5">
                <CheckCircle className="h-6 w-6" />
              </div>
              <h3 className="font-heading font-semibold text-lg mb-2">Sleek LMS Exporting</h3>
              <p className="text-xs text-muted-custom leading-relaxed">
                Single-click exports to PDF, DOCX, Moodle-ready XML, or Canvas-compatible formats to easily synchronize with learning management systems.
              </p>
            </Card>
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section id="testimonials" className="py-20 px-6 lg:px-8 max-w-6xl mx-auto">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <h2 className="font-heading font-bold text-3xl tracking-tight mb-4">
            Trusted by Modern Educators
          </h2>
          <p className="text-sm text-muted-custom">
            See how professors and curriculum developers save hundreds of hours while maintaining strict assessment standards.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <Card className="p-8 bg-card">
            <p className="text-sm italic text-muted-custom leading-relaxed mb-6">
              "Creating mid-term assessments with strict Bloom taxonomy alignment used to take our department days. With CampusBot, we upload our reference sheets, configure percentages, and receive highly grounded, ready-to-print papers in minutes."
            </p>
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-xs">
                AH
              </div>
              <div>
                <h4 className="font-semibold text-sm">Dr. Amit Handa</h4>
                <p className="text-[10px] text-muted-custom">Head of CSE Department, NIT</p>
              </div>
            </div>
          </Card>

          <Card className="p-8 bg-card">
            <p className="text-sm italic text-muted-custom leading-relaxed mb-6">
              "The ability to run the system on our college's servers locally was the deciding factor. It guarantees absolute curriculum copyright protection while running smoothly on standard institutional PC hardware."
            </p>
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-secondary/10 text-secondary flex items-center justify-center font-bold text-xs">
                SL
              </div>
              <div>
                <h4 className="font-semibold text-sm">Prof. Sarah Liang</h4>
                <p className="text-[10px] text-muted-custom">Faculty of Software Engineering</p>
              </div>
            </div>
          </Card>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-primary/5 dark:bg-primary/10 border-t border-b border-border-custom/40 px-6 lg:px-8 text-center">
        <div className="max-w-3xl mx-auto">
          <h2 className="font-heading font-bold text-3xl tracking-tight mb-4">
            Ready to Revolutionize Assessment Setting?
          </h2>
          <p className="text-sm text-muted-custom max-w-xl mx-auto mb-8">
            Create an account, select your course, and start generating premium notes and quiz banks instantly.
          </p>
          <Link href="/signup">
            <Button size="lg" className="w-full sm:w-auto">
              Join CampusBot AI Today <ChevronRight className="h-4.5 w-4.5 ml-1" />
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 bg-card border-t border-border-custom px-6 lg:px-8">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm shadow-primary/25">
              <GraduationCap className="h-4.5 w-4.5" />
            </div>
            <span className="font-heading font-bold text-sm tracking-tight text-primary">
              CampusBot <span className="text-secondary font-medium">AI</span>
            </span>
          </div>
          <p className="text-xs text-muted-custom">
            &copy; 2026 CampusBot AI. Designed for modern academic excellence.
          </p>
          <div className="flex gap-4 text-xs text-muted-custom">
            <a href="#" className="hover:text-foreground">Privacy Policy</a>
            <a href="#" className="hover:text-foreground">Terms of Service</a>
            <a href="#" className="hover:text-foreground">Contact Support</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
