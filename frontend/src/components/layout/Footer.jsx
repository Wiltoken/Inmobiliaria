import { Link } from 'react-router-dom';

export default function Footer({ className = '' }) {
  const currentYear = new Date().getFullYear();

  return (
    <footer className={`bg-white border-t border-gray-200 py-6 px-4 ${className}`}>
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          {/* Logo & Copyright */}
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">I</span>
            </div>
            <span className="text-gray-600 text-sm">
              © {currentYear} Inmobiliaria. Todos los derechos reservados.
            </span>
          </div>

          {/* Links */}
          <div className="flex items-center gap-6 text-sm">
            <Link to="/terms" className="text-gray-600 hover:text-primary transition-colors">
              Términos
            </Link>
            <Link to="/privacy" className="text-gray-600 hover:text-primary transition-colors">
              Privacidad
            </Link>
            <Link to="/help" className="text-gray-600 hover:text-primary transition-colors">
              Ayuda
            </Link>
            <Link to="/contact" className="text-gray-600 hover:text-primary transition-colors">
              Contacto
            </Link>
          </div>
        </div>

        {/* Legal Note */}
        <div className="mt-4 text-center text-xs text-gray-400">
          Tratamiento de datos personales según Ley 1581 de 2012
        </div>
      </div>
    </footer>
  );
}
