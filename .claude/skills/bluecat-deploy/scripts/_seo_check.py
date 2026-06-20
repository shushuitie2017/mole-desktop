#!/usr/bin/env python3
"""解析 seo.bluecatbot.com 体检 JSON，打印逐项清单，返回闸门结果。
用法: _seo_check.py <json_file> <min_score> <url>
退出码: 0=过闸（score>=min 且无 fail），1=未过闸，2=数据异常（调用方决定 fail-open）。"""
import sys
import json


def main():
    if len(sys.argv) < 4:
        print("用法: _seo_check.py <json_file> <min_score> <url>")
        return 2
    path, min_score, url = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        print(f"[seo-check] 解析体检结果失败：{e}")
        return 2
    score = d.get("score")
    c = d.get("counts", {}) or {}
    checks = d.get("checks", []) or []
    fails = [ck for ck in checks if ck.get("status") == "fail"]
    warns = [ck for ck in checks if ck.get("status") == "warn"]
    print(f"SEO {score}/100  (pass {c.get('pass', 0)} / warn {c.get('warn', 0)} / fail {c.get('fail', 0)})  {url}")
    for ck in fails:
        print(f"  ✗ FAIL  {ck.get('label')} — {ck.get('note', '')}")
    for ck in warns:
        print(f"  ! warn  {ck.get('label')} — {ck.get('note', '')}")
    ok = isinstance(score, (int, float)) and score >= min_score and not fails
    print(f"GATE {'PASS' if ok else 'FAIL'}  (阈值 {min_score}, 无 fail 且 score≥阈值才过)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
