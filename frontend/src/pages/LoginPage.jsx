import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Mail, Lock, AlertCircle } from 'lucide-react';
import { useAuth } from '../lib/auth';
import { authApi } from '../lib/api';
import { trackLogin } from '../lib/audit';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import Card from '../components/ui/Card';
import toast from 'react-hot-toast';

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [remainingAttempts, setRemainingAttempts] = useState(null);

  const from = location.state?.from?.pathname || '/dashboard';

  const validate = () => {
    const newErrors = {};
    if (!formData.username.trim()) {
      newErrors.username = 'El usuario es requerido';
    }
    if (!formData.password) {
      newErrors.password = 'La contraseña es requerida';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: null }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validate()) return;

    setLoading(true);
    setErrors({});

    try {
      const response = await authApi.login(formData.username, formData.password);
      const { access_token, refresh_token, user } = response.data;

      // Set user roles from response
      const userWithRoles = {
        ...user,
        roles: user.roles || [],
        token: access_token,
        refreshToken: refresh_token,
      };

      login(access_token, refresh_token, userWithRoles);
      trackLogin('email_password');
      toast.success('¡Bienvenido de nuevo!');

      // Redirect based on role
      const isAdmin = user.roles?.some(r => r.name === 'admin' || r.name === 'super_admin');
      navigate(isAdmin ? '/admin/analytics' : from, { replace: true });
    } catch (error) {
      const status = error.response?.status;
      const detail = error.response?.data?.detail;

      if (status === 401) {
        setErrors({ password: 'Usuario o contraseña incorrectos' });
        if (remainingAttempts !== null && remainingAttempts > 1) {
          toast.error(`Credenciales inválidas. ${remainingAttempts - 1} intentos restantes.`);
        }
      } else if (status === 423) {
        toast.error('Tu cuenta está bloqueada. Intenta más tarde.');
      } else if (detail) {
        toast.error(detail);
      } else {
        toast.error('Error al iniciar sesión. Intenta de nuevo.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen min-h-[100dvh] flex items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary rounded-2xl mb-4">
            <span className="text-white font-bold text-2xl">I</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Inmobiliaria</h1>
          <p className="text-gray-500 mt-1">Inicia sesión en tu cuenta</p>
        </div>

        <Card className="p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Error Alert */}
            {(errors.username || errors.password) && (
              <div className="flex items-center gap-2 p-3 bg-error/10 text-error rounded-lg text-sm">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{errors.username || errors.password}</span>
              </div>
            )}

            {/* Username */}
            <Input
              label="Usuario o Email"
              type="text"
              placeholder="Ej: usuario123 o email@ejemplo.com"
              value={formData.username}
              onChange={(e) => handleChange('username', e.target.value)}
              error={errors.username}
              leftIcon={<Mail className="w-5 h-5" />}
              autoComplete="username"
              autoFocus
            />

            {/* Password */}
            <Input
              label="Contraseña"
              type="password"
              placeholder="Tu contraseña"
              value={formData.password}
              onChange={(e) => handleChange('password', e.target.value)}
              error={errors.password}
              leftIcon={<Lock className="w-5 h-5" />}
              autoComplete="current-password"
            />

            {/* Forgot Password Link */}
            <div className="text-right">
              <Link
                to="/forgot-password"
                className="text-sm text-primary hover:underline"
              >
                ¿Olvidaste tu contraseña?
              </Link>
            </div>

            {/* Submit */}
            <Button
              type="submit"
              variant="primary"
              loading={loading}
              fullWidth
              size="lg"
            >
              Iniciar Sesión
            </Button>

            {/* reCAPTCHA Badge */}
            <div className="flex justify-center pt-2">
              <div className="flex items-center gap-1 text-xs text-gray-400">
                <Lock className="w-3 h-3" />
                <span>Protegido por reCAPTCHA</span>
              </div>
            </div>
          </form>
        </Card>

        {/* Register Link */}
        <p className="text-center mt-6 text-gray-500">
          ¿No tienes cuenta?{' '}
          <Link to="/register" className="text-primary font-medium hover:underline">
            Regístrate aquí
          </Link>
        </p>

        {/* Demo Credentials */}
        <Card className="mt-4 p-4 bg-gray-50 border-dashed">
          <p className="text-sm text-gray-500 text-center">
            <strong>Demo:</strong> usuario: <code className="bg-gray-200 px-1 rounded">demo</code> /
            contraseña: <code className="bg-gray-200 px-1 rounded">demo123</code>
          </p>
        </Card>
      </div>
    </div>
  );
}
