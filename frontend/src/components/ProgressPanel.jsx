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
  const [jobStatus, setJobStatus] = useState(jobData);
  const [items, setItems] = useState({});
  const wsRef = useRef(null);

  useEffect(() => {
    // Initial fetch to get items
    getJobStatus(jobData.id).then(status => {
      setJobStatus(status);
      const itemsMap = {};
      if (status.items) {
        status.items.forEach(item => {
          itemsMap[item.videoId] = item;
        });
      }
      setItems(itemsMap);
      
      if (status.status === 'COMPLETED' || status.status === 'FAILED') {
        onCompleted();
      }
    }).catch(console.error);

    // Setup WebSocket
    wsRef.current = connectWebSocket(
      jobData.id,
      (data) => {
        if (data.type === 'job_update') {
          setJobStatus(prev => ({ ...prev, ...data.data }));
          if (data.data.status === 'COMPLETED' || data.data.status === 'FAILED') {
            onCompleted();
          }
        } else if (data.type === 'item_update') {
          setItems(prev => ({
            ...prev,
            [data.data.videoId]: {
              ...prev[data.data.videoId],
              ...data.data
            }
          }));
        }
      },
      (error) => console.error("WS Error:", error)
    );

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [jobData.id, onCompleted]);

  const total = jobStatus.totalCount || 0;
  const completed = jobStatus.completedCount || 0;
  const failed = jobStatus.failedCount || 0;
  const processed = completed + failed;
  const percent = total > 0 ? Math.round((processed / total) * 100) : 0;

  return (
    <div className="card">
      <h2>작업 진행 상황</h2>
      
      <div className="progress-container">
        <div className="progress-bar-bg">
          <div className="progress-bar-fill" style={{width: `${percent}%`}}></div>
        </div>
        <div className="progress-stats">
          <span>{percent}% 완료</span>
          <span>{processed} / {total} 처리됨 (성공: {completed}, 실패/없음: {failed})</span>
        </div>
      </div>

      <div className="status-list">
        {Object.values(items).map(item => (
          <div key={item.id} className="status-item">
            <div className="status-icon" title={STATUS_LABELS[item.status] || item.status}>
              {STATUS_ICONS[item.status] || '❓'}
            </div>
            <div style={{flex: 1}}>
              <div>{item.title || item.videoId}</div>
              {item.error && <div className="status-error">{item.error}</div>}
            </div>
          </div>
        ))}
        {Object.keys(items).length === 0 && (
          <div style={{padding: '1rem', textAlign: 'center', color: 'var(--text-muted)'}}>
            초기화 중...
          </div>
        )}
      </div>
    </div>
  );
}

export default ProgressPanel;
