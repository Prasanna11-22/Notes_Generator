'use client';

import React, { useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useAppStore } from '@/store/useAppStore';
import { useTranslation } from '@/hooks/useTranslation';
import {
  LayoutDashboard,
  GraduationCap,
  Sparkles,
  BookOpen,
  HelpCircle,
  FileSpreadsheet,
  Database,
  History,
  User,
  Settings,
  Menu,
  ChevronLeft,
  ChevronRight,
  Search,
  Bell,
  Sun,
  Moon,
  LogOut,
  Command,
} from 'lucide-react';
import Link from 'next/link';

interface NavItem {
  name: string;
  translationKey: string;
  href: string;
  icon: React.ComponentType<any>;
  badge?: string;
}

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { t } = useTranslation();
  const { sidebarOpen, toggleSidebar, theme, setTheme, user, logout, setUser } = useAppStore();
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [checkingAuth, setCheckingAuth] = useState(true);

  React.useEffect(() => {
    const checkAuthSession = async () => {
      if (typeof window !== 'undefined') {
        const token = localStorage.getItem('access_token');
        
        if (!token) {
          // No token found, redirect to login
          window.location.href = '/login';
          return;
        }

        try {
          const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
          const profileRes = await fetch(`${API_URL}/api/v1/auth/me`, {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });

          if (profileRes.ok) {
            const profileData = await profileRes.json();
            const profile = profileData.data;
            setUser({
              loggedIn: true,
              name: profile.full_name,
              email: profile.email,
              institution: profile.institution || '',
              department: profile.department || '',
            });
            setCheckingAuth(false);
          } else {
            // Token expired or invalid
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            logout();
            window.location.href = '/login';
          }
        } catch (e) {
          console.error('Session validation error:', e);
          // If network is down but token exists, we can allow offline fallback or wait
          setCheckingAuth(false);
        }
      }
    };

    checkAuthSession();
  }, [setUser, logout]);

  const navigation: NavItem[] = [
    { name: 'Dashboard', translationKey: 'nav.dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Course Selection', translationKey: 'nav.courses', href: '/dashboard/courses', icon: GraduationCap },
    { name: 'Generate Content', translationKey: 'nav.generate', href: '/dashboard/generate', icon: Sparkles, badge: 'AI' },
    { name: 'Learning Materials', translationKey: 'nav.notes', href: '/dashboard/learning-material', icon: BookOpen },
    { name: 'MCQ Generator', translationKey: 'nav.mcqs', href: '/dashboard/mcqs', icon: HelpCircle },
    { name: 'Assignments', translationKey: 'nav.assignments', href: '/dashboard/assignments', icon: FileSpreadsheet },
    { name: 'Question Bank', translationKey: 'nav.bank', href: '/dashboard/question-bank', icon: Database },
    { name: 'History', translationKey: 'nav.history', href: '/dashboard/history', icon: History },
    { name: 'Profile', translationKey: 'nav.profile', href: '/dashboard/profile', icon: User },
    { name: 'Settings', translationKey: 'nav.settings', href: '/dashboard/settings', icon: Settings },
  ];

  // Filtered menu items for search command palette simulation
  const filteredNav = navigation.filter((item) =>
    t(item.translationKey).toLowerCase().includes(searchQuery.toLowerCase())
  );

  const activeItem = navigation.find((item) => pathname === item.href) || navigation[0];

  if (checkingAuth) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-secondary text-foreground">
        <div className="flex flex-col items-center gap-3">
          <div className="h-10 w-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-xs font-medium text-muted-custom">Verifying session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-bg-secondary text-foreground transition-colors duration-300">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex flex-col border-r border-border-custom bg-card transition-all duration-300 ${
          sidebarOpen ? 'w-64' : 'w-20'
        }`}
      >
        {/* Brand Header */}
        <div className="flex h-16 items-center justify-between px-4 border-b border-border-custom/50">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm shadow-primary/25">
              <GraduationCap className="h-5.5 w-5.5" />
            </div>
            {sidebarOpen && (
              <span className="font-heading font-bold text-base tracking-tight text-primary">
                CampusBot <span className="text-secondary font-medium">AI</span>
              </span>
            )}
          </div>
          {sidebarOpen && (
            <button
              onClick={toggleSidebar}
              className="hidden lg:flex h-8 w-8 items-center justify-center rounded-lg border border-border-custom hover:bg-muted-bg text-muted-custom transition-all"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Navigation Menu */}
        <nav className="flex-1 space-y-1.5 px-3 py-4 overflow-y-auto">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.translationKey}
                href={item.href}
                className={`group flex items-center gap-3.5 px-3.5 py-3 text-sm font-medium rounded-xl transition-all duration-200 ${
                  isActive
                    ? 'bg-primary text-primary-foreground shadow-sm shadow-primary/10'
                    : 'text-muted-custom hover:bg-muted-bg hover:text-foreground'
                }`}
              >
                <Icon className={`h-5 w-5 shrink-0 transition-transform group-hover:scale-105 ${isActive ? 'text-current' : 'text-muted-custom/80 group-hover:text-foreground'}`} />
                {sidebarOpen && <span className="truncate">{t(item.translationKey)}</span>}
                {sidebarOpen && item.badge && (
                  <span className={`ml-auto px-1.5 py-0.5 text-[10px] font-semibold tracking-wider uppercase rounded-md ${
                    isActive ? 'bg-primary-foreground text-primary' : 'bg-primary/15 text-primary dark:bg-primary/20'
                  }`}>
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Footer Sidebar Toggle (When Collapsed) */}
        {!sidebarOpen && (
          <div className="p-4 border-t border-border-custom/50 flex justify-center">
            <button
              onClick={toggleSidebar}
              className="h-9 w-9 flex items-center justify-center rounded-xl border border-border-custom hover:bg-muted-bg text-muted-custom"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* User profile section */}
        {sidebarOpen && (
          <div className="p-4 border-t border-border-custom/50 bg-bg-secondary/40">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-secondary/10 border border-secondary/20 flex items-center justify-center text-secondary font-bold text-sm font-heading">
                PK
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold truncate leading-4">{user.name}</p>
                <p className="text-[10px] text-muted-custom truncate leading-3">{user.department}</p>
              </div>
              <button
                onClick={async () => {
                  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
                  const access_token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
                  
                  if (access_token) {
                    try {
                      await fetch(`${API_URL}/api/v1/auth/logout`, {
                        method: 'POST',
                        headers: {
                          'Authorization': `Bearer ${access_token}`,
                        },
                      });
                    } catch (e) {
                      console.error('Logout request failed', e);
                    }
                  }
                  
                  if (typeof window !== 'undefined') {
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('refresh_token');
                  }
                  
                  logout();
                  window.location.href = '/login';
                }}
                className="h-8 w-8 flex items-center justify-center rounded-lg text-muted-custom hover:text-red-500 hover:bg-red-500/10 transition-colors"
                title="Log Out"
              >
                <LogOut className="h-4.5 w-4.5" />
              </button>
            </div>
          </div>
        )}
      </aside>

      {/* Main Workspace Frame */}
      <div
        className={`flex flex-col flex-1 min-w-0 transition-all duration-300 ${
          sidebarOpen ? 'lg:pl-64' : 'lg:pl-20'
        }`}
      >
        {/* Top Navbar */}
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border-custom bg-card/95 backdrop-blur-md px-6 shadow-xs">
          {/* Left: Hamburger & Page Info */}
          <div className="flex items-center gap-4">
            <button
              onClick={toggleSidebar}
              className="lg:hidden h-10 w-10 flex items-center justify-center rounded-xl border border-border-custom hover:bg-muted-bg text-muted-custom"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="hidden sm:block">
              <h1 className="font-heading font-semibold text-lg">{activeItem ? t(activeItem.translationKey) : ''}</h1>
              <p className="text-[11px] text-muted-custom">Academic Content System</p>
            </div>
          </div>

          {/* Right: Actions, Search, Notifications, Theme, User */}
          <div className="flex items-center gap-3">
            {/* Search Box Trigger */}
            <button
              onClick={() => setSearchOpen(true)}
              className="flex items-center gap-2 px-3 py-2 text-xs text-muted-custom border border-border-custom rounded-xl hover:bg-muted-bg transition-colors w-40 md:w-56"
            >
              <Search className="h-3.5 w-3.5" />
              <span className="hidden md:inline">{t('common.search')}</span>
              <kbd className="ml-auto pointer-events-none select-none hidden lg:flex items-center gap-0.5 text-[9px] bg-muted-bg border border-border-custom/80 px-1.5 py-0.5 rounded-md font-mono">
                <Command className="h-2 w-2" />K
              </kbd>
            </button>

            {/* Light/Dark Toggle */}
            <button
              onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
              className="h-10 w-10 flex items-center justify-center rounded-xl border border-border-custom hover:bg-muted-bg text-muted-custom transition-all"
              title={theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
            >
              {theme === 'light' ? <Moon className="h-4.5 w-4.5" /> : <Sun className="h-4.5 w-4.5" />}
            </button>

            {/* Notifications */}
            <div className="relative">
              <button className="h-10 w-10 flex items-center justify-center rounded-xl border border-border-custom hover:bg-muted-bg text-muted-custom">
                <Bell className="h-4.5 w-4.5" />
                <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-amber-500 ring-2 ring-card animate-pulse" />
              </button>
            </div>

            {/* Separator */}
            <div className="h-6 w-px bg-border-custom/60" />

            {/* Profile Menu Trigger */}
            <Link href="/dashboard/profile" className="flex items-center gap-2 group">
              <div className="h-9 w-9 rounded-xl bg-primary/10 border border-primary/25 text-primary flex items-center justify-center font-bold text-xs group-hover:bg-primary group-hover:text-primary-foreground transition-all">
                PK
              </div>
            </Link>
          </div>
        </header>

        {/* Content Viewport */}
        <main className="flex-1 p-6 lg:p-8 max-w-7xl mx-auto w-full">
          {children}
        </main>
      </div>

      {/* Command Palette Modal Simulation */}
      {searchOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4 bg-slate-900/40 dark:bg-slate-950/60 backdrop-blur-xs">
          <div className="bg-card w-full max-w-lg rounded-2xl border border-border-custom shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center gap-3 px-4 py-3.5 border-b border-border-custom">
              <Search className="h-4.5 w-4.5 text-muted-custom" />
              <input
                type="text"
                placeholder="Type a section or tool name to navigate..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-transparent border-0 text-sm focus:outline-hidden focus:ring-0 placeholder:text-muted-custom"
                autoFocus
              />
              <button
                onClick={() => {
                  setSearchOpen(false);
                  setSearchQuery('');
                }}
                className="text-[10px] bg-muted-bg hover:bg-muted-bg/85 border border-border-custom/80 px-2 py-1 rounded-lg text-muted-custom transition-all"
              >
                ESC
              </button>
            </div>
            <div className="p-2 max-h-72 overflow-y-auto">
              {filteredNav.length > 0 ? (
                filteredNav.map((item) => {
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.translationKey}
                      onClick={() => {
                        router.push(item.href);
                        setSearchOpen(false);
                        setSearchQuery('');
                      }}
                      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-muted-bg text-sm text-left transition-colors"
                    >
                      <Icon className="h-4.5 w-4.5 text-muted-custom" />
                      <span className="font-medium">{t(item.translationKey)}</span>
                      <span className="ml-auto text-xs text-muted-custom">Go to Page</span>
                    </button>
                  );
                })
              ) : (
                <div className="py-8 text-center text-sm text-muted-custom">
                  No matching sections found.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
