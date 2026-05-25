// FloorplanQA paper landing page — single page with theme toggle in top-right.

const ARXIV_URL = 'https://arxiv.org/abs/2507.07644';
const HF_URL = 'https://huggingface.co/papers/2507.07644';
const CODE_URL = 'https://github.com/OldDeLorean/FloorplanQA';
const PDF_URL = ARXIV_URL.replace('/abs/', '/pdf/') + '.pdf';

const AUTHORS = [
{ name: 'Fedor Rodionov', aff: 1, corresponding: true },
{ name: 'Abdelrahman Eldesokey', aff: 1 },
{ name: 'Michael Birsak', aff: 1 },
{ name: 'John Femiani', aff: 2 },
{ name: 'Bernard Ghanem', aff: 1 },
{ name: 'Peter Wonka', aff: 1 }];


const AFFILIATIONS = [
{ id: 1, name: 'KAUST', full: 'King Abdullah University of Science and Technology' },
{ id: 2, name: 'Miami University', full: 'Miami University, Oxford, OH' }];


const TASKS = [
{ name: 'Pair Distance', fmt: 'N', cat: 'Metric', desc: 'Euclidean distance between two object centroids' },
{ name: 'View Angle', fmt: 'N', cat: 'Metric', desc: 'Smallest angle between inter-object vector and global north' },
{ name: 'Free Space', fmt: 'N', cat: 'Topology', desc: 'Total non-occupied floor area (m²)' },
{ name: 'Max Box', fmt: 'N', cat: 'Topology', desc: 'Area of the largest rectangle fitting inside the room' },
{ name: 'Placement', fmt: 'B', cat: 'Topology', desc: 'Can a w × h object fit fully without overlaps' },
{ name: 'Visibility', fmt: 'L', cat: 'Topology', desc: 'All objects intersecting a centroid-to-centroid ray' },
{ name: 'Repositioning', fmt: 'N', cat: 'Dynamic', desc: 'How far an object can slide in a direction before contact' },
{ name: 'Shortest Path', fmt: 'S', cat: 'Dynamic', desc: 'Collision-free path with required clearance' }];


const BIBTEX = `@inproceedings{rodionov2025floorplanqa,
  title     = {FloorplanQA: A Benchmark for Spatial Reasoning in LLMs
               using Structured Representations},
  author    = {Rodionov, Fedor and Eldesokey, Abdelrahman and Birsak, Michael
               and Femiani, John and Ghanem, Bernard and Wonka, Peter},
  booktitle = {Proceedings of the 43rd International Conference on Machine Learning (ICML)},
  year      = {2025},
  address   = {Seoul, South Korea}
}`;

const ABSTRACT = `We introduce FloorplanQA, a diagnostic benchmark for evaluating spatial reasoning in
large language models grounded in structured representations of indoor scenes
(kitchens, living rooms, bedrooms, bathrooms), encoded symbolically in JSON or XML
layouts. The benchmark covers distance measurement, visibility, path finding, and
object placement within constrained spaces. Our results across 15 frontier
open-source and commercial LLMs reveal that while models may succeed on shallow
queries, they often fail to respect physical constraints and preserve spatial
coherence — though they remain mostly robust to small spatial perturbations.`;

const FINDINGS = [
'Models compute the sum of object areas instead of the union — failing on Free Space and Max Box.',
'Distance and angle errors mostly originate from centroid computation on non-axis-aligned polygons (HSSD layouts).',
'Shortest-path planning collapses in cluttered scenes where buffering narrows corridors.',
'A Python code interpreter rescues arithmetic-heavy tasks (+40 pp on Distance / Angle) but does not help planning.',
'Adding a top-down render to JSON gives selective gains but never compensates for removing the JSON.'];


// ---------- icons ----------
const ICONS = {
  arxiv:
  <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
      <path d="M4 6h16M4 12h16M4 18h10" stroke="currentColor" strokeWidth="1.6" fill="none" strokeLinecap="round" />
    </svg>,

  pdf:
  <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
      <path d="M7 3h7l4 4v14a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" stroke="currentColor" strokeWidth="1.4" fill="none" />
      <path d="M14 3v4h4" stroke="currentColor" strokeWidth="1.4" fill="none" />
    </svg>,

  code:
  <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
      <path d="M8 7l-5 5 5 5M16 7l5 5-5 5M14 4l-4 16" stroke="currentColor" strokeWidth="1.6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>,

  hf:
  <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.4" fill="none" />
      <circle cx="9" cy="11" r="1.2" fill="currentColor" />
      <circle cx="15" cy="11" r="1.2" fill="currentColor" />
      <path d="M9 15c1 1.2 2 1.8 3 1.8s2-.6 3-1.8" stroke="currentColor" strokeWidth="1.4" fill="none" strokeLinecap="round" />
    </svg>,

  sun:
  <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.6" fill="none" />
      <path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"
    stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>,

  moon:
  <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"
    stroke="currentColor" strokeWidth="1.6" fill="none" strokeLinejoin="round" />
    </svg>

};

// ---------- theme toggle ----------
function ThemeToggle({ theme, setTheme }) {
  return (
    <div style={{
      position: 'fixed',
      top: 22,
      right: 22,
      zIndex: 50,
      display: 'flex',
      gap: 0,
      padding: 3,
      border: '1px solid var(--rule)',
      background: 'var(--bg)',
      borderRadius: 999,
      boxShadow: theme === 'dark' ?
      '0 4px 18px rgba(0,0,0,0.4)' :
      '0 2px 10px rgba(0,0,0,0.06)',
      backdropFilter: 'blur(8px)',
      transition: 'background 200ms ease, border-color 200ms ease'
    }}>
      {[
      { id: 'light', icon: ICONS.sun, label: 'Light' },
      { id: 'dark', icon: ICONS.moon, label: 'Dark' }].
      map((opt) => {
        const active = theme === opt.id;
        return (
          <button
            key={opt.id}
            onClick={() => setTheme(opt.id)}
            aria-label={`Switch to ${opt.label} theme`}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '6px 12px',
              border: 'none',
              borderRadius: 999,
              fontFamily: 'var(--mono)',
              fontSize: 11,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              cursor: 'pointer',
              background: active ? 'var(--accent)' : 'transparent',
              color: active ? 'var(--accent-fg)' : 'var(--muted)',
              transition: 'background 160ms ease, color 160ms ease'
            }}>

            {opt.icon}
            <span>{opt.label}</span>
          </button>);

      })}
    </div>);

}

// ---------- main page ----------
function PaperPage() {
  return (
    <div style={{
      maxWidth: 920,
      margin: '0 auto',
      padding: '72px 56px 88px',
      fontFamily: 'var(--serif)'
    }}>
      {/* venue strip */}
      <div style={{
        fontFamily: 'var(--mono)',
        fontSize: 11,
        letterSpacing: '0.16em',
        textTransform: 'uppercase',
        color: 'var(--accent)',
        marginBottom: 22,
        display: 'flex',
        gap: 14,
        alignItems: 'center'
      }}>
        <span style={{ display: 'inline-block', width: 8, height: 8, background: 'var(--accent)', borderRadius: '50%' }} />
        ICML 2026
        <span style={{ color: 'var(--muted)' }}>·</span>
        <span style={{ color: 'var(--muted)' }}>Seoul, South Korea</span>
        <img src="assets/logo-icml.svg" alt="ICML"
             style={{ height: 18, width: 'auto', display: 'block', marginLeft: 8, filter: 'var(--logo-filter, none)' }} />
      </div>

      {/* title */}
      <h1 style={{
        fontWeight: 600,
        fontSize: 56,
        lineHeight: 1.05,
        letterSpacing: '-0.018em',
        margin: '0 0 10px',
        color: 'var(--fg)',
        textWrap: 'balance'
      }}>
        FloorplanQA
      </h1>
      <div style={{
        fontSize: 25,
        fontStyle: 'italic',
        fontWeight: 400,
        color: 'var(--muted)',
        margin: '0 0 30px',
        textWrap: 'balance',
        lineHeight: 1.25
      }}>
        A Benchmark for Spatial Reasoning in LLMs using Structured Representations
      </div>

      {/* authors — single line */}
      <div style={{
        fontSize: 14,
        marginBottom: 24,
        lineHeight: 1.5,
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'clip'
      }}>
        {AUTHORS.map((a, i) =>
        <React.Fragment key={a.name}>
            <span style={{ whiteSpace: 'nowrap' }}>
              {a.name}
              <sup style={{ color: 'var(--accent)', fontFamily: 'var(--mono)', fontSize: 10, marginLeft: 2 }}>{a.aff}</sup>
              {a.corresponding && <sup style={{ color: 'var(--muted)', fontFamily: 'var(--mono)', fontSize: 10, marginLeft: 1 }}>✉</sup>}
            </span>
            {i < AUTHORS.length - 1 && <span style={{ color: 'var(--muted)', margin: '0 6px' }}>·</span>}
          </React.Fragment>
        )}
      </div>

      {/* affiliation logos */}
      <div style={{
        display: 'flex',
        alignItems: 'flex-end',
        gap: 36,
        marginBottom: 36
      }}>
        <AffLogo n={1} src="assets/logo-kaust.png" alt="KAUST" label="KAUST" height={48} />
        <AffLogo n={2} src="assets/logo-miami.png" alt="Miami University" label="Miami University" height={36} />
      </div>

      {/* link buttons */}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 44 }}>
        <LinkBtn href={ARXIV_URL} primary>{ICONS.arxiv}<span>arXiv</span><Meta>2507.07644</Meta></LinkBtn>
        <LinkBtn href={PDF_URL}>{ICONS.pdf}<span>PDF</span></LinkBtn>
        <LinkBtn href={CODE_URL}>{ICONS.code}<span>Code</span><Meta>GitHub</Meta></LinkBtn>
        <LinkBtn href={HF_URL}>{ICONS.hf}<span>Hugging Face</span></LinkBtn>
      </div>

      {/* hero figure: 2x2 grid of 4 example floorplans */}
      <Figure caption="Representative layouts from FloorplanQA. Bottom-right is from HSSD (semi-real); the other three are synthetic layouts generated by our pipeline.">
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 14
        }}>
          {[
          { src: 'assets/fp-h-167.png', label: 'Generated · Living Room' },
          { src: 'assets/fp-bedroom.png', label: 'Generated · Bedroom' },
          { src: 'assets/fp-k-31.png', label: 'Generated · Kitchen' },
          { src: 'assets/fp-hssd-livingroom.png', label: 'HSSD · Living Room' }].
          map(({ src, label }) =>
          <div key={src} style={{
            border: '1px solid var(--rule)',
            padding: 10,
            background: '#ffffff',
            display: 'flex',
            flexDirection: 'column',
            gap: 8
          }}>
              <div style={{
              aspectRatio: '1 / 1',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: '#fff',
              overflow: 'hidden'
            }}>
                <img src={src} alt={label}
              style={{ maxWidth: '100%', maxHeight: '100%', display: 'block' }} />
              </div>
              <div style={{
              fontFamily: 'var(--mono)',
              fontSize: 10.5,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: '#6b6f6a',
              textAlign: 'center',
              paddingTop: 2
            }}>{label}</div>
            </div>
          )}
        </div>
      </Figure>

      <Section number="01" title="Abstract">
        <p style={{ margin: 0, fontSize: 18, lineHeight: 1.65 }}>{ABSTRACT}</p>
      </Section>

      <Section number="02" title="Benchmark at a glance">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1, background: 'var(--rule)', border: '1px solid var(--rule)' }}>
          {[
          ['2,000', 'symbolic layouts'],
          ['16,000', 'spatial Q&A pairs'],
          ['8', 'task types'],
          ['15', 'LLMs evaluated']].
          map(([n, l]) =>
          <div key={l} style={{ background: 'var(--bg)', padding: '22px 18px' }}>
              <div style={{ fontSize: 38, fontWeight: 500, lineHeight: 1, letterSpacing: '-0.02em' }}>{n}</div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--muted)', marginTop: 8 }}>{l}</div>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: 22, marginTop: 18, fontSize: 14, color: 'var(--muted)', flexWrap: 'wrap', alignItems: 'baseline' }}>
          <span><strong style={{ color: 'var(--fg)', fontWeight: 600 }}>1,800</strong> synthetic (Gemini 2.5 Pro)</span>
          <span style={{ color: 'var(--rule)' }}>/</span>
          <span><strong style={{ color: 'var(--fg)', fontWeight: 600 }}>200</strong> from HSSD (semi-real)</span>
          <span style={{ color: 'var(--rule)' }}>/</span>
          <span>kitchens · living rooms · bedrooms</span>
        </div>
      </Section>

      <Section number="03" title="Question taxonomy">
        <div style={{ border: '1px solid var(--rule)', fontSize: 14 }}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1.3fr 0.7fr 0.7fr 2.8fr',
            background: 'var(--subtle)',
            fontFamily: 'var(--mono)',
            fontSize: 11,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            color: 'var(--muted)',
            padding: '10px 16px',
            borderBottom: '1px solid var(--rule)'
          }}>
            <div>Task</div><div>Format</div><div>Category</div><div>Description</div>
          </div>
          {TASKS.map((task, i) =>
          <div key={task.name} style={{
            display: 'grid',
            gridTemplateColumns: '1.3fr 0.7fr 0.7fr 2.8fr',
            padding: '14px 16px',
            borderBottom: i < TASKS.length - 1 ? '1px solid var(--rule)' : 'none',
            alignItems: 'baseline'
          }}>
              <div style={{ fontWeight: 500 }}>{task.name}</div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--accent)' }}>{task.fmt}</div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--muted)', letterSpacing: '0.04em' }}>{task.cat}</div>
              <div>{task.desc}</div>
            </div>
          )}
          <div style={{
            padding: '10px 16px',
            background: 'var(--subtle)',
            fontFamily: 'var(--mono)',
            fontSize: 11,
            color: 'var(--muted)',
            display: 'flex',
            gap: 18,
            flexWrap: 'wrap'
          }}>
            <span><span style={{ color: 'var(--accent)' }}>N</span> scalar</span>
            <span><span style={{ color: 'var(--accent)' }}>B</span> boolean</span>
            <span><span style={{ color: 'var(--accent)' }}>L</span> list</span>
            <span><span style={{ color: 'var(--accent)' }}>S</span> sequence</span>
          </div>
        </div>
      </Section>

      <Section number="04" title="Results">
        <Figure caption="Accuracy of general (top) and reasoning (bottom) models, broken down by model (left) and question type (right). HSSD · Bedrooms · Living Rooms · Kitchens.">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {[
            { src: 'assets/chart-base.png', label: 'General models' },
            { src: 'assets/chart-reason.png', label: 'Reasoning models' }].
            map(({ src, label }) =>
            <div key={src} style={{ position: 'relative' }}>
                <div style={{
                position: 'absolute',
                top: 8,
                left: 10,
                fontFamily: 'var(--mono)',
                fontSize: 10.5,
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                color: '#6b6f6a',
                background: 'rgba(255,255,255,0.92)',
                padding: '3px 8px',
                borderRadius: 2,
                zIndex: 1
              }}>{label}</div>
                <img src={src} alt={label}
              style={{ width: '100%', display: 'block', background: '#fff' }} />
              </div>
            )}
          </div>
        </Figure>
      </Section>

      <Section number="05" title="Key findings">
        <ol style={{ margin: 0, padding: 0, listStyle: 'none' }}>
          {FINDINGS.map((f, i) =>
          <li key={i} style={{
            padding: '14px 0',
            borderTop: '1px solid var(--rule)',
            display: 'grid',
            gridTemplateColumns: '40px 1fr',
            gap: 14,
            alignItems: 'baseline'
          }}>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--accent)', letterSpacing: '0.1em' }}>
                {String(i + 1).padStart(2, '0')}
              </span>
              <span style={{ fontSize: 16, lineHeight: 1.55 }}>{f}</span>
            </li>
          )}
          <li style={{ borderTop: '1px solid var(--rule)', padding: 0, height: 0, listStyle: 'none' }} />
        </ol>
      </Section>

      <Section number="06" title="Vision–language ablation">
        <p style={{ margin: '0 0 18px', fontSize: 16, lineHeight: 1.6 }}>
          Adding a top-down render to the JSON gives selective gains (icons, labeled boxes, photorealistic),
          but image-only modalities fall to 19–40% — symbolic JSON remains the dominant signal.
        </p>
        <Figure caption="Two rendering styles of the same living-room layout: schematic icons (left) vs. a photorealistic top-down image generated by Gemini 3.1 Flash Image (right).">
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 14,
            maxWidth: 540,
            margin: '0 auto'
          }}>
            {[
            { src: 'assets/render-icons.png', label: 'Schematic icons', contain: true },
            { src: 'assets/render-nanobana.png', label: 'Photorealistic', contain: false }].
            map(({ src, label, contain }) =>
            <div key={src} style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 8
            }}>
                <div style={{
                aspectRatio: '3 / 4',
                background: '#fff',
                border: '1px solid var(--rule)',
                overflow: 'hidden',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                  <img src={src} alt={label}
                style={contain ?
                { maxWidth: '100%', maxHeight: '100%', display: 'block' } :
                { width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
                </div>
                <div style={{
                fontFamily: 'var(--mono)',
                fontSize: 10.5,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: 'var(--muted)',
                textAlign: 'center'
              }}>{label}</div>
              </div>
            )}
          </div>
        </Figure>
      </Section>

      <Section number="07" title="Cite">
        <pre style={{
          margin: 0,
          padding: '20px 22px',
          background: 'var(--subtle)',
          border: '1px solid var(--rule)',
          fontFamily: 'var(--mono)',
          fontSize: 12.5,
          lineHeight: 1.65,
          color: 'var(--fg)',
          overflow: 'auto',
          whiteSpace: 'pre'
        }}>{BIBTEX}</pre>
      </Section>

      {/* footer */}
      <div style={{
        marginTop: 56,
        paddingTop: 24,
        borderTop: '1px solid var(--rule)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'baseline',
        gap: 20,
        flexWrap: 'wrap',
        fontFamily: 'var(--mono)',
        fontSize: 11.5,
        color: 'var(--muted)',
        letterSpacing: '0.04em'
      }}>
        <div>
          <a href="mailto:fedor.rodionov@kaust.edu.sa" style={{ color: 'var(--accent)', textDecoration: 'none' }}>
            fedor.rodionov@kaust.edu.sa
          </a>
        </div>
        <div style={{ textAlign: 'right' }}>
          Page template inspired by the Nerfies project page.
        </div>
      </div>
    </div>);

}

function AffLogo({ n, src, alt, label, height }) {
  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'flex-start', gap: 8, height: "73px" }}>
      <div style={{
        display: 'inline-flex',
        alignItems: 'baseline',
        gap: 6,
        fontFamily: 'var(--mono)',
        fontSize: 11,
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
        color: 'var(--muted)'
      }}>
        <sup style={{ color: 'var(--accent)', fontSize: 10 }}>{n}</sup>
        <span>{label}</span>
      </div>
      <div style={{
        background: 'var(--logo-bg)',
        padding: 'var(--logo-pad)',
        borderRadius: 4,
        display: 'inline-flex',
        alignItems: 'center',
        transition: 'background 200ms ease, padding 200ms ease'
      }}>
        <img src={src} alt={alt}
        style={{ height, display: 'block', width: 'auto' }} />
      </div>
    </div>);

}

function Meta({ children }) {
  return (
    <span style={{
      fontFamily: 'var(--mono)',
      fontSize: 10.5,
      color: 'var(--muted)',
      marginLeft: 2,
      letterSpacing: '0.02em'
    }}>{children}</span>);

}

function LinkBtn({ href, primary, children }) {
  const [hover, setHover] = React.useState(false);
  const style = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    padding: '9px 14px',
    fontFamily: 'var(--serif)',
    fontSize: 14,
    textDecoration: 'none',
    borderRadius: 2,
    transition: 'all 140ms ease',
    border: primary ? '1px solid var(--accent)' : '1px solid var(--rule)',
    background: primary ?
    hover ? 'var(--accent)' : 'transparent' :
    hover ? 'var(--subtle)' : 'transparent',
    color: primary ?
    hover ? 'var(--accent-fg)' : 'var(--accent)' :
    'var(--fg)'
  };
  return (
    <a href={href} target="_blank" rel="noopener noreferrer"
    onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
    style={style}>
      {children}
    </a>);

}

function Section({ number, title, children }) {
  return (
    <section style={{ margin: '52px 0 0' }}>
      <div style={{
        display: 'flex',
        alignItems: 'baseline',
        gap: 16,
        marginBottom: 22,
        paddingBottom: 12,
        borderBottom: '1px solid var(--rule)'
      }}>
        <span style={{
          fontFamily: 'var(--mono)',
          fontSize: 11,
          color: 'var(--accent)',
          letterSpacing: '0.12em'
        }}>§ {number}</span>
        <h2 style={{
          fontWeight: 500,
          fontSize: 22,
          margin: 0,
          letterSpacing: '-0.005em'
        }}>{title}</h2>
      </div>
      <div>{children}</div>
    </section>);

}

function Figure({ caption, children }) {
  return (
    <figure style={{ margin: '0 0 8px', padding: 0 }}>
      <div style={{ border: '1px solid var(--rule)', padding: 10, background: 'var(--fig-bg)' }}>
        {children}
      </div>
      <figcaption style={{
        fontSize: 13,
        fontStyle: 'italic',
        color: 'var(--muted)',
        marginTop: 10,
        lineHeight: 1.5,
        textWrap: 'pretty'
      }}>
        {caption}
      </figcaption>
    </figure>);

}

// ---------- app ----------
function App() {
  const [theme, setThemeState] = React.useState(() => {
    if (typeof window === 'undefined') return 'light';
    const saved = localStorage.getItem('floorplanqa-theme');
    if (saved === 'light' || saved === 'dark') return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  const setTheme = (next) => {
    setThemeState(next);
    try {localStorage.setItem('floorplanqa-theme', next);} catch (e) {}
  };

  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  return (
    <>
      <ThemeToggle theme={theme} setTheme={setTheme} />
      <PaperPage />
    </>);

}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
