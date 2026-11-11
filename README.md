# Tire Inspection — workspace สำหรับพัฒนาต่อ

ผู้ใช้ยอมรับโมเดลปัจจุบันสำหรับทดลองหน้างาน วันที่10 พฤศจิกายน2026 ให้เก็บผลเพื่อปรับปรุงภายหลัง ไม่ฝึกใหม่หรือเปลี่ยนกฎในงานแยก workspace นี้

## เปิดใน VS Code
1. File → Open Folder เลือกโฟลเดอร์นี้ (tire-inspection)
2. ใช้ Python 3.14 64-bit และส่วนขยาย Python/Python Debugger
3. เปิด PowerShell terminal ที่โฟลเดอร์นี้ รัน `powershell -ExecutionPolicy Bypass -File scripts/setup-windows.ps1` เพื่อสร้าง .venv และติดตั้ง dependencies (ใช้อินเทอร์เน็ต)
4. Python: Select Interpreter → `.venv/Scripts/python.exe`
5. Run and Debug → Predict one image แล้วระบุภาพ หรือใช้คำสั่งด้านล่าง

ติดตั้ง .venv ใหม่และทดสอบบน Windows แล้ว (10 พ.ย. 2026) ใช้งานได้โดยเลือก interpreter ภายใน .venv ไม่ต้องติดตั้งซ้ำ requirements-windows-lock.txt บันทึกเวอร์ชันที่ติดตั้งครบ ไม่ใช่การรับรองบน Pi

## รันใน terminal ที่โฟลเดอร์นี้
```powershell
.\.venv\Scripts\python.exe inference/predict.py --image "data/input/example.jpg"
.\.venv\Scripts\python.exe inference/inference_engine.py --input "data/input/tire-001" --json-out "outputs/tire-001.json"
.\.venv\Scripts\python.exe scripts/verify-workspace.py
.\.venv\Scripts\python.exe -m unittest discover -s tests
```
นำภาพของคุณใส่ data/input ก่อน ไม่มีภาพตัวอย่างบรรจุมา ใช้ชื่อผลลัพธ์ใหม่ทุก session ปุ่ม Debug หลายภาพเขียนทับ outputs/latest-inspection.json ซึ่งเป็นไฟล์ชั่วคราว

## โครงสร้าง
- inference/: โค้ดภาพเดี่ยวและรวมผลจากแพ็กเกจเดิม
- models/: .pt, .onnx, audit เดิม และ release.json
- ui/: เตรียมพัฒนา UI ยังไม่เลือก framework
- data/input/: ภาพที่จะทดลอง
- data/field-tests/: แบบบันทึกผลหน้างาน
- outputs/: JSON ผลทำนาย
- scripts/: ติดตั้ง Windows และตรวจแพ็กเกจ
- tests/: ตรวจการเลือกโมเดลภายใน workspace
- docs/: ข้อตกลง ข้อจำกัด งานค้าง และหลักฐานการคัดลอก

ไม่มี runtime dependency ไป round2; path ใน audit เดิมเป็นประวัติเท่านั้น โมเดลและthresholdไม่เปลี่ยน แก้เฉพาะ default model และตำแหน่ง cache

อ่าน [PROJECT.md](PROJECT.md), [STATUS.md](STATUS.md), [HANDOFF](docs/HANDOFF.md) ก่อนพัฒนาต่อ

## เริ่มงาน UX/UI
อ่าน [บรีฟสำหรับ session ออกแบบ](docs/UX_UI_BRIEF.md) ก่อนร่างหน้าจอ ยังไม่เลือกframeworkหรือเปลี่ยนโมเดล
