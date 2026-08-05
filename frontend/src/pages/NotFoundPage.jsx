import { Link } from 'react-router-dom';
import { Home, ArrowLeft } from 'lucide-react';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';

export default function NotFoundPage() {
  return (
    <div className="min-h-screen min-h-[100dvh] flex items-center justify-center bg-gray-50 p-4">
      <div className="text-center max-w-md">
        {/* 404 Graphic */}
        <div className="mb-8">
          <div className="text-[120px] font-bold text-gray-200 leading-none select-none">
            404
          </div>
          <div className="-mt-16">
            <div className="w-24 h-24 bg-primary/10 rounded-full flex items-center justify-center mx-auto">
              <Home className="w-12 h-12 text-primary" />
            </div>
          </div>
        </div>

        <Card className="p-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Página no encontrada
          </h1>
          <p className="text-gray-500 mb-6">
            Lo sentimos, la página que buscas no existe o ha sido movida.
          </p>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link to="/dashboard">
              <Button variant="primary" leftIcon={<Home className="w-4 h-4" />}>
                Ir al inicio
              </Button>
            </Link>
            <button onClick={() => window.history.back()}>
              <Button variant="outline" leftIcon={<ArrowLeft className="w-4 h-4" />}>
                Volver atrás
              </Button>
            </button>
          </div>
        </Card>

        {/* Suggestions */}
        <div className="mt-8 text-sm text-gray-400">
          <p>Si crees que esto es un error, contacta a soporte.</p>
        </div>
      </div>
    </div>
  );
}
