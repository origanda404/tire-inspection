## GitHub / Pi update — 14 พฤศจิกายน 2026
ผู้ใช้สั่งส่งโค้ดขึ้น GitHub และขออัปเดต Pi โดยรักษา environment/ข้อมูลเดิม เลือก branch แยก `camera-review-fixes-2026-11-14` จาก `ux-ui-pi-trial` ที่ d5b639f254369376edc78503dfb8f515837a166d; คู่มือ PI_SAFE_UPDATE_2026-11-14.md ใน docs ใช้ detached worktree + data ใหม่และ interpreter UI เดิม ไม่มี pip install/upgrade ไม่แตะ environment โมเดล ไม่ใช้ฐานข้อมูลจริงในการทดสอบ ตรวจ commit SHA ที่ส่งสำเร็จจากแชตก่อนรัน รายงานทดสอบเดิมด้านล่างเป็นหลักฐาน Windows ไม่ใช่ Pi

## Implementation follow-up — 14 พฤศจิกายน 2026
แก้บั๊กจากรีวิวตามคำสั่งแล้ว ดู [FIXES_2026-11-14.md](FIXES_2026-11-14.md) ชุด Python 15/Node 5 ผ่าน กล้องเป็น fake-device ใน tests ต้องทดสอบ Pi/ภาพกลับสีจริงต่อ ชุด ZIP ใหม่ 2026-11-14 ไม่รวม runtime data ไม่ได้ push หรืออัปเกรด environment โมเดลเดิม ข้อความงานค้าง CLI ด้านล่างเป็นประวัติก่อนแก้

## UX/UI implementation — คำสั่งใหม่ 13 พฤศจิกายน 2026
ผู้ใช้สั่งเริ่มพัฒนาเพื่อใช้บน Pi และพร้อมรันคำสั่งทดสอบแล้ว เพิ่ม local web app ใน field_app/ และ ui/ ใช้ ONNX engine เดิม + SQLite ผ่าน API integration tests 4 กรณีและ browser flow ด้วยภาพวิจัยเดิมบน Windows ยังไม่ทดสอบกล้อง Pi end-to-end ดู [FIELD_UI_RUNBOOK.md](FIELD_UI_RUNBOOK.md) และ STATUS.md ชุด ZIP พร้อมคัดลอกไป Pi โดยไม่ต้องอ้างว่า push GitHub แล้ว วิธีเก็บภาพครบวงยังต้องออกแบบหน้างาน รุ่นแรกถ่ายทีละภาพ ไม่สั่งเครื่องถ่วง

## ประวัติส่งต่อ UX/UI — 13 พฤศจิกายน 2026
ผู้ใช้เห็นชอบโครงสร้างและหน้าตาแบบสัมผัสล่าสุดแล้ว ให้บันทึกและส่งต่อแชตหลัก **ยังไม่ต้องเชื่อมระบบจริง** กล้อง Camera Module 3 NoIR (Picamera2 เป็นไลบรารีที่เสนอ ไม่ใช่รุ่นกล้อง); ผู้ใช้กดเครื่องถ่วงเอง; ขั้นเก็บภาพ/จบรอบ/ความครบวงต้องออกแบบใหม่หน้างาน ยังไม่อนุมัติ framework/API/storage รายละเอียดที่ต้องอ่านก่อนทำต่อ: [UX_UI_DECISIONS_2026-11-13.md](UX_UI_DECISIONS_2026-11-13.md)

## อัปเดต 13 พฤศจิกายน 2026
ตัวรันแยก inference/onnx_engine.py มีผล compatibility บน Windows และมีการเทียบไฟล์เดียวกันหนึ่งภาพระหว่าง Pi กับ Windows โดยคะแนนตรงกันที่ 4 ตำแหน่งและผล Normal ตรงกัน (ภาพไม่ใช่ยาง; latency ครั้งเดียว Pi 628.9 ms, Windows 164.9 ms). ดู PI_ONNX_RUNNER.md และ STATUS.md; นี่ไม่ใช่ผลความแม่นยำหรือ benchmark และยังไม่มีการทดสอบภาพยาง ปัญหาพึ่งพา torch/class mapping/ไฟล์หายได้รับการป้องกันในตัวรันใหม่นี้เท่านั้น ตัวรันเดิมและข้อจำกัด coverage ยังคงเดิม งานถัดไปคือทบทวน flow GUI บน Windows/Pi ระหว่างรอภาพยางจากหน้างาน

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

## Code review 14 พฤศจิกายน 2026
ผลรีวิวและขอบเขตการทดสอบ: [CODE_REVIEW_2026-11-14.md](CODE_REVIEW_2026-11-14.md) ควรแก้ stale polling response และการล้างสถานะหมายเหตุที่ยังไม่บันทึกก่อนทดลอง UI ต่อ ปัญหา legacy CLI ยังอยู่ ไม่มีการแก้โค้ดหรือโมเดลในงานรีวิวนี้


## Camera follow-up 14 พฤศจิกายน 2026
ดู [CAMERA_REVIEW_2026-11-14.md](CAMERA_REVIEW_2026-11-14.md): ความหน่วงมีข้อจำกัดในโค้ดชัดเจน ส่วนภาพกลับขาว–ดำต้องเทียบ JPEG ที่บันทึกนอกเบราว์เซอร์ก่อนปรับสี ผู้ใช้ยังไม่ได้ตรวจภาพที่กดถ่าย ไม่ควรสรุปว่า NoIR/RGB-BGR เป็นสาเหตุ ยังไม่ได้แก้ application code
