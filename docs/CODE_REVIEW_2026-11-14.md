# Code review — 2026-11-14

Scope: current working tree, field_app, UI, inference and supporting tests/scripts. Application code and model were not changed.

Findings:
- P1 ui/app.js:70: an outstanding analysis poll replaces global current even after navigation to another session. Node VM reproduction: switch A -> B, resolve A poll, current becomes A. Capture/review/finalize may then target the wrong session. Bind responses to session ID/navigation generation and discard stale responses.
- P2 ui/app.js:25,56: review inputs remain editable during save; saveReview clears reviewDirty unconditionally. Node VM reproduction: visible notes=new, persisted notes=old, dirty=false. Disable editing during save or retain dirty state when the form changed after submission.
- P1 inference/inference_engine.py:95: comma-separated input silently drops missing files and produces an aggregate from only surviving images. Reject incomplete input before inference. This is an existing documented legacy issue; the ONNX runner already rejects missing files.
- P2 inference/inference_engine.py:25-27 and inference/predict.py: class lookup defaults to zero. A different classifier supplied through --model without expected class names can produce Normal instead of a contract error. Validate classes/output first. Existing documented legacy issue; ONNX runner validates mapping.

Verification: both UI race conditions reproduced with actual app.js in a Node VM and stub DOM/API; no browser/hardware claim. unittest discover -s tests -v stalled at test_bad_inputs_camera_and_cross_origin and was interrupted; no passing full-suite claim and no diagnosis of the stall. Pi camera/end-to-end not tested in this review.

## Follow-up implementation
Confirmed code defects addressed after this review; see [FIXES_2026-11-14.md](FIXES_2026-11-14.md) for changes and tests. Hardware colour inversion and measured Pi performance still require device evidence.
