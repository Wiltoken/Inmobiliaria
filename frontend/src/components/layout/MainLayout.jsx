import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import Sidebar from './Sidebar';
import MobileBottomNav from './MobileBottomNav';
import Footer from './Footer';

export default function MainLayout() {
  return (
    <div className="min-h-screen min-h-[100dvh] flex flex-col bg-gray-50">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[100] focus:px-4 focus:py-2 focus:bg-primary focus:text-white focus:rounded-lg">
        Saltar al contenido principal
      </a>

      {/* Top Navbar - Desktop */}
      <Navbar className="hidden md:block" />

      <div className="flex flex-1">
        {/* Sidebar - Desktop */}
        <Sidebar className="hidden md:flex" />

        {/* Main Content */}
        <main id="main-content" className="flex-1 pb-20 md:pb-0 md:ml-64">
          <Outlet />
        </main>
      </div>

      {/* Mobile Bottom Navigation */}
      <MobileBottomNav className="md:hidden" />

      {/* Footer */}
      <Footer className="hidden md:block" />
    </div>
  );
}
