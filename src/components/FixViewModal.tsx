import React, { useState, useEffect } from 'react';
import { X, Download, RefreshCw, Eye, Code2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAppContext } from '@/context/AppContext';
import { useToast } from '@/hooks/use-toast';
import { apiClient } from '@/lib/api';

interface FixViewModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function FixViewModal({ isOpen, onClose }: FixViewModalProps) {
  const { state, dispatch } = useAppContext();
  const { toast } = useToast();
  const [originalCode, setOriginalCode] = useState<string>('');
  const [fixedCode, setFixedCode] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);

  // Load code content when modal opens
  useEffect(() => {
    if (isOpen && state.projectId) {
      loadCodeContent();
    }
  }, [isOpen, state.projectId]);

  const loadCodeContent = async () => {
    if (!state.projectId) return;
    
    setIsLoading(true);
    try {
      // Load original numbered file
      const originalResponse = await fetch(`/api/files/numbered/${state.projectId}`);
      if (originalResponse.ok) {
        const originalText = await originalResponse.text();
        setOriginalCode(originalText);
      }

      // Load fixed temporary file
      const fixedResponse = await fetch(`/api/files/temp-fixed/${state.projectId}`);
      if (fixedResponse.ok) {
        const fixedText = await fixedResponse.text();
        setFixedCode(fixedText);
      }
    } catch (error) {
      console.error('Failed to load code content:', error);
      toast({
        title: "Error",
        description: "Failed to load code content",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const downloadFinalFile = async () => {
    if (!state.projectId) return;
    
    try {
      setIsLoading(true);
      
      // First apply fixes and denumber
      const mergeResponse = await apiClient.applyFixes(state.projectId);
      
      if (mergeResponse.success) {
        // Then download the final file
        const blob = await apiClient.downloadFixedFile(state.projectId);
        
        if (blob) {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.style.display = 'none';
          a.href = url;
          a.download = `fixed_${state.uploadedFile?.name || 'file.cpp'}`;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
          
          dispatch({ type: 'SET_CURRENT_STEP', payload: 'finalize' });
          toast({ 
            title: "Success", 
            description: "Fixed file downloaded successfully" 
          });
          onClose();
        } else {
          throw new Error('Failed to download file');
        }
      } else {
        throw new Error(mergeResponse.error || 'Failed to apply fixes');
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : 'Failed to download file',
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const renderCodeBlock = (code: string, title: string) => (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-2 p-3 border-b bg-muted">
        <Code2 className="w-4 h-4" />
        <span className="font-medium text-sm">{title}</span>
      </div>
      <ScrollArea className="flex-1">
        <pre className="p-4 text-xs font-mono whitespace-pre-wrap break-words">
          <code>{code || 'Loading...'}</code>
        </pre>
      </ScrollArea>
    </div>
  );

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-7xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Eye className="w-5 h-5" />
            Code Fix Preview
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* View Options */}
          <Tabs defaultValue="diff" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="diff">Side-by-Side Diff</TabsTrigger>
              <TabsTrigger value="original">Original Code</TabsTrigger>
              <TabsTrigger value="fixed">Fixed Code</TabsTrigger>
            </TabsList>

            <TabsContent value="diff" className="mt-4">
              <div className="grid grid-cols-2 gap-4 h-[500px] border rounded-lg overflow-hidden">
                {renderCodeBlock(originalCode, "Original (Numbered)")}
                <div className="border-l">
                  {renderCodeBlock(fixedCode, "Fixed (With Violations Resolved)")}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="original" className="mt-4">
              <div className="h-[500px] border rounded-lg overflow-hidden">
                {renderCodeBlock(originalCode, "Original Code (Numbered)")}
              </div>
            </TabsContent>

            <TabsContent value="fixed" className="mt-4">
              <div className="h-[500px] border rounded-lg overflow-hidden">
                {renderCodeBlock(fixedCode, "Fixed Code (With Violations Resolved)")}
              </div>
            </TabsContent>
          </Tabs>

          {/* Action Buttons */}
          <div className="flex justify-between items-center pt-4 border-t">
            <div className="text-sm text-muted-foreground">
              {state.selectedViolations.length} violations fixed
            </div>
            
            <div className="flex gap-3">
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button 
                variant="outline" 
                onClick={loadCodeContent}
                disabled={isLoading}
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              <Button 
                onClick={downloadFinalFile}
                disabled={isLoading}
              >
                <Download className="w-4 h-4 mr-2" />
                {isLoading ? 'Processing...' : 'Download Final File'}
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}