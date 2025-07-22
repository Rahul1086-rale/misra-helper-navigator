import { useState } from 'react';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Play, AlertCircle, AlertTriangle, Info } from 'lucide-react';

interface MisraViolation {
  id: string;
  rule: string;
  severity: 'error' | 'warning' | 'info';
  line: number;
  message: string;
  fix?: string;
}

const CodeEditor = () => {
  const [code, setCode] = useState(`// Example C code with MISRA violations
int main() {
    int x;  // MISRA 9.1: Variable not initialized
    if (x = 5) {  // MISRA 13.4: Assignment in condition
        printf("Hello World");
    }
    return 0;
}`);
  
  const [violations, setViolations] = useState<MisraViolation[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const analyzeCode = async () => {
    setIsAnalyzing(true);
    
    // Simulate analysis delay
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Mock MISRA violations detection
    const mockViolations: MisraViolation[] = [
      {
        id: '1',
        rule: 'MISRA-C:2012 Rule 9.1',
        severity: 'error',
        line: 3,
        message: 'The value of an object with automatic storage duration is read without being initialized',
        fix: 'Initialize variable x: int x = 0;'
      },
      {
        id: '2',
        rule: 'MISRA-C:2012 Rule 13.4',
        severity: 'warning',
        line: 4,
        message: 'The result of an assignment operator should not be used',
        fix: 'Separate assignment and condition: x = 5; if (x == 5)'
      },
      {
        id: '3',
        rule: 'MISRA-C:2012 Rule 21.6',
        severity: 'info',
        line: 5,
        message: 'The Standard Library input/output functions should not be used',
        fix: 'Consider using safer I/O alternatives or add deviation justification'
      }
    ];
    
    setViolations(mockViolations);
    setIsAnalyzing(false);
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'error':
        return <AlertCircle className="w-4 h-4 text-violation-error" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-violation-warning" />;
      case 'info':
        return <Info className="w-4 h-4 text-violation-info" />;
      default:
        return <Info className="w-4 h-4" />;
    }
  };

  const getSeverityBadgeVariant = (severity: string) => {
    switch (severity) {
      case 'error':
        return 'destructive';
      case 'warning':
        return 'secondary';
      case 'info':
        return 'outline';
      default:
        return 'outline';
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">
      {/* Code Input Panel */}
      <Card className="flex flex-col">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Code Input</span>
            <Button 
              onClick={analyzeCode} 
              disabled={isAnalyzing}
              className="flex items-center gap-2"
            >
              <Play className="w-4 h-4" />
              {isAnalyzing ? 'Analyzing...' : 'Analyze Code'}
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1">
          <Textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Paste your C/C++ code here..."
            className="h-full min-h-[400px] font-mono text-sm bg-code-bg border-muted resize-none"
          />
        </CardContent>
      </Card>

      {/* Results Panel */}
      <Card className="flex flex-col">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>MISRA Analysis Results</span>
            {violations.length > 0 && (
              <Badge variant="secondary">
                {violations.length} violation{violations.length !== 1 ? 's' : ''} found
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1">
          {violations.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <div className="text-center">
                <AlertCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No analysis results yet</p>
                <p className="text-sm">Click "Analyze Code" to check for MISRA violations</p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {violations.map((violation) => (
                <Card key={violation.id} className="border-l-4 border-l-primary">
                  <CardContent className="pt-4">
                    <div className="flex items-start gap-3">
                      {getSeverityIcon(violation.severity)}
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center gap-2">
                          <Badge variant={getSeverityBadgeVariant(violation.severity)}>
                            {violation.severity.toUpperCase()}
                          </Badge>
                          <span className="text-sm text-muted-foreground">
                            Line {violation.line}
                          </span>
                        </div>
                        <h4 className="font-semibold text-sm">{violation.rule}</h4>
                        <p className="text-sm text-muted-foreground">{violation.message}</p>
                        {violation.fix && (
                          <div className="mt-3 p-3 bg-muted rounded-md">
                            <p className="text-xs font-medium text-primary mb-1">Suggested Fix:</p>
                            <p className="text-sm font-mono">{violation.fix}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default CodeEditor;