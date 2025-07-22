
import React, { useState, useEffect, useRef } from 'react';
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
  const originalScrollRef = useRef<HTMLDivElement>(null);
  const fixedScrollRef = useRef<HTMLDivElement>(null);

  // Load code content when modal opens and when violations change
  useEffect(() => {
    if (isOpen && state.projectId) {
      loadCodeContent();
    }
  }, [isOpen, state.projectId, state.selectedViolations]);

  const loadCodeContent = async () => {
    if (!state.projectId) return;
    
    setIsLoading(true);
    try {
      // Use the diff API to get proper comparison
      const diffResult = await apiClient.getDiff(state.projectId);

      if (diffResult.success && diffResult.data) {
        setOriginalCode(diffResult.data.original);
        setFixedCode(diffResult.data.fixed);
      } else {
        throw new Error(diffResult.error || 'Failed to get diff data');
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

  // Synchronized scrolling with prevention of infinite loops
  const handleScroll = (e: React.UIEvent<HTMLDivElement>, isOriginal: boolean) => {
    const element = e.currentTarget;
    const scrollTop = element.scrollTop;
    const scrollLeft = element.scrollLeft;
    
    // Prevent infinite loop by checking if scroll position is different
    const otherRef = isOriginal ? fixedScrollRef.current : originalScrollRef.current;
    
    if (otherRef && (otherRef.scrollTop !== scrollTop || otherRef.scrollLeft !== scrollLeft)) {
      // Temporarily remove scroll listener to prevent infinite loop
      otherRef.onscroll = null;
      otherRef.scrollTop = scrollTop;
      otherRef.scrollLeft = scrollLeft;
      
      // Re-add scroll listener after a brief delay
      setTimeout(() => {
        if (otherRef) {
          otherRef.onscroll = (e) => handleScroll(e as any, !isOriginal);
        }
      }, 10);
    }
  };

  // Highlight differences between original and fixed code
  const highlightDifferences = (code: string, isOriginal: boolean) => {
    if (!originalCode || !fixedCode) return code;
    
    const originalLines = originalCode.split('\n');
    const fixedLines = fixedCode.split('\n');
    const codeLines = code.split('\n');
    
    return codeLines.map((line, index) => {
      const originalLine = originalLines[index] || '';
      const fixedLine = fixedLines[index] || '';
      
      // Check if line is different
      const isDifferent = originalLine !== fixedLine;
      const isModified = isDifferent && originalLine && fixedLine;
      const isAdded = !originalLine && fixedLine;
      const isRemoved = originalLine && !fixedLine;
      
      let className = '';
      if (isModified) {
        className = isOriginal ? 'bg-red-50 border-l-2 border-l-red-400' : 'bg-green-50 border-l-2 border-l-green-400';
      } else if (isAdded && !isOriginal) {
        className = 'bg-green-50 border-l-2 border-l-green-400';
      } else if (isRemoved && isOriginal) {
        className = 'bg-red-50 border-l-2 border-l-red-400';
      }
      
      return (
        <div key={index} className={`${className} px-2 py-0.5`}>
          {line}
        </div>
      );
    });
  };

  const renderCodeBlock = (code: string, title: string, isOriginal?: boolean) => (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-2 p-3 border-b bg-muted">
        <Code2 className="w-4 h-4" />
        <span className="font-medium text-sm">{title}</span>
      </div>
      <div 
        ref={isOriginal ? originalScrollRef : fixedScrollRef}
        className="flex-1 overflow-auto"
        onScroll={(e) => handleScroll(e, !!isOriginal)}
        style={{ scrollBehavior: 'auto' }}
      >
        <pre className="p-4 text-xs font-mono whitespace-pre-wrap break-words leading-5">
          <code className="block">
            {code ? (
              isOriginal !== undefined ? (
                <div className="space-y-0">
                  {highlightDifferences(code, isOriginal)}
                </div>
              ) : (
                code
              )
            ) : (
              'Loading...'
            )}
          </code>
        </pre>
      </div>
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
              <div className="grid grid-cols-2 gap-0 h-[500px] border rounded-lg overflow-hidden">
                {renderCodeBlock(originalCode, "Original (Numbered)", true)}
                <div className="border-l">
                  {renderCodeBlock(fixedCode, "Fixed (With Violations Resolved)", false)}
                </div>
              </div>
              <div className="mt-2 text-xs text-muted-foreground flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-red-50 border-l-2 border-l-red-400"></div>
                  <span>Removed/Modified lines</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-green-50 border-l-2 border-l-green-400"></div>
                  <span>Added/Fixed lines</span>
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
