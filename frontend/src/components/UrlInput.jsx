import React, { useState } from 'react';
import { resolveUrl, uploadCookies, deleteCookies } from '../api/client';

function UrlInput({ onResolved }) {
  const [url, setUrl] = useState('');
  const [includeShorts, setIncludeShorts] = useState(false);
  const [includeLive, setIncludeLive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 쿠키 관련 상태
  const [showCookieSection, setShowCookieSection] = useState(false);
  const [cookieStatus, setCookieStatus] = useState(null);
  const [cookieUploading, setCookieUploading] = useState(false);

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

  const handleCookieUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setCookieUploading(true);
    setCookieStatus(null);
    try {
      await uploadCookies(file);
      setCookieStatus({ type: 'success', message: '✅ cookies.txt 가 성공적으로 적용되었습니다.' });
    } catch (err) {
      setCookieStatus({ type: 'error', message: `❌ 쿠키 업로드 실패: ${err.message}` });
    } finally {
      setCookieUploading(false);
    }
  };

  const handleCookieDelete = async () => {
    try {
      await deleteCookies();
      setCookieStatus({ type: 'info', message: '쿠키 파일이 삭제되었습니다.' });
    } catch (err) {
      setCookieStatus({ type: 'error', message: `삭제 실패: ${err.message}` });
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
        
        <button type="submit" disabled={!url.trim() || loading} style={{width: '100%', marginBottom: '1.5rem'}}>
          {loading ? (
            <><span className="spinner"></span> 정보 가져오는 중...</>
          ) : '영상 목록 가져오기'}
        </button>
      </form>

      <div style={{borderTop: '1px solid var(--border-color)', paddingTop: '1rem'}}>
        <div 
          onClick={() => setShowCookieSection(!showCookieSection)}
          style={{cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '0.9rem'}}
        >
          <span>🍪 YouTube 인증 우회 (쿠키 파일 설정)</span>
          <span>{showCookieSection ? '▲ 닫기' : '▼ 열기'}</span>
        </div>

        {showCookieSection && (
          <div style={{marginTop: '1rem', padding: '1rem', backgroundColor: '#f9f9f9', borderRadius: '4px', fontSize: '0.9rem'}}>
            <p style={{margin: '0 0 0.75rem 0', color: 'var(--text-muted)'}}>
              YouTube 봇 감지(429 또는 로그인 요구)로 추출이 제한될 때 브라우저에서 추출한 <code>cookies.txt</code>를 등록하여 인증을 우회할 수 있습니다.
            </p>
            {cookieStatus && (
              <div style={{marginBottom: '0.75rem', color: cookieStatus.type === 'success' ? 'var(--success)' : cookieStatus.type === 'error' ? 'var(--error)' : 'var(--info)'}}>
                {cookieStatus.message}
              </div>
            )}
            <div style={{display: 'flex', gap: '0.5rem', alignItems: 'center'}}>
              <label className="secondary" style={{cursor: 'pointer', display: 'inline-block', padding: '0.5rem 1rem', border: '1px solid var(--border-color)', borderRadius: '4px', backgroundColor: 'white'}}>
                {cookieUploading ? '업로드 중...' : '📁 cookies.txt 선택'}
                <input 
                  type="file" 
                  accept=".txt" 
                  onChange={handleCookieUpload} 
                  style={{display: 'none'}} 
                  disabled={cookieUploading}
                />
              </label>
              <button 
                type="button" 
                className="secondary" 
                onClick={handleCookieDelete}
                style={{padding: '0.5rem 1rem'}}
              >
                쿠키 초기화
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default UrlInput;
