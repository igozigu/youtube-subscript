import React, { useState } from 'react';
import UrlInput from './components/UrlInput';
import VideoList from './components/VideoList';
import ProgressPanel from './components/ProgressPanel';
import DownloadOptions from './components/DownloadOptions';

function App() {
  const [step, setStep] = useState('input'); // input, select, processing, download
  const [resolvedData, setResolvedData] = useState(null);
  const [jobData, setJobData] = useState(null);

  const handleUrlResolved = (data) => {
    setResolvedData(data);
    setStep('select');
  };

  const handleJobCreated = (job) => {
    setJobData(job);
    setStep('processing');
  };

  const handleJobCompleted = () => {
    setStep('download');
  };

  const resetWorkflow = () => {
    setStep('input');
    setResolvedData(null);
    setJobData(null);
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>📺 YouTube 대본 추출기</h1>
      </header>
      
      <main className="app-main">
        {step === 'input' && (
          <UrlInput onResolved={handleUrlResolved} />
        )}
        
        {step === 'select' && resolvedData && (
          <VideoList 
            resolvedData={resolvedData} 
            onJobCreated={handleJobCreated}
            onCancel={resetWorkflow}
          />
        )}
        
        {step === 'processing' && jobData && (
          <ProgressPanel 
            jobData={jobData} 
            onCompleted={handleJobCompleted} 
          />
        )}
        
        {step === 'download' && jobData && (
          <DownloadOptions 
            jobData={jobData} 
            onReset={resetWorkflow} 
          />
        )}
      </main>
    </div>
  );
}

export default App;
