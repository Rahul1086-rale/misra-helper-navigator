import { Card, CardContent } from '@/components/ui/card';
import { AlertCircle, AlertTriangle, Info, CheckCircle } from 'lucide-react';

const Stats = () => {
  const stats = [
    {
      label: 'Critical Errors',
      value: '1',
      icon: AlertCircle,
      color: 'text-violation-error'
    },
    {
      label: 'Warnings',
      value: '1',
      icon: AlertTriangle,
      color: 'text-violation-warning'
    },
    {
      label: 'Info',
      value: '1',
      icon: Info,
      color: 'text-violation-info'
    },
    {
      label: 'Compliance Score',
      value: '87%',
      icon: CheckCircle,
      color: 'text-success'
    }
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {stats.map((stat, index) => {
        const Icon = stat.icon;
        return (
          <Card key={index}>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <Icon className={`w-5 h-5 ${stat.color}`} />
                <div>
                  <p className="text-2xl font-bold">{stat.value}</p>
                  <p className="text-sm text-muted-foreground">{stat.label}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
};

export default Stats;