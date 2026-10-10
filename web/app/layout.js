import './globals.css';
import { AuthProvider } from '../components/auth';
export const metadata={title:'Punjab Sports Mart | Operations Copilot',description:'Policy-backed retail operations, incident triage, and source-based analytics.'};
export default function RootLayout({children}) {return <html lang="en"><body><AuthProvider>{children}</AuthProvider></body></html>;}
