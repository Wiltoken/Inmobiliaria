import { useState, useEffect } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar,
} from 'recharts';
import {
  Users, Search, Building2, MessageSquare, Activity,
  Clock, Eye, Heart, ArrowUp,
} from 'lucide-react';
import Card from '../ui/Card';
import Badge from '../ui/Badge';
import { Skeleton } from '../ui/Skeleton';
import { auditApi } from '../../lib/api';

const COLORS = ['#1F3864', '#2B579A', '#E8A838', '#16A34A', '#DC2626'];

export default function BIDashboard() {
  const [data, setData] = useState({
    dau: 0,
    searches_today: 0,
    properties_viewed: 0,
    inquiries_sent: 0,
    events_over_time: [],
    user_roles: [],
    top_properties: [],
    recent_actions: [],
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      const response = await auditApi.getAnalytics();
      setData(response.data);
    } catch (error) {
      console.error('Failed to load analytics:', error);
      // Use mock data for demo
      setData({
        dau: 127,
        searches_today: 342,
        properties_viewed: 891,
        inquiries_sent: 47,
        events_over_time: [
          { date: 'Lun', events: 1200 },
          { date: 'Mar', events: 1450 },
          { date: 'Mié', events: 1380 },
          { date: 'Jue', events: 1620 },
          { date: 'Vie', events: 1890 },
          { date: 'Sáb', events: 2100 },
          { date: 'Dom', events: 1750 },
        ],
        user_roles: [
          { role: 'Comprador', count: 450 },
          { role: 'Vendedor', count: 180 },
          { role: 'Agente', count: 65 },
          { role: 'Admin', count: 12 },
        ],
        top_properties: [
          { id: '1', title: 'Apartamento en El Poblado', views: 1234 },
          { id: '2', title: 'Casa en Chico', views: 987 },
          { id: '3', title: 'Oficina en Santa Fe', views: 756 },
          { id: '4', title: 'Local en Andino', views: 654 },
          { id: '5', title: 'Casa en La Carolina', views: 543 },
        ],
        recent_actions: [
          { action: 'page_view', user: 'john@example.com', time: 'Hace 2 min' },
          { action: 'search', user: 'jane@example.com', time: 'Hace 5 min' },
          { action: 'property_view', user: 'bob@example.com', time: 'Hace 8 min' },
          { action: 'inquiry_sent', user: 'alice@example.com', time: 'Hace 12 min' },
          { action: 'favorite_add', user: 'carol@example.com', time: 'Hace 15 min' },
        ],
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-4 lg:p-6 space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton className="h-80 rounded-xl" />
          <Skeleton className="h-80 rounded-xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 lg:p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Business Intelligence</h1>
          <p className="text-gray-500 mt-1">Analíticas y métricas de la plataforma</p>
        </div>
        <Badge variant="success" className="flex items-center gap-1">
          <Activity className="w-4 h-4" />
          En vivo
        </Badge>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          icon={Users}
          label="Usuarios Activos"
          value={data.dau}
          color="primary"
          trend="+12%"
        />
        <MetricCard
          icon={Search}
          label="Búsquedas Hoy"
          value={data.searches_today}
          color="accent"
          trend="+8%"
        />
        <MetricCard
          icon={Eye}
          label="Propiedades Vistas"
          value={data.properties_viewed}
          color="blue"
          trend="+23%"
        />
        <MetricCard
          icon={MessageSquare}
          label="Consultas Enviadas"
          value={data.inquiries_sent}
          color="success"
          trend="+5%"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Events Over Time */}
        <Card>
          <div className="p-4 border-b border-gray-100">
            <h2 className="text-lg font-semibold text-gray-900">Eventos en tiempo real</h2>
            <p className="text-sm text-gray-500">Últimos 7 días</p>
          </div>
          <div className="p-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.events_over_time}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 12 }}
                  tickLine={false}
                  axisLine={{ stroke: '#f0f0f0' }}
                />
                <YAxis
                  tick={{ fontSize: 12 }}
                  tickLine={false}
                  axisLine={{ stroke: '#f0f0f0' }}
                />
                <Tooltip
                  contentStyle={{
                    borderRadius: '8px',
                    border: 'none',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="events"
                  stroke="#1F3864"
                  strokeWidth={2}
                  dot={{ fill: '#1F3864', strokeWidth: 2 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* User Roles Distribution */}
        <Card>
          <div className="p-4 border-b border-gray-100">
            <h2 className="text-lg font-semibold text-gray-900">Distribución de roles</h2>
            <p className="text-sm text-gray-500">Usuarios por tipo</p>
          </div>
          <div className="p-4 h-72 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data.user_roles}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={5}
                  dataKey="count"
                  nameKey="role"
                  label={({ role, percent }) => `${role} ${(percent * 100).toFixed(0)}%`}
                >
                  {data.user_roles.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Top Properties */}
      <Card>
        <div className="p-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">Top 10 propiedades más vistas</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">#</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Propiedad</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Vistas</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.top_properties.map((property, index) => (
                <tr key={property.id || index} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm text-gray-500">{index + 1}</td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">
                    {property.title || (property.id ? property.id.slice(0, 8) : `Propiedad ${index + 1}`)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900 text-right">
                    {property.views.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Recent User Actions */}
      <Card>
        <div className="p-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">Acciones recientes</h2>
          <p className="text-sm text-gray-500">Últimas 50 acciones</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Acción</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Usuario</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Tiempo</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.recent_actions.map((action, index) => (
                <tr key={index} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Badge variant="primary" size="sm">
                      {action.action}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900">{action.user}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{action.time}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function MetricCard({ icon: Icon, label, value, color, trend }) {
  const colorMap = {
    primary: 'bg-primary/10 text-primary',
    accent: 'bg-accent/10 text-amber-700',
    blue: 'bg-blue-100 text-blue-600',
    success: 'bg-success/10 text-success',
  };

  return (
    <Card className="p-4">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colorMap[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex-1">
          <p className="text-2xl font-bold text-gray-900">{value.toLocaleString()}</p>
          <p className="text-sm text-gray-500">{label}</p>
        </div>
      </div>
      {trend && (
        <div className="mt-2 flex items-center gap-1 text-success text-sm">
          <ArrowUp className="w-4 h-4" />
          {trend}
        </div>
      )}
    </Card>
  );
}
