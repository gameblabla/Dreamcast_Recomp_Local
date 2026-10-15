#!/usr/bin/env python3
"""disc_extract.py: pull the files (1ST_READ.BIN and everything else) out of a Dreamcast disc dump. Stdlib only.

  python3 -I tools/disc_extract.py DISC OUTDIR [--boot-only]     (--boot-only: just 1ST_READ.BIN + IP.BIN, saves disk)

DISC may be a .gdi (GD-ROM, what Redump/most dumps use), a .cue (+ .bin tracks), a .iso, or a folder that already
holds the files (then 1ST_READ.BIN is just located). 2048-byte and raw 2352-byte sectors are detected automatically.
.cdi / .mds / .chd are not read directly: convert first (`cdi2iso`, `mdf2iso`, `chdman extractcd -i x.chd -o x.cue`).
Result: OUTDIR/<all disc files, original names>, and OUTDIR/1ST_READ.BIN (the file the Dreamcast boots; case-insensitive
lookup, falls back to the largest *.BIN in the root if the disc has no 1ST_READ.BIN). Also writes OUTDIR/IP.BIN when the
bootstrap is available (.gdi / first data track).
"""
import os, re, struct, sys

GD_HD_START = 45000


class Track:
    def __init__(self, path, lba_start, sector_size, data_off):
        self.path, self.lba, self.ss, self.off = path, lba_start, sector_size, data_off
        self.f = open(path, 'rb')
        self.n = os.path.getsize(path) // sector_size

    def read(self, lba, count=1):
        out = b''
        for i in range(count):
            self.f.seek((lba - self.lba + i) * self.ss + self.off)
            out += self.f.read(2048)
        return out

    def has(self, lba):
        return 0 <= lba - self.lba < self.n


def detect_layout(path):
    """-> (sector_size, data_offset) if the file has an ISO9660 PVD at sector 16, else None."""
    with open(path, 'rb') as f:
        for ss, off in ((2048, 0), (2352, 16), (2352, 24)):
            f.seek(16 * ss + off)
            if f.read(6)[1:6] == b'CD001':
                return ss, off
    return None


def detect_sector_size(path):
    """for tracks without a PVD (GD low-density audio/data): guess from size alone"""
    sz = os.path.getsize(path)
    return 2352 if sz % 2352 == 0 else 2048


def parse_gdi(gdi):
    base = os.path.dirname(os.path.abspath(gdi))
    tr = []
    lines = open(gdi).read().splitlines()
    for line in lines[1:]:
        p = line.split()
        if len(p) < 6:
            continue
        num, lba, typ, ss = int(p[0]), int(p[1]), int(p[2]), int(p[3])
        name = line.split('"')[1] if '"' in line else p[4]
        if typ == 4:
            tr.append(Track(os.path.join(base, name), lba, ss, 16 if ss == 2352 else 0))
    return tr


def parse_cue(cue):
    base = os.path.dirname(os.path.abspath(cue))
    tr, cur = [], None
    for line in open(cue, errors='replace').read().splitlines():
        m = re.match(r'\s*FILE\s+"(.*)"', line)
        if m:
            cur = os.path.join(base, m.group(1)); continue
        m = re.match(r'\s*TRACK\s+(\d+)\s+(\S+)', line)
        if m and cur and m.group(2).upper().startswith(('MODE1', 'MODE2')) and os.path.exists(cur):
            lay = detect_layout(cur)
            if lay:
                tr.append((cur, lay))
    return tr


def read_dir(tracks, lba, size):
    t = next(t for t in tracks if t.has(lba))
    data = t.read(lba, (size + 2047) // 2048)[:size]
    ents, i = [], 0
    while i < len(data):
        n = data[i]
        if n == 0:
            i = (i // 2048 + 1) * 2048
            continue
        rec = data[i:i + n]
        ext, sz = struct.unpack_from('<I', rec, 2)[0], struct.unpack_from('<I', rec, 10)[0]
        fl, nl = rec[25], rec[32]
        name = rec[33:33 + nl]
        if name not in (b'\x00', b'\x01'):
            nm = name.decode('latin-1').split(';')[0]
            ents.append((nm, ext, sz, bool(fl & 2)))
        i += n
    return ents


def walk(tracks, lba, size, prefix=''):
    for nm, ext, sz, isdir in read_dir(tracks, lba, size):
        if isdir:
            yield from walk(tracks, ext, sz, prefix + nm + '/')
        else:
            yield prefix + nm, ext, sz


def build_tracks(disc):
    ext = os.path.splitext(disc)[1].lower()
    if ext == '.gdi':
        return parse_gdi(disc)
    if ext == '.cue':
        tr = []
        for path, (ss, off) in parse_cue(disc):
            tr.append((path, ss, off))
        out = []
        # GD-ROM dumps ship the high-density data track starting at LBA 45000; plain CDs start at 0. Decide with the root directory.
        for path, ss, off in tr:
            for base in (0, GD_HD_START, 11702 + 150):
                t = Track(path, base, ss, off)
                pvd = t.read(base + 16)
                if pvd[1:6] != b'CD001':
                    continue
                root_lba, root_sz = struct.unpack_from('<I', pvd, 156 + 2)[0], struct.unpack_from('<I', pvd, 156 + 10)[0]
                if t.has(root_lba):
                    try:
                        if read_dir([t], root_lba, root_sz):
                            out.append(t); break
                    except Exception:
                        pass
        return out
    if ext in ('.iso', '.bin', '.img'):
        lay = detect_layout(disc)
        if lay:
            for base in (0, GD_HD_START, 11702 + 150):
                t = Track(disc, base, *lay)
                pvd = t.read(base + 16)
                root_lba = struct.unpack_from('<I', pvd, 156 + 2)[0]
                if t.has(root_lba):
                    return [t]
    return []


def main():
    args = [x for x in sys.argv[1:] if not x.startswith('--')]
    boot_only = '--boot-only' in sys.argv
    if len(args) != 2:
        sys.exit(__doc__)
    disc, out = args
    os.makedirs(out, exist_ok=True)
    if os.path.isdir(disc):
        src = disc
    else:
        tracks = build_tracks(disc)
        if not tracks:
            sys.exit('[ERROR] %s: no ISO9660 data track found (or unsupported format: see --help text: .cdi/.mds/.chd must be converted)' % disc)
        # every data track may hold its own ISO9660 volume (CD part + GD-ROM high-density part): take the one that has the boot file
        best = None
        for vt in tracks:
            pvd = vt.read(vt.lba + 16)
            if pvd[1:6] != b'CD001':
                continue
            root_lba, root_sz = struct.unpack_from('<I', pvd, 158)[0], struct.unpack_from('<I', pvd, 166)[0]
            try:
                files = list(walk(tracks, root_lba, root_sz))
            except Exception:
                continue
            score = (any(f[0].upper().endswith('1ST_READ.BIN') for f in files), len(files))
            if best is None or score > best[0]:
                best = (score, vt, pvd, files)
        if best is None:
            sys.exit('[ERROR] no readable volume')
        _, pvd_t, pvd, files = best
        n = 0
        for name, ext, sz in files:
            if boot_only and not name.upper().endswith('1ST_READ.BIN'):
                continue
            t = next((t for t in tracks if t.has(ext)), None)
            if t is None:
                continue
            dst = os.path.join(out, name)
            os.makedirs(os.path.dirname(dst) or out, exist_ok=True)
            with open(dst, 'wb') as f:
                left = sz; lba = ext
                while left > 0:
                    k = min(left, 2048 * 256)
                    f.write(t.read(lba, (k + 2047) // 2048)[:k]); lba += 256; left -= k
            n += 1
        try:   # IP.BIN = first 16 sectors of the data area
            open(os.path.join(out, 'IP.BIN'), 'wb').write(pvd_t.read(pvd_t.lba, 16))
        except Exception:
            pass
        print('extracted %d files to %s' % (n, out))
        src = out
    boot = None
    cands = []
    for dp, dn, fn in os.walk(src):
        for f in fn:
            if f.upper() == '1ST_READ.BIN':
                boot = os.path.join(dp, f)
            elif dp == src and f.upper().endswith('.BIN') and f.upper() != 'IP.BIN':
                cands.append((os.path.getsize(os.path.join(dp, f)), os.path.join(dp, f)))
    if boot is None and cands:
        boot = max(cands)[1]
        print('[WARN] no 1ST_READ.BIN on the disc; using the largest root .BIN: %s' % boot)
    if boot is None:
        sys.exit('[ERROR] boot executable not found')
    dst = os.path.join(out, '1ST_READ.BIN')
    if os.path.abspath(boot) != os.path.abspath(dst):
        open(dst, 'wb').write(open(boot, 'rb').read())
    print('boot executable: %s (%d bytes)' % (dst, os.path.getsize(dst)))


if __name__ == '__main__':
    main()
