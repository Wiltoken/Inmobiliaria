import { Link } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Building2, Users, Heart, MessageSquare, TrendingUp, ArrowRight } from 'lucide-react';
import Card from '../ui/Card';
import Badge from '../ui/Badge';
import Button from '../ui/Button';

export default function AgentDashboard({
  stats = {},
  chartData = [],
  recentClients = [],
  loading = false,
}) {
  return (
    <div className="p-4 lg:p-6 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Panel de Agente</h1>
        <p className="text-gray-500 mt-1">
          Métricas y desempeño de tu actividad
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              <Building2 className="w-5 h-5 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.activeListings || 0}</p>
              <p className="text-sm text-gray-500">Listados activos</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
              <Users className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.totalClients || 0}</p>
              <p className="text-sm text-gray-500">Clientes</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
              <Heart className="w-5 h-5 text-accent" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.matchesGenerated || 0}</p>
              <p className="text-sm text-gray-500">Matches generados</p>
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-success" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.inquiriesReceived || 0}</p>
              <p className="text-sm text-gray-500">Consultas</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Chart */}
      <Card>
        <Card className="p-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Matches por semana</h2>
              <p className="text-sm text-gray-500">Últimas 8 semanas</p>
            </div>
            <TrendingUp className="w-5 h-5 text-success" />
          </div>

          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="week"
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
                <Bar
                  dataKey="matches"
                  fill="#E8A838"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </Card>

      {/* Recent Clients */}
      <Card>
        <div className="p-4 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Últimos clientes</h2>
            <Link to="/clients">
              <Button variant="ghost" size="sm" rightIcon={<ArrowRight className="w-4 h-4" />}>
                Ver todos
              </Button>
            </Link>
          </div>
        </div>

        <div className="divide-y divide-gray-100">
          {recentClients.length > 0 ? (
            recentClients.slice(0, 5).map((client) => (
              <div key={client.id} className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                    <span className="text-primary font-medium">
                      {client.name?.charAt(0) || 'C'}
                    </span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{client.name}</p>
                    <p className="text-sm text-gray-500">{client.email}</p>
                  </div>
                </div>
                <Badge
                  variant={
                    client.status === 'active' ? 'success' :
                    client.status === 'interested' ? 'accent' :
                    client.status === 'pending' ? 'warning' : 'secondary'
                  }
                >
                  {client.status === 'active' ? 'Activo' :
                   client.status === 'interested' ? 'Interesado' :
                   client.status === 'pending' ? 'Pendiente' : 'Inactivo'}
                </Badge>
              </div>
            ))
          ) : (
            <div className="p-8 text-center">
              <Users className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No hay clientes registrados</p>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}

// Helper Card sub-components
function CardHeader({ children, className = '' }) {
  return <div className={`px-4 py-3 border-b border-gray-100 ${className}`}>{children}</div>;
}

function CardBody({ children, className = '' }) {
  return <div className={`p-4 ${className}`}>{children}</div>;
}
