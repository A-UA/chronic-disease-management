import { Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import FormData from 'form-data';

@Injectable()
export class AgentProxyService {
  private agentUrl = process.env.AGENT_URL || 'http://localhost:8000';

  constructor(private readonly httpService: HttpService) {}

  async parseDocument(file: Express.Multer.File, kbId: string): Promise<number> {
    const formData = new FormData();
    formData.append('kb_id', kbId);
    formData.append('file', file.buffer, {
      filename: file.originalname,
      contentType: file.mimetype,
    });

    try {
      const response = await firstValueFrom(
        this.httpService.post(`${this.agentUrl}/internal/knowledge/parse`, formData, {
          headers: formData.getHeaders(),
        })
      ) as any;
      if (response.data && response.data.chunk_count !== undefined) {
        return response.data.chunk_count;
      }
    } catch (e: any) {
      console.error('Agent upload failed:', e.message);
    }
    return 0;
  }
}
