import Header from '@/components/Header';
import CodeEditor from '@/components/CodeEditor';
import Stats from '@/components/Stats';

const Index = () => {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="container mx-auto px-6 py-6">
        <Stats />
        <CodeEditor />
      </main>
    </div>
  );
};

export default Index;
