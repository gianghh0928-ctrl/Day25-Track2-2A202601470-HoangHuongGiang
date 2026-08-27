# NimbusAI — Báo cáo Tối ưu hóa Chi phí GPU (GPU FinOps Report)

**Kỳ báo cáo:** Tháng 6/2026 (Tính theo hàng tháng)  
**Chi phí Ban đầu (Baseline Spend):** $27,133  
**Chi phí Sau Tối ưu (Optimized Spend):** $14,626  
**Tổng Chi phí Tiết kiệm (Projected savings):** $12,507  (**46%**)

## 1. Phân bổ Chi phí Tiết kiệm Theo Đòn bẩy (Savings by Lever)

| Đòn bẩy Tối ưu (Lever) | Chi phí Tiết kiệm (USD) | Tỷ lệ Tiết kiệm (%) |
|---|---|---|
| Inference (cascade/cache/batch) | $1,212 | 4.5% |
| Purchasing (spot/reserved) | $10,040 | 37.0% |
| Right-size util-lies | $655 | 2.4% |
| Kill idle GPUs | $600 | 2.2% |

## 2. Phân tích Kỹ thuật & Hiện tượng 'GPU-Util Lie'

- **Bản chất của GPU-Util Lie**: Trong kiểm toán Mission 1, thiết bị `gpu-h100-4` ghi nhận chỉ số `gpu_util_pct` từ `nvidia-smi` đạt tới **98.2%**, nhưng chỉ số **MFU (Model FLOPs Utilization)** thực tế chỉ đạt **0.194 (19.4%)**.
- **Nguyên nhân cốt lõi**: `nvidia-smi` chỉ đo thời gian mà GPU clock đang ở trạng thái hoạt động (bận), nhưng KHÔNG đo được khối lượng FLOPs thực tế được tính toán. Hiện tượng này xảy ra do nghẽn băng thông bộ nhớ (Memory Bandwidth Stalls), chờ truyền dữ liệu (PCIe bottleneck) hoặc kích thước batch quá nhỏ.
- **Hệ quả FinOps**: Doanh nghiệp đang phải trả 100% chi phí thuê GPU H100 cao cấp nhưng chỉ tận dụng được chưa tới 1/5 hiệu năng tính toán thực tế.

## 3. Lộ trình Hành động Đề xuất (Actionable Roadmap by ROI)

1. **Ưu tiên 1 (ROI Cao nhất - Tối ưu Mua sắm Purchasing)**: Chuyển đổi các workload steady-state (như inference real-time) sang **Reserved Instances (chiết khấu 45%)** và các job training có thể ngắt sang **Spot Instances (chiết khấu ~60-70%)**. Giúp tiết kiệm ngay **$10,040 / tháng**.
2. **Ưu tiên 2 (Tối ưu Inference Request - High Yield)**: Áp dụng đồng thời **Prompt Caching** (giảm 90% chi phí input cached), **Batch API** (giảm 50% chi phí cho eval/batch) và **Model Cascading** (chuyển 80% câu hỏi đơn giản sang model nhỏ). Giúp giảm đơn giá từ **$6.488/1M-token** xuống **$1.126/1M-token** (tiết kiệm **$1,212 / tháng**).
3. **Ưu tiên 3 (Right-sizing & Thu hồi GPU Idle)**: Thu hồi các GPU bỏ không (tiết kiệm **$600 / tháng**) và hạ cấp hạ tầng (Right-sizing) đối với các GPU bị 'Util Lie' từ H100 xuống A100/A10G (tiết kiệm **$655 / tháng**).

## 4. Tác động Bền vững & Năng lượng (Sustainability)

- **Mức tiêu thụ năng lượng bình quân**: 0.24 Wh / truy vấn.
- **Lượng phát thải Carbon bình quân**: 0.091 gCO2e / truy vấn (tại vùng `us-east-1`).
- **Khu vực tối ưu nhất (Sạch nhất + Rẻ nhất)**: `europe-north1` (Sử dụng 100% năng lượng tái tạo/thủy điện với mức carbon cực thấp).

## 5. Phân tích Mở rộng 'Your Turn' (Advanced Insights)

- **Chiến lược mua Nâng cao (Advanced Tier Policy)**: Đã tính toán thêm chi phí ghi checkpoint & làm lại (rework cost ~0.5h) cho Spot instance với tỷ lệ gián đoạn 5%. Kết quả khẳng định Spot vẫn tối ưu chi phí vượt trội cho công việc training có thể checkpoint.
- **Ngưỡng Kinh tế của Prompt Caching**: Xác định điểm hòa vốn khi tỷ lệ đọc cache (Cache Read Hit Rate) đạt tối thiểu **20%**, giúp đảm bảo chi phí tiết kiệm vượt qua chi phí lưu trữ/ghi overhead.
- **Phân bổ Ngân sách Reasoning**: Kiểm toán chỉ số request dạng Reasoning (như o1/o3-mini) tiêu tốn năng lượng gấp ~80 lần request tiêu chuẩn, từ đó đề xuất quy tắc phân luồng chặt chẽ.
- **Lập lịch Nhận thức Carbon (Carbon-Aware Scheduling)**: Chuyển toàn bộ job training gián đoạn sang vùng `europe-north1` giúp giảm **80.0%** tổng lượng carbon phát thải.

---
_Báo cáo được tổng hợp tự động từ dữ liệu telemetry tháng 6/2026._