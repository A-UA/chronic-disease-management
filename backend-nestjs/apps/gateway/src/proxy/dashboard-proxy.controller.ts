import { Controller, Get, Inject, UseGuards } from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';
import { firstValueFrom } from 'rxjs';
import {
  AUTH_SERVICE,
  PATIENT_SERVICE,
  AI_SERVICE,
  AUTH_DASHBOARD_STATS,
  PATIENT_DASHBOARD_STATS,
  AI_DASHBOARD_STATS,
} from '@cdm/shared';
import type {
  AuthDashboardStatsVO,
  PatientDashboardStatsVO,
  AiDashboardStatsVO,
  DashboardStatsVO,
} from '@cdm/shared';
import { JwtAuthGuard } from '../guards/jwt-auth.guard.js';

/**
 * Dashboard BFF 聚合控制器
 * 并行调用 auth / patient / ai 三个微服务，合并为前端所需的统一统计视图
 */
@Controller('dashboard')
@UseGuards(JwtAuthGuard)
export class DashboardProxyController {
  constructor(
    @Inject(AUTH_SERVICE) private readonly authClient: ClientProxy,
    @Inject(PATIENT_SERVICE) private readonly patientClient: ClientProxy,
    @Inject(AI_SERVICE) private readonly aiClient: ClientProxy,
  ) {}

  @Get('stats')
  async getStats(): Promise<DashboardStatsVO> {
    // 并行向三个微服务发送 TCP 请求
    const [authStats, patientStats, aiStats] = await Promise.all([
      firstValueFrom(
        this.authClient.send<AuthDashboardStatsVO>({ cmd: AUTH_DASHBOARD_STATS }, {}),
      ),
      firstValueFrom(
        this.patientClient.send<PatientDashboardStatsVO>({ cmd: PATIENT_DASHBOARD_STATS }, {}),
      ),
      firstValueFrom(
        this.aiClient.send<AiDashboardStatsVO>({ cmd: AI_DASHBOARD_STATS }, {}),
      ),
    ]);

    return {
      totalOrganizations: authStats.totalOrganizations,
      totalUsers: authStats.totalUsers,
      activeUsers24h: authStats.activeUsers24h,
      totalPatients: patientStats.totalPatients,
      totalConversations: aiStats.totalConversations,
      totalTokensUsed: aiStats.totalTokensUsed,
      recentFailedDocs: aiStats.recentFailedDocs,
      tokenUsageTrend: aiStats.tokenUsageTrend,
    };
  }
}
