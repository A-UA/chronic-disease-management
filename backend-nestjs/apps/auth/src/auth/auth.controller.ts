import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { AuthService } from './auth.service.js';
import { IdentityPayload } from '@cdm/shared';

@Controller()
export class AuthController {
  constructor(private readonly authService: AuthService) {}

  @MessagePattern({ cmd: 'login' })
  async login(@Payload() data: { username: string; password: string }) {
    return this.authService.login(data.username, data.password);
  }

  @MessagePattern({ cmd: 'select_org' })
  async selectOrg(@Payload() data: { orgId: number; selectionToken: string }) {
    return this.authService.selectOrg(data.orgId, data.selectionToken);
  }

  @MessagePattern({ cmd: 'switch_org' })
  async switchOrg(@Payload() data: { identity: IdentityPayload; orgId: number }) {
    return this.authService.switchOrg(data.identity, data.orgId);
  }

  @MessagePattern({ cmd: 'my_orgs' })
  async myOrgs(@Payload() data: { identity: IdentityPayload }) {
    return this.authService.listMyOrgs(data.identity.userId);
  }

  @MessagePattern({ cmd: 'get_me' })
  async getMe(@Payload() data: { identity: IdentityPayload }) {
    return this.authService.getMe(data.identity);
  }

  @MessagePattern({ cmd: 'menu_tree' })
  async menuTree(@Payload() data: { identity: IdentityPayload }) {
    return this.authService.getMenuTree(data.identity);
  }
}
