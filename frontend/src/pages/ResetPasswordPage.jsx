import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Lock, ArrowLeft, CheckCircle } from 'lucide-react';
import { authApi } from '../lib/api';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import Card from '../components/ui/Card';
import toast from 'react-hot-toast';

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (!token) {
      toast.error('Token de recuperación inválido');
    }
  }, [token]);

  const validate = () => {
    const newErrors = {};
    if (!password) {
      newErrors.password = 'La contraseña es requerida';
    } else if (password.length < 8) {
      newErrors.password = 'La contraseña debe tener al menos 8 caracteres';
    }
    if (password !== confirmPassword) {
      newErrors.confirmPassword = 'Las contraseñas no coinciden';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validate()) return;

    setLoading(true);

    try {
      await authApi.resetPassword(token, password);
      setSuccess(true);
      toast.success('Contraseña actualizada correctamente');
    } catch (error) {
      const detail = error.response?.data?.detail;
      toast.error(detail || 'Error al restablecer la contraseña');
    } finally {
      setLoading(false);
    }
  };

  // Success state
  if (success) {
    return (
      <div className="min-h-screen min-h-[100dvh] flex items-center justify-center bg-gray-50 p-4">
        <div className="w-full max-w-md text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-success/10 rounded-full mb-4">
            <CheckCircle className="w-8 h-8 text-success" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">¡Contraseña actualizada!</h1>
          <p className="text-gray-500 mb-6">
            Tu contraseña ha sido actualizada correctamente.
            Ahora puedes iniciar sesión con tu nueva contraseña.
          </p>
          <Link to="/login">
            <Button variant="primary" size="lg">
              Ir al login
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  // No token state
  if (!token) {
    return (
      <div className="min-h-screen min-h-[100dvh] flex items-center justify-center bg-gray-50 p-4">
        <div className="w-full max-w-md text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-error/10 rounded-full mb-4">
            <Lock className="w-8 h-8 text-error" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Enlace inválido</h1>
          <p className="text-gray-500 mb-6">
            Este enlace de recuperación no es válido o ha expirado.
            Solicita uno nuevo.
          </p>
          <Link to="/forgot-password">
            <Button variant="primary">
              Solicitar nuevo enlace
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
          <h1 className="text-2xl font-bold text-gray-900">Nueva contraseña</h1>
          <p className="text-gray-500 mt-1">
            Ingresa tu nueva contraseña
          </p>
        </div>

        <Card className="p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Nueva contraseña"
              type="password"
              placeholder="Mínimo 8 caracteres"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              error={errors.password}
              leftIcon={<Lock className="w-5 h-5" />}
              autoFocus
            />

            <Input
              label="Confirmar contraseña"
              type="password"
              placeholder="Repite tu nueva contraseña"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              error={errors.confirmPassword}
              leftIcon={<Lock className="w-5 h-5" />}
            />

            <Button
              type="submit"
              variant="primary"
              loading={loading}
              fullWidth
              size="lg"
            >
              Actualizar contraseña
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
