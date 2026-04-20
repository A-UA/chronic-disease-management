import { IsEmail, IsNotEmpty, IsString, IsOptional, IsArray } from 'class-validator';

// ─── Gateway 层 HTTP 请求体 DTO（用于 class-validator 校验） ───

export class LoginDto {
  @IsEmail()
  username: string;

  @IsNotEmpty()
  @IsString()
  password: string;
}

export class RegisterDto {
  @IsEmail()
  email: string;

  @IsNotEmpty()
  @IsString()
  password: string;

  @IsString()
  @IsOptional()
  name?: string;
}

export class SelectOrgDto {
  @IsString()
  orgId: string;

  @IsString()
  selectionToken: string;
}

export class SwitchOrgDto {
  @IsString()
  orgId: string;
}

// ─── 通用分页 Query DTO ───

export class PaginationQueryDto {
  @IsOptional()
  skip?: string;

  @IsOptional()
  limit?: string;
}

// ─── Gateway 创建体 DTO ───

export class CreateUserDto {
  @IsEmail()
  email: string;

  @IsString()
  @IsOptional()
  password?: string;

  @IsString()
  @IsOptional()
  name?: string;

  @IsString()
  @IsOptional()
  orgId?: string;

  @IsArray()
  @IsOptional()
  roleIds?: string[];
}

export class UpdateUserDto {
  @IsEmail()
  @IsOptional()
  email?: string;

  @IsString()
  @IsOptional()
  password?: string;

  @IsString()
  @IsOptional()
  name?: string;
}

export class CreateTenantDto {
  @IsString()
  name: string;

  @IsString()
  slug: string;

  @IsString()
  @IsOptional()
  planType?: string;
}

export class UpdateTenantDto {
  @IsString()
  @IsOptional()
  name?: string;

  @IsString()
  @IsOptional()
  slug?: string;

  @IsString()
  @IsOptional()
  planType?: string;
}

export class CreateOrgDto {
  @IsString()
  name: string;

  @IsString()
  code: string;

  @IsString()
  tenantId: string;

  @IsString()
  @IsOptional()
  parentId?: string;
}

export class UpdateOrgDto {
  @IsString()
  @IsOptional()
  name?: string;

  @IsString()
  @IsOptional()
  code?: string;

  @IsString()
  @IsOptional()
  parentId?: string;

  @IsString()
  @IsOptional()
  status?: string;
}

export class CreateRoleDto {
  @IsString()
  name: string;

  @IsString()
  code: string;

  @IsString()
  @IsOptional()
  tenantId?: string;

  @IsString()
  @IsOptional()
  parentRoleId?: string;
}

export class UpdateRoleDto {
  @IsString()
  @IsOptional()
  name?: string;

  @IsString()
  @IsOptional()
  code?: string;

  @IsString()
  @IsOptional()
  parentRoleId?: string;
}

export class CreatePermissionDto {
  @IsString()
  name: string;

  @IsString()
  code: string;

  @IsString()
  resourceId: string;

  @IsString()
  actionId: string;
}

export class UpdatePermissionDto {
  @IsString()
  @IsOptional()
  name?: string;

  @IsString()
  @IsOptional()
  code?: string;

  @IsString()
  @IsOptional()
  resourceId?: string;

  @IsString()
  @IsOptional()
  actionId?: string;
}

export class CreateMenuDto {
  @IsString()
  name: string;

  @IsString()
  code: string;

  @IsString()
  @IsOptional()
  menuType?: string;

  @IsString()
  @IsOptional()
  path?: string;

  @IsString()
  @IsOptional()
  icon?: string;

  @IsString()
  @IsOptional()
  parentId?: string;

  @IsString()
  @IsOptional()
  tenantId?: string;

  @IsString()
  @IsOptional()
  permissionCode?: string;
}

export class UpdateMenuDto {
  @IsString()
  @IsOptional()
  name?: string;

  @IsString()
  @IsOptional()
  code?: string;

  @IsString()
  @IsOptional()
  menuType?: string;

  @IsString()
  @IsOptional()
  path?: string;

  @IsString()
  @IsOptional()
  icon?: string;

  @IsString()
  @IsOptional()
  parentId?: string;

  @IsString()
  @IsOptional()
  permissionCode?: string;
}

export class CreateKbDto {
  @IsString()
  name: string;

  @IsString()
  @IsOptional()
  description?: string;
}
