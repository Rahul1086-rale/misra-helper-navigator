import React from 'react';
import { AppProvider } from '@/context/AppContext';
import ChatInterface from '@/components/ChatInterface';
import FileUploadSection from '@/components/FileUploadSection';
import WorkflowControls from '@/components/WorkflowControls';
import CodeSnippetsPanel from '@/components/CodeSnippetsPanel';

export default function ChatPage() {
  return (
    <AppProvider>
      <div className="min-h-screen bg-background">
        <div className="container mx-auto p-4">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[calc(100vh-2rem)]">
            {/* Left Sidebar */}
            <div className="lg:col-span-1 space-y-4 overflow-y-auto">
              <FileUploadSection />
              <WorkflowControls />
            </div>
            
            {/* Main Chat Area */}
            <div className="lg:col-span-2">
              <ChatInterface />
            </div>
            
            {/* Right Sidebar */}
            <div className="lg:col-span-1 space-y-4 overflow-y-auto">
              <CodeSnippetsPanel />
            </div>
          </div>
        </div>
      </div>
    </AppProvider>
  );
}