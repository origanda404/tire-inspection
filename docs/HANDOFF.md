# UX/UI field trial - 13 November 2026

Added local-only touch UI, FastAPI sessions, camera adapter, unchanged ONNX engine integration, SQLite drafts/history and ZIP/CSV export. Windows real-engine API tests (4 cases), pip check and JS syntax pass. Browser upload, inference and finalize previously passed on Windows. Pi camera/UI integration remains unverified.

Use branch ux-ui-pi-trial in a separate worktree and a new .venv-ui; preserve the working Pi checkout/environment. requirements-ui.txt installs web packages only. Read FIELD_UI_RUNBOOK.md before installation. No model, policy or motor-control changes.

---

## อัปเดต 13 พฤศจิกายน 2026
ตัวรันแยก inference/onnx_engine.py พร้อมทดสอบบน Windows แล้ว ดู PI_ONNX_RUNNER.md และ STATUS.md ปัญหาพึ่งพา torch/class mapping/ไฟล์หายได้รับการป้องกันในตัวรันใหม่นี้เท่านั้น ตัวรันเดิมและข้อจำกัด coverage ยังคงเดิม งานถัดไปยืนยันติดตั้งและเทียบผลบน Pi จริง

# ส่งต่อ session พัฒนา

## มติล่าสุด
ผู้ใช้พอใจโมเดลปัจจุบัน ให้ทดลองหน้างานและบันทึกผลไว้ปรับปรุงภายหลัง คงน้ำหนักและthresholdเดิม: Abnormal>=.25 ก่อน Warning>=.35 มิฉะนั้นNormal อย่ารื้อการตัดสินใจนี้อัตโนมัติ

## เปลี่ยนเฉพาะการแยกแพ็กเกจ
คัดลอกscriptsและmodelsจากtire_modelเดิม แก้default modelเป็นmodels/production_yolo11n_cls.pt และย้ายcacheไป.cache เพิ่มrelease.jsonโดยauditต้นทางคงเดิม

## งานค้าง (ยังไม่แก้)
1. ตรวจชื่อคลาส: scores.get(...,0) อาจคืนNormalเมื่อโมเดลผิดประเภท
2. รายการภาพคั่นcommaข้ามไฟล์หายเงียบ ๆ ต้องออกแบบerror
3. การรวมผลเป็นmaximum severityของภาพที่ส่งมา ไม่ตรวจตัวตนยาง/ความครบวง UIต้องไม่อ้างว่าตรวจครบทั้งเส้นอัตโนมัติ
4. Scriptsยังimport torch/ultralyticsแม้ใช้ONNX จึงติดตั้งแค่onnxruntime+Pillowไม่ได้ ต้องพัฒนาตัวรันPiและตรวจparityต่างหาก
5. UI/framework, กล้อง, storage และAPIยังไม่เลือก ถามก่อนเพิ่มstack
6. JSONเดิมไม่มีmodel version/tire ID/ground truthครบ ใช้แบบบันทึกfield-testsคู่กับผลก่อน

## ข้อจำกัดผลวิจัย
E4 OOF macro-F1ประมาณ53.1–53.4%, Warning recall6/45 ต่อseed ไม่ใช่independent testของfull-data fit TyreNetไม่มีWarningและขอบเขตไม่ตรงทั้งหมด; thresholdให้Normalถูก48/830, Normal→Abnormal524/830, Abnormal→Normal1/863 อย่าเรียก99.9%ว่าaccuracyรวม คะแนนสูงของตัวอย่างไม่ใช่การรับรองทั่วไป

ยังไม่มีผลPi 4 ห้ามนำเวลาบนnotebookมาอ้างแทน เวลาในJSONปัจจุบันรวมการเรียกpredict ไม่ใช่end-to-endตั้งแต่กล้องถึงUI

## เก็บผลหน้างาน
ใช้tire_id, session_id, view_id, ภาพ, เวอร์ชันโมเดล, คะแนนและผลหลังใช้กฎ, ผลช่างพร้อมเหตุผล, แสง/ระยะ/อุปกรณ์/เวลา ช่องไม่ทราบเว้นว่าง อย่าใช้ผลโมเดลเป็นground truth
