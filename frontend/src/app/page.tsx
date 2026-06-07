'use client';
import React, { useEffect, useState, ChangeEvent } from 'react';

interface MetricsData {
  total_leads: number;
  progress_bar_percentage: number;
  counters: {
    queued: number;
    ringing: number;
    in_progress: number;
    completed: number;
    failed: number;
  };
  timeline?: TimelineEvent[];
}

interface TimelineEvent {
  id: number;
  name: string;
  phone: string;
  status: string;
  time: string;
}

interface LeadDetail {
  lead_id: number;
  phone_number: string;
  name: string;
  lead_status: string;
  call_status: string;
  transcript: string | null;
  ai_summary: string | null;
  recording_url: string | null;
  created_at: string | null;
}

interface LeadsDetailData {
  campaign_id: number;
  total_leads: number;
  leads: LeadDetail[];
}

export default function TelemetryControlDashboard() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [metrics, setMetrics] = useState<MetricsData>({
    total_leads: 0,
    progress_bar_percentage: 0,
    counters: { queued: 0, ringing: 0, in_progress: 0, completed: 0, failed: 0 }
  });
  const [leadsDetail, setLeadsDetail] = useState<LeadDetail[]>([]);
  const [selectedLead, setSelectedLead] = useState<LeadDetail | null>(null);
  const [modalLoading, setModalLoading] = useState<boolean>(false);
  const [allocatedNum, setAllocatedNum] = useState<string>('+18555019001');
  const [inboundPrompt, setInboundPrompt] = useState<string>('You are a technical support agent for a SaaS platform...');
  const [inboundVoice, setInboundVoice] = useState<string>('jBpfwMwrlv6462CDreEM');
  const [inboundLogs, setInboundLogs] = useState<string[]>([]);
  const [isConfiguring, setIsConfiguring] = useState<boolean>(false);
  const [drawerOpen, setDrawerOpen] = useState<boolean>(false);
  const targetCampaignId = 1;

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/v1/outbound/campaign/${targetCampaignId}/metrics`);
        if (res.ok) {
          const data = await res.json();
          setMetrics(data);
        }
      } catch (err) {
        console.error('Telemetry link sync offline:', err);
      }
    };

    const fetchLeadsDetail = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/v1/outbound/campaign/${targetCampaignId}/leads-detail`);
        if (res.ok) {
          const data = await res.json();
          setLeadsDetail(data.leads);
        }
      } catch (err) {
        console.error('Failed to fetch leads detail:', err);
      }
    };

    fetchMetrics();
    fetchLeadsDetail();
    const interval = setInterval(() => {
      fetchMetrics();
      fetchLeadsDetail();
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setLogs((prev) => [...prev, `Selected file ready: ${e.target.files[0].name}`]);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      alert('Please select a valid CSV file first.');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`http://localhost:8000/api/v1/outbound/campaign/${targetCampaignId}/upload-csv`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setLogs((prev) => [...prev, `🚀 Injected ${data.total_imported} customer rows into dialing matrix.`]);
        setFile(null);
      } else {
        setLogs((prev) => [...prev, `❌ Error: ${data.detail || 'Upload failed.'}`]);
      }
    } catch (err) {
      setLogs((prev) => [...prev, `❌ Network crash: ${String(err)}`]);
    } finally {
      setLoading(false);
    }
  };
  const closeDrawer = () => {
    setDrawerOpen(false);
    setSelectedLead(null);
  };

  const handleViewDetails = async (leadId: number, leadName: string) => {
    setModalLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/outbound/lead/${leadId}/details`);
      if (res.ok) {
        const data = await res.json();
        setSelectedLead({ ...data, lead_id: leadId, name: leadName });
        setDrawerOpen(true);
      } else {
        const errorData = await res.json();
        setLogs((prev) => [...prev, `❌ Failed to load lead details: ${errorData.detail || 'Unknown error'}`]);
      }
    } catch (err) {
      console.error('Failed fetching lead details:', err);
      setLogs((prev) => [...prev, `❌ Failed to load lead details: ${String(err)}`]);
    } finally {
      setModalLoading(false);
    }
  };

  const handleProvisionInbound = async () => {
    setIsConfiguring(true);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/inbound/campaign/1/assign-number`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          allocated_phone_number: allocatedNum,
          system_prompt: inboundPrompt,
          voice_id: inboundVoice,
        }),
      });

      const data = await res.json();
      if (res.ok) {
        setInboundLogs((prev) => [...prev, `⚡ Inbound Active: ${allocatedNum} is now picking up live calls.`]);
      } else {
        setInboundLogs((prev) => [...prev, `❌ Provision failed: ${data.detail || JSON.stringify(data)}`]);
      }
    } catch (err) {
      setInboundLogs((prev) => [...prev, `❌ Server offline: ${String(err)}`]);
    } finally {
      setIsConfiguring(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return '#10b981';
      case 'failed':
        return '#ef4444';
      case 'in-progress':
      case 'ringing':
        return '#3b82f6';
      case 'queued':
        return '#a855f7';
      default:
        return '#64748b';
    }
  };

  return (
    <div style={{ padding: '3rem', fontFamily: 'system-ui, sans-serif', background: '#090d16', color: '#f8fafc', minHeight: '100vh' }}>
      <header style={{ marginBottom: '2.5rem' }}>
        <h1 style={{ fontSize: '2rem', margin: 0, fontWeight: '700', letterSpacing: '-0.025em' }}>Campaign Operations Center</h1>
        <p style={{ color: '#94a3b8', margin: '0.5rem 0 0 0' }}>Real-time telemetry streams and pipeline acceleration diagnostics.</p>
      </header>

      <div style={{ background: '#111827', border: '1px solid #1f2937', padding: '1.5rem', borderRadius: '12px', marginBottom: '2.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: '600' }}>
          <span style={{ color: '#94a3b8' }}>Overall Campaign Progress</span>
          <span style={{ color: '#38bdf8' }}>{metrics.progress_bar_percentage}% Complete</span>
        </div>
        <div style={{ width: '100%', background: '#1e293b', height: '12px', borderRadius: '999px', overflow: 'hidden' }}>
          <div style={{ width: `${metrics.progress_bar_percentage}%`, background: 'linear-gradient(90deg, #3b82f6, #a855f7)', height: '100%', transition: 'width 0.4s ease-out' }} />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1.5rem', marginBottom: '3rem' }}>
        {[
          { label: 'Total Database Leads', val: metrics.total_leads, color: '#f8fafc' },
          { label: 'Queued in Redis', val: metrics.counters.queued, color: '#a855f7' },
          { label: 'Live (Ringing/Active)', val: metrics.counters.ringing + metrics.counters.in_progress, color: '#3b82f6' },
          { label: 'Completed Agent Calls', val: metrics.counters.completed, color: '#10b981' },
          { label: 'Failed Carrier Drops', val: metrics.counters.failed, color: '#ef4444' }
        ].map((card, idx) => (
          <div key={idx} style={{ background: '#111827', border: '1px solid #1f2937', padding: '1.25rem', borderRadius: '12px' }}>
            <div style={{ textTransform: 'uppercase', fontSize: '0.7rem', color: '#64748b', fontWeight: 'bold', letterSpacing: '0.05em' }}>{card.label}</div>
            <div style={{ fontSize: '1.75rem', fontWeight: 'bold', marginTop: '0.5rem', color: card.color }}>{card.val}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginBottom: '3rem' }}>
        <div style={{ background: '#111827', border: '1px solid #1f2937', padding: '2rem', borderRadius: '16px' }}>
          <h2 style={{ fontSize: '1.25rem', margin: '0 0 0.5rem 0' }}>Launch Call Blast</h2>
          <p style={{ color: '#64748b', fontSize: '0.875rem', margin: '0 0 1.5rem 0' }}>Pipe dynamic consumer lists into the asynchronous engine.</p>
          <div style={{ border: '2px dashed #334155', borderRadius: '8px', padding: '2.5rem', textAlign: 'center', background: '#0f172a' }}>
            <input type='file' accept='.csv' onChange={handleFileChange} id='csvFileField' style={{ display: 'none' }} />
            <label htmlFor='csvFileField' style={{ cursor: 'pointer', display: 'block' }}>
              <span style={{ color: '#3b82f6', fontWeight: '600', display: 'block', marginBottom: '0.25rem' }}>Select spreadsheet template</span>
              <span style={{ color: '#475569', fontSize: '0.75rem' }}>Maps standard phone header keys instantly</span>
            </label>
          </div>

          {file && (
            <div style={{ marginTop: '1rem', background: '#1e293b', padding: '0.75rem 1rem', borderRadius: '6px', fontSize: '0.875rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: '#38bdf8', fontFamily: 'monospace' }}>{file.name}</span>
              <button onClick={handleUpload} disabled={loading} style={{ background: '#10b981', border: 'none', color: '#fff', padding: '0.5rem 1rem', borderRadius: '4px', fontWeight: 'bold', cursor: 'pointer', opacity: loading ? 0.6 : 1 }}>
                {loading ? 'Processing...' : 'Execute Blast'}
              </button>
            </div>
          )}
        </div>

        <div style={{ background: '#111827', border: '1px solid #1f2937', padding: '2rem', borderRadius: '16px' }}>
          <h2 style={{ fontSize: '1.25rem', margin: '0 0 1rem 0' }}>Engine Telemetry Streams</h2>
          <div style={{ background: '#020617', borderRadius: '8px', padding: '1rem', minHeight: '260px', maxHeight: '260px', overflowY: 'auto', border: '1px solid #1e293b', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {!metrics.timeline || metrics.timeline.length === 0 ? (
              <div style={{ color: '#334155', textAlign: 'center', marginTop: '5.5rem' }}>Awaiting pipeline instructions...</div>
            ) : (
              metrics.timeline.map((event) => {
                const statusColor =
                  event.status === 'completed' ? '#10b981' :
                  event.status === 'in-progress' ? '#3b82f6' :
                  event.status === 'ringing' ? '#f59e0b' : '#ef4444';

                return (
                  <div key={event.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#0f172a', padding: '0.75rem 1rem', borderRadius: '8px', borderLeft: `4px solid ${statusColor}`, transition: 'all 0.3s ease' }}>
                    <div>
                      <div style={{ fontWeight: '600', fontSize: '0.9rem', color: '#f8fafc' }}>{event.name}</div>
                      <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.15rem' }}>{event.phone}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span style={{ fontSize: '0.75rem', fontWeight: 'bold', textTransform: 'uppercase', color: statusColor, background: 'rgba(15, 23, 42, 0.6)', padding: '0.2rem 0.5rem', borderRadius: '4px', border: `1px solid ${statusColor}` }}>
                        {event.status}
                      </span>
                      <div style={{ fontSize: '0.7rem', color: '#475569', marginTop: '0.25rem', fontFamily: 'monospace' }}>{event.time}</div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Inbound Voice Route Provisioning UI Panel */}
      <div style={{ background: '#111827', border: '1px solid #1f2937', padding: '2rem', borderRadius: '16px', marginBottom: '3rem' }}>
        <h2 style={{ fontSize: '1.25rem', margin: '0 0 0.5rem 0' }}>Configure Inbound AI Agent</h2>
        <p style={{ color: '#64748b', fontSize: '0.875rem', margin: '0 0 1.5rem 0' }}>Instantly provision numbers and deploy automated inbound customer call routes.</p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', fontWeight: 'bold', marginBottom: '0.5rem', textTransform: 'uppercase' }}>Select Platform Number</label>
            <select
              value={allocatedNum}
              onChange={(e) => setAllocatedNum(e.target.value)}
              style={{ width: '100%', padding: '0.75rem', background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', color: '#fff' }}>
              <option value="+18555019001">+1 (855) 501-9001 [Toll-Free Sandbox Number]</option>
              <option value="+18555019002">+1 (855) 501-9002 [Toll-Free Tech Support Line]</option>
              <option value="+12125550193">+1 (212) 555-0193 [New York Local Line]</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', fontWeight: 'bold', marginBottom: '0.5rem', textTransform: 'uppercase' }}>Inbound Agent Prompt Persona</label>
            <textarea
              rows={3}
              value={inboundPrompt}
              onChange={(e) => setInboundPrompt(e.target.value)}
              style={{ width: '100%', padding: '0.75rem', background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', color: '#fff', fontSize: '0.9rem', resize: 'vertical', fontFamily: 'inherit' }}
            />
          </div>

          <button
            onClick={handleProvisionInbound}
            disabled={isConfiguring}
            style={{ width: '100%', background: 'linear-gradient(90deg, #a855f7, #3b82f6)', border: 'none', color: '#fff', padding: '0.75rem', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer', transition: 'opacity 0.2s', opacity: isConfiguring ? 0.7 : 1 }}>
            {isConfiguring ? 'Deploying Routing Mesh...' : 'Deploy Inbound Routing Protocol'}
          </button>
        </div>

        {inboundLogs.length > 0 && (
          <div style={{ marginTop: '1.25rem', background: '#020617', padding: '0.75rem', borderRadius: '6px', fontFamily: 'monospace', fontSize: '0.8rem', color: '#38bdf8', border: '1px solid #1e293b' }}>
            {inboundLogs.map((l, i) => <div key={i}>{l}</div>)}
          </div>
        )}
      </div>

      <div style={{ background: '#111827', border: '1px solid #1f2937', padding: '2rem', borderRadius: '16px', marginBottom: '3rem' }}>
        <h2 style={{ fontSize: '1.25rem', margin: '0 0 1.5rem 0' }}>Lead Call Log & Transcript Library</h2>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #1f2937' }}>
                <th style={{ textAlign: 'left', padding: '0.75rem', color: '#94a3b8', fontWeight: '600' }}>Name</th>
                <th style={{ textAlign: 'left', padding: '0.75rem', color: '#94a3b8', fontWeight: '600' }}>Phone</th>
                <th style={{ textAlign: 'left', padding: '0.75rem', color: '#94a3b8', fontWeight: '600' }}>Call Status</th>
                <th style={{ textAlign: 'left', padding: '0.75rem', color: '#94a3b8', fontWeight: '600' }}>Summary</th>
                <th style={{ textAlign: 'center', padding: '0.75rem', color: '#94a3b8', fontWeight: '600' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {leadsDetail.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '2rem', color: '#475569' }}>No leads uploaded yet. Start by uploading a CSV file above.</td>
                </tr>
              ) : (
                leadsDetail.map((lead, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid #1e293b', ':hover': { background: '#0f172a' } }}>
                    <td style={{ padding: '0.75rem', color: '#f8fafc' }}>{lead.name}</td>
                    <td style={{ padding: '0.75rem', color: '#64748b', fontFamily: 'monospace' }}>{lead.phone_number}</td>
                    <td style={{ padding: '0.75rem' }}>
                      <span style={{ display: 'inline-block', background: getStatusColor(lead.call_status), color: '#fff', padding: '0.25rem 0.75rem', borderRadius: '999px', fontSize: '0.75rem', fontWeight: '600' }}>
                        {lead.call_status || 'pending'}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem', color: '#94a3b8', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {lead.ai_summary || '—'}
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                      <button
                        onClick={() => handleViewDetails(lead.lead_id, lead.name)}
                        style={{ background: '#3b82f6', border: 'none', color: '#fff', padding: '0.4rem 0.75rem', borderRadius: '4px', cursor: 'pointer', fontSize: '0.75rem', fontWeight: '600' }}>
                        {modalLoading ? 'Loading...' : 'View Details'}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {selectedLead && (
        <div
          onClick={() => setSelectedLead(null)}
          style={{
            position: 'fixed',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(2,6,23,0.6)',
            backdropFilter: 'blur(8px) brightness(0.7)',
            zIndex: 1000,
            padding: '2rem'
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: '100%',
              maxWidth: '720px',
              background: 'rgba(17,24,39,0.9)',
              borderRadius: '12px',
              padding: '1.5rem',
              boxShadow: '0 20px 50px rgba(2,6,23,0.6)',
              color: '#e6eef8',
              maxHeight: '86vh',
              overflowY: 'auto',
              border: '1px solid rgba(255,255,255,0.04)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
              <div>
                <h3 style={{ fontSize: '1.25rem', margin: 0, fontWeight: 800 }}>{selectedLead.name || 'Lead Details'}</h3>
                <div style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '0.25rem' }}>{selectedLead.phone_number}</div>

                <div style={{ 
                  display: 'grid', 
                  gridTemplateColumns: '1fr 1fr', 
                  gap: '1rem', 
                  background: '#1e293b', 
                  padding: '0.75rem 1rem', 
                  borderRadius: '8px',
                  marginTop: '0.5rem',
                  border: '1px solid #334155'
                }}>
                  <div>
                    <span style={{ display: 'block', fontSize: '0.7rem', color: '#64748b', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Dial Timestamp</span>
                    <span style={{ fontSize: '0.85rem', color: '#cbd5e1', fontWeight: '500' }}>{selectedLead.formatted_time || 'Awaiting connection...'}</span>
                  </div>
                  <div>
                    <span style={{ display: 'block', fontSize: '0.7rem', color: '#64748b', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Call Duration</span>
                    <span style={{ fontSize: '0.85rem', color: '#38bdf8', fontWeight: '600' }}>{selectedLead.duration_display || '—'}</span>
                  </div>
                </div>
              </div>

              <button
                onClick={() => setSelectedLead(null)}
                aria-label='Close'
                style={{
                  background: '#1e293b',
                  border: 'none',
                  color: '#94a3b8',
                  fontSize: '1.25rem',
                  cursor: 'pointer',
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center'
                }}
              >
                ×
              </button>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem' }}>
              <div>
                <div style={{ color: '#64748b', fontSize: '0.85rem', fontWeight: 700 }}>Call Status</div>
                <div style={{ marginTop: '0.35rem' }}>
                  <span style={{ display: 'inline-block', background: getStatusColor(selectedLead.call_status || selectedLead.status || 'pending'), color: '#fff', padding: '0.35rem 0.75rem', borderRadius: '999px', fontSize: '0.75rem', fontWeight: 700 }}>
                    {selectedLead.call_status || selectedLead.status || 'pending'}
                  </span>
                </div>
              </div>
              <div style={{ textAlign: 'right', color: '#94a3b8', fontSize: '0.85rem' }}>
                {/* Reserved for future meta info like timestamps or call duration */}
              </div>
            </div>

            <hr style={{ border: 'none', height: '1px', background: 'rgba(255,255,255,0.03)', margin: '1rem 0' }} />

            <div style={{ marginBottom: '1rem' }}>
              <h4 style={{ color: '#94a3b8', fontSize: '0.9rem', fontWeight: 700, margin: '0 0 0.5rem 0' }}>AI Executive Summary</h4>
              <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '8px', color: '#cbd5e1', lineHeight: 1.6 }}>
                {selectedLead.ai_summary || '—'}
              </div>
            </div>

            {selectedLead.recording_url && (
              <div style={{ marginBottom: '1rem' }}>
                <h4 style={{ color: '#94a3b8', fontSize: '0.9rem', fontWeight: 700, margin: '0 0 0.5rem 0' }}>Call Audio Recording</h4>
                <div style={{ background: '#0f172a', padding: '0.75rem', borderRadius: '8px' }}>
                  <audio controls src={selectedLead.recording_url} style={{ width: '100%' }} />
                </div>
              </div>
            )}

            <div style={{ marginBottom: '0.5rem' }}>
              <h4 style={{ color: '#94a3b8', fontSize: '0.9rem', fontWeight: 700, margin: '0 0 0.5rem 0' }}>Conversation Transcript</h4>
              <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '8px', color: '#cbd5e1', lineHeight: 1.6, maxHeight: '48vh', overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.9rem' }}>
                {selectedLead.transcript || 'Transcript not available.'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
