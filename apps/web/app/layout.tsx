import type { Metadata } from 'next';
import './tokens.css';
import './globals.css';
import './workflow-ux.css';

export const metadata: Metadata = {
  title: 'AI-GO 무엇이든 물어보살 · 해피콜 작업대',
  description: '전화와 웹 접수부터 물류 확인, 센터 회신까지 이어지는 합성 데이터 시연',
};
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="ko"><body>{children}</body></html>;
}
