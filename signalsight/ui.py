"""Styling and reusable HTML components."""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700;800&display=swap');
/* Palette: Vivid Orange #FA5F05 · Deep orange #BC4704 · Peach #FDB78F · Paper white #F6F6F6 / #FFFFFF
   Dark Azure #333F48 · Graphite #605D5B · Onyx #0B0C0D · Black #060607 */
:root{--orange:#FA5F05;--deep:#BC4704;--peach:#FDB78F;--paper:#F6F6F6;--white:#FFFFFF;--azure:#333F48;--graphite:#605D5B;
--onyx:#0B0C0D;--black:#060607;--muted:#A9A5A2;--line:rgba(246,246,246,.10);--card:rgba(51,63,72,.45);--ease:cubic-bezier(.16,1,.3,1)}
html{scroll-behavior:smooth}
html,body,[class*="st-"],.stApp{font-family:'Manrope','Segoe UI',system-ui,sans-serif}
/* Streamlit draws its icons (expander arrows, upload, sidebar toggle) with an icon font. Keep that font, or the
   icon names show up as plain text on top of the labels. */
[data-testid="stIconMaterial"],[data-testid="stIconMaterial"] *,[class*="material-symbols"],[class*="material-icons"],.material-icons{
font-family:'Material Symbols Rounded','Material Symbols Outlined','Material Icons'!important;
font-feature-settings:'liga'!important;letter-spacing:normal!important;text-transform:none!important}

/* background: the branding gradient drifts very slowly behind everything (animated on .stApp itself so the layout is untouched) */
.stApp{color:var(--paper);background-color:var(--onyx);
background-image:radial-gradient(40% 36% at 6% 0%,rgba(250,95,5,.26),transparent 70%),
radial-gradient(34% 32% at 100% 4%,rgba(253,183,143,.13),transparent 70%),
radial-gradient(38% 34% at 92% 100%,rgba(188,71,4,.22),transparent 70%),
radial-gradient(30% 28% at 0% 100%,rgba(51,63,72,.55),transparent 70%),
linear-gradient(180deg,#0B0C0D 0%,#060607 100%);
background-size:150% 150%,150% 150%,150% 150%,150% 150%,100% 100%;background-repeat:no-repeat;background-attachment:fixed;
animation:ss-bg 34s ease-in-out infinite alternate}
@keyframes ss-bg{0%{background-position:0% 0%,100% 0%,100% 100%,0% 100%,0 0}
50%{background-position:18% 12%,82% 18%,84% 86%,14% 82%,0 0}100%{background-position:34% 22%,66% 34%,64% 70%,30% 66%,0 0}}

/* Layout: leave room for Streamlit's fixed top bar so page titles never slide underneath it */
[data-testid="stHeader"]{background:transparent!important}
.block-container,[data-testid="stMainBlockContainer"]{padding-top:4.8rem!important;padding-bottom:5rem!important;max-width:1250px}
h1,h2,h3{letter-spacing:-.015em;color:var(--white);font-weight:800;line-height:1.25;overflow-wrap:anywhere}
h1{margin-top:0}
p,li,label,.stCaption,[data-testid="stCaptionContainer"]{overflow-wrap:anywhere}
[data-testid="stCaptionContainer"]{color:var(--muted)}
[data-testid="stColumn"]{min-width:0}
[data-testid="stHorizontalBlock"]{row-gap:.6rem}
[data-testid="stVerticalBlock"]>[data-testid="stElementContainer"]{max-width:100%}
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input{min-width:0;text-overflow:ellipsis}
[data-testid="stWidgetLabel"] p{white-space:normal;overflow-wrap:anywhere;line-height:1.3}

/* sidebar */
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#060607 0%,#0B0C0D 55%,#12161a 100%);border-right:1px solid var(--line)}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]{padding-top:1rem}
.ss-brand{font-weight:800;font-size:1.35rem;color:var(--white);letter-spacing:-.02em}
.ss-sub{color:var(--muted);font-size:.8rem;margin-bottom:.9rem;line-height:1.35}
section[data-testid="stSidebar"] [role="radiogroup"]{gap:4px}
section[data-testid="stSidebar"] [role="radiogroup"]>label{padding:8px 12px;border-radius:12px;border:1px solid transparent;
transition:background .6s var(--ease),border-color .6s var(--ease),transform .6s var(--ease)}
section[data-testid="stSidebar"] [role="radiogroup"]>label:hover{background:rgba(250,95,5,.08);transform:translateX(3px)}
section[data-testid="stSidebar"] [role="radiogroup"]>label:has(input:checked){background:rgba(250,95,5,.16);border-color:rgba(250,95,5,.55)}

/* cards */
.kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin:.4rem 0 1.2rem}
.kpi,.card{background:var(--card);border:1px solid var(--line);border-radius:16px;box-shadow:0 10px 30px rgba(0,0,0,.35);
-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);min-width:0;
transition:transform .9s var(--ease),box-shadow .9s var(--ease),border-color .9s var(--ease)}
.kpi{padding:12px 15px}
.card{padding:16px 18px;min-height:150px;height:auto}
.kpi:hover,.card:hover{transform:translateY(-4px);box-shadow:0 16px 38px rgba(0,0,0,.5);border-color:rgba(250,95,5,.45)}
.kpi-l{font-size:.78rem;color:var(--muted);font-weight:500;overflow-wrap:anywhere}
.kpi-v{font-size:1.65rem;font-weight:800;line-height:1.25;color:var(--white);overflow-wrap:anywhere}
.kpi-s{font-size:.78rem;color:var(--muted);overflow-wrap:anywhere}
.card h4{margin:0 0 6px;color:var(--orange);font-weight:800}
.card p{margin:0;color:#CFCBC8;font-size:.9rem;line-height:1.5}
.note{background:rgba(250,95,5,.10);border:1px solid rgba(250,95,5,.38);border-radius:12px;padding:10px 14px;color:var(--peach);
font-size:.86rem;margin:.5rem 0 1rem;line-height:1.5}
.pill{display:inline-block;padding:2px 11px;border-radius:999px;font-size:.74rem;margin:2px 4px 2px 0;background:rgba(51,63,72,.6);
border:1px solid var(--line);color:var(--muted)}
.pill.ok{background:rgba(250,95,5,.16);border-color:rgba(250,95,5,.5);color:var(--peach)}
/* welcome-page cards share one row height */
[data-testid="stHorizontalBlock"]:has(.card){align-items:stretch}
[data-testid="stHorizontalBlock"]:has(.card)>[data-testid="stColumn"]>[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"]:has(.card) [data-testid="stElementContainer"],
[data-testid="stHorizontalBlock"]:has(.card) [data-testid="stMarkdown"],
[data-testid="stHorizontalBlock"]:has(.card) [data-testid="stMarkdownContainer"]{height:100%}

/* buttons, inputs, maps: slow, soft easing */
div.stButton>button,div.stDownloadButton>button{border-radius:12px;font-weight:700;border:1px solid rgba(246,246,246,.16);
transition:transform .7s var(--ease),box-shadow .7s var(--ease),background .7s var(--ease),border-color .7s var(--ease)}
div.stButton>button:hover,div.stDownloadButton>button:hover{transform:translateY(-2px);border-color:var(--orange);box-shadow:0 10px 24px rgba(250,95,5,.28)}
div.stButton>button[kind="primary"]{background:linear-gradient(90deg,#BC4704,#FA5F05 55%,#FD8F4F);border:0;color:#fff}
div.stButton>button[kind="primary"]:hover{box-shadow:0 12px 30px rgba(250,95,5,.45)}
[data-baseweb="input"],[data-baseweb="select"]>div{border-radius:12px!important}
[data-baseweb="input"]:focus-within,[data-baseweb="select"]>div:focus-within{box-shadow:0 0 0 3px rgba(250,95,5,.30)!important}
[data-testid="stMetric"]{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:12px 16px;min-width:0}
[data-testid="stExpander"] details{border-radius:14px;border:1px solid var(--line);background:rgba(51,63,72,.22)}
[data-testid="stAlert"]{border-radius:14px}
[data-testid="stDataFrame"]{border-radius:14px;overflow:hidden}
iframe{display:block;width:100%;max-width:100%;border-radius:18px;border:1px solid var(--line)!important;box-shadow:0 12px 34px rgba(0,0,0,.5)}

/* page change: the whole page eases in slowly, cards follow one after another */
@keyframes ss-page{from{opacity:0;transform:translateY(22px)}to{opacity:1;transform:none}}
@keyframes ss-soft{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
[class*="st-key-page_"]{animation:ss-page 1.3s var(--ease) both}
.kpi,.card{animation:ss-soft 1.4s var(--ease) both}
.kpi:nth-child(2){animation-delay:.12s}.kpi:nth-child(3){animation-delay:.24s}
.kpi:nth-child(4){animation-delay:.36s}.kpi:nth-child(5){animation-delay:.48s}
[data-testid="stColumn"]:nth-child(2) .card{animation-delay:.15s}[data-testid="stColumn"]:nth-child(3) .card{animation-delay:.3s}
[data-testid="stColumn"]:nth-child(4) .card{animation-delay:.45s}
@media (max-width:640px){.block-container,[data-testid="stMainBlockContainer"]{padding-left:1rem!important;padding-right:1rem!important}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}html{scroll-behavior:auto}}
</style>
"""

# Welcome page. Everything here is drawn with CSS/SVG, so it works offline and needs no image files.
# Motion: signal rings radiate from the beacon, ")))" arcs pulse, data packets travel from the tower to devices,
# coverage zones breathe, and a four-bar signal meter fills up.
HERO = """
<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;700;800&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0}
html,body{height:100%}
body{font-family:'Manrope','Segoe UI',system-ui,sans-serif;color:#F6F6F6;overflow:hidden;position:relative;
background:linear-gradient(135deg,#060607 0%,#0B0C0D 55%,#12161a 100%)}
.glow{position:absolute;border-radius:50%;filter:blur(60px);animation:drift 20s ease-in-out infinite alternate}
.g1{width:420px;height:420px;background:#FA5F05;opacity:.30;right:4%;top:-150px}
.g2{width:340px;height:340px;background:#BC4704;opacity:.32;left:-90px;bottom:-130px;animation-delay:-8s}
.g3{width:260px;height:260px;background:#FDB78F;opacity:.14;left:38%;top:-80px;animation-delay:-13s}
.grid{position:absolute;inset:0;opacity:.7;background-image:linear-gradient(rgba(246,246,246,.045) 1px,transparent 1px),
linear-gradient(90deg,rgba(246,246,246,.045) 1px,transparent 1px);background-size:38px 38px;
-webkit-mask-image:radial-gradient(70% 80% at 70% 40%,#000,transparent);mask-image:radial-gradient(70% 80% at 70% 40%,#000,transparent);
animation:pan 26s linear infinite}
.wrap{position:relative;display:flex;align-items:center;justify-content:space-between;height:100%;padding:0 52px;gap:24px}
.txt{max-width:520px;min-width:0}
.txt>*{opacity:0;animation:rise 1.6s cubic-bezier(.16,1,.3,1) forwards}
.kicker{display:flex;align-items:flex-end;gap:12px;margin-bottom:14px;color:#FDB78F;font-size:12.5px;font-weight:700;letter-spacing:.14em;
text-transform:uppercase;animation-delay:.05s}
.bars{display:flex;align-items:flex-end;gap:3px;height:24px}
.bars i{display:block;width:5px;border-radius:2px;background:#FA5F05;transform-origin:bottom;animation:fill 2.6s ease-in-out infinite}
.bars i:nth-child(1){height:7px}.bars i:nth-child(2){height:12px;animation-delay:.2s}
.bars i:nth-child(3){height:18px;animation-delay:.4s}.bars i:nth-child(4){height:24px;animation-delay:.6s}
h1{font-size:62px;line-height:1.02;font-weight:800;letter-spacing:-.035em;animation-delay:.15s;
background:linear-gradient(90deg,#FFFFFF 0%,#FDB78F 62%,#FA5F05 100%);-webkit-background-clip:text;background-clip:text;color:transparent;
-webkit-text-fill-color:transparent}
h2{font-size:20px;font-weight:700;margin:14px 0 12px;color:#F6F6F6;line-height:1.3;animation-delay:.4s}
p{color:#B9B5B2;line-height:1.6;font-size:15px;animation-delay:.65s}
.chips{margin-top:20px;display:flex;gap:10px;flex-wrap:wrap;animation-delay:.9s}
.chips span{background:rgba(51,63,72,.6);border:1px solid rgba(246,246,246,.14);color:#F6F6F6;padding:7px 14px;border-radius:999px;font-size:13px;font-weight:500}
svg{width:46%;max-width:520px;max-height:100%;height:auto;flex:0 1 auto;overflow:visible;opacity:0;animation:rise 2s cubic-bezier(.16,1,.3,1) .3s forwards}
.zone{transform-box:fill-box;transform-origin:center;animation:breathe 8s ease-in-out infinite}
.z2{animation-delay:-2s}.z3{animation-delay:-4s}.z4{animation-delay:-6s}
.ring{fill:none;stroke:#FA5F05;stroke-width:2.2;transform-box:fill-box;transform-origin:center;opacity:0;animation:wave 7.2s ease-out infinite}
.r2{animation-delay:1.8s}.r3{animation-delay:3.6s}.r4{animation-delay:5.4s}
.arc{fill:none;stroke:#FDB78F;stroke-width:3.2;stroke-linecap:round;opacity:.15;animation:arc 2.4s ease-in-out infinite}
.a2{animation-delay:.3s}.a3{animation-delay:.6s}
.beacon{transform-box:fill-box;transform-origin:center;animation:beacon 2.4s ease-in-out infinite}
.dev{animation:glow 3.6s ease-in-out infinite}.d2{animation-delay:.9s}.d3{animation-delay:1.8s}.d4{animation-delay:2.7s}
@keyframes rise{from{opacity:0;transform:translateY(26px)}to{opacity:1;transform:none}}
@keyframes wave{0%{transform:scale(.06);opacity:.9}100%{transform:scale(1);opacity:0}}
@keyframes breathe{0%,100%{transform:scale(1)}50%{transform:scale(1.04)}}
@keyframes glow{0%,100%{opacity:.4}50%{opacity:1}}
@keyframes arc{0%,100%{opacity:.12}35%{opacity:1}}
@keyframes beacon{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.45);opacity:.65}}
@keyframes fill{0%,100%{transform:scaleY(.35);opacity:.45}45%{transform:scaleY(1);opacity:1}}
@keyframes drift{from{transform:translate(0,0)}to{transform:translate(46px,34px)}}
@keyframes pan{from{background-position:0 0}to{background-position:38px 38px}}
@media(max-width:760px){.wrap{flex-direction:column;justify-content:center;padding:18px 20px;gap:6px}
h1{font-size:40px}h2{font-size:16px;margin:8px 0}p{display:none}.chips{margin-top:10px}.chips span{padding:5px 10px;font-size:12px}
.kicker{margin-bottom:8px}svg{width:auto;height:46%;max-width:100%}}
@media(max-width:760px) and (max-height:520px){svg{display:none}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;opacity:1!important}.pkt{display:none}}
</style></head><body>
<div class="glow g1"></div><div class="glow g2"></div><div class="glow g3"></div><div class="grid"></div>
<div class="wrap">
<div class="txt">
<div class="kicker"><div class="bars"><i></i><i></i><i></i><i></i></div>Live coverage prediction</div>
<h1>SignalSight</h1>
<h2>See where your cell towers reach, and where the next one should go</h2>
<p>Enter your towers, view predicted signal on a live map, spot dead zones, and let the optimizer suggest new sites.</p>
<div class="chips"><span>Signal map</span><span>Dead-zone finder</span><span>Tower placement</span><span>Before and after</span></div>
</div>
<svg viewBox="0 0 520 500" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
<ellipse class="zone" cx="260" cy="428" rx="244" ry="56" fill="#333F48" fill-opacity=".55"/>
<ellipse class="zone z2" cx="260" cy="428" rx="196" ry="45" fill="#605D5B" fill-opacity=".55"/>
<ellipse class="zone z3" cx="260" cy="428" rx="146" ry="33" fill="#BC4704" fill-opacity=".65"/>
<ellipse class="zone z4" cx="260" cy="428" rx="94" ry="21" fill="#FA5F05" fill-opacity=".85"/>
<circle class="ring" cx="260" cy="70" r="230"/><circle class="ring r2" cx="260" cy="70" r="230"/>
<circle class="ring r3" cx="260" cy="70" r="230"/><circle class="ring r4" cx="260" cy="70" r="230"/>
<g fill="none" stroke-linecap="round" stroke-linejoin="round" stroke="#F6F6F6">
<path stroke-width="5" d="M252 124 L180 424 M268 124 L340 424"/>
<path stroke-width="3.2" d="M260 124 L260 76"/>
<path stroke-width="3" stroke="#B9B5B2" d="M198 352 L322 352 M214 292 L306 292 M228 232 L292 232 M241 176 L279 176 M186 396 L334 396
M198 352 L334 396 M322 352 L186 396 M214 292 L322 352 M306 292 L198 352 M228 232 L306 292 M292 232 L214 292 M241 176 L292 232 M279 176 L228 232 M252 124 L279 176 M268 124 L241 176"/>
</g>
<rect x="236" y="148" width="11" height="26" rx="3" fill="#F6F6F6"/><rect x="273" y="148" width="11" height="26" rx="3" fill="#F6F6F6"/>
<g fill="none" stroke-linecap="round">
<path class="arc" d="M284 52 A28 28 0 0 1 284 88"/><path class="arc a2" d="M296 42 A46 46 0 0 1 296 98"/><path class="arc a3" d="M308 32 A64 64 0 0 1 308 108"/>
<path class="arc" d="M236 52 A28 28 0 0 0 236 88"/><path class="arc a2" d="M224 42 A46 46 0 0 0 224 98"/><path class="arc a3" d="M212 32 A64 64 0 0 0 212 108"/>
</g>
<circle class="beacon" cx="260" cy="70" r="8" fill="#FA5F05"/><circle cx="260" cy="70" r="4" fill="#FFFFFF"/>
<g class="dev"><rect x="82" y="408" width="12" height="20" rx="3" fill="#FDB78F"/></g>
<g class="dev d2"><rect x="430" y="404" width="12" height="20" rx="3" fill="#FDB78F"/></g>
<g class="dev d3"><rect x="128" y="440" width="12" height="20" rx="3" fill="#FA5F05"/></g>
<g class="dev d4"><rect x="388" y="442" width="12" height="20" rx="3" fill="#FA5F05"/></g>
<g class="pkt" fill="#FDB78F">
<circle r="3.6"><animateMotion dur="3.4s" repeatCount="indefinite" begin="0s" path="M260 70 Q130 150 88 408"/><animate attributeName="opacity" values="0;1;1;0" dur="3.4s" repeatCount="indefinite" begin="0s"/></circle>
<circle r="3.6"><animateMotion dur="3.4s" repeatCount="indefinite" begin="0.85s" path="M260 70 Q400 140 436 404"/><animate attributeName="opacity" values="0;1;1;0" dur="3.4s" repeatCount="indefinite" begin="0.85s"/></circle>
<circle r="3.6"><animateMotion dur="3.4s" repeatCount="indefinite" begin="1.7s" path="M260 70 Q170 210 134 440"/><animate attributeName="opacity" values="0;1;1;0" dur="3.4s" repeatCount="indefinite" begin="1.7s"/></circle>
<circle r="3.6"><animateMotion dur="3.4s" repeatCount="indefinite" begin="2.55s" path="M260 70 Q360 210 394 442"/><animate attributeName="opacity" values="0;1;1;0" dur="3.4s" repeatCount="indefinite" begin="2.55s"/></circle>
</g>
</svg>
</div></body></html>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def kpi(label: str, value: str, sub: str = "", accent: str = "#FA5F05") -> str:
    return (f'<div class="kpi" style="border-top:3px solid {accent}"><div class="kpi-l">{label}</div>'
            f'<div class="kpi-v">{value}</div><div class="kpi-s">{sub}</div></div>')


def kpi_row(items: list[str]) -> None:
    st.markdown('<div class="kpi-row">' + "".join(items) + "</div>", unsafe_allow_html=True)


def note(text: str) -> None:
    st.markdown(f'<div class="note">{text}</div>', unsafe_allow_html=True)


def embed_html(html: str, height: int) -> None:
    """Embed a self-contained HTML document (map or hero) in an iframe."""
    try:
        components.html(html, height=height, scrolling=False)
    except Exception:  # newer Streamlit versions may drop components.html
        st.iframe(html, height=height)
