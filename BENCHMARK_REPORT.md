# Benchmark & Observability Report — Day 14

> Báo cáo thực hành dựa trên JSON, CSV, log và ảnh của lần chạy ngày 25/11/2026.
> Mọi con số phải lấy từ report JSON / CSV / screenshot thật, không ước lượng.

**Họ tên:** Nguyễn Minh Đạt
**Ngày chạy:** 25/11/2026
**Môi trường:** Windows, Ubuntu 24.04.2 LTS trên WSL2, Python 3.12.3; agent benchmark chạy local (v1:8001, v2:8002). WSL báo 12 logical CPU, 7617 MiB RAM qua nproc/free tại lần rà cuối; đây là tài nguyên WSL nhìn thấy, không khẳng định cấu hình vật lý toàn máy.

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | ≤ 500 ms | Ngưỡng mặc định của load_test.py cho bài thực hành. |
| Error rate `/ask` | ≤ 2% | Ngưỡng mặc định của load_test.py; có tính lỗi mock. |
| Accuracy trên golden dataset | ≥ 80% baseline; mục tiêu v2 sau sửa 100% | Gate mặc định của eval và mục tiêu CP7 sau sửa knowledge base. |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 4.21 | 195.1 | 224.4 | 1711.2 | 1.33% | PASS |
| 10 | 40.65 | 193.5 | 219.2 | 1683.9 | 1.00% | PASS |
| 50 | 108.58 | 199.1 | 266.2 | 1694.8 | 2.33% | FAIL (error rate) |
| 100 | 67.27 | 551.3 | 3382.8 | 3544.4 | 1.33% | FAIL (p95) |

**Nhận xét:** RPS có tăng tuyến tính theo concurrency không? Vì sao?

Mỗi mức gửi 300 request. RPS tăng từ 4.21 lên 40.65 khi concurrency 1 → 10, nhưng không tiếp tục tăng tuyến tính: mức 50 đạt 108.58 RPS, mức 100 giảm còn 67.27 RPS trong khi p95 tăng từ 266.2 lên 3382.8 ms. Đây là dấu hiệu suy giảm hiệu năng khi tăng tải trong lần đo này; chưa đủ bằng chứng quy nguyên nhân cho CPU, hàng đợi hay scheduler cụ thể. Agent và load generator dùng chung máy, phép đo ngắn ở các mức cao và mock có độ trễ/lỗi ngẫu nhiên nên không kết luận 50 là mức tối ưu cố định. Mức 50 lỗi 7/300 (2.33%), vượt SLO 2%; chưa thể quy lỗi đó riêng cho quá tải khi mock cũng chủ động sinh 503. Giữ nguyên kết quả FAIL để phản ánh số đo thực tế.

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 191 | 220 | 230.5 |
| 0.03 (mặc định) | 221.7 | 222.8 | 1688.4 |
| 0.1 | 301.8 | 1676.1 | 1713.8 |

**Nhận xét:** Chỉ số nào nhạy nhất với request chậm? Vì sao SLO không nên đặt theo average?

Ba lần đo đều dùng 300 request, concurrency=20 và khởi động lại v2 với từng MOCK_SLOW_RATE. Khi tăng 0 → 0.03, avg tăng 191.0 → 221.7 ms, p95 chỉ tăng 220.0 → 222.8 ms nhưng p99 tăng 230.5 → 1688.4 ms: p99 nhạy hơn với nhóm request chậm hiếm. Ở mức 0.1, p95 tăng lên 1676.1 ms, vượt SLO 500 ms, trong khi avg vẫn chỉ 301.8 ms và p50 là 192.4 ms. Trung bình che khuất trải nghiệm của nhóm người dùng phải chờ lâu; cần dùng percentile phù hợp và theo dõi error rate cùng lúc. MOCK_SLOW_RATE là xác suất, không bảo đảm đúng tỷ lệ chậm trong mỗi mẫu 300 request; đây là số đo từng lần chạy, không phải giá trị xác định cho mọi lần.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 4.3% (1/23) | 91.3% (21/23) | 100% (23/23) |
| Avg tokens / câu | 57.1 | 109 | 123.7 |
| Tổng cost (USD) | 0.000404 | 0.000759 | 0.000877 |
| Cost / câu đúng (USD) | 0.00040395 | 0.00003616 | 0.00003815 |
| Quality gate | FAIL | PASS (80%, không regression) | PASS (100%, không regression) |

**Những câu v2 trả lời sai ban đầu và cách bạn sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| security-02 | token; hết hạn; chữ ký | Bổ sung tài liệu so sánh JWT/API key, chữ ký, claims, hết hạn và giới hạn bảo mật. Trigger jwt/api key/api-key. |
| scaling-03 | cpu; memory; custom metrics | Bổ sung tài liệu Kubernetes HPA, các nguồn metrics, điều kiện cấu hình tài nguyên và giới hạn replica. Trigger kubernetes/hpa/horizontal pod autoscaler. |

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:**

V2 cải thiện 20 câu, tăng accuracy 87.0 điểm phần trăm, không có regression so với v1. Retrieval tăng tokens trung bình từ 57.1 lên 109.0 và tổng chi phí mock từ 0.000404 lên 0.000759 USD, nhưng cost/câu đúng giảm từ 0.00040395 xuống 0.00003616 USD (khoảng 11.2 lần). p95 lần đo v1=314.3 ms và v2=266.9 ms; có jitter và request chậm ngẫu nhiên nên không kết luận retrieval luôn làm giảm latency. V2 trước sửa vẫn thiếu hai chủ đề; đã bổ sung KB ở cả develop và production. Sau restart v2, eval cuối đạt 23/23, không lỗi, cải thiện hai câu và không regression; p95=279.7 ms, tổng cost mock=0.000877 USD. KB mới làm tokens trung bình tăng lên 123.7 và cost/câu đúng tăng nhẹ so với v2 trước sửa, đổi lại đạt đủ 23 câu. Accuracy ở đây dựa trên keyword của bộ 23 câu, không bảo đảm chất lượng cho mọi câu hỏi.

---


### 3.1 Quality gate trong CI (Exercise 7.3)

Sau khi job CI cài dependency, khởi động app ứng viên và chờ /health sẵn sàng, chạy eval với baseline đã được review. Ví dụ bước GitHub Actions dưới đây giả định agent v2 đã chạy ở cổng 8002 và baseline tồn tại (working-directory tính từ gốc repo):

```yaml
- name: Evaluate candidate against reviewed baseline
  working-directory: 06-lab-complete/benchmark-observability/develop
  run: >-
    python eval/run_eval.py
    --url http://localhost:8002
    --min-accuracy 1.0
    --baseline reports/eval_v2.json
    --out reports/eval_candidate.json
```

Script trả exit code 1 khi không đạt ngưỡng hoặc có regression, khiến step/job thất bại. Không dùng continue-on-error hoặc nối `|| true`. Cấu hình branch protection yêu cầu job này thành công để chặn merge PR lỗi. Đoạn trên là thiết kế bước CI, chưa chạy một GitHub Actions workflow thực tế; baseline không được ghi đè bằng kết quả ứng viên. Lần eval cuối sinh viên tự chạy trên máy trả quality gate PASS 100%, không regression.

## 4. Observability stack (production)

### 4.1 Screenshot

- [x] Dashboard Grafana khi đang có tải (thấy rõ Golden Signals)
- [x] Một trace chậm trong Jaeger (thấy span nào chiếm thời gian)
- [x] Một trace lỗi trong Jaeger (có event `exception`)
- [x] Trang Alerts của Prometheus có ít nhất 2 alert cùng **firing**

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` (cùng B) | AgentHighErrorRate FIRING | Quan sát A+B sau 211s; không đo riêng lần firing đầu | Error rate |
| B | `MOCK_SLOW_RATE=0.3` (cùng A) | AgentHighLatencyP95 FIRING | Quan sát A+B sau 211s; không đo riêng lần firing đầu | p95/p99 |
| C | `LLM_MODEL=mock-llm-large` | LLMCostBurnRateHigh FIRING | Không đo được lần kích hoạt mới; alert đã active từ trước | p95 705.94 ms; burn rate quan sát 26.0183 USD/giờ (mock) |
| D | Pause agent-2, giữ agent-3 chạy | AgentInstanceDown FIRING | Lần đầu quan sát sau 50.12s theo monotonic, poll mỗi 5s | up của target bị pause bằng 0 |
| E | `AGENT_VERSION=v1`, model nhỏ, 2 instance | Không có alert chất lượng; alert cost cũ còn firing | Không áp dụng thời gian phát hiện chất lượng vì chưa có rule | agent_info version=v1; eval chỉ đúng 1/23 |

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**

Cần eval trên golden dataset, quality gate trước deploy và đánh giá mẫu traffic sau deploy (keyword/semantic/LLM judge hoặc phản hồi người dùng). Latency và error rate tốt chỉ chứng minh API phục vụ được, không chứng minh nội dung đúng. Trong thí nghiệm E thực tế, v1 đạt 1/23 và eval thoát 1; alert cost cũ vẫn firing nên không nói tất cả alert đều xanh. Các rule hiện tại không kiểm tra accuracy, vì vậy không báo riêng sự cố chất lượng.

### 4.2.1 Kết quả thí nghiệm A+B kết hợp

Sinh viên áp dụng đồng thời MOCK_ERROR_RATE=0.2 và MOCK_SLOW_RATE=0.3, giữ Locust chạy 30 users. Mốc lệnh trước Compose: 25/11/2026 17:15:03 +0700. Đến 17:18:34 +0700, ảnh Prometheus cho thấy AgentHighErrorRate, AgentHighLatencyP95 và LLMCostBurnRateHigh cùng FIRING; AgentInstanceDown inactive.

Khoảng từ mốc áp dụng đến lúc quan sát là 211 giây (3 phút 31 giây). Đây là giới hạn trên theo lần quan sát, không phải thời điểm đầu tiên từng alert firing. Không ghi 211 giây thành thời gian phát hiện riêng của từng alert. Alert cost đã firing ở ảnh sớm hơn; chưa đủ bằng chứng quy nó cho riêng thay đổi A+B hoặc thí nghiệm model lớn C. Không phát sinh phí LLM thật vì stack dùng mock.

AgentHighErrorRate yêu cầu error rate >5% trong 1 phút, AgentHighLatencyP95 yêu cầu p95 >1 giây trong 2 phút. Cần thêm thời gian scrape/evaluation và cửa sổ rate; Pending chưa được tính là Firing. Ảnh minh chứng được sinh viên hướng dẫn lưu screenshots/prometheus-alert-firing.png. Không có thời gian firing riêng cho A/B; kết quả C/D/E bổ sung bên dưới.

Sau ảnh, AI trả MOCK_ERROR_RATE=0.01 và MOCK_SLOW_RATE=0.03 trong .env local, giữ nguyên key; sinh viên cần chạy Compose để áp dụng trước benchmark scaling.
### 4.2.2 Model lớn (C)

Sinh viên chạy cấu hình model lớn với Locust 30 users, một instance. Ảnh Grafana khoảng 17:30 GMT+7 cho thấy traffic 16.6 req/s, error rate 1.25%, p95 705.94 ms, LLM cost (1h) 3.3641 USD mô phỏng. Panel tổng cost theo cửa sổ 1 giờ không phải burn rate. Ảnh chi tiết Prometheus khoảng 17:32 cho thấy LLMCostBurnRateHigh FIRING, value=26.018293866735387 (USD/giờ mô phỏng), ngưỡng >2 và for=2m. Active Since hiển thị 12m16.312s: alert đã active từ trước, nên không đo được thời gian firing mới cho riêng thí nghiệm C và không dùng giá trị này làm độ trễ phát hiện kể từ đổi model.

Đơn giá trong mock của model lớn cao hơn khoảng 16.67 lần cho cùng số token; latency_factor là 2.5. Số đo thực tế còn phụ thuộc throughput, token/câu và cửa sổ rate 5 phút, nên không kết luận burn rate quan sát phải tăng đúng hệ số đó. p95 cao hơn ảnh baseline khoảng 294 ms nhưng vẫn dưới ngưỡng alert latency 1 giây trong lần quan sát này. Không có lời gọi LLM trả phí thật.
### 4.2.3 Pause instance và quality regression (D/E)

D: Script tạm pause đúng container agent-2, giữ agent-3 phục vụ, poll Prometheus API mỗi 5 giây rồi tự unpause trong finally. Bằng chứng reports/chaos_instance_down.json ghi bắt đầu 10:35:27.781550Z, lần đầu quan sát AgentInstanceDown FIRING 10:36:13.476171Z; elapsed đo bằng monotonic là 50.12 giây. Hai đồng hồ không cho cùng chênh lệch tuyệt đối; giữ nguyên timestamp và elapsed gốc, không ép khớp. Target 172.24.0.7:8000 có up=0, activeAt=10:35:37.401817116Z. Rule cần 30 giây cộng thời gian scrape/evaluation. Container đã unpause ngay sau phép đo.

Dùng pause thay stop giúp target vẫn tồn tại trong Docker DNS nhưng không đáp ứng scrape. Request qua Nginx có thể bị chờ hoặc 504 mà agent chưa xử lý xong để ghi metric; vì vậy metric error của agent có thể không phản ánh toàn bộ lỗi người dùng thấy. Cần thêm metric/synthetic check ở load balancer.

E: Sau khi đưa agent sang v1 và model nhỏ, chạy eval qua Nginx với key lấy trong bộ nhớ từ môi trường container, không in key. reports/eval_production_v1_chaos.json có 1/23 đúng, accuracy=0.0435, errors=0, quality gate exit=1. Snapshot reports/chaos_v1_alerts.json chỉ có alert cost còn firing; không có rule phát hiện accuracy thấp. Metrics xác nhận version=v1, histogram question length có count 237 và 257 trên hai instance lúc quan sát. Kết thúc đã khôi phục v2/model nhỏ và dừng Locust.

Unit test alert rules: promtool test rules alert_rules_test.yml trả exit 0, SUCCESS; lưu reports/promtool_result.txt. Không sửa rule/test để đạt kết quả.

### 4.3 Debug bằng trace

Chọn 1 trace chậm nhất bạn tìm được:

- `trace_id`: 4d5005297991e0ac3f82b52e67c6975c
- Jaeger hiển thị tổng thời gian khoảng 7200 ms, span `chat mock-llm-small` khoảng 7100 ms; retrieval 23.8 ms. Tỷ lệ span chat/tổng khoảng 98.6%, tính từ số giây đã làm tròn trên ảnh, không phải số đo chính xác.
- Model mock-llm-small, input 76 token, output 39 token; status HTTP 200.
- Hai dòng log JSON do sinh viên grep theo cùng trace_id (đã bỏ tiền tố Compose agent-1):

```json
{"ts":"2026-11-25T10:05:27.915216+00:00","level":"INFO","service":"observable-agent","instance":"5ebd86684ce0","event":"llm_call","trace_id":"4d5005297991e0ac3f82b52e67c6975c","span_id":"ac4b3a696ed2fe0c","request_id":"b0c0a4c02b67","model":"mock-llm-small","agent_version":"v2","input_tokens":76,"output_tokens":39,"cost_usd":3.5e-05,"llm_ms":193.2}
{"ts":"2026-11-25T10:05:27.915933+00:00","level":"INFO","service":"observable-agent","instance":"5ebd86684ce0","event":"http_request","trace_id":"4d5005297991e0ac3f82b52e67c6975c","span_id":"ac4b3a696ed2fe0c","request_id":"b0c0a4c02b67","method":"POST","route":"/ask","status":200,"ms":220.8}
```

Đối chiếu: trace_id, instance và số token khớp, xác nhận có thể liên kết log với trace. Tuy nhiên thời gian Jaeger (~7.2 s) không khớp http_request.ms=220.8 ms. llm_ms=193.2 lấy từ result.latency_s của mock (độ trễ được sinh theo công thức, không đo toàn bộ thời gian thực thi); middleware HTTP dùng time.perf_counter, còn span có timestamp riêng. Chưa xác định được nguyên nhân chênh lệch, có thể liên quan đồng hồ/môi trường WSL hoặc instrumentation; không kết luận provider thực sự mất 7.1 s chỉ từ ảnh này. Giữ nguyên cả hai bằng chứng và ghi rõ bất nhất. Cần thêm trace hoặc đối chiếu đồng hồ nếu muốn chẩn đoán nguyên nhân.
---

### 4.4 Trace lỗi upstream và log tương ứng

Ảnh sinh viên cung cấp cho thấy trace `e9c48087b47688ca92ac72166b0d7cbb`, tổng 97.9 ms, span chat mock-llm-small 76.5 ms, retrieval 18.2 ms. Span chat có error.type=upstream_unavailable và event exception, loại utils.mock_llm.LLMError, message Upstream LLM error: 503 Service Unavailable (mock). Đây là lỗi chủ động mô phỏng của bài lab.

Log sinh viên lấy từ Compose, cùng trace_id và request_id:

```json
{"ts":"2026-11-25T10:11:17.948104+00:00","level":"INFO","service":"observable-agent","instance":"5ebd86684ce0","event":"llm_error","trace_id":"e9c48087b47688ca92ac72166b0d7cbb","span_id":"0e961cf9d7e7ff74","request_id":"68c81cc538cb","error":"Upstream LLM error: 503 Service Unavailable (mock)"}
{"ts":"2026-11-25T10:11:17.948540+00:00","level":"INFO","service":"observable-agent","instance":"5ebd86684ce0","event":"http_request","trace_id":"e9c48087b47688ca92ac72166b0d7cbb","span_id":"0e961cf9d7e7ff74","request_id":"68c81cc538cb","method":"POST","route":"/ask","status":503,"ms":97.0}
```

Ảnh trace này và log HTTP thống nhất về mã lỗi và thời gian gần 98 ms; chênh lệch nhỏ do phạm vi đo span/middleware. Trong code, mock phát sinh exception, span ghi exception và đánh dấu ERROR, endpoint chuyển thành HTTP 503. Một exception có thể làm nhiều span cha được đánh dấu lỗi; số error span không đồng nghĩa có từng đó request lỗi độc lập. Lưu ảnh minh chứng dưới tên screenshots/jaeger-error-trace.png.

### 4.5 Metrics và đọc dashboard (Exercise 7.1/7.4)

- Counter: http_requests_total đếm request theo method/route/status. Gauge: agent_in_flight_requests biểu diễn số request đang xử lý. Histogram: http_request_duration_seconds có bucket/count/sum để đo phân bố latency.
- Dùng route.path và unmatched thay URL tùy ý ngăn bot quét hàng nghìn đường dẫn tạo hàng nghìn label/time series. Không dùng nội dung câu hỏi hoặc request_id làm label.
- Đã thêm Histogram agent_question_length_chars với buckets 20,50,100,200,500,1000,2000 vào develop và production, observe len(question) mỗi request. Smoke test gửi Docker (6 ký tự) cho count=1 và sum=6, lưu reports/question_length_metric.txt; production cũng đã ghi count qua request thật.
- Ảnh baseline Grafana có tải cho thấy 20.0 req/s, error rate 1.10%, p95 293.65 ms, một instance. Ảnh không hiển thị avg bằng số nên không bịa giá trị; benchmark local mặc định cùng concurrency20 cho avg221.7/p95 222.8/p99 1688.4 ms nhưng là phép đo riêng, không trộn thành số cùng thời điểm dashboard. Khoảng cách avg/p95/p99 cho biết nhóm request chậm và độ lệch phân bố.
- Ảnh baseline một instance không chứng minh chia đều hai instance. Khi thử hai instance v1, số request ghi vào histogram là 237/257, cho thấy cả hai có phục vụ với mức khá gần nhau trong snapshot đó; không khẳng định hoàn toàn đều ở mọi thời điểm.
- Input tokens gồm system prompt, câu hỏi và context retrieval; output chỉ là câu trả lời, nên input tokens/s thường lớn hơn. Trace mẫu có input76/output39, phù hợp nhận xét này, không phải quy luật bắt buộc mọi câu.
- GET http://localhost:8080/metrics đã kiểm tra thực tế trả 404 (reports/public_metrics_check.json); Nginx chặn endpoint vận hành ra ngoài, còn Prometheus scrape trực tiếp agent trong mạng Docker.

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | 65.94 | 200 | 240 | 1700 | 72/7117 (1.01%) |
| 3 | 65.94 | 200 | 230 | 1700 | 64/7085 (0.90%) |

**Giải thích kết quả:** Scale có cải thiện p95 không? Nút thắt nằm ở đâu?

Bảng dùng riêng hàng POST /ask trong scale_1_stats.csv và scale_3_stats.csv, tránh trộn health check vào latency agent. Với 1 → 3 instance, RPS gần như không đổi (65.9404 → 65.9355), p50 vẫn 200 ms, p95 giảm 240 → 230 ms (khoảng 4.2%), p99 vẫn 1700 ms. Trong lần đo này, thêm replica không mang lại tăng throughput đáng kể. Mock LLM có thời gian chờ bất đồng bộ và request chậm giả lập; thêm instance không loại bỏ độ trễ đó. Tải giới hạn ở 100 user cùng thời gian nghĩ của Locust, nên một instance có thể đã đáp ứng phần lớn tải được phát; chưa có bằng chứng CPU agent bão hòa để coi đây là phép đo công suất cực đại. Cần xem thêm CPU, in-flight, hàng đợi và thử nhiều mức tải mới xác định được nút thắt chính xác. Failures là 503 mock (terminal một instance 72 lỗi, ba instance 65 lỗi); error rate CSV tương ứng gần 1%. Exit code 1 không làm mất giá trị phép đo.

Nguồn và giới hạn: CSV cuối cùng hiện có 7117/7085 request /ask, 72/64 failures cho một/ba instance, còn terminal khi tắt Locust in 7137/7145 request và 72/65 failures. Hai nguồn không khớp hoàn toàn; có thể CSV là snapshot trước khi các request cuối hoàn tất, nhưng chưa xác minh nguyên nhân. Báo cáo giữ nguyên CSV làm bằng chứng chính, không sửa file đo hoặc thay số để ép khớp terminal. Cả hai lần dùng cùng lệnh 100 users, ramp 10/s, thời gian yêu cầu 2 phút, cùng cấu hình mặc định và không chạy tải web song song.

---

## 6. Kết luận

- 3 điều bạn học được về benchmark & observability:
  1. Tăng concurrency không bảo đảm throughput tăng tuyến tính; cần đọc cùng RPS, percentile và error rate.
  2. Eval phát hiện thiếu kiến thức dù hạ tầng vẫn hoạt động; sửa KB phải kiểm tra regression trên bộ dữ liệu cố định.
  3. Trace_id nối log với span để tìm lỗi, nhưng phải đối chiếu phạm vi đo khi thời gian trace và log bất nhất.
- Nếu đưa agent này lên production thật, bạn sẽ thêm metric / alert nào nữa?

Bổ sung metrics lỗi/latency ở Nginx hoặc synthetic check bên ngoài để thấy 502/504 mà agent chưa ghi nhận; CPU/RAM và queue depth để phân biệt bão hòa tài nguyên với upstream chậm; tỷ lệ câu trả lời đạt chất lượng qua eval định kỳ và phản hồi người dùng; token/cost thực tế theo nhà cung cấp với cảnh báo ngân sách. Tránh label user_id/request_id có cardinality cao, lấy trace_id từ log thay vì label Prometheus.









