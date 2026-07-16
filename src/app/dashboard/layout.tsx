import { DashboardLayout } from '@/components/dashboard-layout';

export default function SubLayout({ children }: { children: React.ReactNode }) {
  return <DashboardLayout>{children}</DashboardLayout>;
}
