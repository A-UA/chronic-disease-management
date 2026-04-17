import { Controller, Get, Post, Put, Delete, Body, Param, Query, UseGuards, Inject } from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';
import { firstValueFrom } from 'rxjs';
import { AUTH_SERVICE } from '@cdm/shared';
import type { IdentityPayload } from '@cdm/shared';
import { PaginationQueryDto, CreateOrgDto, UpdateOrgDto } from '@cdm/shared';
import { JwtAuthGuard } from '../guards/jwt-auth.guard.js';
import { CurrentUser } from '../decorators/current-user.decorator.js';

@Controller('organizations')
@UseGuards(JwtAuthGuard)
export class OrganizationProxyController {
  constructor(@Inject(AUTH_SERVICE) private readonly authClient: ClientProxy) {}

  @Get()
  async list(@Query() query: PaginationQueryDto, @CurrentUser() user: IdentityPayload) {
    return firstValueFrom(this.authClient.send({ cmd: 'org_list' }, { ...query, identity: user }));
  }

  @Post()
  async create(@Body() body: CreateOrgDto, @CurrentUser() user: IdentityPayload) {
    return firstValueFrom(this.authClient.send({ cmd: 'org_create' }, { data: body, identity: user }));
  }

  @Put(':id')
  async update(@Param('id') id: string, @Body() body: UpdateOrgDto, @CurrentUser() user: IdentityPayload) {
    return firstValueFrom(this.authClient.send({ cmd: 'org_update' }, { id, data: body, identity: user }));
  }

  @Delete(':id')
  async delete(@Param('id') id: string, @CurrentUser() user: IdentityPayload) {
    return firstValueFrom(this.authClient.send({ cmd: 'org_delete' }, { id, identity: user }));
  }
}
