const fs = require('fs');
const path = require('path');

const modules = [
  { mod: 'Tenant', entity: 'TenantEntity', dir: 'organization', prefix: 'tenant', route: 'tenants' },
  { mod: 'Organization', entity: 'OrganizationEntity', dir: 'organization', prefix: 'org', route: 'organizations' },
  { mod: 'User', entity: 'UserEntity', dir: 'user', prefix: 'user', route: 'users' },
  { mod: 'Role', entity: 'RoleEntity', dir: 'rbac', prefix: 'role', route: 'rbac/roles' },
  { mod: 'Permission', entity: 'PermissionEntity', dir: 'rbac', prefix: 'permission', route: 'rbac/permissions' },
  { mod: 'Menu', entity: 'MenuEntity', dir: 'menu', prefix: 'menu', route: 'menus' },
];

const backendDir = path.join(__dirname, 'apps/auth/src');
const gatewayDir = path.join(__dirname, 'apps/gateway/src');

function writeIfMiss(filePath, content) {
  if (!fs.existsSync(filePath)) {
    fs.writeFileSync(filePath, content);
    console.log('Created: ' + filePath);
  }
}

function entityFileName(entity) {
  if (entity === 'OrganizationEntity') return 'organization.entity.js';
  if (entity === 'TenantEntity') return 'tenant.entity.js';
  if (entity === 'UserEntity') return 'user.entity.js';
  if (entity === 'RoleEntity') return 'role.entity.js';
  if (entity === 'PermissionEntity') return 'permission.entity.js';
  if (entity === 'MenuEntity') return 'menu.entity.js';
  return '';
}

for (const m of modules) {
  // --- AUTH SERVICE ---
  const svcFile = path.join(backendDir, m.dir, m.prefix + '.service.ts');
  if (!fs.existsSync(svcFile) && m.mod !== 'Menu') { // skip menu.service.ts since it exists
    writeIfMiss(svcFile, "import { Injectable } from '@nestjs/common';\n" +
"import { InjectRepository } from '@nestjs/typeorm';\n" +
"import { Repository } from 'typeorm';\n" +
"import { " + m.entity + " } from './" + entityFileName(m.entity) + "';\n\n" +
"@Injectable()\n" +
"export class " + m.mod + "Service {\n" +
"  constructor(@InjectRepository(" + m.entity + ") private readonly repo: Repository<" + m.entity + ">) {}\n" +
"  async list(payload: any) {\n" +
"    const skip = Number(payload.skip) || 0;\n" +
"    const limit = Number(payload.limit) || 50;\n" +
"    const [items, total] = await this.repo.findAndCount({ skip, take: limit });\n" +
"    return { items, total };\n" +
"  }\n" +
"  async create(payload: any) {\n" +
"    const entity = this.repo.create(payload as any);\n" +
"    return this.repo.save(entity);\n" +
"  }\n" +
"  async update(id: string, data: any) {\n" +
"    await this.repo.update(id, data);\n" +
"    return this.repo.findOne({ where: { id } as any });\n" +
"  }\n" +
"  async delete(id: string) {\n" +
"    await this.repo.delete(id);\n" +
"    return { success: true };\n" +
"  }\n" +
"}\n");
  }

  // --- AUTH CONTROLLER ---
  const ctrlFile = path.join(backendDir, m.dir, m.prefix + '.controller.ts');
  writeIfMiss(ctrlFile, "import { Controller } from '@nestjs/common';\n" +
"import { MessagePattern, Payload } from '@nestjs/microservices';\n" +
"import { " + m.mod + "Service } from './" + m.prefix + ".service.js';\n\n" +
"@Controller()\n" +
"export class " + m.mod + "Controller {\n" +
"  constructor(private readonly service: " + m.mod + "Service) {}\n\n" +
"  @MessagePattern({ cmd: '" + m.prefix + "_list' })\n" +
"  list(@Payload() payload: any) { return this.service.list(payload); }\n\n" +
"  @MessagePattern({ cmd: '" + m.prefix + "_create' })\n" +
"  create(@Payload() payload: any) { return this.service.create(payload); }\n\n" +
"  @MessagePattern({ cmd: '" + m.prefix + "_update' })\n" +
"  update(@Payload() payload: any) { return this.service.update(payload.id, payload.data); }\n\n" +
"  @MessagePattern({ cmd: '" + m.prefix + "_delete' })\n" +
"  delete(@Payload() payload: any) { return this.service.delete(payload.id); }\n" +
"}\n");

  // --- GATEWAY PROXY ---
  const proxyFile = path.join(gatewayDir, 'proxy', m.prefix + '-proxy.controller.ts');
  writeIfMiss(proxyFile, "import { Controller, Get, Post, Put, Delete, Body, Param, Query, UseGuards, Inject } from '@nestjs/common';\n" +
"import { ClientProxy } from '@nestjs/microservices';\n" +
"import { firstValueFrom } from 'rxjs';\n" +
"import { AUTH_SERVICE, IdentityPayload } from '@cdm/shared';\n" +
"import { JwtAuthGuard } from '../guards/jwt-auth.guard.js';\n" +
"import { CurrentUser } from '../decorators/current-user.decorator.js';\n\n" +
"@Controller('" + m.route + "')\n" +
"@UseGuards(JwtAuthGuard)\n" +
"export class " + m.mod + "ProxyController {\n" +
"  constructor(@Inject(AUTH_SERVICE) private readonly authClient: ClientProxy) {}\n\n" +
"  @Get()\n" +
"  async list(@Query() query: any, @CurrentUser() user: IdentityPayload) {\n" +
"    const res = await firstValueFrom(this.authClient.send({ cmd: '" + m.prefix + "_list' }, { ...query, identity: user }));\n" +
"    if ('" + m.route + "' === 'menus' || '" + m.route + "' === 'rbac/permissions' || '" + m.route + "' === 'rbac/roles') {\n" +
"       if (res && res.items) return res.items;\n" +
"       return res;\n" +
"    }\n" +
"    // tenants, orgs, users list endpoints expect PaginatedResult { total, items }\n" +
"    return res;\n" +
"  }\n\n" +
"  @Post()\n" +
"  async create(@Body() body: any, @CurrentUser() user: IdentityPayload) {\n" +
"    return firstValueFrom(this.authClient.send({ cmd: '" + m.prefix + "_create' }, { ...body, identity: user }));\n" +
"  }\n\n" +
"  @Put(':id')\n" +
"  async update(@Param('id') id: string, @Body() body: any, @CurrentUser() user: IdentityPayload) {\n" +
"    return firstValueFrom(this.authClient.send({ cmd: '" + m.prefix + "_update' }, { id, data: body, identity: user }));\n" +
"  }\n\n" +
"  @Delete(':id')\n" +
"  async delete(@Param('id') id: string, @CurrentUser() user: IdentityPayload) {\n" +
"    return firstValueFrom(this.authClient.send({ cmd: '" + m.prefix + "_delete' }, { id, identity: user }));\n" +
"  }\n" +
"}\n");
}
