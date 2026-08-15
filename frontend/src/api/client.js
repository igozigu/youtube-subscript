const API_BASE = '/api';

export const resolveUrl = async (url, includeShorts, includeLive) => {
  const response = await fetch(`${API_BASE}/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, include_shorts: includeShorts, include_live: includeLive })
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'URL 분석에 실패했습니다.');
  }
  return response.json();
};

export const createJob = async (videoIds, sourceUrl, sourceTitle, languages, outputFormat) => {
  const response = await fetch(`${API_BASE}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ video_ids: videoIds, source_url: sourceUrl, source_title: sourceTitle, languages, output_format: outputFormat })
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || '작업 생성에 실패했습니다.');
  }
  return response.json();
};

export const getJobStatus = async (jobId) => {
  const response = await fetch(`${API_BASE}/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error('작업 상태를 가져오는데 실패했습니다.');
  }
  return response.json();
};

export const getDownloadUrl = (jobId, format) => {
  return `${API_BASE}/jobs/${jobId}/download?format=${format}`;
};

export const connectWebSocket = (jobId, onMessage, onError, onClose) => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/jobs/${jobId}`;
  
  const ws = new WebSocket(wsUrl);
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.error('WebSocket message parsing error', e);
    }
  };
  
  ws.onerror = (error) => {
    console.error('WebSocket error', error);
    if (onError) onError(error);
  };
  
  ws.onclose = () => {
    if (onClose) onClose();
  };
  
  return ws;
};
