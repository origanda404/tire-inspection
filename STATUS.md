## GitHub / Pi update — 14 พฤศจิกายน 2026
ผู้ใช้สั่งส่งโค้ดขึ้น GitHub และขออัปเดต Pi โดยรักษา environment/ข้อมูลเดิม เลือก branch แยก `camera-review-fixes-2026-11-14` จาก `ux-ui-pi-trial` ที่ d5b639f254369376edc78503dfb8f515837a166d; คู่มือ PI_SAFE_UPDATE_2026-11-14.md ใน docs ใช้ detached worktree + data ใหม่และ interpreter UI เดิม ไม่มี pip install/upgrade ไม่แตะ environment โมเดล ไม่ใช้ฐานข้อมูลจริงในการทดสอบ ตรวจ commit SHA ที่ส่งสำเร็จจากแชตก่อนรัน รายงานทดสอบเดิมด้านล่างเป็นหลักฐาน Windows ไม่ใช่ Pi

# แก้บั๊กจากรีวิว — 14 พฤศจิกายน 2026

แก้ UI stale polling/หมายเหตุหาย, legacy CLI ภาพหาย/คลาสผิด, ภาพสดจาก latest-frame cache 640×480 แยกจากภาพบันทึก 1280×960, ยกเลิก preview เดิม, reconnect จริงและ timeout/buffer cleanup เพิ่ม diagnostics/download original ภาพกลับขาว–ดำยังต้องยืนยันไฟล์จริงบน Pi ไม่ได้กลับสีภาพชดเชย โมเดล/threshold เดิม
Python tests 15 + Node UI 5 ผ่าน, hash โมเดลตรง release ชุดทดสอบเดิมค้างเพราะ Windows asyncio socketpair ใน sandbox; นอก sandbox ผ่าน รายละเอียด [FIXES_2026-11-14.md](docs/FIXES_2026-11-14.md) ชุดส่ง Pi outputs/field-ui-pi-2026-11-14.zip ยังไม่ได้ push หรือติดตั้งบน Pi

# UX/UI — เริ่ม implementation ตามคำสั่งใหม่ 13 พฤศจิกายน 2026

## ส่ง GitHub แล้ว — ตามคำสั่งผู้ใช้
Branch `ux-ui-pi-trial`, commit `d5b639f254369376edc78503dfb8f515837a166d` ต่อจาก `pi-onnx-runner` commit `5a0e895acc7c76fc69df14ca19aec4c5e93163e7` ส่งผ่าน GitHub connector และ fetch กลับมาตรวจแล้ว diff เฉพาะ 15 ไฟล์ UI/tests/docs; models/, inference/ และ requirements-pi.txt ไม่มี diff ไม่ merge main/PR เดิม
ปรับ requirements-ui.txt เป็นแพ็กเกจเว็บเท่านั้น และ ignore .venv-ui/ ใช้ worktree/environment ใหม่บน Pi โดยคง checkout และ .venv เดิม รอผลตรวจ path/branch/environment จากผู้ใช้ก่อนให้ขั้นติดตั้ง Tests 4 กรณีผ่านกับภาพสังเคราะห์และโมเดลจริง จึงรันซ้ำได้โดยไม่ต้องมีภาพวิจัยที่ไม่อยู่ใน Git
ข้อความ «ไม่ได้ push» ด้านล่างเป็นประวัติก่อนการส่งครั้งนี้

ผู้ใช้สั่งพัฒนาเพื่อใช้กับโมเดลบน Pi และแจ้งว่าเข้าถึง Pi ได้ จะรันคำสั่งทดสอบให้ แทนคำสั่งเดิมที่ให้คง mock ไว้
เพิ่ม field_app/ และหน้าเว็บ ui/ เชื่อม ONNX engine เดิมกับ SQLite/ภาพต้นฉบับ บันทึกร่าง ผลคนแยก AI เปิดประวัติและส่งออก ZIP/CSV เปิดเฉพาะ localhost มี Picamera2 adapter สำหรับทดลองภาพสด/ถ่ายทีละภาพ (ยังไม่ใช่ข้อสรุปเก็บภาพครบวง)
ผ่าน integration tests 4 กรณีด้วยโมเดลจริงบน Windows, pip check, syntax Python/JS และ browser flow สร้างรอบ → นำเข้า Warning_26.jpg → ผล Warning → ยืนยันบันทึก โดยผลคนยังไม่ยืนยัน ทดสอบนี้ใช้ภาพวิจัยเดิม ไม่ใช่ผลหน้างาน
ยังไม่ทดสอบ adapter กล้อง/จอสัมผัส/Pi end-to-end ไม่เปลี่ยนโมเดล กฎ หรือ round2 และไม่ได้ push GitHub คู่มือ [FIELD_UI_RUNBOOK.md](docs/FIELD_UI_RUNBOOK.md), ชุดส่ง Pi outputs/field-ui-pi-2026-11-13.zip

# UX/UI — ประวัติร่างตรวจ 13 พฤศจิกายน 2026

**มติล่าสุด:** ผู้ใช้เห็นชอบโครงสร้างและหน้าตาร่างล่าสุดแล้ว ให้บันทึกและส่งต่อแชตหลัก **ยังไม่ต้องเชื่อมระบบจริง** กล้อง Camera Module 3 NoIR; ผู้ใช้ควบคุมเครื่องถ่วงเอง; วิธีเก็บภาพ/จบรอบ/ความครบวงต้องออกแบบใหม่หน้างาน ชุดเทคโนโลยีและระบบบันทึกยังเป็นข้อเสนอ ดู [ข้อสรุป UX/UI ล่าสุด](docs/UX_UI_DECISIONS_2026-11-13.md) ข้อความรอตรวจหน้าตาด้านล่างเป็นประวัติก่อนมตินี้

ผู้ใช้เห็นชอบโครงสร้างโดยประมาณแล้ว ขอปรับตามหน้าตา HTML ตัวอย่างและเน้นปุ่มใหญ่สำหรับสัมผัส จัดทำร่างสีเข้ม/ปุ่มฟ้าขนาดขั้นต่ำ 60px ให้ตรวจอีกครั้ง ยังไม่อนุมัติหรือเริ่มเชื่อมระบบจริง ดูบันทึกร่างด้านล่าง

ผู้ใช้ยืนยันให้กล้อง Pi เป็นเส้นทางหลัก นำเข้าภาพบนคอมไว้ทดสอบ ขนาดจอสัมผัสยังไม่แน่ใจ จัดทำ wireframe ในแชตให้ตรวจโดยสมมติ 1024×600 ชั่วคราว ทุกสถานะและผลเป็น mock ยังไม่เชื่อมกล้อง/AI/ระบบบันทึก ไม่เลือก framework/API/storage รายละเอียด [บันทึกร่าง](docs/UX_WIREFRAME_REVIEW_2026-11-13.md)

# อัปเดต 13 พฤศจิกายน 2026 — ONNX runner

เพิ่ม inference/onnx_engine.py ใช้ ONNX Runtime + NumPy + Pillow โดยไม่ใช้ torch/ultralytics โมเดลและกฎเดิม ตรวจ hash ทั้ง PT/ONNX ตรง release

เทียบ Windows กับตัวรันเดิม PT และ ONNX: ภาพวิจัย 280 ภาพไม่ซ้ำ + ภาพสังเคราะห์ 5 ภาพ ผล argmax/threshold ตรงทั้งหมด 285 ภาพ ความต่างคะแนนดิบสูงสุด 8.046627044677734e-07 (เกณฑ์ 1e-5) ทดสอบ boundary ของกฎ, aggregate, ไฟล์หาย และ CLI โดยบล็อก import torch/torchvision/ultralytics ผ่าน

หลักฐาน outputs/onnx-runner-check-2026-11-13/ คู่มือ docs/PI_ONNX_RUNNER.md และ requirements-pi.txt ยังไม่ยืนยันการติดตั้ง/ผล/เวลา/RAM บน Pi จริง ไม่ใช่การประเมินความแม่นยำใหม่ ตัวรันใหม่ตรวจ hash/class/ไฟล์หายแล้ว ตัวรันเก่ายังไม่แก้ ไม่มีการตรวจ coverage หรือตัวตนยาง

หลักฐานภาพหน้าจอจาก Pi: ตัวรัน ONNX ประมวลผล `/home/evminburi/test.jpg` สำเร็จ ได้ Normal 0.7549, Warning 0.2364, Abnormal 0.0087 และผลตัดสิน Normal; latency 628.9 ms ตาม timing scope ที่รวมอ่านภาพ/เตรียมภาพ/inference ไม่รวมโหลดโมเดล/กล้อง/UI เวอร์ชัน ONNX Runtime 1.31.1, NumPy 2.4.6, Pillow 13.0.0 ภาพไม่ใช่ยาง จึงเป็น runtime smoke check เท่านั้น ไม่ใช่ผลคุณภาพโมเดลหรือ benchmark; ยังไม่มีการเทียบภาพเดียวกันกับ Windows หรือเก็บ RAM/อุณหภูมิ

เทียบไฟล์เดียวกัน `test.jpg` บน Windows กับ Pi: คะแนน Normal/Warning/Abnormal ตรงกันที่ 4 ตำแหน่ง และผลตัดสิน Normal ตรงกัน; latency หนึ่งครั้ง Windows 164.9 ms, Pi 628.9 ms. เป็น parity ของ software path สำหรับภาพเดียวที่ไม่ใช่ยาง ไม่ใช่ผลความแม่นยำหรือ benchmark; ยังไม่มีการวัดซ้ำ/เก็บ RAM/อุณหภูมิ

---

# สถานะ — 10 พฤศจิกายน 2026

ติดตั้ง .venv แยกบน Windows ด้วย Python 3.14.7 แล้ว ไม่ใช้ site-packages จาก round2 ทดสอบ single-image CLI และ multiple-image CLI/JSON ผ่าน โมเดลและthresholdเดิมไม่เปลี่ยน ตรวจhashตรงrelease

ทดสอบ PT/ONNX กับภาพวิจัยเดิม3ภาพ ผลargmaxและผลหลังthresholdตรงกัน เปรียบเทียบคะแนนที่APIปัดเป็น4ตำแหน่งด้วยtolerance0.001 ไม่ใช่การรับรองparityทุกภาพหรือความแม่นยำหน้างาน ภาพ3ภาพเป็นคนละตัวอย่าง การรวมผลใช้ทดสอบทางเดินข้อมูลเท่านั้น ไม่ใช่ผลยางเส้นเดียว

pip check, ตรวจhash/syntax และunit tests2รายการผ่าน บันทึกเวอร์ชันครบในrequirements-windows-lock.txt หลักฐาน: outputs/windows-check-2026-11-10/ และ docs/WINDOWS_CHECK.md

ยังไม่ทดสอบPi 4 ไม่ฝึกใหม่ ไม่เปลี่ยนกฎ งานค้างด้านclass validation/ภาพหาย/coverageยังอยู่ในdocs/HANDOFF.md

## ส่งต่อ UX/UI
จัดทำ [บรีฟล่าสุด](docs/UX_UI_BRIEF.md) แล้ว ระบุข้อมูล/ข้อจำกัดจริงเพื่อเริ่มflowและwireframe ผู้ใช้ยืนยันรองรับเบราว์เซอร์บนคอมพิวเตอร์และจอสัมผัสที่ต่อ Pi โดยทีมวิจัย3Rเป็นผู้ดำเนินการและบันทึกผล ยังไม่ได้อนุมัติframework/API/storage

## Code review 14 พฤศจิกายน 2026
ตรวจ working tree แล้ว พบ UI race 2 จุดที่จำลองซ้ำได้ และปัญหา CLI เดิม 2 จุด ดู docs/CODE_REVIEW_2026-11-14.md ยังไม่แก้ application code/โมเดล ชุด unittest ค้างที่กรณีแรกและหยุดแล้ว จึงยังไม่ยืนยันว่าผ่าน ไม่ได้ทดสอบ Pi/กล้องจริง


## Camera review 14 พฤศจิกายน 2026
ผู้ใช้แจ้งภาพหน่วงและกลับขาว–ดำจริง ยังไม่ตรวจภาพที่บันทึก พบ preview polling 700 ms, ใช้ still capture ร่วมกับการถ่าย, วงรอบ preview ซ้อนหลังหยุด/เปิดใหม่ และ reconnect ไม่สร้าง device ใหม่เมื่อ device เดิมเสีย จำลองสองกรณีหลังได้ สาเหตุกลับสียังไม่ยืนยัน ดู docs/CAMERA_REVIEW_2026-11-14.md ไม่มีการแก้ runtime/โมเดลหรือทดสอบ Pi จริง


ผลตรวจเพิ่มเติมหลังแพ็กชุด 14 พฤศจิกายน 2026: legacy PT และ ONNX ให้ผลตัดสิน/คะแนนปัดเศษตรงกันใน synthetic smoke 1 ภาพ; bundle manifest ตรงกับ source ทั้ง 15 ไฟล์ SHA256 ZIP 6c402e2963fecf69481bc8d2c9c63593fb0eedf6978f2296958ba566c39b1d89 ไม่ใช่ผลทดสอบ Pi/ความแม่นยำหน้างาน
