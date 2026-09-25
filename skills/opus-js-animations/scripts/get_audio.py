#!/usr/bin/env python3
"""Get source audio (a reading, song, speech) from YouTube or any site yt-dlp supports.
Installs yt-dlp (and checks ffmpeg) if they're missing, updates yt-dlp and retries once when
a download fails (sites change often and old versions break), saves the metadata, and warns
when the voice is still sounding at the end of the section (a cut-off last word).

  python3 get_audio.py "<url>" [--from 0] [--to 75] [--out source] [--video]
  python3 get_audio.py --search "dylan thomas do not go gentle"   list candidates, download nothing
  python3 get_audio.py --install                                 just make sure the tools are there

Writes into --out (default ./source):
  source.wav   the audio section, 48 kHz (lossless from the site's stream)
  meta.txt     title | uploader | duration | url, then the description
  clip.mp4     with --video: 720p video of the section, to read on-screen text/translation
  sheet.png    with --video: one frame every 3 s tiled, to read that text quickly

Take a section a little longer than you need (--to +10 s) and trim later at a measured quiet
point; the end check below tells you if the section ends mid-word.
Stdlib only. Say where the audio came from, and let the user decide about reuse rights.
"""
import argparse, json, os, platform, shutil, subprocess, sys, urllib.request
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('url', nargs='?')
ap.add_argument('--from', dest='t0', type=float, default=None, help='section start (s)')
ap.add_argument('--to', dest='t1', type=float, default=None, help='section end (s)')
ap.add_argument('--out', default='source')
ap.add_argument('--video', action='store_true', help='also keep a 720p clip + frame sheet')
ap.add_argument('--search', help='list the top results for a query and exit')
ap.add_argument('--install', action='store_true', help='only install/check yt-dlp and ffmpeg')
a = ap.parse_args()

LOCAL_BIN = Path.home() / '.local' / 'bin'


def run(cmd, **kw):
    return subprocess.run(cmd, text=True, capture_output=True, **kw)


def works(exe):
    try:
        return run([exe, '--version'], timeout=60).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def find_ytdlp():
    for exe in [shutil.which('yt-dlp'), str(LOCAL_BIN / 'yt-dlp')]:
        if exe and works(exe):
            return exe
    return None


def install_ytdlp():
    """Try, in order: Homebrew, pipx, pip --user, then the official standalone binary."""
    attempts = []
    if shutil.which('brew'):
        attempts.append(['brew', 'install', 'yt-dlp'])
    if shutil.which('pipx'):
        attempts.append(['pipx', 'install', 'yt-dlp'])
    attempts.append([sys.executable, '-m', 'pip', 'install', '--user', '-U', 'yt-dlp[default]'])
    for cmd in attempts:
        print('installing yt-dlp:', ' '.join(cmd))
        r = run(cmd)
        exe = find_ytdlp()
        if exe:
            return exe
        print('  not usable afterwards' + (' (installed, but not on PATH)' if r.returncode == 0 else ': ' + (r.stderr or r.stdout).strip()[-200:]))
    # standalone binary: needs no Python at all
    name = {'Darwin': 'yt-dlp_macos', 'Linux': 'yt-dlp_linux'}.get(platform.system(), 'yt-dlp.exe')
    if platform.system() == 'Linux' and platform.machine() in ('aarch64', 'arm64'):
        name = 'yt-dlp_linux_aarch64'
    url = f'https://github.com/yt-dlp/yt-dlp/releases/latest/download/{name}'
    LOCAL_BIN.mkdir(parents=True, exist_ok=True)
    dest = LOCAL_BIN / 'yt-dlp'
    print('downloading the standalone binary:', url)
    urllib.request.urlretrieve(url, dest)
    dest.chmod(0o755)
    if works(str(dest)):
        if str(LOCAL_BIN) not in os.environ.get('PATH', ''):
            print(f'  note: add {LOCAL_BIN} to PATH to call yt-dlp directly')
        return str(dest)
    sys.exit('could not install yt-dlp; see https://github.com/yt-dlp/yt-dlp#installation')


def update_ytdlp(exe):
    """Newer yt-dlp fixes most 'Unable to extract' / 403 / signature errors."""
    real = os.path.realpath(exe)
    with open(real, 'rb') as f:
        is_script = f.read(2) == b'#!'                 # pip/pipx installs are Python entry scripts
    if 'Cellar' in real or '/homebrew/' in real:
        cmd = ['brew', 'upgrade', 'yt-dlp']
    elif 'pipx' in real:
        cmd = ['pipx', 'upgrade', 'yt-dlp']
    elif not is_script:
        cmd = [exe, '-U']                              # the standalone binary updates itself
    else:
        cmd = [sys.executable, '-m', 'pip', 'install', '--user', '-U', 'yt-dlp[default]']
    print('updating yt-dlp:', ' '.join(cmd))
    run(cmd)


def need_ffmpeg():
    if shutil.which('ffmpeg') and shutil.which('ffprobe'):
        return
    if shutil.which('brew'):
        print('installing ffmpeg: brew install ffmpeg')
        run(['brew', 'install', 'ffmpeg'])
    if not shutil.which('ffmpeg'):
        sys.exit('ffmpeg is required: macOS `brew install ffmpeg`, Debian/Ubuntu `sudo apt install ffmpeg`, '
                 'Windows `winget install ffmpeg`')


exe = find_ytdlp() or install_ytdlp()
need_ffmpeg()
print('yt-dlp', run([exe, '--version']).stdout.strip(), '·', exe)
if a.install:
    sys.exit(0)

if a.search:
    r = run([exe, '--flat-playlist', '--print', '%(id)s | %(duration_string)s | %(uploader)s | %(title)s',
             f'ytsearch8:{a.search}'])
    print(r.stdout or r.stderr)
    print('pick one and run: get_audio.py "https://youtu.be/<id>" --from S --to E')
    sys.exit(0)

if not a.url:
    ap.error('give a URL, or --search "query"')

out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
section = []
if a.t0 is not None or a.t1 is not None:
    section = ['--download-sections', f'*{a.t0 or 0}-{a.t1 if a.t1 is not None else "inf"}', '--force-keyframes-at-cuts']


def fetch(args):
    r = run([exe, '-q', '--no-playlist', '--no-warnings', *args, a.url])
    if r.returncode != 0:
        update_ytdlp(exe)
        r = run([exe, '-q', '--no-playlist', '--no-warnings', *args, a.url])
    if r.returncode != 0:
        sys.exit('download failed:\n' + r.stderr.strip()[-1500:])


# metadata first: the title and description often identify the content exactly
m = run([exe, '--no-playlist', '--skip-download', '--dump-single-json', a.url])
if m.returncode != 0:
    update_ytdlp(exe)
    m = run([exe, '--no-playlist', '--skip-download', '--dump-single-json', a.url])
if m.returncode == 0:
    info = json.loads(m.stdout)
    head = f"{info.get('title')} | {info.get('uploader')} | {info.get('duration')} s | {info.get('webpage_url')}"
    (out / 'meta.txt').write_text(head + '\n\n' + (info.get('description') or '') + '\n')
    print(head)

for f in out.glob('source.*'):
    f.unlink()
fetch(['-f', 'ba/b', '-x', '--audio-format', 'wav', '--postprocessor-args', 'ExtractAudio:-ar 48000',
       *section, '-o', str(out / 'source.%(ext)s')])
wav = out / 'source.wav'
if not wav.exists():
    sys.exit('no audio file was produced')

if a.video:
    for f in out.glob('clip.*'):
        f.unlink()
    fetch(['-f', 'bv*[height<=720]+ba/b[height<=720]', '--merge-output-format', 'mp4', *section,
           '-o', str(out / 'clip.%(ext)s')])
    run(['ffmpeg', '-v', 'error', '-y', '-i', str(out / 'clip.mp4'), '-vf', 'fps=1/3,scale=480:-1,tile=6x3',
         '-frames:v', '1', str(out / 'sheet.png')])

dur = float(run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(wav)]).stdout or 0)
tail = run(['ffmpeg', '-hide_banner', '-sseof', '-0.4', '-i', str(wav), '-af', 'volumedetect', '-f', 'null', '-'])
mean = next((float(l.split(':')[1].split()[0]) for l in tail.stderr.splitlines() if 'mean_volume' in l), -99.0)
print(f'→ {wav} ({dur:.2f} s)')
if mean > -35:
    print(f'WARNING: still {mean:.0f} dB in the last 0.4 s: the section likely ends mid-word or mid-phrase. '
          'If you need the audio up to here, download a longer section (--to later) and trim at a measured quiet point.')
else:
    print(f'end check: quiet tail ({mean:.0f} dB)')
print('next: python3 align_audio.py', wav, '--lang <code>')
