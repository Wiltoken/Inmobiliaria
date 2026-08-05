import toast from 'react-hot-toast';

// Toast configurations
const toastConfig = {
  duration: 4000,
  style: {
    background: '#1F3864',
    color: '#fff',
    borderRadius: '12px',
    padding: '12px 16px',
  },
  success: {
    iconTheme: {
      primary: '#16A34A',
      secondary: '#fff',
    },
  },
  error: {
    iconTheme: {
      primary: '#DC2626',
      secondary: '#fff',
    },
  },
};

export const Toast = {
  success: (message) => toast.success(message, toastConfig),
  error: (message) => toast.error(message, toastConfig),
  loading: (message) => toast.loading(message, toastConfig),
  promise: (promise, messages) => toast.promise(promise, {
    success: messages.success || 'Listo',
    error: messages.error || 'Error',
    loading: messages.loading || 'Cargando...',
  }, toastConfig),
  custom: (message, options) => toast(message, { ...toastConfig, ...options }),
};

export default Toast;
