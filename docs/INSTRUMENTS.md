# Instruments: free sampled libraries, synths and the SFZ player (2026-10-15)

The General MIDI soundfont (GeneralUser GS) can't sound like the Persona band. Free sample libraries whose
licences allow released music now replace it for the parts that matter, played by `arrange/sampler.py` (an
SFZ player in numpy) and registered in `arrange/instruments.py`. They live in `<library>/instruments/`
(`%USERPROFILE%\MouthMixer\instruments`), are never committed, and every instrument falls back to its GM
cousin when its library isn't installed, so songs still render everywhere.

| Key | Library | Author | Licence | Notes |
|---|---|---|---|---|
| `sfz:rhodes` | jRhodes3d (stereo, no crossfades) | Jeff Learman | samples CC-BY-SA; music made with it free to use | 1977 Rhodes Mark I; our auto-pan, chorus, light amp, -4 dB at 300 Hz |
| `sfz:bass_finger`, `sfz:bass_ghost`, `sfz:bass_stac` | Black And Blue Basses (the black Washburn, fingers, neck pickup) | Karoryfer Samples | CC0 | mapped an octave above how it sounds: played with a +12 key shift; p/mp/mf/f layers, 4 round robins |
| `kit:muldjord` | MuldjordKit | DrumGizmo team (FreePats) | **CC-BY 4.0: credit** | GM drum notes mapped onto its keys 48-66; closed hat chokes the open hat |
| `kit:latin` | VCSL congas, bongos, tambourine, triangles, shaker | Versilian Studios | CC0 | on GM percussion notes (60-65, 54, 80-82) |
| `sfz:piano` | Salamander Grand Piano V3 (FLAC) | Alexander Holm | **CC-BY 3.0: credit** | |
| `sfz:violins`, `violins_spic`, `violins_pizz`, `violas`, `cellos`, `cellos_spic` | VSCO-2 Community Edition | Versilian Studios | CC0 | SFZ generated from the file names (`folder_sfz`) |
| `sfz:trumpet`, `trumpet_stac`, `trombone`, `trombone_stac`, `horn` | VSCO-2 CE brass | Versilian Studios | CC0 | |
| `sfz:tenor_sax` | FreePats Tenor Saxophone | FreePats | CC0 | |
| `sfz:guitar_clean` | FreePats FSBS Clean Electric (bridge) | FreePats | CC0 | our amp: drive, +3 dB at 2.4 kHz |
| `synth:organ_jazz/gospel/rock/soft` | our tonewheel organ (`arrange/synths.py`) | | ours | drawbars, click, 3rd-harmonic percussion, chorus-vibrato, two-rotor Leslie, drive |
| `synth:saw_lead/super_pad/brass_stab/sub_bass/pluck` | our analog-style synth | | ours | PolyBLEP oscillators, state-variable low-pass, filter envelope |
| `sfx:reverse_crash`, `sfx:boom` | the kit's crash reversed; a synthesised sub drop | | | transitions into sections |

**Credits for anything released with these sounds:** "Drums: MuldjordKit by the DrumGizmo team (CC-BY 4.0).
Piano: Salamander Grand Piano by Alexander Holm (CC-BY 3.0)." (`instruments.credits()` lists them all.)

**Installing on another PC** (what this session did; about 2.9 GB after unpacking and removing unused folders):
- MuldjordKit: `github.com/freepats/muldjordkit/releases` (SFZ+FLAC 7z) to `instruments/MuldjordKit`
- Black And Blue Basses: `github.com/sfzinstruments/karoryfer.black-and-blue-basses/releases` to `instruments/BlackAndBlue`
- jRhodes3d: `git clone https://github.com/sfzinstruments/jlearman.jRhodes3d instruments/jRhodes3d`
- Salamander: `freepats.zenvoid.org/Piano/SalamanderGrandPiano/SalamanderGrandPiano-SFZ+FLAC-V3+20200602.tar.gz`
- Tenor sax: `freepats.zenvoid.org/Reed/TenorSaxophone/TenorSaxophone-SFZ+FLAC-20200717.tar.gz`
- Guitar: `github.com/freepats/electric-guitar-FSBS-clean/releases` (SFZ+FLAC 7z)
- VSCO-2 CE (`github.com/sgossner/VSCO-2-CE`, Strings and Brass) and VCSL (`github.com/sgossner/VCSL`, the
  Conga, Bongos, Triangles, Tambourine 1 and Shaker, Small folders), with a sparse checkout.

**Not used, and why:** Virtual Playing Orchestra (only a Google Drive download; VSCO-2 is its CC0 source);
madmom and ADTOF models (non-commercial); Vital (needs an account); Decent Sampler / Kontakt / LABS libraries
(proprietary players).
