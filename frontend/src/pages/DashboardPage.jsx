import { useEffect, useState } from 'react';
import { useAuth } from '../lib/auth';
import { matchesApi, propertiesApi, favoritesApi, adminApi } from '../lib/api';
import BuyerDashboard from '../components/dashboard/BuyerDashboard';
import SellerDashboard from '../components/dashboard/SellerDashboard';
import AgentDashboard from '../components/dashboard/AgentDashboard';
import AdminDashboard from '../components/dashboard/AdminDashboard';
import { SkeletonPropertyList } from '../components/ui/Skeleton';

export default function DashboardPage({ onPageView }) {
  const { isBuyer, isSeller, isAgent, isAdmin } = useAuth();
  const [data, setData] = useState({
    matches: [],
    properties: [],
    stats: {},
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    onPageView?.('dashboard');
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);

      if (isBuyer()) {
        const [matchesRes, propertiesRes, statsRes] = await Promise.allSettled([
          matchesApi.list(),
          propertiesApi.list({ page: 1, page_size: 6, sort: 'created_at:desc' }),
          Promise.resolve({ data: { propertiesViewed: 24, newMatches: 5, favorites: 12, activeInquiries: 3 } }),
        ]);

        setData({
          matches: matchesRes.status === 'fulfilled' ? matchesRes.value.data.items || [] : [],
          properties: propertiesRes.status === 'fulfilled' ? propertiesRes.value.data.items || [] : [],
          stats: statsRes.status === 'fulfilled' ? statsRes.value.data : {},
        });
      } else if (isSeller()) {
        const [propertiesRes] = await Promise.allSettled([
          propertiesApi.list({ owner_id: 'me' }),
        ]);

        setData({
          properties: propertiesRes.status === 'fulfilled' ? propertiesRes.value.data.items || [] : [],
          stats: { totalViews: 1234, pendingInquiries: 5 },
        });
      } else if (isAgent()) {
        setData({
          chartData: [
            { week: 'Sem 1', matches: 12 },
            { week: 'Sem 2', matches: 19 },
            { week: 'Sem 3', matches: 15 },
            { week: 'Sem 4', matches: 22 },
            { week: 'Sem 5', matches: 28 },
            { week: 'Sem 6', matches: 25 },
            { week: 'Sem 7', matches: 32 },
            { week: 'Sem 8', matches: 30 },
          ],
          recentClients: [
            { id: '1', name: 'Juan Pérez', email: 'juan@email.com', status: 'active' },
            { id: '2', name: 'María García', email: 'maria@email.com', status: 'interested' },
            { id: '3', name: 'Carlos López', email: 'carlos@email.com', status: 'pending' },
          ],
          stats: { activeListings: 15, totalClients: 42, matchesGenerated: 28, inquiriesReceived: 67 },
        });
      } else if (isAdmin()) {
        const response = await adminApi.dashboard();
        const d = response.data;
        setData({
          stats: {
            totalUsers: d.total_users,
            totalProperties: d.total_properties,
            totalInquiries: d.total_inquiries,
          },
          registrationData: d.registrations_per_month || [],
          roleDistribution: d.role_distribution || [],
          pendingProperties: d.pending_properties || [],
        });
      }
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-4 lg:p-6">
        <SkeletonPropertyList count={3} />
      </div>
    );
  }

  if (isBuyer()) {
    return (
      <BuyerDashboard
        matches={data.matches}
        recentProperties={data.properties}
        loading={loading}
        stats={data.stats}
      />
    );
  }

  if (isSeller()) {
    return (
      <SellerDashboard
        properties={data.properties}
        loading={loading}
        stats={data.stats}
      />
    );
  }

  if (isAgent()) {
    return (
      <AgentDashboard
        chartData={data.chartData}
        recentClients={data.recentClients}
        stats={data.stats}
        loading={loading}
      />
    );
  }

  if (isAdmin()) {
    return (
      <AdminDashboard
        stats={data.stats}
        registrationData={data.registrationData}
        roleDistribution={data.roleDistribution}
        pendingProperties={data.pendingProperties}
        loading={loading}
      />
    );
  }

  // Default fallback
  return (
    <div className="p-4 lg:p-6">
      <h1 className="text-2xl font-bold text-gray-900">Bienvenido</h1>
      <p className="text-gray-500 mt-1">Tu panel de control</p>
    </div>
  );
}
