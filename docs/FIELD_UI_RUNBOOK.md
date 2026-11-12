# Local field UI — รุ่นทดลอง 13 พฤศจิกายน 2026

## สถานะ
ผู้ใช้สั่งเริ่มพัฒนาเพื่อใช้กับโมเดลบน Pi แทนมติเดิมที่ให้หยุดไว้ที่ mock รุ่นนี้ทำงานจริงกับ ONNX engine เดิมและ SQLite บนเครื่อง เปิดเฉพาะ 127.0.0.1:8765 ไม่ใช่บริการ LAN/cloud
ผ่าน API integration tests 4 กรณีบน Windows และทดสอบหน้าเว็บจริง: สร้างรอบทดสอบ นำเข้าภาพ Warning_26.jpg วิเคราะห์ได้ Warning และยืนยันบันทึกสำเร็จ ผลคนยังไม่ยืนยัน ภาพวิจัยเดิมนี้ไม่ใช่ผลหน้างาน
ยังไม่ทดสอบกล้อง/จอสัมผัส/Pi end-to-end หรือภาพยางหมุน ต้องทดสอบตามรายการท้ายเอกสาร

## ไฟล์
- field_app/server.py: API, รอบตรวจ, ร่าง, worker วิเคราะห์ทีละรอบ, export
- field_app/camera.py: Picamera2 หนึ่งตัวเป็นเจ้าของกล้อง ไม่มีคำสั่งเครื่องถ่วง
- ui/index.html, app.css, app.js: หน้าเว็บสัมผัส ไม่มี CDN/อินเทอร์เน็ตขณะใช้งาน
- requirements-ui.txt: dependencies รุ่น UI
- scripts/check-field-ui.py: ตรวจ imports และโหลดโมเดลโดยไม่เปิดกล้อง
- data/field-runtime/: ข้อมูลจริงบนเครื่อง (ไม่เข้า Git และไม่อยู่ในชุดแจก)

## Windows
จากโฟลเดอร์ tire-inspection:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ui.txt
.\.venv\Scripts\python.exe -m field_app.server
```
เปิด http://127.0.0.1:8765 เลือกนำเข้าภาพเพื่อทดสอบ กล้อง Pi ใช้ไม่ได้บน Windows

## ส่งไฟล์ไป Pi
ทางหลักสำหรับรอบ GitHub: branch `ux-ui-pi-trial` ต่อยอดจาก `pi-onnx-runner` commit `5a0e895acc7c76fc69df14ca19aec4c5e93163e7` ไม่ merge main และไม่เปลี่ยนโมเดล/engine
แนะนำใช้ git worktree แยกโฟลเดอร์ UI เพื่อรักษา checkout และ .venv ที่รันสำเร็จไว้ ให้ตรวจ pwd, branch, git status และ path ของ .venv เดิมก่อนรันคำสั่งสร้าง worktree
หลัง fetch ให้ตรวจว่า branch มี field_app/server.py และ requirements-ui.txt แล้วจึงสร้าง worktree ใหม่โดยไม่ใช้ --force
ไม่ใช้ git reset --hard, git clean หรือ pip install ใน .venv เดิม

ทางเลือก ZIP (ไม่ใช้ปนกับ checkout Git):
ใช้ชุด ZIP outputs/field-ui-pi-2026-11-13.zip ที่สร้างในงานนี้ คัดลอกผ่าน USB หรือช่องทางที่ผู้ใช้เลือก แตกเป็นโฟลเดอร์ใหม่ ไม่เขียนทับ environment/ผลทดลองเดิม เช่น ~/tire-ui-trial
ชุดนี้ไม่รวม .venv, ภาพวิจัย, ฐานข้อมูล, หรือผลหน้างาน ไม่จำเป็นต้อง pull โค้ดที่ยังไม่ได้ push ไป GitHub

## ตรวจ Pi ก่อนติดตั้ง
ปิด rpicam-hello/rpicam-still หรือโปรแกรมที่ใช้กล้องอยู่ แล้วตรวจ system Python:
```bash
python3 -c "import sys; print(sys.version); import picamera2, libcamera, numpy; print('camera imports OK; numpy', numpy.__version__)"
```
ถ้า import ล้มเหลวให้เก็บข้อความ error เพื่อตรวจแพ็กเกจของ OS ก่อน ไม่ติดตั้ง libcamera ด้วย pip
Picamera2 ใช้แพ็กเกจระบบ ตามคู่มือ Raspberry Pi: https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf
ใน OS ที่มีแพ็กเกจทางการและยังไม่ได้ติดตั้ง ใช้ sudo apt install python3-picamera2 python3-venv หลังตรวจว่า repository ของ OS รองรับ

## สร้าง environment แยกสำหรับ UI
ก่อนติดตั้ง: อ่านเวอร์ชัน onnxruntime/numpy/Pillow จาก Python ของ .venv เดิมและเก็บผล pip freeze เป็นหลักฐานโดยไม่ติดตั้งหรือแก้แพ็กเกจเดิม จากนั้นเลือกเวอร์ชันเหล่านั้นเพื่อติดตั้งใหม่ใน .venv-ui เท่านั้น ห้ามคัดลอกโฟลเดอร์ .venv ข้ามที่
requirements-ui.txt มีเฉพาะแพ็กเกจเว็บ ไม่ติดตั้งหรืออัปเกรดแพ็กเกจ AI ให้อัตโนมัติ ต้องสร้าง AI runtime ใน environment ใหม่ด้วยเวอร์ชันที่ตรวจจากเครื่องจริงก่อน
จากโฟลเดอร์ UI ใหม่ (อย่ารันหาก .venv-ui มีอยู่แล้วจนกว่าจะตรวจ):
```bash
python3 -m venv --system-site-packages .venv-ui
.venv-ui/bin/python -m pip install -r requirements-ui.txt
.venv-ui/bin/python scripts/check-field-ui.py
```
--system-site-packages ใช้เพื่อเข้าถึง Picamera2/libcamera ของระบบ ไม่คัดลอก .venv จาก Windows มาใช้
requirements เป็นช่วงเวอร์ชัน ยังไม่ใช่ lock ของ Pi ถ้าติดตั้งสำเร็จแต่ import กล้องมี error เกี่ยวกับ NumPy/ABI ให้หยุดและส่ง preflight; อย่าอัปเกรด/ดาวน์เกรด environment โมเดลเดิมโดยเดา

ถ้า preflight แจ้งโมเดลโหลดไม่ได้เพราะยังไม่มี ONNX/NumPy/Pillow ให้ติดตั้งเฉพาะใน .venv-ui ตามเวอร์ชันเดิมที่บันทึกไว้ โดยตรวจแผน dependencies ก่อน การที่ .venv-ui มีปัญหาไม่ใช่เหตุให้เปลี่ยน .venv เดิม

เมื่อ imports ที่จำเป็นและ model_load ผ่าน:
```bash
.venv-ui/bin/python -m field_app.server
```
เปิด Chromium บน Pi ไป http://127.0.0.1:8765 เปิดเพียงหนึ่ง server process ปิดด้วย Ctrl+C หลังจบงาน ไม่มี auto-start/systemd ในรุ่นนี้

## ขั้นทดลอง
1. กดตรวจ/โหลดโมเดล กรอกรหัสยางและผู้บันทึก เลือกกล้อง Pi แล้วสร้างรอบ
2. เปิดกล้อง ตรวจภาพสดให้เห็นหน้ายางชัด รุ่นนี้ JPEG 1280×960 และ preview แบบ snapshot polling ไม่ใช่วิดีโอความเร็วสูง ค่านี้เป็นค่าเริ่มต้นทดสอบ ไม่ใช่ข้อสรุปหน้างาน
3. กดถ่ายภาพทีละภาพ ดูภาพเต็มเพื่อเช็กความชัด ยังไม่มีระบบจับมุม/ครบวง/จับภาพอัตโนมัติ ผู้ใช้ควบคุมเครื่องถ่วงเอง
4. วิเคราะห์ภาพที่เก็บ ดูความคืบหน้าจากจำนวนที่วิเคราะห์จริง ใช้ safety_prediction และ overall_condition เดิม ไม่คำนวณผลใหม่ด้วยคะแนนเฉลี่ย
5. กรอกผลคนเมื่อมีผู้ยืนยัน หรือปล่อยว่าง บันทึกหมายเหตุก่อนออก; ภาพเก็บเป็นร่างอัตโนมัติ แต่ข้อความหมายเหตุต้องกดบันทึก
6. ยืนยันบันทึกแล้วรอบนั้นเป็นอ่านอย่างเดียว ตรวจซ้ำให้สร้างรอบใหม่ด้วยรหัสยางเดิม ส่งออก ZIP รวม session.json, results.csv และภาพต้นฉบับ
7. รีสตาร์ตแอปแล้วเปิดประวัติ ตรวจว่าภาพ ผล และหมายเหตุยังอยู่ เก็บภาพหน้าจอและผล preflight เป็นหลักฐาน

## เกณฑ์ก่อนนำไปทดสอบหน้างาน
- กล้องเปิด/ถ่าย/ดูเต็ม/วิเคราะห์/ยืนยัน/เปิดย้อนหลัง/ส่งออกได้บน Pi จริง
- เทียบภาพยางไฟล์เดียวกันกับ CLI เดิม คะแนนและผลต้องตรงกัน
- ทดลองกล้องไม่พร้อม ไฟล์ภาพหาย และเปิดโปรแกรมกลับหลังหยุดกลางรอบ ต้องมี error/ร่าง ไม่แสดง Normal แทนไม่มีผล
- วัดเวลา end-to-end, RAM/อุณหภูมิ และตรวจความชัดขณะหมุนจริงก่อนตัดสินช่วงจับภาพ
- ปุ่ม/ข้อความต้องกดและอ่านได้บนจอจริง วิธีจบรอบและรับรอง coverage ยังรอออกแบบหน้างาน

## ข้อมูลและข้อจำกัด
ข้อมูลอยู่ data/field-runtime/sessions.sqlite3 และโฟลเดอร์รหัสรอบ ภาพตรวจ SHA-256 ก่อนวิเคราะห์/ยืนยัน/ส่งออก เก็บเวอร์ชันโมเดลกับกฎ ไม่มีการลบข้อมูลผ่าน UI
สำรองทั้ง data/field-runtime ตอนปิด server หรือส่งออก ZIP ทีละรอบ ZIP เป็นสำเนาส่งออก ยังไม่มีปุ่มนำเข้าประวัติจาก ZIP
ร่างที่กำลังวิเคราะห์เมื่อแอปหยุดจะขึ้น error ให้ลองใหม่เมื่อเปิดแอป ไม่อ้างว่ารับประกันกู้ข้อมูลจากไฟดับ/SD card เสีย
จำกัด 100 ภาพต่อรอบและ 20 MB/ภาพเพื่อควบคุมทรัพยากร ไม่ใช่เกณฑ์ครบวง มีพื้นที่สำรองขั้นต่ำ 100 MB ตอนรับภาพ
ยังไม่มีถ่ายอัตโนมัติ เลือกตัดภาพจากรอบ แก้ไขรอบที่ยืนยันแล้ว ระบบบัญชีผู้ใช้ LAN หรือการยืนยัน coverage หลายแท็บควรหลีกเลี่ยงเพราะรุ่นนี้ออกแบบสำหรับผู้ปฏิบัติงานหนึ่งคน
