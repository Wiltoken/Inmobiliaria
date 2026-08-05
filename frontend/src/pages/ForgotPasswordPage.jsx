import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, ArrowLeft, CheckCircle } from 'lucide-react';
import { authApi } from '../lib/api';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import Card from '../components/ui/Card';
import toast from 'react-hot-toast';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!email.trim()) {
      setError('El email es requerido');
      return;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError('Email inválido');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await authApi.forgotPassword(email);
      setSent(true);
      toast.success('Correo de recuperación enviado');
    } catch (error) {
      const detail = error.response?.data?.detail;
      toast.error(detail || 'Error al enviar el correo');
    } finally {
      setLoading(false);
    }
  };

  // Show success state
  if (sent) {
    return (
      <div className="min-h-screen min-h-[100dvh] flex items-center justify-center bg-gray-50 p-4">
        <div className="w-full max-w-md text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-success/10 rounded-full mb-4">
            <CheckCircle className="w-8 h-8 text-success" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Correo enviado</h1>
          <p className="text-gray-500 mb-6">
            Hemos enviado un enlace de recuperación a <strong>{email}</strong>.
            Revisa tu bandeja de entrada y sigue las instrucciones.
          </p>

          {/* Dev mode: show token */}
          {import.meta.env.DEV && (
            <Card className="p-4 bg-amber-50 border-amber-200 text-left mb-6">
              <p className="text-sm text-amber-800">
                <strong>Modo desarrollo:</strong> El token de recuperación se mostró
                en la consola del servidor.
              </p>
            </Card>
          )}

          <Link to="/login">
            <Button variant="outline">
              Volver al login
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen min-h-[100dvh] flex items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-md">
        {/* Back Link */}
        <Link
          to="/login"
          className="inline-flex items-center gap-1 text-gray-500 hover:text-gray-700 mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Volver al login
        </Link>

        {/* Logo */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-primary rounded-xl mb-3">
            <span className="text-white font-bold text-xl">I</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Recuperar contraseña</h1>
          <p className="text-gray-500 mt-1">
            Ingresa tu email y te enviaremos un enlace
          </p>
        </div>

        <Card className="p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 bg-error/10 text-error rounded-lg text-sm">
                {error}
              </div>
            )}

            <Input
              label="Email"
              type="email"
              placeholder="tu@email.com"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setError('');
              }}
              error={error}
              leftIcon={<Mail className="w-5 h-5" />}
              autoFocus
            />

            <Button
              type="submit"
              variant="primary"
              loading={loading}
              fullWidth
              size="lg"
            >
              Enviar enlace de recuperación
            </Button>
          </form>
        </Card>

        {/* Help Text */}
        <p className="text-center mt-6 text-gray-500 text-sm">
          ¿No recibes el correo? Revisa tu carpeta de spam o{' '}
          <Link to="/contact" className="text-primary hover:underline">
            contacta a soporte
          </Link>
        </p>
      </div>
    </div>
  );
}
