# ตัวรัน ONNX สำหรับ Pi

สถานะ: เตรียมตัวรัน CPU ที่ไม่ import torch/ultralytics แล้ว ต้องยืนยันบน Pi จริงอีกครั้ง ไม่ฝึกใหม่ ไม่เปลี่ยนโมเดลหรือ threshold

## Windows
เปิด Terminal ที่โฟลเดอร์ tire-inspection แล้วรัน:

```powershell
.\.venv\Scripts\python.exe inference/onnx_engine.py --input data/input/smoke-2026-11-10/Warning_26.jpg --json-out outputs/onnx-single.json
.\.venv\Scripts\python.exe scripts/check-onnx-runner.py
```

`--input` รับภาพเดียว โฟลเดอร์ หรือรายชื่อภาพคั่น comma โฟลเดอร์ต้องมีภาพยางเส้นเดียวถ้าจะตีความผลรวมเป็นผลของยางเส้นนั้น ภาพ smoke เป็นคนละตัวอย่าง ห้ามตีความเป็นยางเส้นเดียว

## สถานะ Pi ที่ตรวจแล้ว — 13 พฤศจิกายน 2026
Raspberry Pi 4 Model B Rev 1.5, Debian GNU/Linux 12 (bookworm), `aarch64`, Python 3.11.2. ผู้ใช้รายงานว่ารายการกล้องตรวจพบแล้ว ภาพสดและการถ่ายภาพนิ่งผ่าน แต่ยังไม่ได้ทดสอบกับยาง/ขาตั้งหรือหน้างาน และยังไม่ได้รัน ONNX บน Pi

## ดึงโค้ดจาก GitHub ไป Pi
Repository ปัจจุบันเป็น public. หลัง branch `pi-onnx-runner` มี commit พร้อมแล้ว ให้เปิด Terminal บน Pi และรัน:

```bash
git clone --branch pi-onnx-runner https://github.com/origanda404/tire-inspection.git
cd tire-inspection
```

หลัง pull request นี้ถูกรวมเข้า `main` แล้ว การดึงครั้งใหม่ใช้ `git clone https://github.com/origanda404/tire-inspection.git` ได้

ไม่คัดลอก `.venv` ของ Windows ไป Pi ให้สร้าง environment บน Pi เอง:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-pi.txt
.venv/bin/python inference/onnx_engine.py --input path/to/image.jpg --json-out outputs/pi-result.json
.venv/bin/python -m pip freeze > outputs/pi-environment.txt
```

`requirements-pi.txt` เป็นช่วงเวอร์ชันสำหรับเตรียมติดตั้ง ไม่ใช่ lock ที่ทดสอบบน Pi แล้ว หากติดตั้งไม่ได้ให้ตรวจ OS/Python ก่อนเปลี่ยนระบบหรือติดตั้งแพ็กเกจทดแทน

## ความเหมือนกับโปรแกรมเดิม
- EXIF orientation → RGB → ImageOps.pad 224x224 LANCZOS สีพื้น 114 → float32 RGB NCHW หาร 255
- โมเดลคืน probability อยู่แล้ว ไม่ทำ softmax ซ้ำ
- Abnormal >= 0.25 ก่อน; Warning >= 0.35; ที่เหลือ Normal ใช้คะแนนก่อนปัดเศษ
- รวมผลตามระดับรุนแรงที่สุดของภาพที่ส่งเข้า ไม่ตรวจความครบวงหรือตัวตนยาง
- อ่านชื่อคลาสจาก metadata และตรวจ SHA-256 กับ release ก่อนรัน
- ไฟล์หาย/ภาพเสีย/ผลลัพธ์ไม่ถูกต้องเป็น error ไม่แปลงเป็น Warning หรือ Normal

JSON คงฟิลด์เดิม เพิ่ม timing_scope และ coverage_note เวลา latency ของตัวรันใหม่รวมอ่านภาพ เตรียมภาพ และ inference แต่ไม่รวมโหลดโมเดล กล้อง หรือ UI จึงไม่ควรเทียบกับ latency เดิมตรง ๆ

## หลักฐานและงานยืนยันต่อ
ผล Windows อยู่ outputs/onnx-runner-check-2026-11-13/parity.json สคริปต์เทียบ probability ดิบกับทั้ง PT และ ONNX ผ่าน Ultralytics ใช้ tolerance 0.00001 และตรวจ argmax/ผลตามกฎตรงกัน รวมภาพสังเคราะห์ทดสอบรูปแบบภาพ ไม่ใช่ผลความแม่นยำอิสระ

บน Pi ต้องใช้ภาพไฟล์เดียวกันเทียบคะแนน/คำตอบกับ Windows บันทึก OS, Python, เวอร์ชันแพ็กเกจ เวลา RAM และอุณหภูมิ ผล Windows ไม่ยืนยันผลหรือความเร็วบน Pi
