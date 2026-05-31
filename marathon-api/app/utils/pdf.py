import io
from datetime import date, datetime

def generate_certificate_pdf(
    participant_name: str,
    bib_number: str,
    distance: str,
    finish_time: datetime,
    event_name: str,
    event_date: date,
    location: str = ""
) -> bytes:
    # Format values
    finish_str = finish_time.strftime("%H:%M:%S")  # e.g. 01:23:45
    date_str   = event_date.strftime("%d · %m · %Y")  # e.g. 15 · 12 · 2026
    date_short = event_date.strftime("%b %d, %Y")      # e.g. Dec 15, 2026
    name_initials = "".join(w[0].upper() for w in participant_name.split()[:2])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500&family=DM+Mono:wght@400;500&display=swap');

  /* ── Page setup ── */
  @page {{
    size: A4 landscape;
    margin: 0;
  }}

  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}

  body {{
    width: 297mm;
    height: 210mm;
    background: #F8F7F4;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'DM Sans', sans-serif;
    -webkit-font-smoothing: antialiased;
  }}

  /* ── Certificate card ── */
  .cert {{
    width: 260mm;
    height: 185mm;
    background: #FFFFFF;
    position: relative;
    overflow: hidden;
  }}

  /* ── Top accent bar ── */
  .cert-top-bar {{
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 6mm;
    background: #E8450A;
  }}

  /* ── Bottom bar ── */
  .cert-bottom-bar {{
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 3mm;
    background: #1A1917;
  }}

  /* ── Inset border ── */
  .cert-border {{
    position: absolute;
    top: 9mm; left: 6mm; right: 6mm; bottom: 5mm;
    border: 0.3mm solid #E8E6E1;
  }}

  /* ── Corner ornaments ── */
  .corner {{
    position: absolute;
    width: 14mm;
    height: 14mm;
  }}
  .corner-tl {{ top: 9mm;  left: 6mm; }}
  .corner-tr {{ top: 9mm;  right: 6mm; transform: scaleX(-1); }}
  .corner-bl {{ bottom: 5mm; left: 6mm;  transform: scaleY(-1); }}
  .corner-br {{ bottom: 5mm; right: 6mm;  transform: scale(-1,-1); }}

  /* ── Watermark ── */
  .watermark {{
    position: absolute;
    bottom: 30mm;
    left: 50%;
    transform: translateX(-50%);
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 52mm;
    letter-spacing: -2mm;
    color: rgba(232, 69, 10, 0.035);
    white-space: nowrap;
    text-transform: uppercase;
    pointer-events: none;
    user-select: none;
  }}

  /* ── Left accent column ── */
  .cert-left-col {{
    position: absolute;
    top: 6mm; bottom: 3mm; left: 0;
    width: 18mm;
    background: #1A1917;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 3mm;
    padding: 8mm 0;
  }}

  .vert-text {{
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 3mm;
    letter-spacing: 1.5mm;
    text-transform: uppercase;
    color: rgba(255,255,255,0.5);
    writing-mode: vertical-rl;
    transform: rotate(180deg);
  }}

  .vert-dot {{
    width: 1.2mm;
    height: 1.2mm;
    border-radius: 50%;
    background: #E8450A;
  }}

  /* ── Main content ── */
  .cert-content {{
    position: absolute;
    top: 6mm; bottom: 3mm;
    left: 18mm; right: 0;
    padding: 10mm 14mm 10mm 12mm;
    display: flex;
    flex-direction: column;
  }}

  /* ── Header row ── */
  .cert-header {{
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 5mm;
  }}

  .cert-logo {{
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 4mm;
    letter-spacing: 0.8mm;
    text-transform: uppercase;
    color: #E8450A;
  }}

  .cert-logo-dot {{
    color: #1A1917;
  }}

  .cert-badge {{
    background: #FDF0EB;
    border: 0.3mm solid rgba(232,69,10,0.25);
    border-radius: 1mm;
    padding: 1.5mm 4mm;
    font-size: 2.8mm;
    font-weight: 500;
    letter-spacing: 0.5mm;
    text-transform: uppercase;
    color: #E8450A;
  }}

  /* ── Divider ── */
  .divider-row {{
    display: flex;
    align-items: center;
    gap: 3mm;
    margin-bottom: 5mm;
  }}
  .divider-line {{
    flex: 1;
    height: 0.3mm;
    background: #E8E6E1;
  }}
  .divider-diamond {{
    width: 2mm;
    height: 2mm;
    background: #E8450A;
    transform: rotate(45deg);
    flex-shrink: 0;
  }}

  /* ── Presented to ── */
  .presented-label {{
    font-size: 2.8mm;
    letter-spacing: 0.8mm;
    text-transform: uppercase;
    color: #A09D97;
    font-weight: 500;
    text-align: center;
    margin-bottom: 2mm;
  }}

  /* ── Name ── */
  .cert-name {{
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 14mm;
    letter-spacing: -0.5mm;
    color: #1A1917;
    text-align: center;
    line-height: 1;
    margin-bottom: 3mm;
  }}

  /* ── Body text ── */
  .cert-body {{
    font-size: 3.5mm;
    color: #6B6862;
    font-weight: 400;
    text-align: center;
    line-height: 1.6;
    margin-bottom: 5mm;
  }}
  .cert-body strong {{
    color: #1A1917;
    font-weight: 600;
  }}

  /* ── Stats row ── */
  .stats-row {{
    display: flex;
    gap: 0;
    border: 0.3mm solid #E8E6E1;
    border-radius: 1.5mm;
    overflow: hidden;
    margin-bottom: 5mm;
  }}

  .stat-cell {{
    flex: 1;
    padding: 3mm 4mm;
    text-align: center;
    border-right: 0.3mm solid #E8E6E1;
  }}
  .stat-cell:last-child {{ border-right: none; }}

  .stat-label {{
    font-size: 2.3mm;
    letter-spacing: 0.6mm;
    text-transform: uppercase;
    color: #A09D97;
    font-weight: 500;
    margin-bottom: 1.5mm;
  }}

  .stat-value {{
    font-family: 'DM Mono', monospace;
    font-size: 6mm;
    font-weight: 500;
    color: #1A1917;
    letter-spacing: -0.2mm;
    line-height: 1;
  }}

  .stat-unit {{
    font-family: 'DM Mono', monospace;
    font-size: 2.5mm;
    color: #A09D97;
    margin-top: 1mm;
  }}

  /* ── Footer ── */
  .cert-footer {{
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    padding-top: 4mm;
    border-top: 0.3mm solid #E8E6E1;
    margin-top: auto;
  }}

  .sig-block {{}}
  .sig-line {{
    width: 30mm;
    height: 0.3mm;
    background: #D1CEC7;
    margin-bottom: 1.5mm;
  }}
  .sig-label {{
    font-size: 2.5mm;
    letter-spacing: 0.5mm;
    text-transform: uppercase;
    color: #A09D97;
    font-weight: 500;
  }}

  .verified-badge {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1.5mm;
  }}
  .verified-circle {{
    width: 10mm;
    height: 10mm;
    border-radius: 50%;
    background: #FDF0EB;
    border: 0.3mm solid rgba(232,69,10,0.25);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 3.5mm;
    color: #E8450A;
  }}
  .verified-label {{
    font-size: 2.3mm;
    letter-spacing: 0.5mm;
    text-transform: uppercase;
    color: #A09D97;
    font-weight: 500;
  }}

  .event-block {{
    text-align: right;
  }}
  .event-name-sm {{
    font-family: 'Syne', sans-serif;
    font-size: 3mm;
    font-weight: 700;
    letter-spacing: 0.4mm;
    text-transform: uppercase;
    color: #6B6862;
    margin-bottom: 1mm;
  }}
  .event-date-val {{
    font-family: 'DM Mono', monospace;
    font-size: 3mm;
    color: #A09D97;
  }}

  /* ── BIB row ── */
  .bib-row {{
    display: flex;
    justify-content: center;
    margin-bottom: 5mm;
  }}
  .bib-badge {{
    display: flex;
    align-items: center;
    gap: 3mm;
    background: #FDF0EB;
    border: 0.3mm solid rgba(232,69,10,0.2);
    border-radius: 1mm;
    padding: 2mm 5mm;
  }}
  .bib-label {{
    font-size: 2.5mm;
    letter-spacing: 0.6mm;
    text-transform: uppercase;
    color: #E8450A;
    font-weight: 600;
  }}
  .bib-num {{
    font-family: 'DM Mono', monospace;
    font-size: 6mm;
    font-weight: 500;
    color: #E8450A;
    letter-spacing: 0.5mm;
  }}
</style>
</head>
<body>
<div class="cert">

  <!-- Structural bars -->
  <div class="cert-top-bar"></div>
  <div class="cert-bottom-bar"></div>
  <div class="cert-border"></div>

  <!-- Watermark -->
  <div class="watermark">Finisher</div>

  <!-- Left column -->
  <div class="cert-left-col">
    <span class="vert-text">Marathon Platform</span>
    <div class="vert-dot"></div>
    <span class="vert-text">{event_date.year}</span>
  </div>

  <!-- Corner ornaments -->
  <div class="corner corner-tl">
    <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M4 4 L4 22 M4 4 L22 4" stroke="#E8450A" stroke-width="1.5"
            stroke-linecap="round"/>
      <path d="M4 4 L4 14 M4 4 L14 4" stroke="#E8E6E1" stroke-width="0.5"
            stroke-linecap="round"/>
      <circle cx="4" cy="4" r="2" fill="#E8450A"/>
    </svg>
  </div>
  <div class="corner corner-tr">
    <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M4 4 L4 22 M4 4 L22 4" stroke="#E8450A" stroke-width="1.5"
            stroke-linecap="round"/>
      <path d="M4 4 L4 14 M4 4 L14 4" stroke="#E8E6E1" stroke-width="0.5"
            stroke-linecap="round"/>
      <circle cx="4" cy="4" r="2" fill="#E8450A"/>
    </svg>
  </div>
  <div class="corner corner-bl">
    <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M4 4 L4 22 M4 4 L22 4" stroke="#E8450A" stroke-width="1.5"
            stroke-linecap="round"/>
      <path d="M4 4 L4 14 M4 4 L14 4" stroke="#E8E6E1" stroke-width="0.5"
            stroke-linecap="round"/>
      <circle cx="4" cy="4" r="2" fill="#E8450A"/>
    </svg>
  </div>
  <div class="corner corner-br">
    <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M4 4 L4 22 M4 4 L22 4" stroke="#E8450A" stroke-width="1.5"
            stroke-linecap="round"/>
      <path d="M4 4 L4 14 M4 4 L14 4" stroke="#E8E6E1" stroke-width="0.5"
            stroke-linecap="round"/>
      <circle cx="4" cy="4" r="2" fill="#E8450A"/>
    </svg>
  </div>

  <!-- Main content -->
  <div class="cert-content">

    <!-- Header -->
    <div class="cert-header">
      <div class="cert-logo">Marathon<span class="cert-logo-dot">·</span>Platform</div>
      <div class="cert-badge">Certificate of Completion</div>
    </div>

    <!-- Divider -->
    <div class="divider-row">
      <div class="divider-line"></div>
      <div class="divider-diamond"></div>
      <div class="divider-line"></div>
    </div>

    <!-- Name -->
    <div class="presented-label">This certificate is proudly presented to</div>
    <div class="cert-name">{participant_name}</div>

    <!-- Body -->
    <div class="cert-body">
      for successfully completing the<br>
      <strong>{event_name} — {distance} Run</strong><br>
      {"held at " + location if location else ""}
    </div>

    <!-- BIB -->
    <div class="bib-row">
      <div class="bib-badge">
        <div class="bib-label">Race BIB</div>
        <div class="bib-num">#{bib_number}</div>
      </div>
    </div>

    <!-- Stats -->
    <div class="stats-row">
      <div class="stat-cell">
        <div class="stat-label">Finish Time</div>
        <div class="stat-value">{finish_str[:5]}</div>
        <div class="stat-unit">hrs · min</div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">Seconds</div>
        <div class="stat-value">{finish_str[6:]}</div>
        <div class="stat-unit">sec</div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">Distance</div>
        <div class="stat-value">{distance}</div>
        <div class="stat-unit">completed</div>
      </div>
      <div class="stat-cell">
        <div class="stat-label">Race Date</div>
        <div class="stat-value" style="font-size:4.5mm">{event_date.strftime("%b %d")}</div>
        <div class="stat-unit">{event_date.year}</div>
      </div>
    </div>

    <!-- Footer -->
    <div class="cert-footer">
      <div class="sig-block">
        <div class="sig-line"></div>
        <div class="sig-label">Race Director</div>
      </div>

      <div class="verified-badge">
        <div class="verified-circle">{name_initials}</div>
        <div class="verified-label">Verified</div>
      </div>

      <div class="event-block">
        <div class="event-name-sm">{event_name}</div>
        <div class="event-date-val">{date_str}</div>
      </div>
    </div>

  </div><!-- /cert-content -->

</div><!-- /cert -->
</body>
</html>"""

    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration

    font_config = FontConfiguration()
    return HTML(string=html).write_pdf(
        font_config=font_config,
        presentational_hints=True
    )
