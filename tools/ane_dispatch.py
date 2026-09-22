"""ANE dispatch-rate measurement via Apple's xctrace "Neural Engine" instrument.

WHY THIS EXISTS. ioreg publishes no ANE counters, `_ANEPerformanceStats` does not exist, and
powermetrics co-sampling of per-engine dispatch is not available. xctrace ships a Neural Engine
instrument whose `ane-hw-intervals` table gives per-dispatch start and duration. No entitlement,
no kext, no reboot.

TWO TRAPS, BOTH REAL:
 1. A ZERO IS MEANINGLESS WITHOUT PROVING THE ANE RAN. Pair every reading with the CPU_ONLY
    divergence check in gates/g3_placement.py. A dead instrument and a dead workload look alike.
 2. XCTRACE REUSES XML ELEMENTS BY id/ref. A naive regex sees only the first occurrence of each
    value and undercounts, plausibly. Resolve ref -> id, and require the TOOK-CHECK: the interval
    count must match an independent in-process predict count PLUS exactly two load dispatches.

THE TWO LOAD DISPATCHES ARE REAL, NOT SLOP. Measured here at n=100/200/300, the offset is a
   constant +2: one multi-second compile/load interval and one ~26 ms first-touch, both before the
   first predict. They are reported separately below. If the offset is anything other than 2, the
   ref/id resolution is undercounting -- do not read the rate.
"""
import os, shutil, subprocess, sys, xml.etree.ElementTree as ET


COUNT_FILE = os.environ.setdefault("KEV_ANE_COUNT_FILE", "predicts.txt")


def record(cmd, out="ne.trace"):
    shutil.rmtree(out, ignore_errors=True)
    if os.path.exists(COUNT_FILE):
        os.remove(COUNT_FILE)           # stale count would make the took-check a no-op
    subprocess.run(["xcrun", "xctrace", "record", "--instrument", "Neural Engine",
                    "--output", out, "--launch", "--"] + cmd, check=True)
    return out


def parse(trace, xml="ane.xml"):
    subprocess.run(["xcrun", "xctrace", "export", "--input", trace, "--xpath",
                    '/trace-toc/run[@number="1"]/data/table[@schema="ane-hw-intervals"]',
                    "--output", xml], check=True, capture_output=True)
    cache = {}
    def val(el):
        if el is None:
            return None
        r = el.get("ref")
        if r:
            return cache.get(r)                      # <- the undercount trap
        if el.get("id"):
            cache[el.get("id")] = el.text
        return el.text
    rows = ET.parse(xml).getroot().findall(".//row")
    pairs = []
    for r in rows:                       # pair PER ROW: an unresolved ref must drop the whole row,
        a = val(r.find("start-time"))    # not silently shift start-times against durations
        b = val(r.find("duration"))
        if a and b:
            pairs.append((int(a), int(b)))
    if len(pairs) < 3:
        return None
    st = [a for a, _ in pairs]
    du = [b for _, b in pairs]
    # Classify by SHAPE, never by position. "The first two are load" was measured on one model
    # (a 3.5 s compile interval + a 26 ms first-touch) and is FALSE on others: the attn-adapter
    # model shows NO compile-shaped interval at all (compile happens before any dispatch) and
    # 301 = 300 issued + 1 at-load validation predict. Positional classification read that as a
    # 299/300 took-check MISMATCH, twice, on 2026-09-20/21.
    med = sorted(du)[len(du) // 2]
    order = sorted(range(len(st)), key=lambda i: st[i])
    load = [i for i in order if not (0.5 * med < du[i] < 1.5 * med)]   # outliers = compile/first-touch
    steady = [i for i in order if 0.5 * med < du[i] < 1.5 * med]
    ss, sd = [st[i] for i in steady], [du[i] for i in steady]
    span = (max(ss) - min(ss)) / 1e9
    d = sorted(sd)
    return {"intervals": len(st), "steady": len(sd),
            "load_ms": [round(du[i] / 1e6, 2) for i in load],
            "span_s": round(span, 3),
            "rate_per_s": round(len(sd) / span, 1),
            "duty_pct": round(sum(sd) / 1e9 / span * 100, 1),
            "p50_ms": round(d[len(d) // 2] / 1e6, 4),
            "p99_ms": round(d[int(len(d) * .99)] / 1e6, 4),
            "max_ms": round(d[-1] / 1e6, 2)}


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: ane_dispatch.py <command that prints its own predict count> [args...]\n"
                 "       e.g. ane_dispatch.py python bench/workload.py 300")
    r = parse(record(sys.argv[1:]))
    if not r:
        sys.exit("0 intervals. Prove the ANE ran (CPU_ONLY divergence) before reading this as a null.")
    print(f"\n  ANE DISPATCH  {r['intervals']} intervals "
          f"= 2 load ({r['load_ms'][0]} ms compile, {r['load_ms'][1]} ms first-touch) "
          f"+ {r['steady']} predict")
    print(f"  STEADY STATE  {r['steady']} over {r['span_s']}s  rate {r['rate_per_s']}/s  "
          f"duty {r['duty_pct']}%  p50 {r['p50_ms']} ms  p99 {r['p99_ms']} ms  "
          f"max {r['max_ms']} ms")
    try:
        want = int(open(COUNT_FILE).read().strip())
    except Exception:
        print(f"  \u26d4 TOOK-CHECK: NOT PERFORMED. The workload wrote no count to {COUNT_FILE};")
        print("     xctrace captures the launched process stdout, so a printed count is not enough.")
        print("     Read nothing above as verified until this check runs.")
        return
    ok = r["steady"] == want
    print(f"  \u26d4 TOOK-CHECK: steady {r['steady']} vs in-process predicts {want} -> "
          f"{'PASS' if ok else '*** FAIL — ref/id resolution undercounted, not a slow ANE ***'}")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
