# อัปเดต 13 พฤศจิกายน 2026 — ONNX runner

เพิ่ม inference/onnx_engine.py ใช้ ONNX Runtime + NumPy + Pillow โดยไม่ใช้ torch/ultralytics โมเดลและกฎเดิม ตรวจ hash ทั้ง PT/ONNX ตรง release

เทียบ Windows กับตัวรันเดิม PT และ ONNX: ภาพวิจัย 280 ภาพไม่ซ้ำ + ภาพสังเคราะห์ 5 ภาพ ผล argmax/threshold ตรงทั้งหมด 285 ภาพ ความต่างคะแนนดิบสูงสุด 8.046627044677734e-07 (เกณฑ์ 1e-5) ทดสอบ boundary ของกฎ, aggregate, ไฟล์หาย และ CLI โดยบล็อก import torch/torchvision/ultralytics ผ่าน

หลักฐาน outputs/onnx-runner-check-2026-11-13/ คู่มือ docs/PI_ONNX_RUNNER.md และ requirements-pi.txt ยังไม่ยืนยันการติดตั้ง/ผล/เวลา/RAM บน Pi จริง ไม่ใช่การประเมินความแม่นยำใหม่ ตัวรันใหม่ตรวจ hash/class/ไฟล์หายแล้ว ตัวรันเก่ายังไม่แก้ ไม่มีการตรวจ coverage หรือตัวตนยาง

---

# สถานะ — 10 พฤศจิกายน 2026

ติดตั้ง .venv แยกบน Windows ด้วย Python 3.14.7 แล้ว ไม่ใช้ site-packages จาก round2 ทดสอบ single-image CLI และ multiple-image CLI/JSON ผ่าน โมเดลและthresholdเดิมไม่เปลี่ยน ตรวจhashตรงrelease

ทดสอบ PT/ONNX กับภาพวิจัยเดิม3ภาพ ผลargmaxและผลหลังthresholdตรงกัน เปรียบเทียบคะแนนที่APIปัดเป็น4ตำแหน่งด้วยtolerance0.001 ไม่ใช่การรับรองparityทุกภาพหรือความแม่นยำหน้างาน ภาพ3ภาพเป็นคนละตัวอย่าง การรวมผลใช้ทดสอบทางเดินข้อมูลเท่านั้น ไม่ใช่ผลยางเส้นเดียว

pip check, ตรวจhash/syntax และunit tests2รายการผ่าน บันทึกเวอร์ชันครบในrequirements-windows-lock.txt หลักฐาน: outputs/windows-check-2026-11-10/ และ docs/WINDOWS_CHECK.md

ยังไม่ทดสอบPi 4 ไม่ฝึกใหม่ ไม่เปลี่ยนกฎ งานค้างด้านclass validation/ภาพหาย/coverageยังอยู่ในdocs/HANDOFF.md

## ส่งต่อ UX/UI
จัดทำ [บรีฟล่าสุด](docs/UX_UI_BRIEF.md) แล้ว ระบุข้อมูล/ข้อจำกัดจริงเพื่อเริ่มflowและwireframe ผู้ใช้ยืนยันรองรับเบราว์เซอร์บนคอมพิวเตอร์และจอสัมผัสที่ต่อ Pi โดยทีมวิจัย3Rเป็นผู้ดำเนินการและบันทึกผล ยังไม่ได้อนุมัติframework/API/storage
