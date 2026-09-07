import { useState, useEffect, useCallback } from "react";

const API = "http://localhost:8000";

const SENTIMENT_COLORS = {
  POSITIVE: { text: "#34d399", bg: "rgba(52, 211, 153, 0.1)", border: "rgba(52, 211, 153, 0.3)" },
  NEGATIVE: { text: "#f87171", bg: "rgba(248, 113, 113, 0.1)", border: "rgba(248, 113, 113, 0.3)" },
  NEUTRAL:  { text: "#fbbf24", bg: "rgba(251, 191, 36, 0.1)", border: "rgba(251, 191, 36, 0.3)" },
  "":       { text: "#9ca3af", bg: "rgba(156, 163, 175, 0.1)", border: "rgba(156, 163, 175, 0.2)" },
};

const STATUS_BADGES = {
  pending:   { text: "#818cf8", bg: "rgba(129, 140, 248, 0.1)", border: "rgba(129, 140, 248, 0.3)", pulse: false },
  dialing:   { text: "#fbbf24", bg: "rgba(251, 191, 36, 0.1)", border: "rgba(251, 191, 36, 0.3)", pulse: true },
  active:    { text: "#34d399", bg: "rgba(52, 211, 153, 0.15)", border: "rgba(52, 211, 153, 0.5)", pulse: true },
  completed: { text: "#10b981", bg: "rgba(16, 185, 129, 0.15)", border: "rgba(16, 185, 129, 0.3)", pulse: false },
  failed:    { text: "#ef4444", bg: "rgba(239, 68, 68, 0.15)", border: "rgba(239, 68, 68, 0.3)", pulse: false },
};

export default function App() {
  const [tab, setTab]           = useState("dashboard");
  const [leads, setLeads]       = useState([]);
  const [stats, setStats]       = useState({});
  const [uploading, setUploading] = useState(false);
  const [launching, setLaunching] = useState(false);
  const [msg, setMsg]           = useState("");
  const [selected, setSelected] = useState(null);
  
  // Quick manual dial states
  const [singleName, setSingleName]   = useState("");
  const [singlePhone, setSinglePhone] = useState("");
  const [singleNiche, setSingleNiche] = useState("Photo Frames");
  const [singleFootprint, setSingleFootprint] = useState("No Website");
  const [addingLead, setAddingLead]   = useState(false);
  const [dialImmediately, setDialImmediately] = useState(true);

  const formatPhoneNumber = (val) => {
    if (!val) return "";
    let cleaned = val.replace(/[^\d+]/g, "");
    if (cleaned.includes("+")) {
      cleaned = "+" + cleaned.replace(/\+/g, "");
    }
    if (cleaned.startsWith("+91")) {
      const rest = cleaned.substring(3).replace(/\D/g, "");
      if (rest.length <= 5) {
        return `+91 ${rest}`;
      } else {
        return `+91 ${rest.substring(0, 5)} ${rest.substring(5, 10)}`;
      }
    }
    if (cleaned.startsWith("+1")) {
      const rest = cleaned.substring(2).replace(/\D/g, "");
      if (rest.length <= 3) {
        return `+1 (${rest}`;
      } else if (rest.length <= 6) {
        return `+1 (${rest.substring(0, 3)}) ${rest.substring(3)}`;
      } else {
        return `+1 (${rest.substring(0, 3)}) ${rest.substring(3, 6)}-${rest.substring(6, 10)}`;
      }
    }
    if (!cleaned.startsWith("+")) {
      const digits = cleaned.replace(/\D/g, "");
      if (digits.startsWith("91") && digits.length > 2) {
        const rest = digits.substring(2);
        if (rest.length <= 5) {
          return `+91 ${rest}`;
        } else {
          return `+91 ${rest.substring(0, 5)} ${rest.substring(5, 10)}`;
        }
      } else {
        if (digits.length <= 5) {
          return digits;
        } else {
          return `${digits.substring(0, 5)} ${digits.substring(5, 10)}`;
        }
      }
    }
    return cleaned;
  };

  const handleDialLead = async (leadId) => {
    try {
      const r = await fetch(`${API}/api/leads/${leadId}/dial`, { method: "POST" });
      const d = await r.json();
      if (r.ok) {
        setMsg(d.message || "Call initiated!");
      } else {
        setMsg(d.detail || d.message || "Failed to initiate call.");
      }
    } catch (err) {
      setMsg("Network error initiating call.");
    } finally {
      fetchLeads();
      fetchStats();
    }
  };


  const fetchLeads = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/leads`);
      if (r.ok) setLeads(await r.json());
    } catch (e) {
      console.error("Failed to fetch leads", e);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/stats`);
      if (r.ok) setStats(await r.json());
    } catch (e) {
      console.error("Failed to fetch stats", e);
    }
  }, []);

  useEffect(() => {
    fetchLeads();
    fetchStats();
    const id = setInterval(() => { fetchLeads(); fetchStats(); }, 5000);
    return () => clearInterval(id);
  }, [fetchLeads, fetchStats]);

  const uploadCSV = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    setMsg("");
    const fd = new FormData();
    fd.append("file", file);
    try {
      const r = await fetch(`${API}/api/leads/upload`, { method: "POST", body: fd });
      const d = await r.json();
      setMsg(d.message || d.detail || "Leads uploaded successfully!");
    } catch (err) {
      setMsg("Error uploading leads file.");
    } finally {
      fetchLeads();
      fetchStats();
      setUploading(false);
      e.target.value = null; // Reset file input
    }
  };

  const startCampaign = async () => {
    setLaunching(true);
    setMsg("");
    try {
      const r = await fetch(`${API}/api/campaign/start`, { method: "POST" });
      const d = await r.json();
      setMsg(`Campaign started — ${d.dialed} calls initiated!`);
    } catch (err) {
      setMsg("Failed to start campaign.");
    } finally {
      setLaunching(false);
      fetchLeads();
      fetchStats();
    }
  };

  const exportExcel = () => {
    window.open(`${API}/api/export`, "_blank");
  };

  const handleAddSingleLead = async (e) => {
    e.preventDefault();
    if (!singlePhone.trim()) return;
    setAddingLead(true);
    setMsg("");
    try {
      const r = await fetch(`${API}/api/leads`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          name: singleName, 
          phone: singlePhone,
          niche: singleNiche,
          footprint: singleFootprint
        }),
      });
      const d = await r.json();
      if (r.ok) {
        setMsg(d.message || "Lead added successfully!");
        const leadId = d.id;
        setSingleName("");
        setSinglePhone("");
        setSingleNiche("Photo Frames");
        setSingleFootprint("No Website");
        if (dialImmediately && leadId) {
          await handleDialLead(leadId);
        }
      } else {
        setMsg(d.detail || d.message || "Failed to add lead.");
      }
    } catch (err) {
      setMsg("Network error adding lead.");
    } finally {
      setAddingLead(false);
      fetchLeads();
      fetchStats();
    }
  };

  const statusBadge = (status) => {
    const cfg = STATUS_BADGES[status] || { text: "#9ca3af", bg: "rgba(156,163,175,0.1)", border: "rgba(156,163,175,0.2)", pulse: false };
    return (
      <span className={`status-badge-custom ${cfg.pulse ? "badge-pulse-anim" : ""}`} style={{
        backgroundColor: cfg.bg,
        color: cfg.text,
        border: `1px solid ${cfg.border}`,
        padding: "4px 10px",
        borderRadius: "8px",
        fontSize: "11px",
        fontWeight: "600",
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
        textTransform: "uppercase",
        letterSpacing: "0.5px"
      }}>
        {cfg.pulse && <span style={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: cfg.text, display: "inline-block" }} className="dot-blink-anim" />}
        {status}
      </span>
    );
  };

  const sentimentBadge = (sentiment) => {
    if (!sentiment) return <span style={{ color: "#4b5563" }}>—</span>;
    const cfg = SENTIMENT_COLORS[sentiment] || SENTIMENT_COLORS[""];
    return (
      <span style={{
        color: cfg.text,
        backgroundColor: cfg.bg,
        border: `1px solid ${cfg.border}`,
        padding: "3px 8px",
        borderRadius: "6px",
        fontSize: "11px",
        fontWeight: "600",
        letterSpacing: "0.5px"
      }}>
        {sentiment}
      </span>
    );
  };

  return (
    <div className="dashboard-container">
      {/* Styles Injection */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

        body {
          margin: 0;
          background-color: #030712;
          background-image: 
            radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.15) 0%, transparent 45%),
            radial-gradient(circle at 90% 80%, rgba(139, 92, 246, 0.15) 0%, transparent 45%),
            radial-gradient(circle at 50% 50%, rgba(16, 185, 129, 0.05) 0%, transparent 60%);
          color: #f3f4f6;
          font-family: 'Outfit', sans-serif;
          min-height: 100vh;
          -webkit-font-smoothing: antialiased;
        }

        .dashboard-container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 32px 24px;
        }

        /* Glass Panels */
        .glass-header {
          background: rgba(17, 24, 39, 0.6);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 20px;
          padding: 24px 32px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 28px;
          box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        }

        .glass-card {
          background: rgba(17, 24, 39, 0.45);
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-radius: 16px;
          padding: 20px 24px;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .glass-card:hover {
          transform: translateY(-4px);
          border-color: rgba(99, 102, 241, 0.4);
          box-shadow: 0 12px 24px -10px rgba(99, 102, 241, 0.15), 0 8px 16px -12px rgba(99, 102, 241, 0.15);
        }

        .glass-table-container {
          background: rgba(17, 24, 39, 0.5);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 20px;
          overflow: hidden;
          box-shadow: 0 10px 30px 0 rgba(0, 0, 0, 0.25);
        }

        /* Buttons & Actions */
        .gradient-btn {
          background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
          color: #ffffff;
          border: none;
          padding: 10px 22px;
          border-radius: 12px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          display: inline-flex;
          align-items: center;
          gap: 8px;
          box-shadow: 0 4px 15px rgba(99, 102, 241, 0.35);
        }

        .gradient-btn:hover:not(:disabled) {
          transform: translateY(-1.5px);
          box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
          filter: brightness(1.1);
        }

        .gradient-btn:disabled {
          background: #374151;
          color: #9ca3af;
          box-shadow: none;
          cursor: not-allowed;
        }

        .secondary-btn {
          background: rgba(255, 255, 255, 0.05);
          color: #e5e7eb;
          border: 1px solid rgba(255, 255, 255, 0.08);
          padding: 10px 20px;
          border-radius: 12px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          display: inline-flex;
          align-items: center;
          gap: 8px;
        }

        .secondary-btn:hover:not(:disabled) {
          background: rgba(255, 255, 255, 0.09);
          border-color: rgba(255, 255, 255, 0.2);
          color: #ffffff;
        }

        /* Stats Cards */
        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
          gap: 16px;
          margin-bottom: 28px;
        }

        .stat-value {
          font-size: 28px;
          font-weight: 700;
          line-height: 1;
          margin-top: 6px;
          letter-spacing: -0.5px;
        }

        /* Table UI */
        .glass-table {
          width: 100%;
          border-collapse: collapse;
          text-align: left;
        }

        .glass-table th {
          padding: 16px 20px;
          font-size: 12px;
          font-weight: 600;
          color: #9ca3af;
          text-transform: uppercase;
          letter-spacing: 1px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          background: rgba(10, 15, 30, 0.4);
        }

        .glass-table td {
          padding: 16px 20px;
          font-size: 13.5px;
          color: #e5e7eb;
          border-bottom: 1px solid rgba(255, 255, 255, 0.06);
          transition: background 0.2s ease;
        }

        .glass-table tr:hover td {
          background: rgba(255, 255, 255, 0.02);
        }

        /* Modal styling */
        .modal-overlay {
          position: fixed;
          inset: 0;
          background: rgba(3, 7, 18, 0.85);
          backdrop-filter: blur(8px);
          -webkit-backdrop-filter: blur(8px);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
          animation: fadeIn 0.25s ease-out;
        }

        .modal-content {
          background: rgba(17, 24, 39, 0.95);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 24px;
          width: 90%;
          max-width: 650px;
          max-height: 80vh;
          overflow: hidden;
          display: flex;
          flex-direction: column;
          box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
          animation: slideUp 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        }

        .modal-body {
          overflow-y: auto;
          padding: 24px;
          flex-grow: 1;
        }

        /* Bubble transcripts */
        .chat-bubble {
          margin: 8px 0;
          padding: 12px 16px;
          border-radius: 16px;
          font-size: 13.5px;
          line-height: 1.5;
          max-width: 85%;
          display: inline-block;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .bubble-agent {
          background: linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(139, 92, 246, 0.2) 100%);
          border: 1px solid rgba(99, 102, 241, 0.3);
          color: #e0e7ff;
          float: left;
          clear: both;
          border-bottom-left-radius: 4px;
        }

        .bubble-customer {
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.08);
          color: #f3f4f6;
          float: right;
          clear: both;
          border-bottom-right-radius: 4px;
        }

        /* Alerts */
        .alert-success {
          background: rgba(16, 185, 129, 0.1);
          border: 1px solid rgba(16, 185, 129, 0.3);
          color: #34d399;
          padding: 12px 20px;
          border-radius: 12px;
          font-size: 13px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 24px;
          box-shadow: 0 4px 12px rgba(16, 185, 129, 0.05);
        }

        /* Animations definition */
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        @keyframes slideUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .dot-blink-anim {
          animation: blink 1.2s infinite ease-in-out;
        }

        @keyframes blink {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 1; }
        }

        .badge-pulse-anim {
          animation: borderPulse 1.8s infinite;
        }

        @keyframes borderPulse {
          0% { box-shadow: 0 0 0 0 rgba(251, 191, 36, 0.4); }
          70% { box-shadow: 0 0 0 6px rgba(251, 191, 36, 0); }
          100% { box-shadow: 0 0 0 0 rgba(251, 191, 36, 0); }
        }
      `}</style>

      {/* Header Panel */}
      <div className="glass-header">
        <div>
          <h1 style={{
            fontSize: "24px",
            fontWeight: "700",
            margin: 0,
            background: "linear-gradient(135deg, #a78bfa 0%, #818cf8 50%, #34d399 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            letterSpacing: "-0.5px"
          }}>
            AI Calling Sales Agent
          </h1>
          <p style={{ fontSize: "13px", color: "#9ca3af", margin: "6px 0 0" }}>
            Real-Time Speech-to-Speech Telephony · Powered by Gemini Live API
          </p>
        </div>
        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          <label className="secondary-btn" style={{ cursor: "pointer" }}>
            {uploading ? "⏳ Uploading..." : "📂 Upload Leads CSV"}
            <input type="file" accept=".csv,.xlsx,.xls" style={{ display: "none" }} onChange={uploadCSV} disabled={uploading} />
          </label>
          <button onClick={startCampaign} disabled={launching || leads.filter(l => l.status === "pending").length === 0} className="gradient-btn">
            {launching ? "🚀 Launching..." : "⚡ Start Campaign"}
          </button>
          <button onClick={exportExcel} className="secondary-btn" style={{ padding: "10px 14px" }} title="Export as Excel">
            📥 Export
          </button>
        </div>
      </div>

      {msg && (
        <div className="alert-success">
          <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            ✨ {msg}
          </span>
          <span style={{ cursor: "pointer", fontWeight: "bold", opacity: 0.7 }} onClick={() => setMsg("")}>✕</span>
        </div>
      )}

      {/* Stats Board */}
      <div className="stats-grid">
        {[
          { label: "Total Leads",  value: stats.total     || 0, color: "#818cf8", border: "rgba(129, 140, 248, 0.4)" },
          { label: "Completed",    value: stats.completed  || 0, color: "#10b981", border: "rgba(16, 185, 129, 0.4)" },
          { label: "Positive",     value: stats.positive   || 0, color: "#34d399", border: "rgba(52, 211, 153, 0.4)" },
          { label: "Negative",     value: stats.negative   || 0, color: "#f87171", border: "rgba(248, 113, 113, 0.4)" },
          { label: "Neutral",      value: stats.neutral    || 0, color: "#fbbf24", border: "rgba(251, 191, 36, 0.4)" },
          { label: "Pending",      value: stats.pending    || 0, color: "#9ca3af", border: "rgba(156, 163, 175, 0.3)" },
        ].map(s => (
          <div key={s.label} className="glass-card" style={{ borderLeft: `4px solid ${s.color}` }}>
            <div style={{ fontSize: "11.5px", fontWeight: "600", color: "#9ca3af", textTransform: "uppercase", letterSpacing: "0.5px" }}>{s.label}</div>
            <div className="stat-value" style={{ color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Quick Add Lead Form */}
      <div className="glass-card" style={{ marginBottom: "28px", padding: "20px 24px" }}>
        <h3 style={{ margin: "0 0 16px 0", fontSize: "15px", fontWeight: "600", color: "#a5b4fc", display: "flex", alignItems: "center", gap: "8px" }}>
          <span>⚡</span> Quick Add Lead (Test Phone Number)
        </h3>
        <form onSubmit={handleAddSingleLead} style={{ display: "flex", gap: "16px", flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: "1.2", minWidth: "180px" }}>
            <label style={{ fontSize: "11px", fontWeight: "600", color: "#9ca3af", textTransform: "uppercase" }}>Lead Name</label>
            <input 
              type="text" 
              placeholder="e.g. John Doe" 
              value={singleName}
              onChange={e => setSingleName(e.target.value)}
              style={{
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: "10px",
                padding: "10px 14px",
                color: "#ffffff",
                fontFamily: "inherit",
                fontSize: "13px",
                outline: "none"
              }}
            />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: "1.2", minWidth: "180px" }}>
            <label style={{ fontSize: "11px", fontWeight: "600", color: "#9ca3af", textTransform: "uppercase" }}>Phone Number (with Country Code)</label>
            <input 
              type="text" 
              placeholder="e.g. +91XXXXXXXXXX" 
              value={singlePhone}
              onChange={e => setSinglePhone(formatPhoneNumber(e.target.value))}
              required
              style={{
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: "10px",
                padding: "10px 14px",
                color: "#ffffff",
                fontFamily: "monospace",
                fontSize: "13.5px",
                outline: "none"
              }}
            />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: "1", minWidth: "150px" }}>
            <label style={{ fontSize: "11px", fontWeight: "600", color: "#9ca3af", textTransform: "uppercase" }}>Category</label>
            <select
              value={singleNiche}
              onChange={e => setSingleNiche(e.target.value)}
              style={{
                background: "rgba(25,30,50,0.8)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: "10px",
                padding: "10px 14px",
                color: "#ffffff",
                fontSize: "13px",
                outline: "none",
                height: "38px"
              }}
            >
              {["Photo Frames", "Personalized Gifts", "Gifts", "Printing", "T-Shirt", "Albums"].map(opt => (
                <option key={opt} value={opt} style={{ background: "#030712" }}>{opt}</option>
              ))}
            </select>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: "1", minWidth: "150px" }}>
            <label style={{ fontSize: "11px", fontWeight: "600", color: "#9ca3af", textTransform: "uppercase" }}>Footprint</label>
            <select
              value={singleFootprint}
              onChange={e => setSingleFootprint(e.target.value)}
              style={{
                background: "rgba(25,30,50,0.8)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: "10px",
                padding: "10px 14px",
                color: "#ffffff",
                fontSize: "13px",
                outline: "none",
                height: "38px"
              }}
            >
              {["No Website", "Only Maps Listing", "Slow/Basic Site"].map(opt => (
                <option key={opt} value={opt} style={{ background: "#030712" }}>{opt}</option>
              ))}
            </select>
          </div>
          <div style={{ display: "flex", alignItems: "center", height: "38px", minWidth: "150px" }}>
            <label style={{ 
              display: "flex", 
              alignItems: "center", 
              gap: "8px", 
              fontSize: "12px", 
              fontWeight: "600", 
              color: "#a5b4fc", 
              cursor: "pointer",
              userSelect: "none"
            }}>
              <input 
                type="checkbox" 
                checked={dialImmediately}
                onChange={e => setDialImmediately(e.target.checked)}
                style={{
                  width: "16px",
                  height: "16px",
                  accentColor: "#8b5cf6",
                  cursor: "pointer"
                }}
              />
              <span>⚡ Dial Immediately</span>
            </label>
          </div>
          <div>
            <button 
              type="submit" 
              disabled={addingLead || !singlePhone} 
              className="gradient-btn" 
              style={{ height: "38px", padding: "0 24px" }}
            >
              {addingLead ? "Adding..." : "➕ Add Lead"}
            </button>
          </div>
        </form>
      </div>

      {/* Main Call Logs Table */}
      <div className="glass-table-container">
        <div style={{
          padding: "18px 24px",
          background: "rgba(10, 15, 30, 0.4)",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          fontSize: "14px",
          fontWeight: "600",
          color: "#e5e7eb",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center"
        }}>
          <span>Active Campaign Logs & Call Results</span>
          {leads.some(l => l.status === "dialing" || l.status === "active") && (
            <span style={{ fontSize: 12, color: "#fbbf24", display: "flex", alignItems: "center", gap: 6 }} className="pulse">
              ● Live Campaign Processing
            </span>
          )}
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="glass-table">
            <thead>
              <tr>
                {["Name", "Phone Number", "Category", "Footprint", "Status", "Sentiment", "Call Summary", "Duration", "Actions"].map(h => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {leads.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ padding: "48px 24px", textAlign: "center", color: "#9ca3af" }}>
                    <div style={{ fontSize: "24px", marginBottom: "8px" }}>📂</div>
                    No leads uploaded yet. Click "Upload Leads CSV" to import leads!
                  </td>
                </tr>
              ) : leads.map(l => (
                <tr key={l.id}>
                  <td style={{ fontWeight: "500", color: "#ffffff" }}>{l.name || "—"}</td>
                  <td style={{ fontFamily: "monospace", letterSpacing: "0.5px", color: "#9ca3af" }}>{l.phone}</td>
                  <td style={{ color: "#c084fc", fontWeight: "600", fontSize: "12px" }}>{l.niche || "Photo Frames"}</td>
                  <td style={{ fontSize: "11.5px" }}>
                    {l.footprint ? (
                      <span style={{
                        backgroundColor: l.footprint === "Only Maps Listing" ? "rgba(245, 158, 11, 0.1)" : 
                                         l.footprint === "Slow/Basic Site" ? "rgba(59, 130, 246, 0.1)" : "rgba(239, 68, 68, 0.1)",
                        color: l.footprint === "Only Maps Listing" ? "#fbbf24" : 
                               l.footprint === "Slow/Basic Site" ? "#60a5fa" : "#f87171",
                        padding: "3px 8px",
                        borderRadius: "6px",
                        border: `1px solid ${l.footprint === "Only Maps Listing" ? "rgba(245, 158, 11, 0.25)" : 
                                              l.footprint === "Slow/Basic Site" ? "rgba(59, 130, 246, 0.25)" : "rgba(239, 68, 68, 0.25)"}`,
                        fontWeight: "600"
                      }}>
                        {l.footprint}
                      </span>
                    ) : "No Website"}
                  </td>
                  <td>{statusBadge(l.status)}</td>
                  <td>{sentimentBadge(l.sentiment)}</td>
                  <td style={{
                    maxWidth: "180px",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    color: "#9ca3af"
                  }} title={l.summary}>
                    {l.summary || "—"}
                  </td>
                  <td style={{ color: "#9ca3af", fontWeight: "500" }}>
                    {l.duration ? `${l.duration}s` : "—"}
                  </td>
                  <td style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    {l.transcript && (
                      <button onClick={() => setSelected(l)} className="secondary-btn" style={{
                        padding: "6px 12px",
                        fontSize: "11.5px",
                        borderRadius: "8px",
                        borderColor: "rgba(99, 102, 241, 0.3)",
                        color: "#a5b4fc",
                        whiteSpace: "nowrap"
                      }}>
                        View Transcript
                      </button>
                    )}
                    {l.status === "dialing" || l.status === "active" ? (
                      <span style={{ 
                        color: "#fbbf24", 
                        fontSize: "11.5px", 
                        fontWeight: "600",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                        whiteSpace: "nowrap"
                      }}>
                        <span style={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: "#fbbf24", display: "inline-block" }} className="dot-blink-anim" />
                        In Call
                      </span>
                    ) : (
                      <button onClick={() => handleDialLead(l.id)} className="secondary-btn" style={{
                        padding: "6px 12px",
                        fontSize: "11.5px",
                        borderRadius: "8px",
                        borderColor: "rgba(16, 185, 129, 0.3)",
                        color: "#34d399",
                        whiteSpace: "nowrap"
                      }}>
                        📞 Call
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Transcript & Summary Modal */}
      {selected && (
        <div className="modal-overlay" onClick={() => setSelected(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            {/* Modal Header */}
            <div style={{
              padding: "20px 24px",
              borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center"
            }}>
              <div>
                <strong style={{ fontSize: "16px", color: "#ffffff" }}>{selected.name || "Lead Details"}</strong>
                <span style={{ marginLeft: "12px", fontFamily: "monospace", color: "#9ca3af", fontSize: "13px" }}>{selected.phone}</span>
              </div>
              <button onClick={() => setSelected(null)} style={{
                background: "rgba(255, 255, 255, 0.05)",
                border: "none",
                borderRadius: "50%",
                width: "32px",
                height: "32px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#e5e7eb",
                cursor: "pointer",
                fontSize: "14px",
                transition: "background 0.2s"
              }} onMouseOver={e => e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.1)"}
                 onMouseOut={e => e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.05)"}>✕</button>
            </div>

            {/* Modal Scroll Body */}
            <div className="modal-body">
              {/* Call Summary Section */}
              {selected.summary && (
                <div style={{
                  background: "rgba(99, 102, 241, 0.06)",
                  border: "1px solid rgba(99, 102, 241, 0.15)",
                  borderRadius: "14px",
                  padding: "16px 18px",
                  fontSize: "13px",
                  color: "#e0e7ff",
                  marginBottom: "24px",
                  lineHeight: "1.5"
                }}>
                  <div style={{ fontWeight: "700", marginBottom: "6px", color: "#c7d2fe", textTransform: "uppercase", fontSize: "11px", letterSpacing: "0.5px" }}>
                    AI Summary & Analysis
                  </div>
                  {selected.summary}
                  <div style={{ marginTop: "12px", display: "flex", gap: "12px", alignItems: "center" }}>
                    <span style={{ fontSize: "11.5px", color: "#a5b4fc" }}>
                      Sentiment Score: {sentimentBadge(selected.sentiment)}
                    </span>
                    <span style={{ color: "rgba(255,255,255,0.15)" }}>|</span>
                    <span style={{ fontSize: "11.5px", color: "#9ca3af" }}>
                      Call Duration: <strong>{selected.duration || 0}s</strong>
                    </span>
                  </div>
                </div>
              )}

              {/* Chat Bubble Logs */}
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                <div style={{ fontWeight: "700", color: "#9ca3af", textTransform: "uppercase", fontSize: "11px", letterSpacing: "0.5px", marginBottom: "4px" }}>
                  Call Transcript
                </div>
                {selected.transcript ? (
                  selected.transcript.split("\n").map((line, i) => {
                    const isAgent = line.startsWith("Agent");
                    const cleanLine = line.replace(/^(Agent \(Priya\):|Customer:)/, "").trim();
                    if (!cleanLine) return null;
                    return (
                      <div key={i} style={{ width: "100%" }}>
                        <div className={`chat-bubble ${isAgent ? "bubble-agent" : "bubble-customer"}`}>
                          <div style={{ fontSize: "10px", fontWeight: "700", opacity: 0.6, marginBottom: "4px", textTransform: "uppercase" }}>
                            {isAgent ? "Priya (AI Assistant)" : "Customer"}
                          </div>
                          {cleanLine}
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div style={{ padding: "20px", textAlign: "center", color: "#6b7280", fontStyle: "italic" }}>
                    No transcript dialog captured for this call.
                  </div>
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div style={{
              padding: "16px 24px",
              borderTop: "1px solid rgba(255, 255, 255, 0.08)",
              textAlign: "right",
              background: "rgba(10, 15, 30, 0.3)"
            }}>
              <button onClick={() => setSelected(null)} className="secondary-btn" style={{ padding: "8px 20px" }}>
                Close Logs
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
