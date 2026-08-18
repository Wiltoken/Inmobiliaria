import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { User, Mail, Lock, Phone, Building2, Briefcase, Check } from 'lucide-react';
import { useAuth } from '../lib/auth';
import { authApi } from '../lib/api';
import { trackRegistration } from '../lib/audit';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import Card from '../components/ui/Card';
import Stepper from '../components/ui/Stepper';
import toast from 'react-hot-toast';

const roleOptions = [
  {
    value: 'buyer',
    label: 'Comprador',
    description: 'Busco mi propiedad ideal',
    icon: Briefcase,
  },
  {
    value: 'seller',
    label: 'Vendedor',
    description: 'Quiero publicar mis propiedades',
    icon: Building2,
  },
  {
    value: 'agent',
    label: 'Agente',
    description: 'Soy agente inmobiliario',
    icon: User,
  },
];

export default function RegisterPage() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  const [formData, setFormData] = useState({
    role: '',
    name: '',
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    phone: '',
    company: '',
    license: '',
    agency_name: '',
    budget_min: '',
    budget_max: '',
    preferred_locations: '',
    acceptTerms: false,
  });

  const validateStep1 = () => {
    const newErrors = {};
    if (!formData.role) {
      newErrors.role = 'Selecciona un tipo de cuenta';
    }
    if (!formData.name.trim()) {
      newErrors.name = 'El nombre es requerido';
    }
    if (!formData.username.trim()) {
      newErrors.username = 'El usuario es requerido';
    } else if (formData.username.length < 3) {
      newErrors.username = 'El usuario debe tener al menos 3 caracteres';
    }
    if (!formData.email.trim()) {
      newErrors.email = 'El email es requerido';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Email inválido';
    }
    if (!formData.password) {
      newErrors.password = 'La contraseña es requerida';
    } else if (formData.password.length < 8) {
      newErrors.password = 'La contraseña debe tener al menos 8 caracteres';
    }
    if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Las contraseñas no coinciden';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validateStep2 = () => {
    const newErrors = {};
    if (!formData.acceptTerms) {
      newErrors.acceptTerms = 'Debes aceptar los términos y privacidad';
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

  const handleNext = () => {
    if (step === 1 && validateStep1()) {
      setStep(2);
    }
  };

  const handleBack = () => {
    setStep(1);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateStep2()) return;

    setLoading(true);
    setErrors({});

    try {
      const payload = {
        username: formData.username,
        email: formData.email,
        password: formData.password,
        name: formData.name,
        role: formData.role,
        ...(formData.role === 'seller' && formData.phone && { phone: formData.phone }),
        ...(formData.role === 'seller' && formData.company && { company_name: formData.company }),
        ...(formData.role === 'buyer' && formData.budget_min && { budget_min: parseFloat(formData.budget_min) }),
        ...(formData.role === 'buyer' && formData.budget_max && { budget_max: parseFloat(formData.budget_max) }),
        ...(formData.role === 'buyer' && formData.preferred_locations && {
          preferred_locations: formData.preferred_locations.split(',').map(s => s.trim())
        }),
        ...(formData.role === 'agent' && formData.license && { license_number: formData.license.trim() }),
        ...(formData.role === 'agent' && formData.agency_name && { agency_name: formData.agency_name.trim() }),
        consent_given_at: new Date().toISOString(),
      };

      const response = await authApi.register(payload);
      const { access_token, refresh_token, user } = response.data;

      const userWithRoles = {
        ...user,
        roles: [{ id: user.role_id, name: formData.role }],
        token: access_token,
        refreshToken: refresh_token,
      };

      login(access_token, refresh_token, userWithRoles);
      trackRegistration(formData.role);
      toast.success('¡Cuenta creada exitosamente!');
      navigate('/dashboard');
    } catch (error) {
      const detail = error.response?.data?.detail;
      if (Array.isArray(detail)) {
        detail.forEach(d => toast.error(d));
      } else if (detail) {
        toast.error(detail);
      } else {
        toast.error('Error al crear la cuenta. Intenta de nuevo.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen min-h-[100dvh] flex items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-lg">
        {/* Logo */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-primary rounded-xl mb-3">
            <span className="text-white font-bold text-xl">I</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Crear cuenta</h1>
          <p className="text-gray-500 mt-1">Únete a nuestra plataforma</p>
        </div>

        {/* Stepper */}
        <Stepper
          steps={['Basic info', formData.role === 'buyer' ? 'Presupuesto' : formData.role === 'seller' ? 'Empresa' : 'Licencia', 'Términos']}
          currentStep={step}
          className="mb-6"
        />

        <Card className="p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Step 1: Basic Info */}
            {step === 1 && (
              <>
                {/* Role Selection */}
                <div>
                  <label className="label">Tipo de cuenta</label>
                  <div className="grid grid-cols-3 gap-2">
                    {roleOptions.map((option) => {
                      const Icon = option.icon;
                      const isSelected = formData.role === option.value;
                      return (
                        <button
                          key={option.value}
                          type="button"
                          onClick={() => handleChange('role', option.value)}
                          className={`
                            p-3 rounded-lg border-2 text-center transition-all
                            ${isSelected
                              ? 'border-primary bg-primary/5'
                              : 'border-gray-200 hover:border-gray-300'
                            }
                          `}
                        >
                          <Icon className={`w-6 h-6 mx-auto mb-1 ${isSelected ? 'text-primary' : 'text-gray-400'}`} />
                          <span className={`text-sm font-medium ${isSelected ? 'text-primary' : 'text-gray-600'}`}>
                            {option.label}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                  {errors.role && <p className="text-sm text-error mt-1">{errors.role}</p>}
                </div>

                {/* Name */}
                <Input
                  label="Nombre completo"
                  placeholder="Tu nombre"
                  value={formData.name}
                  onChange={(e) => handleChange('name', e.target.value)}
                  error={errors.name}
                  leftIcon={<User className="w-5 h-5" />}
                />

                {/* Username */}
                <Input
                  label="Usuario"
                  placeholder="Ej: usuario123"
                  value={formData.username}
                  onChange={(e) => handleChange('username', e.target.value)}
                  error={errors.username}
                  leftIcon={<User className="w-5 h-5" />}
                />

                {/* Email */}
                <Input
                  label="Email"
                  type="email"
                  placeholder="tu@email.com"
                  value={formData.email}
                  onChange={(e) => handleChange('email', e.target.value)}
                  error={errors.email}
                  leftIcon={<Mail className="w-5 h-5" />}
                />

                {/* Password */}
                <Input
                  label="Contraseña"
                  type="password"
                  placeholder="Mínimo 8 caracteres"
                  value={formData.password}
                  onChange={(e) => handleChange('password', e.target.value)}
                  error={errors.password}
                  leftIcon={<Lock className="w-5 h-5" />}
                />

                {/* Confirm Password */}
                <Input
                  label="Confirmar contraseña"
                  type="password"
                  placeholder="Repite tu contraseña"
                  value={formData.confirmPassword}
                  onChange={(e) => handleChange('confirmPassword', e.target.value)}
                  error={errors.confirmPassword}
                  leftIcon={<Lock className="w-5 h-5" />}
                />

                <Button type="button" variant="primary" fullWidth onClick={handleNext}>
                  Continuar
                </Button>
              </>
            )}

            {/* Step 2: Role-specific fields */}
            {step === 2 && (
              <>
                {/* Buyer: Budget & Location */}
                {formData.role === 'buyer' && (
                  <>
                    <div className="grid grid-cols-2 gap-2">
                      <Input
                        label="Presupuesto mínimo (COP)"
                        type="number"
                        placeholder="Ej: 200000000"
                        value={formData.budget_min}
                        onChange={(e) => handleChange('budget_min', e.target.value)}
                        leftIcon={<span className="text-gray-400">$</span>}
                      />
                      <Input
                        label="Presupuesto máximo (COP)"
                        type="number"
                        placeholder="Ej: 500000000"
                        value={formData.budget_max}
                        onChange={(e) => handleChange('budget_max', e.target.value)}
                        leftIcon={<span className="text-gray-400">$</span>}
                      />
                    </div>
                    <Input
                      label="Ubicaciones preferidas"
                      placeholder="Ej: Chapinero, Poblado, Chico (separadas por coma)"
                      value={formData.preferred_locations}
                      onChange={(e) => handleChange('preferred_locations', e.target.value)}
                    />
                  </>
                )}

                {/* Seller: Phone & Company */}
                {formData.role === 'seller' && (
                  <>
                    <Input
                      label="Teléfono de contacto"
                      type="tel"
                      placeholder="Ej: +57 300 123 4567"
                      value={formData.phone}
                      onChange={(e) => handleChange('phone', e.target.value)}
                      leftIcon={<Phone className="w-5 h-5" />}
                    />
                    <Input
                      label="Nombre de empresa (opcional)"
                      placeholder="Nombre de tu inmobiliaria"
                      value={formData.company}
                      onChange={(e) => handleChange('company', e.target.value)}
                      leftIcon={<Building2 className="w-5 h-5" />}
                    />
                  </>
                )}

                {/* Agent: License */}
                {formData.role === 'agent' && (
                  <>
                    <Input
                      label="Número de licencia"
                      placeholder="Tu número de licencia profesional"
                      value={formData.license}
                      onChange={(e) => handleChange('license', e.target.value)}
                    />
                    <Input
                      label="Inmobiliaria (opcional)"
                      placeholder="Nombre de tu inmobiliaria"
                      value={formData.agency_name}
                      onChange={(e) => handleChange('agency_name', e.target.value)}
                      leftIcon={<Building2 className="w-5 h-5" />}
                    />
                  </>
                )}

                {/* Terms Checkbox */}
                <div className="space-y-2">
                  <label className="flex items-start gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.acceptTerms}
                      onChange={(e) => handleChange('acceptTerms', e.target.checked)}
                      className="mt-1 w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
                    />
                    <span className="text-sm text-gray-600">
                      Acepto los{' '}
                      <Link to="/terms" className="text-primary hover:underline">
                        Términos y Condiciones
                      </Link>{' '}
                      y la{' '}
                      <Link to="/privacy" className="text-primary hover:underline">
                        Política de Privacidad
                      </Link>
                      . Consiento el tratamiento de mis datos personales según Ley 1581 de 2012.
                    </span>
                  </label>
                  {errors.acceptTerms && (
                    <p className="text-sm text-error">{errors.acceptTerms}</p>
                  )}
                </div>

                <div className="flex gap-2">
                  <Button type="button" variant="ghost" onClick={handleBack}>
                    Atrás
                  </Button>
                  <Button type="submit" variant="primary" loading={loading} fullWidth>
                    Crear cuenta
                  </Button>
                </div>
              </>
            )}
          </form>
        </Card>

        {/* Login Link */}
        <p className="text-center mt-6 text-gray-500">
          ¿Ya tienes cuenta?{' '}
          <Link to="/login" className="text-primary font-medium hover:underline">
            Inicia sesión
          </Link>
        </p>
      </div>
    </div>
  );
}
