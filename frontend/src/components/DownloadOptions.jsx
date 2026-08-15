import React, { useEffect, useState } from 'react';
import { getDownloadUrl, getJobStatus } from '../api/client';

function DownloadOptions({ jobData, onReset }) {
  const [stats, setStats] = useState({
    total: 0,
    success: 0,
    noSubtitle: 0,
    failed: 0
  });

  useEffect(() => {
    getJobStatus(jobData.id).then(status => {
      let success = 0;
      let noSub = 0;
      let fail = 0;
      
      if (status.items) {
        status.items.forEach(item => {
          if (item.status === 'COMPLETED') success++;
          else if (item.status === 'NO_SUBTITLE') noSub++;
          else if (item.status === 'FAILED') fail++;
        });
      }
      
      setStats({
        total: status.totalCount,
        success,
        noSubtitle: noSub,
        failed: fail
      });
    }).catch(console.error);
  }, [jobData.id]);

  const handleDownload = (format) => {
    const url = getDownloadUrl(jobData.id, format);
    window.location.href = url;
  };

  return (
    <div className="card">
      <h2>작업 완료!</h2>
      
      <div style={{marginBottom: '2rem', padding: '1rem', backgroundColor: '#f9f9f9', borderRadius: '4px'}}>
        <h3 style={{marginTop: 0, marginBottom: '1rem'}}>요약</h3>
        <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem'}}>
          <span>전체 영상:</span> <strong>{stats.total}개</strong>
        </div>
        <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem'}}>
          <span>성공:</span> <strong style={{color: 'var(--success)'}}>{stats.success}개</strong>
        </div>
        <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem'}}>
          <span>자막 없음:</span> <strong style={{color: 'var(--warning)'}}>{stats.noSubtitle}개</strong>
        </div>
        <div style={{display: 'flex', justifyContent: 'space-between'}}>
          <span>실패:</span> <strong style={{color: 'var(--error)'}}>{stats.failed}개</strong>
        </div>
      </div>

      <h3 style={{marginBottom: '1rem'}}>결과 다운로드</h3>
      <div className="download-buttons">
        <button className="download-btn" onClick={() => handleDownload('markdown')}>
          <span className="icon">📄</span>
          Markdown
        </button>
        <button className="download-btn" onClick={() => handleDownload('json')}>
          <span className="icon">{}</span>
          JSON
        </button>
        <button className="download-btn" onClick={() => handleDownload('zip')}>
          <span className="icon">🗜️</span>
          ZIP (전체)
        </button>
      </div>

      <div style={{textAlign: 'center', marginTop: '2rem'}}>
        <button className="secondary" onClick={onReset}>
          새 작업 시작하기
        </button>
      </div>
    </div>
  );
}

export default DownloadOptions;
