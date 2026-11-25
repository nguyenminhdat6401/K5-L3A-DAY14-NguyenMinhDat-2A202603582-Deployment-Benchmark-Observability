# Day 14 — Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns

Các dòng dưới đây thuộc `01-localhost-vs-production/develop/app.py`.

| Vị trí | Vấn đề | Tác động và hướng khắc phục |
|---|---|---|
| Dòng 17 | API key được hardcode | Trong bài đây là key giả; nếu dùng key thật, việc push source có thể làm lộ key. Đọc secret từ biến môi trường hoặc secret manager. |
| Dòng 18 | URL database chứa thông tin đăng nhập hardcode | Gắn cấu hình với một môi trường và có nguy cơ lộ mật khẩu. Đọc DATABASE_URL từ môi trường. |
| Dòng 21–22 | DEBUG và MAX_TOKENS cố định trong code | Muốn đổi cấu hình phải sửa source. Đọc cấu hình từ môi trường và chuyển kiểu dữ liệu phù hợp. |
| Dòng 33–38 | Dùng print, đặc biệt in API key ở dòng 34 | Khó lọc log theo mức độ và làm lộ secret cho người đọc log. Dùng logging, không ghi secret, chuẩn hóa bản ghi bằng JSON hợp lệ. |
| Toàn bộ app; chú thích dòng 42–43 | Thiếu endpoint /health | Nền tảng không có endpoint liveness chuyên dụng để kiểm tra process. Bổ sung GET /health. |
| Dòng 51 | Bind host localhost | Trong container, chỉ lắng nghe loopback sẽ không nhận được kết nối qua interface mạng của container. Bind 0.0.0.0. |
| Dòng 52 | Port 8000 cố định | Không thích ứng với PORT mà nền tảng cấp. Đọc PORT từ môi trường. |
| Dòng 53 | reload=True | Chế độ theo dõi thay đổi source phù hợp phát triển; tăng tác vụ theo dõi và không phù hợp cách chạy production. Tắt reload khi deploy. |

### Exercise 1.2: Chạy bản develop

Sinh viên chạy trong Ubuntu và cung cấp output terminal ngày 25/11/2026.

Lệnh:

```bash
curl -i -X POST "http://localhost:8000/ask?question=Hello"
```

Kết quả thực tế:

```http
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 07:51:09 GMT
server: uvicorn
content-length: 126
content-type: application/json

{"answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

Nhận xét: endpoint nhận POST, tham số question nằm trong query string vì hàm khai báo `question: str` mà không dùng model body. App trả lời bằng mock LLM; việc gọi thành công trên localhost chưa chứng minh app sẵn sàng cho production.

### Exercise 1.3: So sánh develop và production

Bảng sau dựa trên việc đọc `production/app.py` và `production/config.py`.

| Feature | Develop | Production | Vì sao quan trọng? |
|---|---|---|---|
| Config | Giá trị cố định trong source | Settings đọc os.getenv, có chuyển kiểu và validate | Có thể đổi môi trường mà không sửa source. |
| Host / port | localhost:8000 | HOST mặc định 0.0.0.0, PORT từ môi trường | Nhận kết nối vào container và thích ứng port nền tảng. |
| Debug / reload | reload=True | Điều khiển bởi settings.debug, mặc định false | Tách chế độ phát triển khỏi chế độ triển khai. |
| Health check | Không có /health | GET /health trả trạng thái, uptime, version, environment | Cung cấp endpoint liveness cho nền tảng. |
| Readiness | Không có /ready | GET /ready dựa trên cờ is_ready trong lifecycle | Phân biệt process đang sống và app đã hoàn tất khởi tạo. Bản mẫu này chưa kiểm tra Redis thật. |
| Logging | print, có in key | Dùng logging, có event và không in key trong endpoint | Dễ theo dõi request và giảm nguy cơ lộ secret. Formatter mẫu ghép chuỗi có thể tạo JSON không hợp lệ khi message chứa dấu ngoặc kép; Part 6 cần formatter dùng json.dumps. |
| Lifecycle | Không có lifecycle khởi tạo/dọn dẹp | Có lifespan startup và shutdown | Có nơi khởi tạo kết nối, đánh dấu ready và dọn tài nguyên. Cần test SIGTERM thực tế để xác nhận graceful shutdown. |
| Input /ask | question qua query string | Đọc question từ body JSON; thiếu câu hỏi trả 422 | Client phải gửi đúng hợp đồng API của từng bản. |

Kết quả chạy production do sinh viên cung cấp ngày 25/11/2026:

| Request | HTTP thực tế | Quan sát |
|---|---|---|
| GET /health | 200 OK | Body đọc được có status=ok, uptime_seconds=10.9, version=1.0.0, environment=development; phần cuối output bị cắt khi dán. |
| GET /ready | 200 OK | Header có content-length=14; body không hiển thị đầy đủ trong nội dung được dán. |
| POST /ask với JSON question=Hello | 200 OK | Response đầy đủ bên dưới. |

```json
{"question":"Hello","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic.","model":"gpt-4o-mini"}
```

Nhận xét: production ở đây là tên thư mục bản mẫu, không tự đặt ENVIRONMENT=production. Output thực tế vẫn là environment=development theo cấu hình mặc định. Trường model là nhãn cấu hình; câu trả lời vẫn do mock LLM tạo, không phải bằng chứng đã gọi API thật. Chưa kiểm chứng graceful shutdown bằng SIGTERM.

## Part 2: Docker

### Exercise 2.1: Dockerfile cơ bản

Dựa trên `02-docker/develop/Dockerfile`:

1. Base image là `python:3.11`, chứa Python và môi trường hệ điều hành nền để chạy ứng dụng.
2. Working directory là `/app`; các lệnh và đường dẫn tương đối tiếp theo trong image dùng thư mục này.
3. Copy `requirements.txt` và cài dependency trước khi copy source giúp Docker tái sử dụng layer cài thư viện nếu chỉ source thay đổi. Khi requirements thay đổi, layer cài dependency mới cần build lại.
4. `CMD` đặt lệnh hoặc đối số mặc định và có thể bị thay thế bởi lệnh truyền sau tên image trong `docker run`. `ENTRYPOINT` đặt chương trình chính; với exec form, đối số truyền sau tên image thường được nối vào chương trình đó, còn muốn thay chương trình dùng `--entrypoint`. Dockerfile này dùng `CMD ["python", "app.py"]`.

### Exercise 2.2: Build và chạy container develop

Sinh viên chạy từ gốc repo:

```bash
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
docker images my-agent:develop
docker run --rm --name day14-develop -p 8000:8000 my-agent:develop
```

Kết quả build: FINISHED, thời gian hiển thị 173.9 giây. Kích thước hiển thị từ `docker images`:

```text
REPOSITORY   TAG       IMAGE ID       CREATED          SIZE
my-agent     develop   e7bd0c16897a   57 seconds ago   1.67GB
```

Lệnh kiểm tra từ terminal thứ hai:

```bash
curl -i -X POST "http://localhost:8000/ask?question=What%20is%20Docker"
```

Output sinh viên cung cấp:

```text
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 08:08:15 GMT
server: uvicorn
content-length: 103
content-type: application/json
```

Nội dung answer đọc được: `Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!`. Phần body được dán thiếu dấu đóng cuối, nên không ghi lại thành một response JSON nguyên vẹn.

Nhận xét: app đã trả HTTP 200 khi chạy trong container và được truy cập qua cổng 8000 của host. `-p 8000:8000` ánh xạ cổng host vào cổng ứng dụng trong container.

### Exercise 2.3: Multi-stage và so sánh kích thước

Sinh viên đã build production bằng lệnh từ gốc repo:

```bash
docker build -f 02-docker/production/Dockerfile -t my-agent:advanced .
docker images --filter "reference=my-agent:*"
```

Kết quả thực tế:

```text
REPOSITORY   TAG        IMAGE ID       CREATED          SIZE
my-agent     advanced   68f3540c7f22   58 seconds ago   240MB
my-agent     develop    e7bd0c16897a   7 minutes ago    1.67GB
```

| Image | Kích thước hiển thị |
|---|---:|
| Develop (python:3.11, single-stage) | 1.67 GB |
| Production (python:3.11-slim, multi-stage) | 240 MB |

Quy đổi theo đơn vị thập phân: 1.67 GB ≈ 1670 MB. Phần trăm giảm xấp xỉ `(1670 - 240) / 1670 * 100% = 85.6%`. Chênh lệch khoảng 1430 MB; đây là phép tính từ số hiển thị đã làm tròn của Docker.

Giải thích theo Dockerfile production:

- Stage builder dùng python:3.11-slim, cài gcc và libpq-dev, rồi cài dependency vào /root/.local.
- Stage runtime dùng python:3.11-slim mới, chỉ copy dependency đã cài cùng source cần chạy. Công cụ build ở stage builder không được mang sang runtime.
- Image giảm dung lượng nhờ cả base slim và việc tách công cụ build khỏi runtime; không thể quy toàn bộ mức giảm cho multi-stage riêng lẻ vì hai image còn khác base và requirements.
- Runtime khai báo user non-root và HEALTHCHECK. Kích thước đo được 240 MB đáp ứng ngưỡng dưới 500 MB; chưa chạy test runtime image advanced riêng ở bước này.

### Exercise 2.4: Docker Compose

Sinh viên chạy trong `02-docker/production/`:

```bash
touch .env.local
docker compose -p k5-day14-docker up -d --build
docker compose -p k5-day14-docker ps
```

Kết quả ps do sinh viên cung cấp:

| Service | Container | Trạng thái | Cổng |
|---|---|---|---|
| agent | k5-day14-docker-agent-1 | Up (healthy) | 8000/tcp nội bộ |
| nginx | k5-day14-docker-nginx-1 | Up | Host 80 → container 80; host 443 → container 443 |
| qdrant | k5-day14-docker-qdrant-1 | Up (healthy) | 6333–6334/tcp nội bộ |
| redis | k5-day14-docker-redis-1 | Up (healthy) | 6379/tcp nội bộ |

Sơ đồ cấu hình stack:

```text
Client → localhost:80 → Nginx → agent:8000
                                 │
                   Cấu hình kết nối trong mạng internal:
                   REDIS_URL → redis:6379
                   QDRANT_URL → qdrant:6333
```

Nginx reverse proxy request tới agent. Các service dùng chung mạng Docker `internal`, phân giải tên service bằng DNS nội bộ. Chỉ Nginx publish cổng ra host; agent, Redis và Qdrant không publish cổng trực tiếp. Redis và Qdrant có volume lưu dữ liệu. Compose chờ Redis và Qdrant healthy trước khi khởi động agent. Đây là mạng bridge tên internal, không phải khai báo Docker network `internal: true`.

Lưu ý: cấu hình cung cấp địa chỉ Redis/Qdrant, nhưng code `main.py` mẫu Part 2 chưa sử dụng hai service này để xử lý /ask. Kết quả gọi API không chứng minh đã truy vấn database. Cổng 443 được ánh xạ trong Compose nhưng Nginx hiện chỉ cấu hình listen 80; chưa có HTTPS/TLS.

Kiểm tra health qua Nginx:

```bash
curl -i http://localhost/health
```

```http
HTTP/1.1 200 OK
Server: nginx
Date: Wed, 25 Nov 2026 08:16:57 GMT
Content-Type: application/json
Content-Length: 96
Connection: keep-alive
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block

{"status":"ok","uptime_seconds":56.7,"version":"2.0.0","timestamp":"2026-11-25T08:16:57.308633"}
```

Kiểm tra agent qua Nginx:

```bash
curl -i -X POST http://localhost/ask -H "Content-Type: application/json" -d '{"question":"Explain microservices"}'
```

```http
HTTP/1.1 200 OK
Server: nginx
Date: Wed, 25 Nov 2026 08:17:01 GMT
Content-Type: application/json
Content-Length: 95
Connection: keep-alive
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block

{"answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}
```

Kết luận từ lần chạy: cả /health và POST /ask qua cổng 80 đều trả 200; header Server: nginx cùng body của agent xác nhận luồng reverse proxy hoạt động. Lần chạy này có một container agent; chưa kiểm chứng phân phối tải nhiều replica.

## Part 3: Cloud Deployment

### Exercise 3.1/3.2: Deploy agent Part 6

Đã deploy agent trong 06-lab-complete lên Render, không deploy app mẫu Part 3. URL public: https://lab14-agent.onrender.com. Web service lab14-agent và Key Value lab14-redis đều dùng Free compute, cùng region Oregon. Redis-compatible datastore nối qua private URL; API key là secret trong môi trường Render.

Kiểm tra thực tế ngày 25/11/2026 sau khi deployment báo Live: GET /health → 200, GET /ready → 200, POST /ask thiếu key → 401, POST /ask key đúng → 200. Xem body và lệnh tái hiện trong DEPLOYMENT.md. Ba ảnh deployment đã lưu trong screenshots/dashboard.png, running.png và test.png; test.png đã kiểm tra trực quan không có API key.

Railway đã được thử nhưng workspace bị restricted do unusual activity; deployment Redis bị Blocked dù còn trial credit. Không nâng cấp gói, không dùng tài khoản khác để né hạn chế. Render là nền tảng thay thế được đề bài cho phép.

### So sánh railway.toml và render.yaml

| Nội dung | Railway | Render |
|---|---|---|
| Cấu trúc | TOML với [build] và [deploy] | YAML với danh sách services và envVars |
| Build | builder=DOCKERFILE, dockerfilePath=Dockerfile | runtime=docker, rootDir=06-lab-complete, dockerfilePath=./Dockerfile |
| Health | healthcheckPath=/health | healthCheckPath=/health |
| Secret | Đặt AGENT_API_KEY và Redis reference trong môi trường nền tảng | generateValue hoặc sync:false trong Blueprint; lần deploy thực tế dùng dashboard Generate và URL private |
| Tài nguyên | Service và Redis tạo riêng trong project | Web service và Key Value cùng region; file YAML hiện mô tả web service, datastore tạo riêng |

Hai file cùng mô tả cách build/chạy agent nhưng có schema và cách khai báo tài nguyên khác nhau. Lần deploy Render này tạo service qua dashboard từ public repo, không áp dụng Blueprint tự động. Railway CLI thực tế cảnh báo Config as Code sẽ hết hỗ trợ sau 01/12/2026; chưa migrate vì đường deploy đã chuyển sang Render.

### Exercise 3.3: Pipeline Cloud Run

1. cloudbuild.yaml chạy cài requirements và pytest trước bước build.
2. Docker build tạo image có tag theo COMMIT_SHA và latest, tái sử dụng cache khi có thể.
3. Push image lên registry, rồi gcloud deploy revision dùng image theo commit lên Cloud Run ở asia-southeast1.
4. service.yaml mô tả cấu hình instance/concurrency, tài nguyên, port, secret từ Secret Manager và các probe /health, /ready. Đây là đọc cấu hình mẫu; không deploy GCP trong bài này.

## Part 4: API Security

### Exercise 4.1: API Key authentication

Trong `04-api-gateway/develop/app.py`, APIKeyHeader đọc header X-API-Key với auto_error=False. Hàm verify_api_key kiểm tra thiếu key (401) và key sai (403 ở bản mẫu này). Endpoint /ask dùng Depends(verify_api_key), nên việc kiểm tra chạy trước logic trả lời. Giá trị mong đợi lấy từ AGENT_API_KEY lúc khởi động app.

Để đổi key, cập nhật AGENT_API_KEY trong môi trường triển khai rồi restart/redeploy app; cập nhật key phía client. Bản mẫu chỉ hỗ trợ một key, không có giai đoạn chấp nhận đồng thời key cũ và mới.

Sinh viên chạy:

```bash
AGENT_API_KEY=secret-key-123 python app.py
```

`secret-key-123` là key minh họa dùng cho app local, không phải key của nhà cung cấp LLM. App vẫn dùng mock LLM.

Test thiếu key:

```bash
curl -i -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"question":"Hello"}'
```

```http
HTTP/1.1 401 Unauthorized
date: Wed, 25 Nov 2026 08:22:15 GMT
server: uvicorn
content-length: 67
content-type: application/json
```

Body lỗi không hiển thị trong output sinh viên dán; chỉ xác nhận mã 401 thực tế.

Test có key đúng:

```bash
curl -i -X POST http://localhost:8000/ask -H "X-API-Key: secret-key-123" -H "Content-Type: application/json" -d '{"question":"Hello"}'
```

```http
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 08:22:27 GMT
server: uvicorn
content-length: 122
content-type: application/json

{"question":"Hello","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận."}
```

Nhận xét: thiếu key bị chặn, key đúng được phép gọi. Nội dung câu trả lời mock nhắc tới cloud không chứng minh app đã deploy; lần test này chạy localhost. Trường hợp key sai chưa được test thực tế. Part 6 yêu cầu cả key thiếu và key sai đều trả 401, khác mã 403 của bản mẫu develop.

### Exercise 4.2: JWT authentication

Sinh viên lấy access token từ POST /auth/token với tài khoản demo student, lưu vào biến TOKEN và gọi endpoint bằng Authorization: Bearer $TOKEN. Token không được ghi vào bài.

```bash
curl -i -X POST http://localhost:8000/ask -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"question":"Explain JWT"}'
```

Kết quả thực tế:

```http
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 08:25:00 GMT
server: uvicorn
content-length: 192
content-type: application/json
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin

{"question":"Explain JWT","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.","usage":{"requests_remaining":9,"budget_remaining_usd":1.9e-05}}
```

Flow: client gửi thông tin đăng nhập đến /auth/token, nhận token có chữ ký; các request tiếp theo gửi token qua Bearer header để server xác thực và lấy danh tính/role. Không gửi lại mật khẩu ở từng request /ask.

Lưu ý code mẫu: trường usage.budget_remaining_usd trong response /ask đang được gán usage.total_cost_usd, nên giá trị 1.9e-05 thực chất là chi phí tích lũy, không phải ngân sách còn lại. Endpoint /me/usage tính phần ngân sách còn lại riêng. Không sửa code mẫu ở bước thực hành này.

### Exercise 4.3: Rate limiting

Thuật toán mẫu là sliding window lưu timestamp theo user trong RAM. User thường giới hạn 10 request/60 giây; admin dùng limiter riêng 100 request/60 giây, không phải bỏ giới hạn hoàn toàn. Trong production cần state dùng chung trong Redis để các worker/instance cùng thấy hạn mức.

Sinh viên chạy:

```bash
for i in {1..20}; do
  printf '\nRequest %s\n' "$i"
  curl -i -X POST http://localhost:8000/ask \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"question":"Test rate limit"}'
  printf '\n'
done
```

Kết quả thực tế ngày 25/11/2026:

- Request Explain JWT lúc 08:25:00 GMT trả 200, requests_remaining=9.
- Vòng lặp chạy lúc 08:25:30 GMT: request 1–9 trả 200; request 10–20 trả 429 (9 thành công, 11 bị giới hạn).
- Request trước vòng lặp vẫn thuộc cửa sổ 60 giây, nên request số 10 trong vòng lặp đã là lần gọi thứ 11 tính cả request trước đó.

Một response 429 thực tế, từ request số 10:

```http
HTTP/1.1 429 Too Many Requests
date: Wed, 25 Nov 2026 08:25:30 GMT
server: uvicorn
x-ratelimit-limit: 10
x-ratelimit-remaining: 0
x-ratelimit-reset: 1795595191
retry-after: 30
content-length: 98
content-type: application/json
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":30}}
```

Retry-After: 30 hướng dẫn client chờ trước khi thử lại. Kết quả xác nhận giới hạn có hiệu lực trong một process; chưa kiểm chứng state qua restart hoặc nhiều worker ở Part 4.

### Exercise 4.4: Cost guard

Phân tích bản mẫu `04-api-gateway/production/cost_guard.py`:

- Trước khi gọi LLM, check_budget kiểm tra tổng chi phí theo user và tổng service.
- Sau khi gọi LLM, record_usage cộng input/output token và tính chi phí theo hai đơn giá trong code.
- Budget mặc định của mẫu là 1 USD/ngày/user và 10 USD/ngày toàn service. Vượt budget user trả 402; vượt budget toàn service trả 503.
- Mẫu dùng dictionary trong RAM; phần record theo user đổi sang ngày mới khi truy cập. Biến _global_today được khai báo nhưng chưa có logic reset _global_cost theo ngày trong các hàm hiện tại.
- Cost ở đây là số ước lượng từ mock, không phải hóa đơn nhà cung cấp.

Cách triển khai yêu cầu ví dụ 10 USD/tháng với Redis:

1. Dùng key budget theo user và tháng, ví dụ budget:<user_id>:2026-11; xác định timezone thống nhất cho kỳ ngân sách.
2. Đọc chi phí đã dùng; kiểm tra chi phí đã dùng cộng chi phí dự kiến có vượt 10 USD không.
3. Dùng thao tác nguyên tử (ví dụ Lua script Redis) để kiểm tra và giữ chỗ chi phí, tránh nhiều request đồng thời cùng vượt kiểm tra.
4. Sau khi có usage thực tế, điều chỉnh phần giữ chỗ; giải phóng phần chưa dùng hoặc khi lời gọi thất bại theo chính sách rõ ràng.
5. Dùng key theo tháng và TTL để dọn dữ liệu cũ; tháng mới dùng key mới. State được chia sẻ giữa worker và còn sau khi restart app.

Rate limit bảo vệ tần suất, còn cost guard bảo vệ ngân sách; một request có thể tốn nhiều token nên cần cả hai. Phần này là giải thích thiết kế theo checkpoint K5; chưa chạy test hết budget 402 và chưa triển khai Redis cho mẫu Part 4. Logic Redis bắt buộc sẽ được hoàn thiện ở Part 6.
## Part 5: Scaling & Reliability

### Exercise 5.1: Health và readiness

Sinh viên chạy bản có sẵn trong `05-scaling-reliability/develop/`:

```bash
python -m pip install -r requirements.txt
python app.py
```

Kết quả thực tế ngày 25/11/2026:

| Endpoint | HTTP | Nội dung quan sát được |
|---|---|---|
| GET /health | 200 OK | status=ok, uptime_seconds=7.0, version=1.0.0, environment=development; checks.memory.status=ok. Phần cuối body bị cắt khi dán nên không ghi số used_percent. |
| GET /ready | 200 OK | Body đầy đủ bên dưới. |

```bash
curl -i http://localhost:8000/health
curl -i http://localhost:8000/ready
```

Response /ready:

```http
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 08:28:40 GMT
server: uvicorn
content-length: 37
content-type: application/json

{"ready":true,"in_flight_requests":1}
```

Liveness cho biết process còn đáp ứng; readiness cho biết instance đã khởi tạo xong và có thể nhận traffic. Code mẫu /ready kiểm tra cờ _is_ready, không ping Redis; Part 6 cần kiểm tra Redis thực tế để trả 503 khi mất kết nối. Middleware đếm request trước khi xử lý rồi giảm sau khi hoàn tất, nên chính request /ready làm in_flight_requests bằng 1 dù không có request khác.

### Exercise 5.2: Graceful shutdown

Bản mẫu có lifespan startup/shutdown và theo dõi số request đang xử lý. Khi shutdown cần hoàn thành request đang chạy, dọn tài nguyên và thoát; Uvicorn xử lý signal và điều phối quá trình này. Kiểm tra bổ sung bằng subprocess thật: request POST /ask?question=LongTask đang chạy, gửi SIGTERM sau 50 ms; request trả 200 và process exit 0. Lưu reports/part5_graceful_shutdown.json.

### Exercise 5.3–5.5: Stateless, load balancing và history

Sinh viên chạy stack trong `05-scaling-reliability/production/`:

```bash
touch .env.local
docker compose -p k5-day14-scaling up -d --build --scale agent=3
docker compose -p k5-day14-scaling ps
python3 test_stateless.py
```

Sự cố thực hành: lần build đầu gặp Docker Hub 429 khi lấy metadata python:3.11-slim; lần chạy sau build thành công (69.6 giây). Nginx ban đầu không bind được cổng 8080 do utc-campus-app-1 đang publish 127.0.0.1:8080. Sau khi hướng dẫn tạm dừng container chiếm cổng và khởi động lại stack, sinh viên cung cấp ps và test thành công bên dưới. Chưa có bằng chứng đã bật lại app cũ.

Trạng thái thực tế: agent-1, agent-2, agent-3 và Redis đều Up (healthy); Nginx Up và publish 8080:80.

Kết quả test:

```text
Session ID: 851b843d-b7d1-4901-82b3-d00364022bd1
Request 1: instance-b8b563 — What is Docker?
Request 2: instance-098e43 — Why do we need containers?
Request 3: instance-5427f7 — What is Kubernetes?
Request 4: instance-b8b563 — How does load balancing work?
Request 5: instance-098e43 — What is Redis used for?
Total requests: 5
Instances used: {'instance-b8b563', 'instance-098e43', 'instance-5427f7'}
All requests served despite different instances!
Total messages: 10
Session history preserved across all instances via Redis!
```

Giải thích:

- Nginx phân phối 5 request tới đủ 3 instance. Cùng session vẫn có đủ 5 message user và 5 message assistant khi đọc history.
- Mỗi process có bộ nhớ riêng; nếu lưu history trong dictionary cục bộ thì instance khác không thấy đầy đủ các lượt trước. Lưu state trong Redis dùng chung cho phép các instance xử lý cùng session nhất quán trong kịch bản tuần tự này.
- Stateless ở đây nghĩa là agent không phụ thuộc state cục bộ cho session; toàn hệ thống vẫn có state trong Redis.
- Endpoint thực tế là POST /chat qua cổng 8080; test_stateless.py tạo session, gửi 5 câu hỏi rồi đọc history. Script không tự kill instance.
- Lần test này chứng minh phân phối request và chia sẻ history; chưa chứng minh failover khi kill instance, phục hồi Redis sau restart hoặc graceful shutdown lúc có request đang chạy.

## Part 6: Production Readiness

### Baseline trước khi hoàn thiện

Sinh viên chạy `python check_production_ready.py --static-only` trong Ubuntu ngày 25/11/2026: Result 0/12 tiêu chí đạt, 5/24 checks passed. Runtime/Docker chưa chạy; bản khung còn thiếu các thành phần bắt buộc.

### Phần hoàn thiện code

Đã bổ sung: config từ môi trường và .env, auth key thiếu/sai trả 401, health độc lập Redis, readiness ping Redis, rate limit sliding window 60 giây trong Redis bằng Lua nguyên tử dùng thời gian Redis, chi phí tích lũy theo ngày UTC và API credential trong Redis, logging bằng json.dumps, lifecycle cleanup để Uvicorn xử lý SIGTERM, Docker multi-stage slim/non-root/HEALTHCHECK với exec và PORT, Compose agent + Redis có volume, .dockerignore và railway.toml.

Không chỉnh sửa script chấm hoặc mock LLM. Token được ước lượng bằng ceil(số byte UTF-8 / 4), tối thiểu 1; không phải usage thật từ nhà cung cấp. Cost guard kiểm tra tổng đã dùng trước lời gọi rồi cộng chi phí sau; nhiều request đang chạy có thể vượt budget trước khi bị chặn ở request tiếp theo. Production có ngân sách cứng cần cơ chế giữ chỗ trước lời gọi. Rate/budget Redis keys dùng hash của API key, không lưu API key nguyên văn trong tên key.

### Kết quả kiểm tra đầy đủ sau sửa

Sinh viên chạy `python check_production_ready.py` trên Ubuntu ngày 25/11/2026, không dùng --static-only hoặc --skip-docker. Output do sinh viên cung cấp:

```text
📋 Checklist Deliverable
   ✅ Dockerfile (multi-stage, < 500 MB)
   ✅ docker-compose.yml (agent + redis)
   ✅ .dockerignore
   ✅ Health check endpoint (GET /health)
   ✅ Readiness endpoint (GET /ready)
   ✅ API Key authentication
   ✅ Rate limiting
   ✅ Cost guard
   ✅ Config từ environment variables
   ✅ Structured logging
   ✅ Graceful shutdown
   ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
Result: 12/12 tiêu chí đạt · 41/41 checks passed
🎉 PASS 12/12 — PRODUCTION READY! Deploy nào!
```

Các bằng chứng runtime/Docker từ cùng lần chạy:

| Kiểm tra | Kết quả thực tế |
|---|---|
| Docker build | Thành công trong 24 giây |
| Image Part 6 | 63 MB theo cách hiển thị của script (script chia byte cho 1024²) |
| Container /health | 200 |
| App hai worker | /health và /ready 200 |
| Redis mất kết nối | /ready 503, /health vẫn 200 |
| Auth | Thiếu/sai key 401, key đúng 200 |
| Rate limit từ env | RATE_LIMIT_PER_MINUTE=5, trả 429 sau 5 request thành công |
| State sau restart app | Vẫn trả 429 |
| Cost guard budget nhỏ | Trả 402 ở request thứ 2 |
| Logging | 17 dòng JSON hợp lệ |
| SIGTERM khi có request | Request vẫn 200, process thoát exit code 0 |
| docker stop | Exit code 0 trong 0.8 giây |
| Config deploy | Railway builder và healthcheckPath=/health hợp lệ; CMD dùng PORT |

Giới hạn: script đã xác nhận đủ checklist local, nhưng chưa có URL public thực tế. Tiêu chí Public URL ready trong lần chạy này kiểm tra cấu hình triển khai, không chứng minh agent đã deploy. Cần làm CP6 để hoàn thành bằng chứng Deployment.

## AI log

### 25/11/2026 — Hỗ trợ Part 1

- Yêu cầu: đọc repo Day 14, hướng dẫn thao tác; sinh viên chạy terminal, AI soạn phần trả lời.
- Hỗ trợ nhận được: hướng dẫn chạy bản develop, phân tích anti-pattern theo dòng code, lập bảng so sánh với production, ghi nhận output curl do sinh viên cung cấp.
- Tự chạy và kiểm tra: sinh viên khởi động app develop, mở trang chủ và chạy POST /ask?question=Hello; kết quả HTTP 200 và answer từ mock LLM như mục Exercise 1.2.
- Tự sửa/diễn giải: chưa ghi nhận chỉnh sửa của sinh viên; cần đọc lại các nhận xét và giải thích được bằng lời của mình. Sinh viên đã chạy bản production và cung cấp HTTP 200 cho /health, /ready, POST /ask; AI ghi kết quả và lưu ý giới hạn của output bị cắt.


### 25/11/2026 — Hỗ trợ Part 2 (develop)

- Yêu cầu: AI soạn phần bài viết; sinh viên tự chạy các lệnh Docker trong Ubuntu.
- Hỗ trợ nhận được: hướng dẫn bật Docker Desktop WSL integration, xử lý quyền socket, giải thích Dockerfile và ghi lại bằng chứng build/test.
- Tự chạy và kiểm tra: sinh viên build thành công my-agent:develop, đo kích thước 1.67 GB, chạy container và cung cấp HTTP 200 cho POST /ask với câu hỏi What is Docker.
- Cập nhật: sinh viên đã build image production advanced (68f3540c7f22), đo 240 MB so với develop 1.67 GB. AI tính mức giảm xấp xỉ 85.6% từ số hiển thị đã làm tròn và giải thích hai stage. Stack Compose chưa chạy kiểm chứng. Sinh viên cần đọc và giải thích được câu trả lời Exercise 2.1.


### 25/11/2026 — Hỗ trợ Part 2 (Compose)

- Yêu cầu: tiếp tục ghi bài từ kết quả terminal sinh viên chạy.
- Hỗ trợ nhận được: giải thích các service, sơ đồ giao tiếp, ghi output ps và hai response HTTP qua Nginx.
- Tự chạy và kiểm tra: sinh viên bật stack project k5-day14-docker, xác nhận agent/Redis/Qdrant healthy và Nginx Up; GET /health và POST /ask đều 200 qua localhost:80.
- Giới hạn: chưa test HTTPS hoặc nhiều replica; API mẫu Part 2 không sử dụng Redis/Qdrant trong logic /ask.

### 25/11/2026 — Hỗ trợ Part 4 (API key)

- Yêu cầu: hướng dẫn thực hành và ghi câu trả lời từ output do sinh viên tự chạy.
- Hỗ trợ nhận được: giải thích API key local khác key nhà cung cấp LLM, phân tích verify_api_key và cách đổi key; ghi kết quả kiểm tra.
- Tự chạy và kiểm tra: sinh viên chạy app develop với key demo, xác nhận POST /ask thiếu key trả 401, có key đúng trả 200.
- Chưa kiểm chứng: JWT, rate limit và cost guard; không coi nội dung mock nhắc tới cloud là bằng chứng deploy.

### 25/11/2026 — Hỗ trợ Part 4 (JWT, rate limit, cost guard)

- Hỗ trợ nhận được: AI đọc output terminal được dán, ghi response JWT 200 và rate limit 429, giải thích sliding window và thiết kế cost guard dùng Redis; chỉ ra tên trường budget_remaining_usd không khớp giá trị trong /ask mẫu.
- Tự chạy và kiểm tra: sinh viên lấy JWT, gọi Explain JWT thành công, chạy 20 request; 9 request đầu vòng lặp trả 200, 11 request sau trả 429 vì đã có một request trước đó trong cùng cửa sổ.
- Giới hạn: chưa test budget 402 hoặc rate limit qua restart/multiple worker; không đưa token vào file bài nộp. Sinh viên cần đọc và giải thích được phần thiết kế Redis.

### 25/11/2026 — Hỗ trợ Part 5 (health/readiness)

- Hỗ trợ nhận được: hướng dẫn chạy bản develop, ghi mã HTTP và body /ready từ output sinh viên, giải thích liveness/readiness và bộ đếm request.
- Tự chạy và kiểm tra: sinh viên chạy app mẫu và xác nhận GET /health, GET /ready đều trả 200; /ready có ready=true và in_flight_requests=1.
- Chưa kiểm chứng: graceful shutdown với request đang chạy, nhiều instance và session history trong Redis.

### 25/11/2026 — Hỗ trợ Part 5 (scaling/stateless)

- Hỗ trợ nhận được: AI hướng dẫn xử lý lỗi Docker Hub 429 và xung đột cổng 8080, giải thích test stateless và ghi bằng chứng từ output sinh viên.
- Tự chạy và kiểm tra: sinh viên chạy stack có ba agent healthy, Redis healthy và Nginx; script gửi 5 request qua ba instance và đọc đủ 10 message của session.
- Giới hạn: chưa test kill instance, Redis restart hoặc SIGTERM khi có request đang xử lý. App utc-campus-app-1 đã được hướng dẫn tạm dừng để giải phóng 8080; cần bật lại khi không còn dùng cổng cho lab.

### 25/11/2026 — Hỗ trợ Part 6 (hoàn thiện bản khung)

- Yêu cầu: AI sửa code, sinh viên tự chạy terminal và kiểm tra.
- Hỗ trợ nhận được: AI hoàn thiện các TODO trong sáu module app, Dockerfile, Compose, .dockerignore, .env.example và railway.toml; script chấm được giữ nguyên.
- Tự chạy và kiểm tra: sinh viên cung cấp baseline static-only 0/12 trước sửa. Chưa có kết quả chạy sau sửa; cần chạy đầy đủ, xem từng lỗi và giải thích được logic.
- Giới hạn: chưa deploy, chưa đo image Part 6, chi phí là ước lượng mock và chưa có cơ chế giữ chỗ ngân sách cho các request đồng thời.

### 25/11/2026 — Kiểm chứng Part 6 sau sửa

- Sinh viên tự chạy script đầy đủ trên Ubuntu với Docker; cung cấp kết quả PASS 12/12, 41/41 checks passed.
- AI ghi Checklist Deliverable và các số đo runtime/Docker vào bài, không tự tạo số đo.
- Đã kiểm chứng local; URL public và Redis cloud chưa được tạo/kiểm tra. Các giới hạn về ước lượng token và ngân sách đồng thời đã mô tả vẫn áp dụng.

### 25/11/2026 — Deploy Render và kiểm chứng URL public

- Sinh viên yêu cầu AI tự deploy, đăng nhập Render trực tiếp rồi trả quyền điều khiển.
- AI tạo Redis-compatible Key Value miễn phí, cấu hình web service Docker miễn phí, tạo API key bằng Render Generate, nối private Redis URL, commit/push riêng 12 file Part 6 (21d557e), deploy và kiểm chứng 4 HTTP request public.
- Kết quả: health=200, ready=200, ask thiếu key=401, ask key đúng=200. Không lưu API key vào bài hoặc repo; ảnh screenshot còn cần bổ sung.

### 25/11/2026 — Part 7: concurrency benchmark

- Sinh viên tự khởi động v1:8001 và v2:8002, chạy load_test.py với 300 request ở concurrency 1, 10, 50, 100; bốn file reports/load_v2_c*.json được lưu.
- AI đọc file JSON trên máy và điền bảng 2.1, SLO và nhận xét vào BENCHMARK_REPORT.md. Mức 1/10 PASS, mức 50 FAIL error rate, mức 100 FAIL p95; không sửa số đo hoặc chạy lại để chọn kết quả đẹp.
- Chưa hoàn thành tail latency, eval và observability stack.

### 25/11/2026 — Part 7: tail latency

- Sinh viên khởi động lại v2 lần lượt với MOCK_SLOW_RATE 0, 0.03, 0.1 và tự chạy mỗi lần 300 request, concurrency 20, lưu ba reports/load_v2_slow_*.json.
- AI đọc ba file JSON, điền bảng 2.2 và giải thích p99 nhạy với lỗi đuôi hiếm, p95 tăng khi nhóm request chậm đủ lớn; giữ nguyên kết quả SLO FAIL p95 ở mức 0.1.
- Eval v1/v2 và quan sát Docker stack chưa hoàn thành.

### 25/11/2026 — Part 7: eval baseline và bổ sung knowledge base

- Sinh viên chạy eval v1 và v2, lưu eval_v1.json và eval_v2.json. V1=1/23, v2=21/23, 20 câu cải thiện và không regression.
- AI đọc report và bộ câu hỏi ở chế độ chỉ đọc, bổ sung tài liệu JWT/API key và Kubernetes HPA vào KNOWLEDGE_BASE trong develop/utils/mock_llm.py và production/utils/mock_llm.py. Không sửa golden_dataset.jsonl, script eval hoặc report baseline.
- Đã điền số đo v1/v2 vào báo cáo; sinh viên cần restart v2 và chạy gate 100% để xác nhận bản sửa. Chưa khẳng định đạt 23/23 trước lần chạy thực tế.

### 25/11/2026 — Part 7: xác nhận eval sau sửa

- Sinh viên restart v2, chạy --min-accuracy 1.0 --baseline reports/eval_v2.json --out reports/eval_v2_fixed.json.
- File JSON thực tế có 23/23, accuracy 1.0, errors 0, avg tokens 123.7, cost 0.000877 USD, cost/câu đúng 0.00003815 USD, p95 279.7 ms. Output cho thấy hai câu cải thiện, 0 regression, gate PASS.
- AI ghi các số vào báo cáo và giải thích step CI dựa trên exit code để chặn merge. Chưa chạy workflow GitHub Actions thực tế; quan sát stack Docker còn phải làm.

### 25/11/2026 — Sửa lỗi khởi động agent observability

- Sinh viên build stack Part 7; log agent lặp ModuleNotFoundError: No module named uvicorn.
- Nguyên nhân trong Dockerfile: user agent có home /app, nhưng dependency pip --user được copy sang /home/agent/.local; PATH tìm được executable ở đó trong khi Python user-site không dùng cùng vị trí.
- AI sửa riêng Dockerfile production của Part 7 để builder cài vào virtualenv /opt/venv, runtime copy đúng cùng đường dẫn và PATH trỏ /opt/venv/bin. Giữ non-root, HEALTHCHECK và một worker/container để metrics chính xác theo process.
- Chờ sinh viên rebuild và kiểm chứng; chưa ghi stack đã hoạt động thành công.

### 25/11/2026 — Part 7: đối chiếu trace và log

- Sinh viên tạo tải Locust và cung cấp ảnh Grafana có tải, trace Jaeger 4d5005297991e0ac3f82b52e67c6975c, cùng hai log JSON khớp trace_id.
- AI ghi dữ liệu vào phần 4.3 của báo cáo và phát hiện bất nhất: Jaeger ~7.2 s, log HTTP 220.8 ms, mock llm_ms 193.2. Không tự thay số hoặc khẳng định nguyên nhân chưa được kiểm chứng.
- Trace lỗi và hai alert cùng firing chưa hoàn thành.

### 25/11/2026 — Part 7: trace lỗi upstream

- Sinh viên cung cấp ảnh span chat có exception mock 503 và hai log JSON cùng trace_id e9c48087b47688ca92ac72166b0d7cbb; HTTP log status=503, ms=97.0, Jaeger tổng 97.9 ms.
- AI ghi bằng chứng và giải thích đường đi exception → span ERROR → HTTP 503 trong báo cáo. Không có API key trong bằng chứng được ghi.
- Hai alert cùng firing và benchmark scale 1/3 còn phải thực hiện.

### 25/11/2026 — Part 7: alert firing và khôi phục cấu hình

- Sinh viên áp dụng fault injection error=0.2/slow=0.3 lúc 17:15:03 +0700, cung cấp ảnh ba alert firing và giờ quan sát 17:18:34 +0700.
- AI ghi khoảng quan sát 211 giây, không coi là thời gian firing đầu tiên của từng alert. Đã trả hai biến về mặc định error=0.01/slow=0.03 trong .env, giữ nguyên API key, chưa push .env.
- Chờ sinh viên áp dụng lại Compose, tắt tải web và chạy benchmark headless scale 1/3. Các thí nghiệm C/D/E riêng chưa có bằng chứng.

### 25/11/2026 — Part 7: benchmark scaling và gom bằng chứng

- Sinh viên chạy headless Locust 100 users, ramp 10/s, 2 phút cho 1 và 3 instance, tải web đã được hướng dẫn dừng. AI đọc file CSV và ghi riêng hàng /ask vào báo cáo.
- CSV có snapshot khác thống kê shutdown terminal; AI ghi rõ khác biệt và dùng file CSV làm nguồn chính, không sửa dữ liệu đo.
- AI copy JSON/CSV ra reports/ và benchmark-results/ ở gốc repo; tạo screenshots/ và chép các ảnh minh chứng sinh viên đã gửi nếu chưa tồn tại. Chưa thấy ảnh test.png được cung cấp trong chat.
- Các thí nghiệm C/D/E riêng còn chưa chạy; phần trả lời lý thuyết và kết luận do AI soạn cần sinh viên đọc, kiểm chứng và giải thích được.

### 25/11/2026 — Part 7: model lớn

- Sinh viên chạy model mock-llm-large và gửi ảnh Grafana, Prometheus. AI ghi p95=705.94 ms, burn rate=26.0183 USD/giờ mock, LLMCostBurnRateHigh FIRING.
- Active Since cho thấy alert active từ trước; không tự suy ra thời gian firing kể từ đổi model. Hai ảnh được lưu riêng, không ghi đè ảnh ba alert firing.
- Thí nghiệm pause instance (D) và đổi v1 (E) chưa được kiểm chứng.


### 25/11/2026 — Hoàn tất các bước còn lại theo yêu cầu sinh viên

- AI tự chạy thí nghiệm D: AgentInstanceDown được quan sát FIRING sau elapsed monotonic 50.12 giây, tự unpause container, lưu raw JSON; ghi rõ khác biệt clock timestamp/monotonic.
- AI chạy thí nghiệm E qua stack v1: 1/23, eval exit1, không có alert chất lượng; lưu eval và alert snapshot. Khôi phục v2/model nhỏ sau test.
- AI bổ sung Histogram độ dài câu hỏi vào develop/production theo Exercise7.1; smoke test count1/sum6 PASS, production có dữ liệu. promtool alert unit tests SUCCESS, /metrics qua Nginx404.
- AI kiểm chứng bổ sung Part5 shutdown: request200, exit0; điền câu hỏi metrics/dashboard, bảng chaos và kết luận; ghi số đo theo đúng nguồn.
- test.png hiện có và được kiểm tra trực quan: URL public, bốn mã200/200/401/200, không hiển thị API key. Secret scan trước push được ghi trong bước kiểm tra cuối.
- Sinh viên dùng AI để triển khai/sửa code và soạn báo cáo; cần tự đọc, hiểu và giải thích được code cùng số đo khi Lab Coach hỏi. Không tự nhận các lần chạy bổ sung của AI là thao tác do sinh viên trực tiếp gõ.
