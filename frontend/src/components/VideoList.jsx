import React, { useState, useEffect } from 'react';
import { createJob } from '../api/client';

function VideoList({ resolvedData, onJobCreated, onCancel }) {
  const { title: sourceTitle, videos, sourceUrl } = resolvedData;
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [recentCount, setRecentCount] = useState(10);
  const [languages, setLanguages] = useState('ko, en');
  const [outputFormat, setOutputFormat] = useState('zip');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // 기본: 전체 선택 (50개 이하) 또는 처음 50개
    const initialSelect = videos
      .slice(0, Math.min(videos.length, 50))
      .map(v => v.video_id);
    setSelectedIds(new Set(initialSelect));
  }, [videos]);

  const toggleSelectAll = () => {
    if (selectedIds.size === videos.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(videos.map(v => v.video_id)));
    }
  };

  const selectRecent = () => {
    const count = parseInt(recentCount) || 0;
    const ids = videos.slice(0, count).map(v => v.video_id);
    setSelectedIds(new Set(ids));
  };

  const toggleVideo = (videoId) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(videoId)) {
      newSelected.delete(videoId);
    } else {
      newSelected.add(videoId);
    }
    setSelectedIds(newSelected);
  };

  const handleSubmit = async () => {
    if (selectedIds.size === 0) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const langs = languages.split(',').map(l => l.trim()).filter(l => l);
      const job = await createJob(
        Array.from(selectedIds),
        sourceUrl,
        sourceTitle,
        langs,
        outputFormat
      );
      onJobCreated(job);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const formatDate = (dateStr) => {
    if (!dateStr || dateStr.length !== 8) return dateStr || '';
    return `${dateStr.slice(0,4)}-${dateStr.slice(4,6)}-${dateStr.slice(6,8)}`;
  };

  return (
    <div className="card">
      <h2>{sourceTitle || '영상 목록'} ({videos.length}개)</h2>
      
      {error && <div className="error-message">{error}</div>}
      {selectedIds.size > 500 && (
        <div className="warning-message">
          ⚠️ 500개 이상의 영상을 선택하셨습니다. 서버 부하 및 YouTube 차단 위험이 있으므로 배치 처리를 권장합니다.
        </div>
      )}

      <div className="video-list-header">
        <div>
          선택됨: <strong>{selectedIds.size}</strong> / {videos.length}
        </div>
        <div className="video-list-actions">
          <button className="secondary" onClick={toggleSelectAll} style={{padding: '0.5rem 1rem'}}>
            {selectedIds.size === videos.length ? '전체 해제' : '전체 선택'}
          </button>
          <div style={{display: 'flex', gap: '0.5rem', alignItems: 'center'}}>
            <input 
              type="number" 
              min="1" 
              max={videos.length} 
              value={recentCount} 
              onChange={e => setRecentCount(e.target.value)} 
            />
            <button className="secondary" onClick={selectRecent} style={{padding: '0.5rem 1rem'}}>
              최근 선택
            </button>
          </div>
        </div>
      </div>

      <div className="video-items">
        {videos.map(video => (
          <div key={video.video_id} className="video-item">
            <input 
              type="checkbox" 
              checked={selectedIds.has(video.video_id)}
              onChange={() => toggleVideo(video.video_id)}
            />
            <div className="video-info">
              <div className="video-title">{video.title}</div>
              <div className="video-meta">
                {formatDate(video.upload_date)} {video.duration ? `• ${formatDuration(video.duration)}` : ''}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div style={{marginBottom: '1.5rem'}}>
        <h3>설정</h3>
        <div style={{marginBottom: '1rem'}}>
          <label style={{display: 'block', marginBottom: '0.5rem'}}>선호 언어 (쉼표로 구분, 우선순위 순)</label>
          <input 
            type="text" 
            value={languages} 
            onChange={e => setLanguages(e.target.value)} 
            placeholder="ko, en"
          />
        </div>
        
        <div>
          <label style={{display: 'block', marginBottom: '0.5rem'}}>출력 형식</label>
          <div className="radio-group">
            <label className="radio-label">
              <input 
                type="radio" 
                name="format" 
                value="zip" 
                checked={outputFormat === 'zip'}
                onChange={() => setOutputFormat('zip')}
              /> ZIP (개별 파일)
            </label>
            <label className="radio-label">
              <input 
                type="radio" 
                name="format" 
                value="md" 
                checked={outputFormat === 'md'}
                onChange={() => setOutputFormat('md')}
              /> Markdown (통합)
            </label>
            <label className="radio-label">
              <input 
                type="radio" 
                name="format" 
                value="json" 
                checked={outputFormat === 'json'}
                onChange={() => setOutputFormat('json')}
              /> JSON
            </label>
          </div>
        </div>
      </div>

      <div style={{display: 'flex', gap: '1rem', justifyContent: 'flex-end'}}>
        <button className="secondary" onClick={onCancel} disabled={loading}>
          취소
        </button>
        <button onClick={handleSubmit} disabled={selectedIds.size === 0 || loading}>
          {loading ? <><span className="spinner"></span> 시작 중...</> : `대본 추출 시작 (${selectedIds.size}개)`}
        </button>
      </div>
    </div>
  );
}

export default VideoList;
