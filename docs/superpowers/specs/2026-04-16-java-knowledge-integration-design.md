# Java Backend Knowledge Base Integration (Sub-project 1)

## 背景 (Context)
系统需要闭环知识库 (Knowledge Base) 在前端与 Python AI Agent 直接的中转链路机制。对于这期双平台并行开发架构中的 Java 实现侧，主要负责前端的文件接收、多租户鉴权记录、源文件往 MinIO 的备份以及向 Python `agent` 容器透传用于高维分解的实体二进制流数据。

## 系统架构与职责 (Architecture)
整个生命周期属于 `patient-service` 领域。Java Gateway 提供分发保护：
1. **API 网关：** 接通去向 `patient-service` 的文件上传、状态拉取通信。
2. **MinIO OSS：** 在 Java 内建 `MinioService` 并挂载 `io.minio` 包处理原始文件的 OSS 托管（保证 `documents.minio_url` 数据库非空约束）。
3. **Agent 透传客户机：** 以 `RestTemplate` 将内存传来的文件再次 `POST` 转至内部 `http://localhost:8000/internal/knowledge/parse` 并等待响应切片统计数。
4. **PostgreSQL 实体存储：** 基于 `spring-boot-starter-data-jpa` 构建 `KnowledgeBase` 及 `Document` 相关的 CRUD Repository。

## 详细设计 (Detailed Design)

### 1. 外部依赖与基础设施修改
- **依赖追加:** 在 `backend-java/patient-service/pom.xml` 中引入 `io.minio:minio:8.5.7` (或其他最新稳定版)。
- **应用配置:** `patient-service/src/main/resources/application.yml` 添加 `minio.endpoint`, `minio.access-key`, `minio.secret-key` 并加载 Agent 中转主机变量 `agent.url`。
- **网关配置:** `gateway/src/main/resources/application.yml` 的 `patient-service` 拦截前缀增加 `/api/v1/kb/**` 与 `/api/v1/documents/**`。

### 2. 数据库实体层 (Entities)
设计以下 JPA Models 对应数据库原表：
* `KnowledgeBaseEntity` (@Table `knowledge_bases`)
  * 并自带 `tenantId`, `orgId` 控制租户查询越界。
  * `documentCount`, `chunkCount` 映射，使用 JPA 公式或者服务内汇总。
* `DocumentEntity` (@Table `documents`)
  * `tenantId`, `kbId`, `orgId` 外键关联。
  * `fileName`, `fileSize`, `fileType`, `minioUrl` (不得为 null)。
  * `status`: 具有 `pending`, `processing`, `completed`, `failed`。
  * `chunkCount`, `failedReason`。

### 3. 数据层与接口对接 (Controllers & Repositories)
**知识库表盘控制器 (`KnowledgeBaseController`)**:
- `GET /api/v1/kb` ：拉取本租户的列表。
- `POST /api/v1/kb` : 新建目录。
- `GET /api/v1/kb/{id}/stats` : 拉取本知识集统计。

**知识文档控制器 (`KnowledgeDocumentController`)**:
- `GET /api/v1/documents/kb/{kbId}/documents` : 查看本库挂载文档状态及列表。
- `POST /api/v1/documents/kb/{kbId}/documents` : 文件表单提交流。

### 4. 业务数据流 (Service workflow)
位于 `KnowledgeDocumentService.uploadDocument`：
1. 从 `IdentityContext` 取出当下租户与组织身份。验证该 `kb_id` 是否属本人组织。
2. 调度 `MinioService.uploadFile` 获取落盘的直链 `minioUrl`。
3. 新建一条 `DocumentEntity`（status="processing"）并写入 Repo。
4. 将原始表单使用 `RestTemplate` 包装请求打向 Agent（携带 `kb_id`）。
5. 阻塞或异步获取 Python 传回后的 `{chunk_count: ...}` 报文。
6. 最后更新当前这条 `DocumentEntity` 状态置为 `completed` ，并将 `chunkCount` 回填。刷新 RAG 知识库主干表面的总文件与切块数量约束。

## 局限与优化
鉴于大文件解析的耗时可能引发网关 `socket-timeout`，且当前业务未配置例如 RabbitMQ 一类的异步回调系统，此版本在 Agent 交互层使用阻塞 HTTP 请求。后续应当优化为此微服务使用 MQ 和 Agent 的 WebSocket/Hook 来解耦耗时的上传流水线。
