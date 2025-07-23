import React from 'react';
import { AppProvider } from '@/context/AppContext';
import NewWorkflowPanel from '@/components/NewWorkflowPanel';
import rtMisraLogo from '@/assets/rt-misra-logo.png';

export default function ChatPage() {
  return (
    <AppProvider>
      <div className="min-h-screen bg-background">
        <div className="container mx-auto p-6">
          <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="mb-8 text-center">
              <div className="flex justify-center mb-4">
                <img src={rtMisraLogo} alt="RT MISRA Copilot" className="h-12" />
              </div>
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