import React from 'react';
import { AppProvider } from '@/context/AppContext';
import NewWorkflowPanel from '@/components/NewWorkflowPanel';

export default function ChatPage() {
  return (
    <AppProvider>
      <div className="min-h-screen bg-background">
        <div className="container mx-auto p-6">
          <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="mb-8 text-center">
              <h1 className="text-3xl font-bold text-foreground mb-2">
                RT MISRA Copilot
              </h1>
              <p className="text-muted-foreground">
                Upload your C++ files and MISRA reports to automatically fix violations
              </p>
            </div>

            {/* Main Workflow Panel */}
            <NewWorkflowPanel />
          </div>
        </div>
      </div>
    </AppProvider>
  );
}