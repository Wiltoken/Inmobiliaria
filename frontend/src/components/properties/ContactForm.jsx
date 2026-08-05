import { useState } from 'react';
import { Send, Phone, Mail, MessageCircle } from 'lucide-react';
import Button from '../ui/Button';
import Input from '../ui/Input';
import { inquiriesApi } from '../../lib/api';
import toast from 'react-hot-toast';
import { useAuth } from '../../lib/auth';

const contactPreferences = [
  { value: 'email', label: 'Email', icon: Mail },
  { value: 'phone', label: 'Teléfono', icon: Phone },
  { value: 'whatsapp', label: 'WhatsApp', icon: MessageCircle },
];

export default function ContactForm({ propertyId, propertyTitle, ownerId }) {
  const { isAuthenticated, isBuyer } = useAuth();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    message: '',
    contact_preference: 'email',
    phone: '',
  });

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!isAuthenticated) {
      toast.error('Debes iniciar sesión para enviar consultas');
      return;
    }

    if (!formData.message.trim()) {
      toast.error('Por favor escribe un mensaje');
      return;
    }

    setLoading(true);

    try {
      await inquiriesApi.create({
        property_id: propertyId,
        to_user_id: ownerId,
        message: formData.message,
        contact_preference: formData.contact_preference,
        phone: formData.phone || undefined,
      });

      toast.success('Consulta enviada correctamente');
      setFormData({ message: '', contact_preference: 'email', phone: '' });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al enviar la consulta');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="font-semibold text-lg">¿Te interesa esta propiedad?</h3>
        <p className="text-sm text-gray-500">
          Envía una consulta al vendedor
        </p>
      </div>

      <form onSubmit={handleSubmit} className="p-4 space-y-4">
        {/* Contact Preference */}
        <div>
          <label className="label">Prefiero ser contactado por</label>
          <div className="flex gap-2">
            {contactPreferences.map((pref) => {
              const Icon = pref.icon;
              const isSelected = formData.contact_preference === pref.value;
              return (
                <button
                  key={pref.value}
                  type="button"
                  onClick={() => handleChange('contact_preference', pref.value)}
                  className={`
                    flex-1 flex items-center justify-center gap-2 py-2 px-3
                    rounded-lg text-sm font-medium transition-all
                    ${isSelected
                      ? 'bg-primary text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }
                  `}
                >
                  <Icon className="w-4 h-4" />
                  <span className="hidden sm:inline">{pref.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Phone (optional but shown for WhatsApp) */}
        {formData.contact_preference !== 'email' && (
          <Input
            label={formData.contact_preference === 'whatsapp' ? 'WhatsApp' : 'Teléfono'}
            type="tel"
            placeholder="Ej: +57 300 123 4567"
            value={formData.phone}
            onChange={(e) => handleChange('phone', e.target.value)}
          />
        )}

        {/* Message */}
        <div>
          <label className="label">Mensaje</label>
          <textarea
            rows={4}
            placeholder={`Hola, me interesa la propiedad "${propertyTitle}". ¿Podríamos agendar una visita?`}
            value={formData.message}
            onChange={(e) => handleChange('message', e.target.value)}
            className={`
              w-full px-4 py-3 rounded-lg border bg-white resize-none
              focus:outline-none focus:ring-2 focus:border-transparent
              placeholder:text-gray-400 transition-all duration-200
              ${formData.message ? 'border-gray-300 focus:ring-primary' : 'border-gray-300 focus:ring-primary'}
            `}
          />
        </div>

        {/* Submit */}
        <Button
          type="submit"
          variant="accent"
          loading={loading}
          fullWidth
          leftIcon={<Send className="w-4 h-4" />}
        >
          Enviar consulta
        </Button>

        {/* Privacy Note */}
        <p className="text-xs text-gray-500 text-center">
          Al enviar este formulario, aceptas nuestra política de privacidad
          y el tratamiento de tus datos según Ley 1581 de 2012.
        </p>
      </form>
    </div>
  );
}

// Simple Textarea component
function Textarea({ label, className = '', ...props }) {
  return (
    <div className={className}>
      {label && <label className="label">{label}</label>}
      <textarea
        className="w-full px-4 py-3 rounded-lg border border-gray-300 bg-white resize-none
                 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent
                 placeholder:text-gray-400 transition-all duration-200"
        {...props}
      />
    </div>
  );
}
