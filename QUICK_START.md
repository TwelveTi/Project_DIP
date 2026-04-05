╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║ 🚀 QUICK START GUIDE - DIP TOOL ║
╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
⚙️ SETUP & INSTALLATION
═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

1. Cài đặt dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Chạy ứng dụng:

   ```bash
   python main.py
   ```

3. Nếu thiếu MediaPipe:
   ```bash
   pip install mediapipe
   ```

═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
🎯 5-MINUTE QUICK TUTORIAL
═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

STEP 1: Open an Image [1 click]
──────────────────────

1. Vào 📁 FILE MANAGEMENT section
2. Nhấp "📂 Open Image"
3. Chọn ảnh từ máy

Kết quả: Ảnh sẽ xuất hiện ở bên trái

STEP 2: Quick Enhancement [1-2 clicks]
──────────────────────────
Ví dụ: Ảnh quá tối

1. Vào ✨ ENHANCEMENT section
2. Thử: "Smart Contrast (CLAHE)" trước
   - Hoặc "Auto Contrast" nếu muốn đơn giản
   - Hoặc "Reduce Glare" nếu ảnh lóa mắt
3. Xem kết quả preview ở bên phải

Nếu không thích → nhấp "Undo" để quay lại

STEP 3: Fine-tune with Sliders [30s]
──────────────────────────────────

1. Vào 🎚️ ADJUSTMENTS section
2. Kéo slider "Brightness" nếu muốn sáng/tối hơn
3. Kéo slider "Contrast" nếu muốn tăng/giảm độ tương phản
4. Xem giá trị thay đổi ngay lập tức

Tip: Kéo chậm để xem preview cập nhật real-time

STEP 4: Apply Filters (Optional) [1-2 clicks]
────────────────────────────────
Nếu ảnh quá mờ hoặc cần cạnh sắc:

1. Vào 🔧 FILTERS section
2. Chọn kernel size (3, 5, 7, 9):
   - 3 = chi tiết nhất
   - 5, 7, 9 = mạnh hơn
3. Chọn filter:
   - Mờ → "Gaussian Blur"
   - Nhiễu → "Median (Remove Spots)"
   - Cạnh sắc → "Sharpen"

STEP 5: Save Your Work [1 click]
─────────────────────

1. Thỏa mãn với kết quả?
2. Nhấp "Apply Changes" (nút xanh) để lưu thay đổi
3. Vào 📁 FILE MANAGEMENT
4. Nhấp "💾 Save Result"
5. Chọn nơi lưu và định dạng (.png, .jpg, .bmp)

═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
🎨 COMMON SCENARIOS
═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

📷 SCENARIO 1: Ảnh Quá Tối
──────────────────────────
Problem: Ảnh chụp trong điều kiện ánh sáng yếu
Solution:

1. ✨ ENHANCEMENT → Click "Enhance Blurry" hoặc "Anti-Backlight"
2. 🎚️ ADJUSTMENTS → Kéo "Brightness" về phải (+30 đến +50)
3. 🎚️ ADJUSTMENTS → Kéo "Contrast" nhẹ lên (1.2 → 1.5)
4. 💾 Save

Result: Ảnh sẽ sáng và rõ hơn

📷 SCENARIO 2: Ảnh Quá Sáng / Lóa Mắt
─────────────────────────────────────
Problem: Ảnh chụp dưới nắng gắt quá sáng
Solution:

1. ✨ ENHANCEMENT → Click "Reduce Glare"
2. 🎚️ ADJUSTMENTS → Kéo "Brightness" về trái (-20 đến -40)
3. 🎚️ ADJUSTMENTS → Kéo "Contrast" lên nhẹ (1.1 → 1.3)
4. 💾 Save

Result: Ảnh sáng cân bằng, không lóa

📷 SCENARIO 3: Ảnh Mờ
──────────────────────
Problem: Ảnh không sắc nét, mờ mắt
Solution:

1. ✨ ENHANCEMENT → Click "Enhance Blurry"
2. 🔧 FILTERS → "Sharpen" filter
3. 🎚️ ADJUSTMENTS → Kéo "Contrast" để tăng sắc nét thêm
4. 💾 Save

Result: Ảnh sắc nét hơn

📷 SCENARIO 4: Ảnh Có Nhiễu (Salt & Pepper)
───────────────────────────────────────────
Problem: Ảnh có những chấm trắng/đen ngẫu nhiên
Solution:

1. 🔧 FILTERS → Chọn kernel size "5"
2. 🔧 FILTERS → "Median (Remove Spots)"
3. Nếu cần làm mịn thêm → "Gaussian Blur"
4. 💾 Save

Result: Ảnh mịn, sạch nhiễu

📷 SCENARIO 5: Cần Chỉnh Sửa Một Phần Ảnh
──────────────────────────────────────────
Problem: Chỉ muốn chỉnh sửa một vùng cụ thể
Solution:

1. ⚙️ ADVANCED TOOLS → "🎯 Draw ROI (Select Area)"
2. Click và kéo để vẽ hình chữ nhật quanh vùng cần chỉnh
3. Áp dụng filters/adjustments từ đó - chỉ vùng ROI bị ảnh hưởng
4. 💾 Save

Result: Chỉ vùng được chọn bị thay đổi

📷 SCENARIO 6: Xóa Nền (Object Detection)
─────────────────────────────────────────
Problem: Muốn xóa nền ảnh tự động
Solution:

1. ⚙️ ADVANCED TOOLS → "🤖 Remove Background (AI)"
2. Chờ xử lý xong (vài giây)
3. 💾 Save (định dạng .png để giữ transparency)

Note: Hoạt động tốt nhất cho ảnh chân dung (selfie, portrait)

═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
💡 PRO TIPS & TRICKS
═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

🔹 TIP #1: Luôn Dùng "Apply Changes" Trước Khi Save
───────────────────────────────────────────────────
Sau khi có kết quả ý muốn:

1. Nhấp "✓ Apply Changes" (nút xanh) → xác nhận thay đổi
2. Rồi "💾 Save Result"

Lý do: Preview là tạm thời, Apply mới lưu vĩnh viễn

🔹 TIP #2: View Modes để So Sánh
───────────────────────────────
Trên thanh toolbar chính:

- "Original" → So sánh gốc vs hiện tại
- "Processed" → Chỉ xem kết quả
- "Split" (mặc định) → Xem gốc vs preview

🔹 TIP #3: Show Histogram Để Kiểm Tra
─────────────────────────────────────

1. ⚙️ ADVANCED TOOLS → "📊 Show Histogram"
2. Xem so sánh tone distribution của ảnh gốc vs chỉnh sửa
3. Giúp quyết định có cần adjust thêm không

🔹 TIP #4: Kernel Size Ảnh Hưởng Cơn Mạnh
──────────────────────────────────────────

- 3 (nhỏ) = Ít thay đổi, giữ chi tiết → Dùng lần đầu
- 5 = Trung bình → Dùng khi muốn rõ hơn
- 7, 9 = Mạnh → Dùng khi cần hiệu ứng rõ rệt

🔹 TIP #5: Undo Sử Dụng Thường Xuyên
──────────────────────────────────────
Nhấp "Undo" để quay lại trước đó nếu:

- Adjustment quá mạnh
- Filter không phù hợp
- Muốn thử cách khác

🔹 TIP #6: Workflow Tối Ưu
──────────────────────────

1. ENHANCEMENT → 2. ADJUSTMENT → 3. FILTER
   Không nên:

- Filters trước → Enhancement sau (kết quả tệ)
- Vì Enhancement tính toán trên histogram

═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
⌨️ KEYBOARD SHORTCUTS (Coming Soon)
═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

Ctrl+O → Open Image
Ctrl+S → Save Result
Ctrl+Z → Undo
Ctrl+R → Reset
Space → Toggle View Mode

(Thêm vào phiên bản tương lai)

═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
❓ TROUBLESHOOTING
═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

❌ Error: "Import customtkinter could not be resolved"
✅ Solution: pip install customtkinter>=5.2.0

❌ Error: "Remove Background" không hoạt động
✅ Solution: pip install mediapipe

❌ Ảnh quá lớn, ứng dụng lag
✅ Solution: Ảnh sẽ tự động resize về 1280px khi load

❌ Slider không responsive
✅ Solution: Thử adjust chậm hơn, có throttle 50ms

═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
📚 FURTHER LEARNING
═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════

📖 Documentation Files:

- UI_UX_IMPROVEMENTS.md (Detailed feature list)
- LAYOUT_DIAGRAM.txt (Visual layout)
- BEFORE_AFTER_COMPARISON.txt (Improvements breakdown)

🔗 Technology Links:

- OpenCV: https://docs.opencv.org/
- CustomTkinter: https://github.com/TomSchimansky/CustomTkinter
- MediaPipe: https://mediapipe.dev/

🎓 Image Processing Concepts:

- Histogram Equalization
- Gamma Correction
- Convolution & Kernels
- Edge Detection (Canny)
- Morphological Operations

═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
✨ HAPPY IMAGE PROCESSING! 📸
═════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
