import React, { useState, useEffect, useRef } from 'react';
import { connectWebSocket, getJobStatus } from '../api/client';

const STATUS_ICONS = {
  PENDING: '⏳',
  PROCESSING: '🔄',
  COMPLETED: '✅',
  NO_SUBTITLE: '⚠️',
  FAILED: '❌'
};

const STATUS_LABELS = {
  PENDING: '대기중',
  PROCESSING: '처리중',
  COMPLETED: '완료',
  NO_SUBTITLE: '자막없음',
  FAILED: '실패'
};

function ProgressPanel({ jobData, onCompleted }) {
  const [jobStatus, setJobStatus] = useState(null);
  const wsRef = useRef(null);
  const jobId = jobData.job_id;

  useEffect(() => {
    // 초기 상태 조회
    getJobStatus(jobId).then(status => {
      setJobStatus(status);
      if (status.status === 'COMPLETED' || status.status === 'FAILED') {
        onCompleted();
      }
    }).catch(console.error);

    // WebSocket 실시간 진행률
    wsRef.current = connectWebSocket(
      jobId,
      (data) => {
        // 백엔드는 전체 JobStatus JSON을 전송
        setJobStatus(data);
        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
          onCompleted();
        }
      },
      (error) => console.error("WebSocket 오류:", error)
    );

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [jobId, onCompleted]);

  if (!jobStatus) {
    return (
      <div className="card">
        <h2>작업 진행 상황</h2>
        <div style={{padding: '2rem', textAlign: 'center', color: 'var(--text-muted)'}}>
          <span className="spinner"></span> 초기화 중...
        </div>
      </div>
    );
  }

  const total = jobStatus.total || 0;
  const completed = jobStatus.completed || 0;
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
  const results = jobStatus.results || [];

  const successCount = results.filter(r => r.status === 'COMPLETED').length;
  const noSubCount = results.filter(r => r.status === 'NO_SUBTITLE').length;
  const failedCount = results.filter(r => r.status === 'FAILED').length;

  return (
    <div className="card">
      <h2>작업 진행 상황</h2>
      
      <div className="progress-container">
        <div className="progress-bar-bg">
          <div className="progress-bar-fill" style={{width: `${percent}%`}}></div>
        </div>
        <div className="progress-stats">
          <span>{percent}% 완료</span>
          <span>
            {completed} / {total} 처리됨
            {successCount > 0 && <> (성공: {successCount})</>}
            {noSubCount > 0 && <> (자막없음: {noSubCount})</>}
            {failedCount > 0 && <> (실패: {failedCount})</>}
          </span>
        </div>
      </div>

      <div className="status-list">
        {results.map((item, idx) => (
          <div key={item.video_id || idx} className="status-item">
            <div className="status-icon" title={STATUS_LABELS[item.status] || item.status}>
              {STATUS_ICONS[item.status] || '❓'}
            </div>
            <div style={{flex: 1}}>
              <div>{item.title || item.video_id}</div>
              {item.error && <div className="status-error">{item.error}</div>}
            </div>
          </div>
        ))}
        {results.length === 0 && (
          <div style={{padding: '1rem', textAlign: 'center', color: 'var(--text-muted)'}}>
            초기화 중...
          </div>
        )}
      </div>
    </div>
  );
}

export default ProgressPanel;
