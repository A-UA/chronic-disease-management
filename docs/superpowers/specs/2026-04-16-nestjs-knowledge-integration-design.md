# NestJS Backend Knowledge Base Integration (Sub-project 2)

## 背景 (Context)
需要在 NestJS/TypeScript 生态下补齐与 Python Agent 相连的 RAG 知识库上传链路。因 NestJS 核心路由系统默认走纯净微服务 TCP (`@nestjs/microservices`)，而在该架构下传递臃肿大口径的 Multipart 序列化 Buffer 会造成内存及 JSON 组装的严重性能灾难。

因此采用**胖网关、瘦微服务 (Gateway-Heavy)** 方案对这一链路实现特化：由于文件存储(MinIO)及向量化注入(Agent)都需要原始的二进制表单结构而无过多定制化业务校验结构，网关直接承接 IO 处理；只在生成状态结束点，将低成本结构透传后台记账落地。 

## 系统架构与职责 (Architecture)
1. **API Gateway (`gateway`)**：
   - 使用 `@nestjs/platform-express` 与 `@types/multer` 提供的 `FileInterceptor` 直接在 HTTP 入口接收。
   - 本地内建封装 `MinioClient`，将接到的二进制原生 `File` 推走获得链接。
   - 使用 `@nestjs/axios` 以 `FormData` 模式再度包装二进制提交到 `localhost:8000/internal/knowledge/parse`，等待切分完毕。
   - 提取上环节响应结果（`kbId`, `url`, `chunkCount`）组装为安全干净的数据，推往 `ClientProxy` 的 TCP 管线通知业务节点落库。
2. **微服务 (`patient-service`)**：
   - 监听特定的微服务 MessagePattern（如 `document_create_sync`）。
   - 不涉及任何物理文件的处理，职责单纯回归至 DB Record 的 CURD（包含利用 `TypeORM` 更新数据库中 `KnowledgeBase` 及 `Document` 两张表）。
3. **共享库 (`shared`)**：
   - 常规扩展消息载体接口声明及常量。

## 详细设计 (Detailed Design)

### 1. 外部依赖 (Dependencies)
- **网关层 (`gateway`)** 需额外补充：
  - `minio` (8.5.x)
  - `@nestjs/axios` 及前置需要的 `axios`, `form-data`
  - `@types/multer`
- 由于网关代理了大部分 IO 获取，业务微服务侧 `patient-service` 不必追加上述包。

### 2. 共享接口层 (`shared`)
- 规划 TCP 请求模型：
  * `{ cmd: 'kb_create' }` 
  * `{ cmd: 'kb_find_all' }`
  * `{ cmd: 'document_create_sync' }`：Payload 包含 { Identity, kbId, fileName, fileType, fileSize, minioUrl, chunkCount, status }

### 3. 数据实体规划 TypeORM Entities (`patient-service`)
新增 `Knowledge` 领域模块：
- **`KnowledgeBaseEntity`**
  - 主键 ID、租户、组织标识索引。
  - 名称、说明栏位等常规数据。 
  - `@Entity('knowledge_bases')`
- **`DocumentEntity`**
  - `@Entity('documents')`
  - 与上方同理关联，`minioUrl` 非空约束保证。并由于 Prisma 结构或原库遗留问题可能需用 `@Column()` 忽略（如果原库无此字段），对于本工程而言，直接加好映射。

### 4. 协同开发侧与数据流 
**Step1: Gateway Document Proxy Controller 上传接口**
暴露：`@Post('api/v1/documents/kb/:kbId/documents')`
1. 依赖挂载 `@UseInterceptors(FileInterceptor('file'))` 从内存获取完整的 Multer File Context。
2. 调用新建服务层 `MinioProxyService.upload(...)` 落库。
3. 调用新建服务层 `HttpProxyService.forwardToAgent(...)` 用 Axios 发出至 Python 的请求。
4. 两者组装完成后组织消息交接令 `patientClient.send({cmd: 'document_create_sync'}, {...})`。

**Step2: Patient Service 控制器**
使用 `@MessagePattern` 监听：
- 获得结构化的 `TCP Payload`。
- 调用内部 `KnowledgeService`，向 TypeORM 调取 `.save()`。
- 将新增出来的 `Document` 主键记录状态回甩给网关。

## 限制与潜在扩展
该重网关设计令 `gateway` 职责边界泛化。长线发展中，可将此文件汇集和上传能力剥离为一个基础通用子系统（如专门的 `file-service` / `BFF` 层）分担主网桥并发性能消耗。但在目前的多服务小中台验证中具备最高的投产效能与安全隔离。
