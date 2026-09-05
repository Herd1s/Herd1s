"""Render the local, dependency-free SVG artwork used by the profile."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def hero(dark: bool) -> str:
    bg, ink, muted, accent, line, panel = (
        ("#10191c", "#edf4ee", "#a1b6ad", "#78d4bc", "#30423e", "#192824")
        if dark else
        ("#f4f7f5", "#172b2a", "#5b736b", "#19776b", "#cfddd5", "#e8eee8")
    )
    copper = "#e4ae82" if dark else "#a76237"
    grid = "".join(
        f'<circle cx="{x}" cy="{y}" r="1" fill="{line}"/>'
        for x in range(640, 975, 22) for y in range(38, 290, 22)
    )
    pins = "".join(
        f'<path d="M {x} 132 v -18 M {x} 264 v 18"/>'
        for x in (742, 766, 790, 814, 838)
    ) + "".join(
        f'<path d="M 722 {y} h -18 M 858 {y} h 18"/>'
        for y in (152, 176, 200, 224, 248)
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="390" viewBox="0 0 1000 390" role="img" aria-labelledby="title desc">
  <title id="title">Herd1s — Build things. Share the process.</title>
  <desc id="desc">Personal open-source portfolio. Embedded systems, robotics and connected devices. An H-shaped circuit connects hardware and software.</desc>
  <rect x="0.5" y="0.5" width="999" height="389" rx="18" fill="{bg}" stroke="{line}"/>
  <g font-family="Segoe UI, Arial, sans-serif">
    <circle cx="45" cy="41" r="5" fill="{accent}"/>
    <text x="60" y="47" font-size="17" letter-spacing="2.5" fill="{muted}">A PERSONAL OPEN-SOURCE LAB</text>
    <text x="40" y="153" font-size="88" font-weight="700" letter-spacing="-4" fill="{ink}">Herd1s<tspan fill="{accent}">.</tspan></text>
    <text x="44" y="216" font-size="34" font-weight="500" letter-spacing="-0.7" fill="{ink}">Build things.</text>
    <text x="44" y="258" font-size="34" font-weight="500" letter-spacing="-0.7" fill="{muted}">Share the process.</text>
    <path d="M 44 301 H 956" stroke="{line}"/>
    <text x="44" y="342" font-size="18" font-weight="500" fill="{muted}">EMBEDDED SYSTEMS</text>
    <circle cx="274" cy="336" r="2.5" fill="{accent}"/>
    <text x="293" y="342" font-size="18" font-weight="500" fill="{muted}">ROBOTICS</text>
    <circle cx="408" cy="336" r="2.5" fill="{accent}"/>
    <text x="427" y="342" font-size="18" font-weight="500" fill="{muted}">CONNECTED DEVICES</text>
    <text x="955" y="342" text-anchor="end" font-size="17" font-family="Consolas, monospace" fill="{accent}">CODE ↔ WORLD</text>
  </g>
  <g aria-hidden="true">
    {grid}
    <circle cx="790" cy="198" r="115" stroke="{line}" fill="none"/>
    <circle cx="790" cy="198" r="88" stroke="{line}" stroke-dasharray="3 9" fill="none"/>
    <path d="M 640 97 H 696 L 725 126 M 863 252 L 891 280 H 944 M 670 240 H 704 M 876 154 H 925 V 96" fill="none" stroke="{accent}" stroke-width="2"/>
    <g fill="{bg}" stroke="{accent}" stroke-width="2">
      <circle cx="640" cy="97" r="5"/>
      <circle cx="944" cy="280" r="5"/>
      <circle cx="670" cy="240" r="5"/>
      <circle cx="925" cy="96" r="5"/>
    </g>
    <g stroke="{muted}" stroke-width="3" stroke-linecap="round">{pins}</g>
    <rect x="722" y="132" width="136" height="132" rx="16" fill="{panel}" stroke="{accent}" stroke-width="2"/>
    <rect x="734" y="144" width="112" height="108" rx="9" fill="none" stroke="{line}"/>
    <path d="M 765 163 V 233 M 815 163 V 233 M 765 198 H 815" fill="none" stroke="{accent}" stroke-width="12" stroke-linecap="square"/>
    <circle cx="836" cy="155" r="4" fill="{copper}"/>
    <circle cx="790" cy="83" r="5" fill="{copper}"/>
  </g>
</svg>
'''


if __name__ == "__main__":
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    for theme in ("light", "dark"):
        destination = assets / f"hero-{theme}.svg"
        destination.write_text(hero(theme == "dark"), encoding="utf-8")
        print(destination.relative_to(ROOT))
