# ผลติดตั้งและทดสอบ Windows — 10 พฤศจิกายน 2026

สร้าง .venv ใหม่ Python3.14.7, include-system-site-packages=false ติดตั้งไลบรารีหลักเวอร์ชันเดิม รวมonnx1.23.2 และบันทึก dependenciesทั้งหมดไว้requirements-windows-lock.txt

ผ่าน: pip check, hashโมเดลสองไฟล์, syntax, unit tests2รายการ, CLIภาพเดี่ยว, CLIหลายภาพและJSON, ผลPT/ONNXสามภาพตรงกันทั้งargmax/threshold เปรียบเทียบคะแนนที่ปัด4ตำแหน่งด้วยtolerance0.001

หลักฐานอยู่ outputs/windows-check-2026-11-10/: inputs.json, parity.json, cli-0.log, cli-1.log, mixed-images-plumbing-only.json, environment.json

ตัวอย่างคัดลอกจากภาพวิจัยเดิมเข้ามาในdata/input/smoke-2026-11-10 เป็นNormal226, Warning26, Abnormal233 ไม่ใช่ชุดอิสระหรือยางเส้นเดียว ไม่ใช้วัดaccuracy/coverage

เปิดworkspaceนี้ในVS Code แล้วเลือก .venv/Scripts/python.exe จากนั้น Run and Debug → Predict one image และระบุdata/input/smoke-2026-11-10/Warning_26.jpg ได้ทันที หรือรัน .venv/Scripts/python.exe inference/predict.py --image data/input/smoke-2026-11-10/Warning_26.jpg

ระหว่างติดตั้ง py aliasใช้งานไม่ได้ จึงใช้base Pythonที่ติดตั้งบนเครื่องโดยตรง ไม่ใช้round2เป็นruntime dependency และใช้.cache/tmpแก้สิทธิ์โฟลเดอร์ชั่วคราว ผลนี้ตรวจบนWindowsเท่านั้น
