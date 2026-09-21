import '../../../../../apps/web/app/tokens.css';
import './harness.css';

export default function Layout({ children }: { children: React.ReactNode }) {
  return <html lang="ko"><body>{children}</body></html>;
}
