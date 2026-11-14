# อัปเดตและทดสอบ Pi โดยรักษา environment/ข้อมูลเดิม

วันที่ 14 พฤศจิกายน 2026 — branch `camera-review-fixes-2026-11-14` ต่อจาก `ux-ui-pi-trial` (`d5b639f254369376edc78503dfb8f515837a166d`) ไม่ merge main

## เงื่อนไข

- ทำบน Pi จากโฟลเดอร์ Git ของ UI เดิม ที่มี remote `origin` เป็น `origanda404/tire-inspection`
- หยุด server UI เดิมด้วย Ctrl+C และปิด rpicam-hello/rpicam-still ก่อนใช้กล้องกับรุ่นใหม่
- ต้องมี environment **UI** ที่ใช้กล้อง/ONNX/FastAPI ได้อยู่แล้ว ตัวอย่างใช้ `.venv-ui/bin/python` ในโฟลเดอร์ UI เดิม ถ้าจริงอยู่ที่อื่นให้แก้เฉพาะตัวแปร UI_PY เป็น absolute path ของ environment UI นั้น **ห้ามชี้ไป .venv โมเดลเพื่อทดลองติดตั้งแพ็กเกจ**
- ไม่มี pip install/upgrade, apt, การคัดลอก venv, reset, clean หรือ checkout ทับโฟลเดอร์เดิมในขั้นตอนนี้ หาก preflight ไม่ผ่าน ให้หยุดเก็บ error ไม่ซ่อม environment โมเดลเดิม
- แต่ละรอบสร้าง worktree แบบ detached ที่ commit ที่ fetch มา และ data directory ใหม่ ไม่อ่าน/เขียน SQLite เดิม ไม่ต้องย้ายข้อมูลเดิมมาทดสอบ

## 1. ตรวจตำแหน่งก่อนเริ่ม

ใน terminal ที่โฟลเดอร์ UI เดิม:

```bash
pwd
git remote -v
git status --short
ls -ld .venv-ui
```

โค้ดเดิมที่มีการแก้ค้างไม่ต้อง stash/reset เพราะใช้ worktree ใหม่ ขั้นถัดไปจะตรวจ remote และ interpreter อีกครั้ง

## 2. สร้างพื้นที่ทดสอบและรัน

คัดลอกทั้งบล็อกใน Bash จากโฟลเดอร์ UI เดิม แก้ EXPECTED_SHA เป็น commit SHA เต็มที่แจ้งในแชต และถ้าต้องเปลี่ยน UI_PY ให้แก้ก่อนรัน:

```bash
bash <<'BASH'
set -euo pipefail
OLD_UI=$(pwd -P)
UI_PY="$OLD_UI/.venv-ui/bin/python"
BRANCH=camera-review-fixes-2026-11-14
EXPECTED_SHA='แทนด้วย_COMMIT_SHA_40_ตัวจากแชต'
REMOTE=$(git remote get-url origin)
case "$REMOTE" in
  https://github.com/origanda404/tire-inspection.git|https://github.com/origanda404/tire-inspection|git@github.com:origanda404/tire-inspection.git) ;;
  *) printf 'หยุด: origin ไม่ตรง repository ที่ตรวจแล้ว: %s\n' "$REMOTE"; exit 1 ;;
esac
[ -x "$UI_PY" ] || { printf 'หยุด: ไม่พบ UI Python: %s\n' "$UI_PY"; exit 1; }
export PYTHONDONTWRITEBYTECODE=1
"$UI_PY" -c 'import sys; assert sys.prefix != sys.base_prefix, "Expected UI virtual environment"; print("UI environment:", sys.prefix)'
TRIAL_ROOT=$(mktemp -d "$HOME/tire-ui-review-20261114-XXXXXX")
printf 'พื้นที่ทดสอบใหม่: %s\n' "$TRIAL_ROOT"
"$UI_PY" -m pip freeze > "$TRIAL_ROOT/ui-packages.before.txt"
git fetch origin "refs/heads/$BRANCH:refs/remotes/origin/$BRANCH"
FIX_SHA=$(git rev-parse "refs/remotes/origin/$BRANCH^{commit}")
printf 'Commit ที่จะทดสอบ: %s\n' "$FIX_SHA"
[ "$FIX_SHA" = "$EXPECTED_SHA" ] || { printf 'หยุด: commit ไม่ตรง EXPECTED_SHA ตรวจค่าจากแชตก่อน\n'; exit 1; }
NEW_UI="$TRIAL_ROOT/code"
git worktree add --detach "$NEW_UI" "$FIX_SHA"
mkdir "$TRIAL_ROOT/data"
export TIRE_DATA_DIR="$TRIAL_ROOT/data"
cd "$NEW_UI"
"$UI_PY" scripts/check-field-ui.py > "$TRIAL_ROOT/preflight.json"
"$UI_PY" - "$TRIAL_ROOT/preflight.json" <<'PY'
import json, sys
report = json.load(open(sys.argv[1], encoding='utf-8'))
failed = {k:v for k,v in report['packages'].items() if not v['ok']}
assert not failed, failed
assert report['model_load'].startswith('passed'), report['model_load']
print('Preflight passed: camera imports + model hash/class/input checks')
PY
"$UI_PY" -m pip freeze > "$TRIAL_ROOT/ui-packages.after-preflight.txt"
cmp "$TRIAL_ROOT/ui-packages.before.txt" "$TRIAL_ROOT/ui-packages.after-preflight.txt"
printf '%s\n' "$UI_PY" > "$TRIAL_ROOT/ui-python.txt"
printf '%s\n' "$FIX_SHA" > "$TRIAL_ROOT/commit.txt"
# เขียน launcher เฉพาะโฟลเดอร์ทดสอบใหม่ เพื่อเปิดซ้ำโดยไม่เผลอใช้ data เดิม
{
  printf '#!/usr/bin/env bash\nset -euo pipefail\n'
  printf 'cd -- %q\n' "$NEW_UI"
  printf 'export PYTHONDONTWRITEBYTECODE=1\nexport TIRE_DATA_DIR=%q\n' "$TRIAL_ROOT/data"
  printf 'exec %q -m field_app.server\n' "$UI_PY"
} > "$TRIAL_ROOT/run-trial.sh"
printf '\nโค้ด: %s\nข้อมูลทดสอบ: %s\nเปิดซ้ำ: bash %q\n' "$NEW_UI" "$TIRE_DATA_DIR" "$TRIAL_ROOT/run-trial.sh"
printf 'เปิด Chromium: http://127.0.0.1:8765 แล้ว Ctrl+Shift+R\n'
bash "$TRIAL_ROOT/run-trial.sh"
BASH
```

`git fetch` เพิ่ม/อัปเดต Git refs และ objects เท่านั้น; `worktree add` เพิ่ม Git metadata กับโฟลเดอร์ใหม่ ไม่สลับ branch/worktree เดิม การใช้ Python ของ UI เดิมเป็นการเรียกใช้งาน ไม่ใช่การติดตั้งหรือแก้แพ็กเกจ ตั้ง PYTHONDONTWRITEBYTECODE เพื่อไม่สร้าง pyc ใน environment

หากพอร์ต 8765 ถูกใช้อยู่ ให้ปิด server เดิมก่อน ไม่เปิดสอง process แข่งใช้กล้อง หากขั้นตอนไหนล้มเหลว บล็อกจะหยุด พื้นที่ทดสอบใหม่ที่สร้างไว้คงอยู่และไม่ลบข้อมูลใด ๆ อัตโนมัติ

## 3. ทดสอบ UI/กล้อง

1. เปิด URL บน Chromium ของ Pi และกด Ctrl+Shift+R เพื่อโหลด JS ใหม่ กดโหลดโมเดล
2. สร้างรหัสยาง `TEST-CAMERA-20261114` เลือกกล้อง กดเปิด/เชื่อมกล้องใหม่ ทดสอบด้วยวัตถุหยุดนิ่งก่อน
3. วางกระดาษขาวกับวัตถุสีดำในภาพเดียวกัน ดูภาพสด กดถ่าย เปิดรูปจาก gallery แล้วกดดาวน์โหลดภาพต้นฉบับ เปิด JPEG ด้วยโปรแกรมนอกเบราว์เซอร์ เปรียบเทียบขาว–ดำ ห้ามสรุปว่าหายจนตรวจภาพจริง
4. ตรวจการเคลื่อนไหวในภาพสด แล้วเข้า/ออกประวัติและกลับมาเปิดกล้องซ้ำ 3 รอบ สังเกตว่าไม่ช้าลงเรื่อย ๆ ทดสอบปุ่มเชื่อมใหม่โดยไม่ถอดสาย CSI ขณะมีไฟ
5. ถ่ายหลายภาพ → วิเคราะห์ → กรอกผู้ตรวจ/หมายเหตุ → บันทึก → ยืนยัน → ส่งออก ZIP ตรวจ JSON/CSV/JPEG
6. ทดสอบการสลับไปเปิดรอบ B ขณะรอบ A กำลังวิเคราะห์ ต้องไม่กระโดดกลับ A และทดสอบปุ่มบันทึกว่าช่องข้อความถูกล็อกระหว่างส่ง
7. หยุด server ด้วย Ctrl+C แล้วเปิด `bash /path/to/TRIAL_ROOT/run-trial.sh` อีกครั้ง ประวัติทดสอบต้องยังอยู่ใน data ของพื้นที่ใหม่นี้

## 4. เก็บหลักฐานสี/ความหน่วง

ขณะ server รุ่นใหม่เปิดอยู่ เปิด terminal ที่สอง กำหนด TRIAL_ROOT ให้ตรง path ที่พิมพ์จากขั้นก่อน (ไม่ใช่โฟลเดอร์ข้อมูลเดิม):

```bash
TRIAL_ROOT='/แทนด้วย/path/พื้นที่ทดสอบใหม่'
UI_PY=$(cat "$TRIAL_ROOT/ui-python.txt")
cd "$TRIAL_ROOT/code"
PYTHONDONTWRITEBYTECODE=1 "$UI_PY" scripts/diagnose-camera.py
# ถ้ามี session ID เต็ม 32 ตัวจาก session.json ใน ZIP ให้แนบภาพบันทึกด้วย
# PYTHONDONTWRITEBYTECODE=1 "$UI_PY" scripts/diagnose-camera.py --session SESSION_ID_32_HEX
PYTHONDONTWRITEBYTECODE=1 "$UI_PY" -m pip freeze > "$TRIAL_ROOT/ui-packages.after-test.txt"
cmp "$TRIAL_ROOT/ui-packages.before.txt" "$TRIAL_ROOT/ui-packages.after-test.txt"
```

ส่ง diagnostics.json, preview JPEG และภาพต้นฉบับที่โหลดไว้ พร้อมบอกว่าภาพกลับสีเกิดใน viewer ไหน ถ้าไฟล์ปกติแต่หน้าเว็บกลับสี ตรวจ forced dark/ส่วนขยาย/accessibility/display ถ้า JPEG กลับสีด้วย ค่อยเทียบ rpicam-hello หลังปิด UI

เวลา request_ms เป็น HTTP round-trip; cache_age_ms เป็นอายุหลังสร้าง JPEG ไม่ใช่ sensor-to-screen latency ไม่ใช้ตัวเลขนี้อ้าง end-to-end benchmark เป้าหมาย preview สูงสุดประมาณ 10 ครั้ง/วินาที ยังไม่มีผลวัดจริงบน Pi

## 5. กลับไปใช้รุ่นเดิม

ปิด server ทดสอบด้วย Ctrl+C แล้วเปิด UI เดิมจากโฟลเดอร์เดิมด้วยคำสั่งเดิมและ TIRE_DATA_DIR เดิม ตัวแปรที่ตั้งในบล็อกทดสอบเป็น child shell จึงไม่เปลี่ยน environment ของ terminal ต้นทาง ไม่มีการ migrate/ย้ายข้อมูลจริง ไม่มีการ merge หรืออัปเกรด environment โมเดล ไม่ลบพื้นที่ทดสอบจนกว่าจะสำรองหลักฐานแล้ว

หลังทดสอบผ่านจึงพิจารณาเปลี่ยนรุ่นใช้งานจริงโดยสำรองข้อมูลและระบุ data path จริงแยกอีกครั้ง เอกสารนี้ยังไม่สั่งนำรุ่นใหม่ไปเขียนข้อมูลหน้างานเดิม
