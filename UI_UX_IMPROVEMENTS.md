# 🎨 DIP Tool - UI/UX Improvements

## 📋 Tổng Quan

Project đã được tái cấu trúc với **UI/UX tốt hơn** bằng cách nhóm các công cụ theo chức năng thực tế, tương tự giao diện taskbar chuyên nghiệp.

---

## 🎯 5 Nhóm Công Cụ Chính

### 1. 📁 **File Management** (Blue #0066cc)

Những công cụ cơ bản để quản lý ảnh:

- **📂 Open Image** - Tải ảnh từ máy
- **💾 Save Result** - Lưu ảnh đã xử lý
- **🔄 Reset to Original** - Hoàn tác tất cả thay đổi về ban đầu

💡 _Luôn ở trên cùng, dễ thấy để bắt đầu công việc_

---

### 2. ✨ **Enhancement** (Green #1e5f3f)

Cải thiện ảnh với một cú click:

- **Auto Contrast** - Tăng cường contrast tự động
- **Smart Contrast (CLAHE)** - Cải thiện tương phản thông minh
- **Enhance Blurry** - Làm sắc nét ảnh mờ
- **Reduce Glare** - Giảm tia sáng, lóa mắt
- **Anti-Backlight** - Khôi phục ảnh chụp lòi nắng

💡 _Tất cả là one-click solutions cho những vấn đề phổ biến_

---

### 3. 🎚️ **Adjustments** (Yellow #666600)

Điều chỉnh chi tiết với **sliders thời gian thực**:

- **Brightness** - Điều chỉnh độ sáng (-100 → +100)
- **Contrast** - Điều chỉnh độ tương phản (0.1 → 3.0)
- **Gamma Correction** - Điều chỉnh gamma (0.1 → 5.0)

💡 _Xem kết quả ngay lập tức khi kéo slider_

---

### 4. 🔧 **Filters** (Teal #2a4f5f)

Bộ lọc chuyên biệt được **nhóm theo loại**:

#### Smoothing (Làm mịn)

- **Mean Filter** - Làm mịn trung bình
- **Gaussian Blur** - Gaussian blur
- **Median Filter** - Loại bỏ nhiễu muối tiêu

#### Sharpening & Edges (Làm sắc nét & Cạnh)

- **Sharpen** - Làm sắc nét bằng Laplacian
- **Detect Edges (Canny)** - Phát hiện cạnh Canny

💡 _Chọn kernel size (3, 5, 7, 9) trước khi áp dụng_

---

### 5. ⚙️ **Advanced Tools** (Purple #4f3f5f)

Công cụ nâng cao cho những tác vụ đặc biệt:

- **🎯 Draw ROI (Select Area)** - Chọn vùng để chỉnh sửa riêng
- **🤖 Remove Background (AI)** - Xóa nền bằng AI (MediaPipe)
- **📊 Show Histogram** - So sánh biểu đồ ảnh gốc vs chỉnh sửa

💡 _Dùng khi cần xử lý phức tạp hơn_

---

## 🚀 Quy Trình Sử Dụng Khuyến Nghị

### Workflow Cơ Bản:

```
1. 📂 Open Image
   ↓
2. ✨ Check Quick Enhancements (Auto Contrast, Enhance Blurry, etc.)
   ↓
3. 🎚️ Fine-tune với Adjustments (Brightness, Contrast, Gamma)
   ↓
4. 🔧 Áp dụng Filters nếu cần
   ↓
5. ⚙️ Advanced Tools cho chỉnh sửa chuyên biệt
   ↓
6. 💾 Save Result
```

---

## 🎨 Color-Coding System

| Nhóm            | Màu       | Ý Nghĩa                       |
| --------------- | --------- | ----------------------------- |
| File Management | 🔵 Blue   | Công cụ cơ bản, quan trọng    |
| Enhancement     | 🟢 Green  | Cải thiện nhanh, một cú click |
| Adjustments     | 🟡 Yellow | Điều chỉnh chi tiết, sliders  |
| Filters         | 🔵 Teal   | Bộ lọc chuyên biệt            |
| Advanced        | 🟣 Purple | Công cụ nâng cao              |

---

## 💡 Mẹo & Thủ Thuật

### 1. ROI Selection (Vùng chỉnh sửa)

- Nhấp "Draw ROI" → Chọn vùng trên ảnh
- Mọi bộ lọc sau đó chỉ áp dụng cho vùng này
- Để chỉnh sửa toàn bộ ảnh, mở lại và skip ROI

### 2. Real-time Preview

- Sliders ở **Adjustments** cập nhật ngay
- **Apply Changes** để lưu, **Undo** để hoàn tác

### 3. Filter Kernel Size

- **3** = Chậm nhưng chi tiết
- **5, 7, 9** = Càng cao càng mạnh nhưng mất chi tiết

### 4. View Modes

- **Original** - Ảnh gốc vs ảnh hiện tại
- **Processed** - Chỉ xem preview
- **Split** - So sánh gốc vs xử lý

---

## 🔧 Cải Thiện UX So Với Trước

| Trước                              | Sau                                        |
| ---------------------------------- | ------------------------------------------ |
| Button ngẫu nhiên không có logic   | ✅ 5 nhóm rõ ràng, có màu riêng            |
| Khó tìm công cụ cần dùng           | ✅ Sắp xếp theo workflow                   |
| Không rõ chức năng của từng button | ✅ Emoji + tên rõ ràng                     |
| Slider không hiển thị giá trị      | ✅ Real-time value display                 |
| Button kích thước không đồng nhất  | ✅ Uniform sizing & spacing                |
| Tidak profesional                  | ✅ Giống giao diện design tool profesional |

---

## 📦 Requirements

```
customtkinter>=5.2.0
opencv-python>=4.8.0
numpy>=1.24.0
Pillow>=10.0.0
matplotlib>=3.7.0
mediapipe>=0.10.0  (for background removal)
scipy>=1.11.0
```

## 🎯 Tương Lai

Những cải thiện tiếp theo có thể:

- ✅ Thêm undo/redo history
- ✅ Lưu công thức xử lý
- ✅ Batch processing
- ✅ Shortcut keys
- ✅ Dark/Light theme toggle

---

**Enjoy! Happy Image Processing! 📸✨**
