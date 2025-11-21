/**
 * Customer Portal - Self-Service Dashboard
 * 
 * Features:
 * - Usage statistics and billing
 * - Invoice management
 * - Support ticket management
 * - BGP peering management
 * - Alert preferences
 * - Plan management
 * - API key management
 * - Keycloak SSO integration
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useKeycloak } from '@react-keycloak/web';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import api from '../lib/api';

interface UsageStats {
  bgp_peerings_count: number;
  api_requests_this_month: number;
  data_transfer_gb: number;
  ml_predictions_count: number;
  storage_used_gb: number;
}

interface Invoice {
  id: string;
  invoice_number: string;
  amount: number;
  currency: string;
  status: 'paid' | 'pending' | 'overdue';
  due_date: string;
  created_at: string;
}

interface SupportTicket {
  id: string;
  subject: string;
  status: 'open' | 'in_progress' | 'resolved' | 'closed';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  created_at: string;
  updated_at: string;
}

interface BillingPlan {
  id: string;
  name: string;
  price: number;
  currency: string;
  features: string[];
  limits: {
    bgp_peerings: number;
    api_requests_per_month: number;
    data_transfer_gb: number;
  };
}

interface APIKey {
  id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
}

interface AlertPreferences {
  email_enabled: boolean;
  slack_enabled: boolean;
  webhook_url: string | null;
  critical_alerts: boolean;
  warning_alerts: boolean;
  info_alerts: boolean;
}

export default function CustomerPortal() {
  const { keycloak, initialized } = useKeycloak();
  const queryClient = useQueryClient();
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  const [newApiKeyName, setNewApiKeyName] = useState('');

  // Check authentication
  if (!initialized || !keycloak.authenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">Authentication Required</h1>
          <Button onClick={() => keycloak.login()}>Login with Keycloak</Button>
        </div>
      </div>
    );
  }

  // Fetch usage statistics
  const { data: usageStats, isLoading: loadingStats } = useQuery<UsageStats>({
    queryKey: ['customer', 'usage-stats'],
    queryFn: async () => {
      const response = await api.get('/api/v1/customer/usage-stats', {
        headers: {
          Authorization: `Bearer ${keycloak.token}`,
        },
      });
      return response.data;
    },
  });

  // Fetch invoices
  const { data: invoices, isLoading: loadingInvoices } = useQuery<Invoice[]>({
    queryKey: ['customer', 'invoices'],
    queryFn: async () => {
      const response = await api.get('/api/v1/customer/invoices', {
        headers: {
          Authorization: `Bearer ${keycloak.token}`,
        },
      });
      return response.data;
    },
  });

  // Fetch support tickets
  const { data: tickets, isLoading: loadingTickets } = useQuery<SupportTicket[]>({
    queryKey: ['customer', 'support-tickets'],
    queryFn: async () => {
      const response = await api.get('/api/v1/customer/support-tickets', {
        headers: {
          Authorization: `Bearer ${keycloak.token}`,
        },
      });
      return response.data;
    },
  });

  // Fetch current plan
  const { data: currentPlan } = useQuery<BillingPlan>({
    queryKey: ['customer', 'current-plan'],
    queryFn: async () => {
      const response = await api.get('/api/v1/customer/plan', {
        headers: {
          Authorization: `Bearer ${keycloak.token}`,
        },
      });
      return response.data;
    },
  });

  // Fetch available plans
  const { data: availablePlans } = useQuery<BillingPlan[]>({
    queryKey: ['customer', 'available-plans'],
    queryFn: async () => {
      const response = await api.get('/api/v1/customer/plans', {
        headers: {
          Authorization: `Bearer ${keycloak.token}`,
        },
      });
      return response.data;
    },
  });

  // Fetch API keys
  const { data: apiKeys, isLoading: loadingApiKeys } = useQuery<APIKey[]>({
    queryKey: ['customer', 'api-keys'],
    queryFn: async () => {
      const response = await api.get('/api/v1/customer/api-keys', {
        headers: {
          Authorization: `Bearer ${keycloak.token}`,
        },
      });
      return response.data;
    },
  });

  // Fetch alert preferences
  const { data: alertPrefs } = useQuery<AlertPreferences>({
    queryKey: ['customer', 'alert-preferences'],
    queryFn: async () => {
      const response = await api.get('/api/v1/customer/alert-preferences', {
        headers: {
          Authorization: `Bearer ${keycloak.token}`,
        },
      });
      return response.data;
    },
  });

  // Change plan mutation
  const changePlanMutation = useMutation({
    mutationFn: async (planId: string) => {
      const response = await api.post(
        '/api/v1/customer/change-plan',
        { plan_id: planId },
        {
          headers: {
            Authorization: `Bearer ${keycloak.token}`,
          },
        }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customer', 'current-plan'] });
      queryClient.invalidateQueries({ queryKey: ['customer', 'usage-stats'] });
      setSelectedPlan(null);
    },
  });

  // Create API key mutation
  const createApiKeyMutation = useMutation({
    mutationFn: async (name: string) => {
      const response = await api.post(
        '/api/v1/customer/api-keys',
        { name },
        {
          headers: {
            Authorization: `Bearer ${keycloak.token}`,
          },
        }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customer', 'api-keys'] });
      setShowApiKeyModal(false);
      setNewApiKeyName('');
    },
  });

  // Delete API key mutation
  const deleteApiKeyMutation = useMutation({
    mutationFn: async (keyId: string) => {
      await api.delete(`/api/v1/customer/api-keys/${keyId}`, {
        headers: {
          Authorization: `Bearer ${keycloak.token}`,
        },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customer', 'api-keys'] });
    },
  });

  // Update alert preferences mutation
  const updateAlertPrefsMutation = useMutation({
    mutationFn: async (prefs: Partial<AlertPreferences>) => {
      const response = await api.put(
        '/api/v1/customer/alert-preferences',
        prefs,
        {
          headers: {
            Authorization: `Bearer ${keycloak.token}`,
          },
        }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customer', 'alert-preferences'] });
    },
  });

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'paid':
      case 'resolved':
        return 'bg-green-100 text-green-800';
      case 'pending':
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-800';
      case 'overdue':
      case 'urgent':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Customer Portal</h1>
        <p className="text-gray-600">Manage your BGP Orchestrator account</p>
        <div className="mt-4 flex items-center gap-4">
          <span className="text-sm text-gray-500">
            Logged in as: {keycloak.tokenParsed?.email || keycloak.tokenParsed?.preferred_username}
          </span>
          <Button variant="outline" size="sm" onClick={() => keycloak.logout()}>
            Logout
          </Button>
        </div>
      </div>

      {/* Usage Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-gray-500">BGP Peerings</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loadingStats ? '...' : usageStats?.bgp_peerings_count || 0}
            </div>
            {currentPlan && (
              <div className="text-sm text-gray-500 mt-1">
                of {currentPlan.limits.bgp_peerings} limit
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-gray-500">API Requests</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loadingStats ? '...' : usageStats?.api_requests_this_month?.toLocaleString() || 0}
            </div>
            {currentPlan && (
              <div className="text-sm text-gray-500 mt-1">
                of {currentPlan.limits.api_requests_per_month.toLocaleString()} limit
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-gray-500">Data Transfer</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loadingStats ? '...' : `${usageStats?.data_transfer_gb?.toFixed(2) || 0} GB`}
            </div>
            {currentPlan && (
              <div className="text-sm text-gray-500 mt-1">
                of {currentPlan.limits.data_transfer_gb} GB limit
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-gray-500">ML Predictions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loadingStats ? '...' : usageStats?.ml_predictions_count?.toLocaleString() || 0}
            </div>
            <div className="text-sm text-gray-500 mt-1">This month</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Invoices */}
        <Card>
          <CardHeader>
            <CardTitle>Invoices</CardTitle>
            <CardDescription>View and download your invoices</CardDescription>
          </CardHeader>
          <CardContent>
            {loadingInvoices ? (
              <div className="text-center py-4">Loading invoices...</div>
            ) : invoices && invoices.length > 0 ? (
              <div className="space-y-4">
                {invoices.map((invoice) => (
                  <div
                    key={invoice.id}
                    className="flex items-center justify-between p-4 border rounded-lg"
                  >
                    <div>
                      <div className="font-medium">{invoice.invoice_number}</div>
                      <div className="text-sm text-gray-500">
                        {new Date(invoice.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-medium">
                        {formatCurrency(invoice.amount, invoice.currency)}
                      </div>
                      <Badge className={getStatusColor(invoice.status)}>{invoice.status}</Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-4 text-gray-500">No invoices found</div>
            )}
          </CardContent>
        </Card>

        {/* Support Tickets */}
        <Card>
          <CardHeader>
            <CardTitle>Support Tickets</CardTitle>
            <CardDescription>Track your support requests</CardDescription>
          </CardHeader>
          <CardContent>
            {loadingTickets ? (
              <div className="text-center py-4">Loading tickets...</div>
            ) : tickets && tickets.length > 0 ? (
              <div className="space-y-4">
                {tickets.map((ticket) => (
                  <div
                    key={ticket.id}
                    className="flex items-center justify-between p-4 border rounded-lg"
                  >
                    <div>
                      <div className="font-medium">{ticket.subject}</div>
                      <div className="text-sm text-gray-500">
                        Created: {new Date(ticket.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <div className="text-right">
                      <Badge className={getStatusColor(ticket.status)}>{ticket.status}</Badge>
                      <Badge className={`mt-1 ${getStatusColor(ticket.priority)}`}>
                        {ticket.priority}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-4 text-gray-500">No support tickets</div>
            )}
            <Button className="mt-4 w-full" variant="outline">
              Create Support Ticket
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Plan Management */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Billing Plan</CardTitle>
          <CardDescription>Manage your subscription plan</CardDescription>
        </CardHeader>
        <CardContent>
          {currentPlan && (
            <div className="mb-6">
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <div className="font-medium text-lg">{currentPlan.name}</div>
                  <div className="text-2xl font-bold mt-2">
                    {formatCurrency(currentPlan.price, currentPlan.currency)}/month
                  </div>
                  <ul className="mt-4 space-y-2">
                    {currentPlan.features.map((feature, idx) => (
                      <li key={idx} className="text-sm text-gray-600">
                        • {feature}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {availablePlans && availablePlans.length > 0 && (
            <div>
              <h3 className="font-medium mb-4">Available Plans</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {availablePlans.map((plan) => (
                  <div
                    key={plan.id}
                    className={`p-4 border rounded-lg ${
                      currentPlan?.id === plan.id ? 'border-blue-500 bg-blue-50' : ''
                    }`}
                  >
                    <div className="font-medium">{plan.name}</div>
                    <div className="text-xl font-bold mt-2">
                      {formatCurrency(plan.price, plan.currency)}/month
                    </div>
                    <Button
                      className="mt-4 w-full"
                      variant={currentPlan?.id === plan.id ? 'outline' : 'default'}
                      disabled={currentPlan?.id === plan.id || changePlanMutation.isPending}
                      onClick={() => {
                        setSelectedPlan(plan.id);
                        changePlanMutation.mutate(plan.id);
                      }}
                    >
                      {currentPlan?.id === plan.id
                        ? 'Current Plan'
                        : changePlanMutation.isPending && selectedPlan === plan.id
                        ? 'Changing...'
                        : 'Change Plan'}
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* API Key Management */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>API Keys</CardTitle>
          <CardDescription>Manage your API keys for programmatic access</CardDescription>
        </CardHeader>
        <CardContent>
          {loadingApiKeys ? (
            <div className="text-center py-4">Loading API keys...</div>
          ) : (
            <div className="space-y-4">
              {apiKeys && apiKeys.length > 0 ? (
                apiKeys.map((key) => (
                  <div
                    key={key.id}
                    className="flex items-center justify-between p-4 border rounded-lg"
                  >
                    <div>
                      <div className="font-medium">{key.name}</div>
                      <div className="text-sm text-gray-500 font-mono">
                        {key.key_prefix}...
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        Created: {new Date(key.created_at).toLocaleDateString()}
                        {key.last_used_at &&
                          ` • Last used: ${new Date(key.last_used_at).toLocaleDateString()}`}
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        if (confirm('Are you sure you want to delete this API key?')) {
                          deleteApiKeyMutation.mutate(key.id);
                        }
                      }}
                    >
                      Delete
                    </Button>
                  </div>
                ))
              ) : (
                <div className="text-center py-4 text-gray-500">No API keys</div>
              )}

              <Button
                className="w-full"
                onClick={() => setShowApiKeyModal(true)}
              >
                Create New API Key
              </Button>

              {showApiKeyModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                  <div className="bg-white p-6 rounded-lg max-w-md w-full">
                    <h3 className="text-lg font-medium mb-4">Create API Key</h3>
                    <input
                      type="text"
                      placeholder="API Key Name"
                      value={newApiKeyName}
                      onChange={(e) => setNewApiKeyName(e.target.value)}
                      className="w-full p-2 border rounded mb-4"
                    />
                    <div className="flex gap-2">
                      <Button
                        className="flex-1"
                        onClick={() => {
                          if (newApiKeyName) {
                            createApiKeyMutation.mutate(newApiKeyName);
                          }
                        }}
                        disabled={!newApiKeyName || createApiKeyMutation.isPending}
                      >
                        Create
                      </Button>
                      <Button
                        variant="outline"
                        className="flex-1"
                        onClick={() => {
                          setShowApiKeyModal(false);
                          setNewApiKeyName('');
                        }}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Alert Preferences */}
      <Card>
        <CardHeader>
          <CardTitle>Alert Preferences</CardTitle>
          <CardDescription>Configure how you receive alerts</CardDescription>
        </CardHeader>
        <CardContent>
          {alertPrefs && (
            <div className="space-y-4">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={alertPrefs.email_enabled}
                  onChange={(e) =>
                    updateAlertPrefsMutation.mutate({ email_enabled: e.target.checked })
                  }
                />
                <span>Email alerts</span>
              </label>

              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={alertPrefs.slack_enabled}
                  onChange={(e) =>
                    updateAlertPrefsMutation.mutate({ slack_enabled: e.target.checked })
                  }
                />
                <span>Slack alerts</span>
              </label>

              <div>
                <label className="block text-sm font-medium mb-2">Webhook URL</label>
                <input
                  type="url"
                  value={alertPrefs.webhook_url || ''}
                  onChange={(e) =>
                    updateAlertPrefsMutation.mutate({ webhook_url: e.target.value || null })
                  }
                  placeholder="https://your-webhook-url.com"
                  className="w-full p-2 border rounded"
                />
              </div>

              <div className="space-y-2">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={alertPrefs.critical_alerts}
                    onChange={(e) =>
                      updateAlertPrefsMutation.mutate({ critical_alerts: e.target.checked })
                    }
                  />
                  <span>Critical alerts</span>
                </label>

                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={alertPrefs.warning_alerts}
                    onChange={(e) =>
                      updateAlertPrefsMutation.mutate({ warning_alerts: e.target.checked })
                    }
                  />
                  <span>Warning alerts</span>
                </label>

                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={alertPrefs.info_alerts}
                    onChange={(e) =>
                      updateAlertPrefsMutation.mutate({ info_alerts: e.target.checked })
                    }
                  />
                  <span>Info alerts</span>
                </label>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

