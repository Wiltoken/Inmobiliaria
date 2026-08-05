import { Link } from 'react-router-dom';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts';
import { Users, Building2, MessageSquare, AlertCircle, ArrowRight, FileText } from 'lucide-react';
import Card from '../ui/Card';
import Badge from '../ui/Badge';
import Button from '../ui/Button';

const COLORS = ['#1F3864', '#2B579A', '#E8A838', '#16A34A', '#DC2626'];

export default function AdminDashboard({
  stats = {},
  registrationData = [],
  roleDistribution = [],
  pendingProperties = [],
  loading = false,
}) {
  return (
    <div className="p-4 lg:p-6 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Panel de Administrador</h1>
        <p className="text-gray-500 mt-1">
          Vista general de la plataforma
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Users className="w-5 h-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.totalUsers || 0}</p>
              <p className="text-sm text-gray-500">Usuarios</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
              <Building2 className="w-5 h-5 text-accent" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.totalProperties || 0}</p>
              <p className="text-sm text-gray-500">Propiedades</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-success" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.totalInquiries || 0}</p>
              <p className="text-sm text-gray-500">Consultas</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-warning/10 flex items-center justify-center">
              <AlertCircle className="w-5 h-5 text-warning" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{pendingProperties.length}</p>
              <p className="text-sm text-gray-500">Pendientes</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Registration Chart */}
        <Card>
          <div className="p-4 border-b border-gray-100">
            <h2 className="text-lg font-semibold text-gray-900">Registros por mes</h2>
            <p className="text-sm text-gray-500">Últimos 6 meses</p>
          </div>
          <div className="p-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={registrationData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="month"
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
                  dataKey="users"
                  stroke="#1F3864"
                  strokeWidth={2}
                  dot={{ fill: '#1F3864', strokeWidth: 2 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Role Distribution */}
        <Card>
          <div className="p-4 border-b border-gray-100">
            <h2 className="text-lg font-semibold text-gray-900">Distribución por rol</h2>
            <p className="text-sm text-gray-500">Usuarios registrados</p>
          </div>
          <div className="p-4 flex items-center justify-center h-64">
            {roleDistribution.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={roleDistribution}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="count"
                    nameKey="role"
                    label={({ role, percent }) => `${role} ${(percent * 100).toFixed(0)}%`}
                  >
                    {roleDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center text-gray-500">
                <Users className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                <p>Sin datos disponibles</p>
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Pending Properties */}
      <Card>
        <div className="p-4 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Propiedades pendientes</h2>
            <p className="text-sm text-gray-500">Requieren aprobación</p>
          </div>
          <Link to="/admin/properties?status=pending">
            <Button variant="ghost" size="sm" rightIcon={<ArrowRight className="w-4 h-4" />}>
              Ver todas
            </Button>
          </Link>
        </div>

        <div className="divide-y divide-gray-100">
          {pendingProperties.length > 0 ? (
            pendingProperties.slice(0, 5).map((property) => (
              <div key={property.id} className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-16 h-16 rounded-lg bg-gray-100 overflow-hidden flex-shrink-0">
                    <img
                      src={property.photos?.[0]?.url || `https://picsum.photos/seed/${property.id}/100/100`}
                      alt={property.title}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{property.title}</p>
                    <p className="text-sm text-gray-500">
                      {property.owner?.username || 'Sin vendedor'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="warning">Pendiente</Badge>
                  <Link to={`/property/${property.id}`}>
                    <Button variant="ghost" size="sm">
                      Revisar
                    </Button>
                  </Link>
                </div>
              </div>
            ))
          ) : (
            <div className="p-8 text-center">
              <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No hay propiedades pendientes</p>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
