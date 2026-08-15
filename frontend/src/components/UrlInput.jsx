import React, { useState } from 'react';
import { resolveUrl } from '../api/client';

function UrlInput({ onResolved }) {
  const [url, setUrl] = useState('');
  const [includeShorts, setIncludeShorts] = useState(false);
  const [includeLive, setIncludeLive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const data = await resolveUrl(url, includeShorts, includeLive);
      onResolved({ ...data, sourceUrl: url });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2>YouTube 링크 입력</h2>
      {error && <div className="error-message">{error}</div>}
      
      <form onSubmit={handleSubmit}>
        <div>
          <input
            type="text"
            placeholder="YouTube 채널, 재생목록, 또는 영상 URL을 입력하세요"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={loading}
          />
        </div>
        
        <div className="toggle-group">
          <label className="checkbox-label">
            <input 
              type="checkbox" 
              checked={includeShorts} 
              onChange={(e) => setIncludeShorts(e.target.checked)}
              disabled={loading}
            />
            쇼츠 포함
          </label>
          <label className="checkbox-label">
            <input 
              type="checkbox" 
              checked={includeLive} 
              onChange={(e) => setIncludeLive(e.target.checked)}
              disabled={loading}
            />
            라이브 스트림 포함
          </label>
        </div>
        
        <button type="submit" disabled={!url.trim() || loading}>
          {loading ? (
            <><span className="spinner"></span> 정보 가져오는 중...</>
          ) : '영상 목록 가져오기'}
        </button>
      </form>
    </div>
  );
}

export default UrlInput;
